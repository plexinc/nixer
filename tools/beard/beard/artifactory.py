import os
import re
import json
import subprocess
import multiprocessing

from typing import Dict, List, Iterable

import requests

from os import getenv

from beard import output, tools, hashtools

ARTIFACTORY_SERVER = getenv("PLEX_ARTIFACTORY_SERVER", "https://artifactory.plex.bz")
ARTIFACTORY_USER = getenv("PLEX_ARTIFACTORY_USER")
ARTIFACTORY_TOKEN = getenv("PLEX_ARTIFACTORY_TOKEN")

DOWNLOAD_CHUNK_COUNT = getenv("PLEX_DOWNLOAD_CHUNK_COUNT", 8)


class ArtifactoryError(Exception):
  pass


mp_lock = multiprocessing.Lock()


class Artifactory(object):
  def __init__(
    self, url=ARTIFACTORY_SERVER, user=ARTIFACTORY_USER, token=ARTIFACTORY_TOKEN
  ):
    self.url = url
    self.user = user
    self.token = token
    if not user or not token:
      print(
        "Please set PLEX_ARTIFACTORY_USER and PLEX_ARTIFACTORY_TOKEN environment variables.",
        "If you don't have a personnal user and token, "
        "a shared token for conan-read user can be found in Engineering 1password vault",
        "(https://start.1password.com/open/i?a=T5WWMAWCJZF3TFJEIJPFAGRUMY&v=ktumzpavxtocrp6du67fqjif3a&i=pwfo26scmowispljme4qorfzt4&h=my.1password.com)",
      )
      raise Exception("MissingArtifactoryCredentials")

  def _api(self, endpoint):
    return "{0}/api/{1}".format(self.url, endpoint)

  def _url(self, path):
    if path[0] == "/":
      path = path[1:]

    return "{url}/{path}".format(url=self.url, path=path)

  def _get(self, url, params=None, headers=None):
    output.trace(f"GET {url} {params}")
    response = requests.get(
      url, auth=(self.user, self.token), params=params, headers=headers
    )
    self._dbg_response(response)
    return response

  def _put(self, url, headers=None, data=None):
    if not headers:
      headers = {}
    output.trace("PUT " + url)
    response = requests.put(
      url, auth=(self.user, self.token), headers=headers, data=data
    )

    self._dbg_response(response, header_only=False)
    return response

  @staticmethod
  def _dbg_response(response, header_only=True):
    ostr = "\n".join(["{}: {}".format(k, v) for k, v in response.headers.items()])
    output.trace(
      "\n\nHTTP/1.1 {}\n{}\n\n{}".format(
        response.status_code, ostr, response.text if not header_only else ""
      )
    )

  @staticmethod
  def _check_response(response):
    # pylint: disable=W0612
    ok_code = 200
    code = response.status_code
    if code != ok_code:
      data = json.loads(response.content)
      error = data["errors"]
      msg = "Response code: {code}. Error: {error}. ".format(**locals())
      raise ArtifactoryError(msg)
    return response.content

  def _download_ref(self, artifactory_repo, repo, ref):
    # pylint: disable=W0612,W0613
    api = self._api("vcs/downloadCommit")
    # to avoid stale caches, first ask for the sha
    sha = self.get_ref_sha(repo, ref)
    req_url = "{api}/{artifactory_repo}/{repo}/{sha}".format(**locals())
    response = self._get(req_url)
    return self._check_response(response), sha

  def download_ref(self, repo, ref):
    """
        Downloads a github ref as a tarball.

          :param repo: The repo to download from, e.g. plexinc/plex-build-profiles
          :param ref: Branch, tag or SHA
          :returns: The tarball data
        """
    return self._download_ref("github", repo, ref)

  def _get_ref_info(self, artifactory_repo, repo, ref_kind):
    # pylint: disable=W0612,W0613
    api = self._api("vcs/{0}".format(ref_kind))
    req_url = "{api}/{artifactory_repo}/{repo}".format(**locals())
    response = self._get(req_url)
    return self._check_response(response)

  def get_branches(self, repo):
    return json.loads(self._get_ref_info("github", repo, "branches"))

  def get_tags(self, repo):
    return json.loads(self._get_ref_info("github", repo, "tags"))

  @staticmethod
  def _is_hashy(ref):
    """:returns: True if the ref could be a valid hash"""
    return re.match(r"[0-9a-f]{5,40}", ref) is not None

  def get_ref_sha(self, repo, ref):
    refs = self.get_branches(repo) + self.get_tags(repo)
    match = next((item["commitId"] for item in refs if item["name"] == ref), None)
    if match:
      return match
    else:
      # The ref is not a tag or branch, but it's possible that it
      # is a SHA for which there is a branch or tag.
      # Searching them allows reporting if the hash is shortened
      # too much.
      match = [item["commitId"] for item in refs if item["commitId"].startswith(ref)]
      if len(match) > 1:
        raise ValueError("SHA matches multiple commits, try a longer one")
      elif len(match) == 1:
        return match[0]

    if not self._is_hashy(ref):
      # the ref doesn't look like a SHA and we couldn't find it
      # in the tags or branches
      raise RuntimeError("Could not find ref " + ref)
    # The ref looks like a SHA so we assume it is.
    return ref

  _default = None

  def upload(
    self, repo, filename, sha256=None, sha1=None, md5=None, properties=None
  ):  # pylint: disable=too-many-arguments
    props_str = ""
    if properties:
      props = []
      for key, value in properties.items():
        props += [f"{key}={value}"]
      props_str = ";" + ";".join(props)

    url = self._url(f"{repo}/{os.path.basename(filename)}{props_str}")
    output.info(f"Deploying {repo}/{os.path.basename(filename)}...")

    # We add a lot of checksums here. Artifactory docs recommend sending
    # all of them to avoid any risk of collisions. and they are pretty
    # cheap anyway.
    sha256 = sha256 or tools.sha256sum(filename)
    headers = {"x-checksum-sha256": sha256}
    if sha1:
      headers["x-checksum-sha1"] = sha1
    if md5:
      headers["x-checksum-md5"] = md5

    # We first call PUT with the header x-checksum-deploy set. That call
    # will copy the file if it already exists so no uploading is needed.
    # If this call returns 404 it means we need to upload the whole file.
    resp = self._put(url, headers={**headers, "x-checksum-deploy": "True"})

    if resp.status_code == 404:
      output.info("Uploading file...")
      with open(filename, "rb") as infile:
        try:
          uploadr = self._put(url, headers=headers, data=infile)
        except requests.exceptions.ChunkedEncodingError as exc:
          output.error("Failed to upload - wrong auth? " + str(exc))
          return False
        uploadr.raise_for_status()
    else:
      # raise for any errors after we have checked 404
      resp.raise_for_status()

    output.info("{} deployed".format(os.path.basename(filename)))
    return True

  def download_artifact(self, artifact, local_root):
    """This function takes a artifact map that you get from a search
        or a listing and then downloads that artifact
        to the local_root"""
    local_dir = os.path.join(
      local_root,
      artifact["properties"]["version"],
      artifact["properties"]["distribution"],
    )
    os.makedirs(local_dir, exist_ok=True)

    self.fetch_file(
      f"{self.url}/{artifact['path']}",
      os.path.join(local_dir, artifact["name"]),
      expected_sha256=artifact["sha256"],
    )

  def search(self, properties: Dict[str, str]) -> Iterable[str]:
    resp = self._get(self._api("search/prop"), params=properties).json()
    info_urls = (item["uri"] for item in resp["results"])
    for info_url in info_urls:
      yield self._get(info_url).json()["downloadUri"]

  def _file_name_from_url(self, url: str) -> str:
    return url.split("/")[-1]

  def fetch_file(self, url: str, path=None, expected_sha256=None):
    if not path:
      filename = self._file_name_from_url(url)
    else:
      filename = path

    with mp_lock:
      print(f"{'Downloading:':14} {filename}")

    res = subprocess.run(
      [
        "curl",
        "--user",
        f"{ARTIFACTORY_USER}:{ARTIFACTORY_TOKEN}",
        "--silent",
        "-o",
        filename,
        url,
      ]
    )
    res.check_returncode()

    if expected_sha256:
      if not hashtools.compare_file_hash(filename, expected_sha256):
        print(f"{'Mismatched hash:':14} {filename}")
        return None

    with mp_lock:
      print(f"{'Finished:':14} {filename}")

    return filename

  def fetch_all(
    self, properties: Dict[str, str], output_dir=".", max_processes=4
  ) -> List[str]:
    with tools.chdir(output_dir):
      pool = multiprocessing.Pool(processes=max_processes)
      filenames = pool.map(self.fetch_file, self.search(properties))
    return filenames

  def promote(
    self,
    project,
    version,
    status=None,
    source=None,
    target=None,
    comment=None,
    ci_user=None,
  ):
    url = self._api(f"build/promote/{project}/{version}")
    data = {
      "status": status,
      "comment": comment,
      "sourceRepo": source,
      "targetRepo": target,
      "ciUser": ci_user,
    }

    rel = self._post(url, jsond=data)
    self._check_response(rel)
    return True

  def uri_for_sha256(self, checksum, repos):
    url = self._api("search/checksum")
    response = self._get(url, params={"sha256": checksum, "repos": repos})
    json_data = self._check_response(response)
    return json.loads(json_data)["results"][0]["uri"]

  def properties_for_path(self, path):
    url = self._api(f"storage/{path}")
    response = self._get(url, params={"properties": ""})
    json_data = self._check_response(response)
    return json.loads(json_data)["properties"]

  def properties_for_sha256(self, checksum, repos):
    url = self._api("search/checksum")
    response = self._get(
      url,
      params={"sha256": checksum, "repos": repos},
      headers={"X-Result-Detail": "properties,info"},
    )
    json_data = self._check_response(response)
    results = json.loads(json_data)["results"][0]
    properties = results["properties"]
    properties["uri"] = results["uri"]
    properties["path"] = f"{results['repo']}/{results['path']}"
    return properties

  def build_info(self, project, version):
    url = self._api(f"build/{project}/{version}")
    response = self._get(url)
    try:
      json_data = self._check_response(response)
      return json.loads(json_data)
    except ArtifactoryError:
      output.error(f"Unable to load build info for {project}/{version}")
      output.error("Exception info follows")
      import traceback

      traceback.print_exc()
      output.error("End of exception info")
      return None

  @staticmethod
  def default():
    if not Artifactory._default:
      Artifactory._default = Artifactory(
        ARTIFACTORY_SERVER, ARTIFACTORY_USER, ARTIFACTORY_TOKEN
      )
    return Artifactory._default
