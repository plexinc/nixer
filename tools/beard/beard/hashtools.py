import hashlib

def _calculate_hash(filepath: str, algo: str):
  with open(filepath, 'rb') as fh:
    m = hashlib.new(algo)
    while True:
      data = fh.read(8192)
      if not data:
        break
      m.update(data)
    return m.hexdigest()

def sha1_from_file(filepath: str):
  return _calculate_hash(filepath, "sha1")

def sha256_from_file(filepath: str):
  return _calculate_hash(filepath, "sha256")

def md5_from_file(filepath: str):
  return _calculate_hash(filepath, "md5")

def compare_file_hash(filepath: str, expected_hash: str, algo="sha256"):
  return expected_hash == _calculate_hash(filepath, algo)
