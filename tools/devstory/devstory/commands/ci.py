import json
import re
from getpass import getpass, getuser
from urllib.parse import unquote_plus

from beard.cloudflare_client import CloudflareAccessClient

from devstory import output
from devstory.common import CommandResult, DsConfig, ds_halo, get_terminal_link

cf_client = CloudflareAccessClient()

JENKINS_URL = "https://ci.plex.bz"


class JenkinsClient:
  def __init__(self):
    self.cf = CloudflareAccessClient()
    self.crumb = None

  def get(self, api, params=None, auth=None):
    auth = auth or _get_auth()
    output.trace(f"GET {api}")
    return self.cf.get(f"{JENKINS_URL}{api}", params=params, auth=auth)

  def post(self, api, params=None, auth=None):
    auth = auth or _get_auth()
    headers = None  # { "Jenkins-Crumb": self._get_crumb() }
    output.trace(f"POST {api}")
    return self.cf.post(
      f"{JENKINS_URL}{api}", params=params, auth=auth, headers=headers
    )

  def _get_crumb(self):
    if self.crumb:
      return self.crumb
    api = '/crumbIssuer/api/xml?xpath=concat(//crumbRequestField,":",//crumb)'
    crumb = self.get(api).text.split(":")[1]
    return crumb


jenkins = JenkinsClient()


def _get_auth():
  config = DsConfig()
  user = config.load_setting("ci", "user")
  if not user:
    user = getuser()
    user = input("Auth for CI API.\nUsername [default: {}]: ".format(user))
  token = config.load_setting("ci", "token")
  if not token:
    token = getpass("Token: ")
  if not user or not token:
    output.error("Need a username and token!")
    return None
  config.save_setting("ci", "user", user)
  config.save_setting("ci", "token", token)
  return user, token


def _get_crumb():
  pass


def _get_org_repo():
  from subprocess import PIPE, run

  res = run(["git", "remote", "get-url", "origin"], stdout=PIPE, check=True)
  url = res.stdout.decode("UTF-8").strip()
  if url.startswith("git@github.com"):
    components = url.split(":")[1].split("/")
  else:
    components = url.split("/")[-2:]
  if components[-1].endswith(".git"):
    components[-1] = components[-1][:-4]
  return components


def _get_current_branch():
  from subprocess import PIPE, run

  res = run(["git", "rev-parse", "--abbrev-ref", "HEAD"], stdout=PIPE, check=True)
  branch = res.stdout.decode("UTF-8")
  return branch.strip()


def _current_project_and_branch(project, branch):
  from subprocess import CalledProcessError

  if not project:
    try:
      org, project = _get_org_repo()
    except CalledProcessError:
      output.error(
        "Git commands failed - maybe you need to specify project and branch?"
      )
      return None, None

    if not org == "plexinc":
      output.error("This is not a plexinc repo - can't build in the CI")
      return None, None

  if not branch:
    try:
      branch = _get_current_branch()
    except CalledProcessError:
      output.error(
        "Failed to get branch from git. Maybe try specify on the command line?"
      )
      return None, None

  return project, branch


def _get_pipelines(refresh_cache=False):
  def _get_pipelines_api():
    params = {
      "q": "type:pipeline;excludedFromFlattening:jenkins.branch.MultiBranchProject,hudson.matrix.MatrixProject,com.cloudbees.hudson.plugins.folder.AbstractFolder",
      "tree": "pipelineFolderNames,displayName",
    }

    auth = _get_auth()
    if not auth:
      return None

    with ds_halo("Getting pipelines..."):
      response = jenkins.get("/blue/rest/search", params=params, auth=auth)
      response.raise_for_status()

      pipelines = {}

      try:
        resp_json = response.json()
        for folder in resp_json:
          for pipe in folder["pipelineFolderNames"]:
            pipelines[pipe] = folder["displayName"].replace(" ", "%20")
      except json.decoder.JSONDecodeError as exc:
        output.error("Error while parsing json response. Displaying contents:")
        print(response.content)
        raise exc

      return pipelines

  cfg = DsConfig()
  pipelines = cfg.load_setting("ci", "pipelines")
  if refresh_cache or pipelines is None:
    output.info("Refreshing pipeline cache")
    pipelines = _get_pipelines_api()
    cfg.save_setting(
      "ci",
      "pipelines",
      # replacing % to avoid ConfigParser interpolation
      json.dumps(pipelines).replace("%", r"%%"),
    )
  else:
    pipelines = json.loads(pipelines)
  return pipelines


def _oldci_to_blueocean(url):
  rgx = (
    r"ci.plex.bz/job/(?P<team>.+)/job/(?P<job>.+)/job/(?P<branch>.+)/(?P<buildnum>\d+)/"
  )
  parts = re.search(rgx, url).groupdict()
  bo_root = "https://ci.plex.bz/blue/organizations/jenkins"
  link = f"{bo_root}/{parts['team']}%2F{parts['job']}/detail/{parts['branch']}/{parts['buildnum']}/"
  link = link.replace("%252F", "%2F")  # don't ask...
  return link


def _run_build(buildstr):
  auth = _get_auth()
  if not auth:
    return None

  queue_item_url = None
  # first we try to build it without parameters.
  response = jenkins.post(f"{buildstr}/build", auth=auth)
  if response.status_code == 400:
    response = jenkins.post(f"{buildstr}/buildWithParameters", auth=auth)
    if response.status_code != 201:
      # ok now we really failed
      output.error(f"Failed to build with parameters: {response.status_code}")
      return None

    queue_item_url = response.headers.get("Location")
    return queue_item_url

  if response.status_code != 201:
    output.error(
      f"Failed to start build with the normal build command: {response.status_code}"
    )
    return None

  queue_item_url = response.headers.get("Location")
  return queue_item_url


def _check_queue_item(queue_item):
  queue_item = queue_item.replace(JENKINS_URL, "")
  tries = 0
  while tries < 5:
    url = f"{queue_item}/api/json"
    response = jenkins.get(url, auth=_get_auth(), params={"tree": "executable[url]"})
    if response.status_code == 200:
      jdata = response.json()
      if "executable" in jdata:
        try:
          exe = jdata["executable"]
          if "url" in exe:
            return exe["url"]
        except KeyError:
          pass

    tries = tries + 1
    # sleep for a bit and try again
    from time import sleep

    sleep(2)

  output.warn("Timed out while waiting for job to start... (not an error)")
  return None


def do_ci_build(project, branch):
  pipelines = _get_pipelines()

  if not pipelines:
    output.error("Couldn't fetch pipelines from CI")
    return CommandResult.Error

  with ds_halo("Getting CI configuration..."):
    project, branch = _current_project_and_branch(project, branch)
    if not project or not branch:
      return CommandResult.Error

  plexdev = DsConfig.load_plex_dev()
  ci_folder = plexdev.load_setting("ci", "folder")
  if ci_folder is None:
    if project not in pipelines:
      pipelines = _get_pipelines(refresh_cache=True)

    if project not in pipelines:
      output.error(f"Failed to find project {project} in the CI")
      return CommandResult.Error

    ci_folder = f"{pipelines[project]}/{project}"

  folder, project_name = ci_folder.split("/")
  buildstr = f"/job/{folder}/job/{project_name}/job/{branch.replace('/', '%2F')}"

  buildname = unquote_plus(f"{folder}/{project_name}/{branch}", "utf-8")

  with ds_halo(f"Asking CI to build {buildname}"):
    queue_item = _run_build(buildstr)
    if not queue_item:
      return CommandResult.Error

  job_url = None
  with ds_halo(f"Waiting for {buildname} to start..."):
    job_url = _check_queue_item(queue_item)

  if job_url:
    output.info(f"Job successfully started: {get_terminal_link(job_url)}")
    output.info(f"Blue Ocean link: {get_terminal_link(_oldci_to_blueocean(job_url))}")

  return CommandResult.Success
