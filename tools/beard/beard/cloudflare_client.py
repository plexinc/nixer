#! /usr/bin/env python3
import platform
import tarfile
import requests
import shutil
import subprocess as sp

from os import getenv, chmod
from pathlib import Path
from urllib.parse import urlparse

import appdirs
import requests

from beard import tools

artifactory_user = getenv("PLEX_ARTIFACTORY_USER")
artifactory_token = getenv("PLEX_ARTIFACTORY_TOKEN")
artifactory = "artifactory.plex.bz/artifactory"


def cloudflared_prog_name():
  ext = "" if platform.system() != "Windows" else ".exe"
  return f"cloudflared{ext}"


def fetch_cloudflared(output_dir, verbose=False):
  if not artifactory_user or not artifactory_token:
    print(
      "Please set PLEX_ARTIFACTORY_USER and PLEX_ARTIFACTORY_TOKEN environment variables.",
      "If you don't have a personnal user and token, "
      "a shared token for conan-read user can be found in Engineering 1password vault",
      "(https://start.1password.com/open/i?a=T5WWMAWCJZF3TFJEIJPFAGRUMY&v=ktumzpavxtocrp6du67fqjif3a&i=pwfo26scmowispljme4qorfzt4&h=my.1password.com)",
    )
    raise Exception("MissingArtifactoryCredentials")
  output_dir = Path(output_dir)
  auth = artifactory_user, artifactory_token
  filename = f"cloudflared-stable-{platform.system().lower()}-amd64.tgz"
  url = f"https://{artifactory}/third-party-sources/cloudflared/{filename}"

  if verbose:
    print(f"Downloading {url}")

  data = requests.get(url, auth=auth, stream=True).raw
  tarball = Path("cloudflared.tgz")
  prog_name = cloudflared_prog_name()

  if verbose:
    print("Extracting...")
  with tools.chdir(output_dir):
    with tarball.open("wb") as tb:
      shutil.copyfileobj(data, tb)
    with tarfile.open(tarball, "r") as tfp:
      tfp.extractall()
    if verbose:
      print("Performing cleanup.")
    if tarball.exists():
      tarball.unlink()
    if platform.system() == "Windows":
      shutil.move("cloudflared", "cloudflared.exe")
    else:
      chmod(prog_name, 0o0744)
  if verbose:
    print(f"{prog_name} is ready to use.")
  return prog_name


class CloudflareAccessClient:
  def __init__(self):
    self.beard_data_dir = Path(appdirs.user_data_dir()) / "beard"
    if not self.beard_data_dir.exists():
      self.beard_data_dir.mkdir(parents=True, exist_ok=True)
    self.cli = self.beard_data_dir / cloudflared_prog_name()
    self._ensure_cli()

  def _ensure_cli(self):
    if not self.cli.exists():
      fetch_cloudflared(output_dir=self.beard_data_dir)

  def _ask_cli(self, *args):
    self._ensure_cli()
    proc = sp.run([str(self.cli), *args], stdout=sp.PIPE)
    proc.check_returncode()
    return proc.stdout.decode()

  def get_token(self, url: str):
    # get only the scheme+netloc parts, i.e.
    # https://ci.plex.bz/some/weird/api?xyz -> https://ci.plex.bz
    url_root = urlparse(url)
    url_root = f"{url_root.scheme}://{url_root.netloc}"
    # `access login` returns either a cached token or a new one after
    # opening a browser window.
    cli_result = self._ask_cli("access", "login", url_root)
    # transform into a list of lines without the empty ones
    cli_result = list(filter(None, cli_result.split("\n")))
    # janky output requires janky parsing ...
    success_msg = "Successfully fetched your token:"
    token = cli_result[cli_result.index(success_msg) + 1]
    return token

  def _req_wrapper(self, req_func, url, headers=None, *args, **kwargs):
    headers = headers or {}
    headers["cf-access-token"] = self.get_token(url)
    req_func = getattr(requests, req_func)
    return req_func(url=url, headers=headers, *args, **kwargs)

  def get(self, url, headers=None, *args, **kwargs):
    return self._req_wrapper("get", url, headers, *args, **kwargs)

  def put(self, url, headers=None, *args, **kwargs):
    return self._req_wrapper("put", url, headers, *args, **kwargs)

  def post(self, url, headers=None, *args, **kwargs):
    return self._req_wrapper("post", url, headers, *args, **kwargs)

  def delete(self, url, headers=None, *args, **kwargs):
    return self._req_wrapper("delete", url, headers, *args, **kwargs)

  def head(self, url, headers=None, *args, **kwargs):
    return self._req_wrapper("head", url, headers, *args, **kwargs)


if __name__ == "__main__":
  fetch_cloudflared(".", verbose=True)
