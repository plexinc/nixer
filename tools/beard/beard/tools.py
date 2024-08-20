import os
import hashlib

from contextlib import contextmanager


@contextmanager
def chdir(dirname):
  try:
    current_dir = os.getcwd()
    os.chdir(dirname)
    yield
  finally:
    os.chdir(current_dir)


def sha256sum(filename, extra_data: str = None):
  h = hashlib.sha256()
  b = bytearray(1024 * h.block_size)
  mv = memoryview(b)
  with open(filename, "rb", buffering=0) as f:
    for n in iter(lambda: f.readinto(mv), 0):
      h.update(mv[:n])
  if extra_data:
    h.update(extra_data.encode())
  return h.hexdigest()
