import os
import re
import json

import requests

from devstory import output

ARTIFACTORY_USER = os.environ.get("PLEX_ARTIFACTORY_USER")
ARTIFACTORY_TOKEN = os.environ.get("PLEX_ARTIFACTORY_TOKEN")


class ArtifactoryError(Exception):
  pass


class Artifactory:
  def __init__(self, url, user, token):
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
    return "{url}/{path}".format(url=self.url, path=path)

  def _get(self, url, params=None, headers=None):
    headers = headers or {}
    output.trace("GET " + url)
    response = requests.get(
      url, params=params, headers=headers, auth=(self.user, self.token)
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

  def _post(self, url, headers=None, data=None):
    if not headers:
      headers = {}
    output.trace("POST " + url)
    response = requests.post(
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
      msg = f"Response code: {code}. Error: {error}. "
      raise ArtifactoryError(msg)
    return response.content

  def _download_ref(self, artifactory_repo, repo, ref):
    # pylint: disable=W0612,W0613
    api = self._api("vcs/downloadCommit")
    # to avoid stale caches, first ask for the sha
    sha = self.get_ref_sha(repo, ref)
    req_url = f"{api}/{artifactory_repo}/{repo}/{sha}"
    response = self._get(req_url)
    return self._check_response(response), sha

  def get(self, endpoint, headers=None, params=None):
    return self._get(self._api(endpoint), headers=headers, params=params)

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
    api = self._api(f"vcs/{ref_kind}")
    req_url = f"{api}/{artifactory_repo}/{repo}"
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

    # The ref is not a tag or branch, but it's possible that it
    # is a SHA for which there is a branch or tag.
    # Searching them allows reporting if the hash is shortened
    # too much.
    # We are using a set here because we only want to count different
    # hashes. Otherwise, we trigger this error if a SHA is on multiple tags/branches.
    match = list(
      set(item["commitId"] for item in refs if item["commitId"].startswith(ref))
    )
    if len(match) > 1:
      raise ValueError("SHA matches multiple commits, try a longer one")

    if len(match) == 1:
      return match[0]

    if not self._is_hashy(ref):
      # the ref doesn't look like a SHA and we couldn't find it
      # in the tags or branches
      raise RuntimeError("Could not find ref " + ref)

    # The ref looks like a SHA so we assume it is.
    return ref

  _default = None

  def upload(
    self, repo, filename, sha256, sha1=None, md5=None
  ):  # pylint: disable=too-many-arguments
    url = self._url(
      "{repo}/{filename}".format(repo=repo, filename=os.path.basename(filename))
    )

    output.info(
      "Deploying {repo}/{filename}...".format(
        repo=repo, filename=os.path.basename(filename)
      )
    )

    # We add a lot of checksums here. Artifactory docs recommend sending
    # all of them to avoid any risk of collisions. and they are pretty
    # cheap anyway.
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

    # raise for any errors after we have checked 404
    resp.raise_for_status()

    output.info("{} deployed".format(os.path.basename(filename)))
    return True

  @staticmethod
  def default():
    if not Artifactory._default:
      Artifactory._default = Artifactory(
        "https://artifactory.plex.bz", ARTIFACTORY_USER, ARTIFACTORY_TOKEN
      )
    return Artifactory._default
