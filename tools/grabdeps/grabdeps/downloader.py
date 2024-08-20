"""
urllib-based downloader (mostly taken from conan_init.py)
"""
import urllib.request
import hashlib
import os
import certifi

from urllib.request import Request, urlopen
from typing import IO
from zlib import decompress, MAX_WBITS
from pathlib import Path

from .utils import print_progressbar, no_cursor, sha256sum
from .cache import Cache
from .filelock import SoftFileLock


class Downloader:
  def __init__(self, base_url: str, cache: Cache):
    self.cache = cache
    self.base_url = base_url

  def _get(self, path: str):
    if path[0] == "/":
      path = path[1:]
    url = f"{self.base_url}/{path}"
    req = Request(url)
    req.add_header("Accept-Encoding", "gzip")
    return urlopen(req, cafile=certifi.where())

  def get(self, path: str):
    response = self._get(path)
    content = response.read()
    return content.decode()

  def get_out_path(self, url: str) -> Path:
    parts = url.split("/")
    dir_path = self.cache.root / parts[-2]
    return dir_path / parts[-1]

  def head(self, path: str):
    url = f"{self.base_url}/{path}"
    req = Request(url, method="HEAD")
    try:
      response = urlopen(req, cafile=certifi.where())
    except:
      return False
    return response.getcode() == 200

  def download(self, url: str, out_filename=None):
    rt_sha = self.get(url + ".sha256")

    if not out_filename:
      out_filename = self.get_out_path(url)
    else:
      out_filename = self.cache.root / out_filename

    out_filename.parent.mkdir(parents=True, exist_ok=True)

    if out_filename.exists():
      local_sha = sha256sum(out_filename)
      if local_sha == rt_sha:
        print(f"  - using cached {out_filename.name}")
        self.cache.access_file(out_filename)
        return
      else:
        print(f"Cached {out_filename.name} is corrupted, redownloading.")
        os.remove(out_filename)

    def _download(out_fp: IO) -> str:
      response = self._get(url)
      compressed = bool(
        response.headers.get("Content-Encoding")
      )  # gzip is the only Content-Encoding

      def _decompress_if_needed(chunk: bytes):
        if compressed:
          return decompress(chunk, MAX_WBITS | 16)
        return chunk

      total_size = int(response.headers.get("Content-Length").strip())
      chunk_size = 64 * 1024
      bytes_read = 0
      hash_alg = hashlib.sha256()

      with no_cursor():
        while True:
          chunk = response.read(chunk_size)
          bytes_read += len(chunk)
          if not chunk:
            break
          dchunk = _decompress_if_needed(chunk)
          out_fp.write(dchunk)
          hash_alg.update(dchunk)
          print_progressbar(bytes_read, total_size)
        print()
      return hash_alg.hexdigest()

    write_success = False
    try:
      with out_filename.open("wb") as out:
        dl_sha = _download(out)
      self.cache.access_file(out_filename)
      if dl_sha == rt_sha:
        write_success = True
      else:
        print(
          f"ERROR: downloaded file hash {dl_sha} != {rt_sha} (the latter value is reported by Artifactory)"
        )
    except:
      import traceback

      traceback.print_last()
    finally:
      if not write_success:
        print(f"There was an error while downloading {out_filename.name}")
        print("Removing corrupted file.")
        try:
          os.remove(out_filename)
        except:
          pass
        print(f"FATAL ERROR: Failed to download {out_filename.name}")
