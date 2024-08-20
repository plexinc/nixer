#! /usr/bin/env python3.6
import json

class PackageInfo(object):
  reference = None

  def __init__(self, info):
    self.packagedata = {}
    self.recipedata = {}

    if isinstance(info, str):
      self.reference = info
    elif isinstance(info, dict):
      self.recipedata = info["recipe"]
      self.reference = self.recipedata["id"]
      if len(info["packages"]) > 0:
        self.packagedata = info["packages"]

  @property
  def name(self):
    return self.reference.split("/")[0]

  @property
  def version(self):
    return self.short_ref.split("/")[1]

  @property
  def success(self):
    recipeok = self.recipedata.get("error", None) is None
    packageok = all([data.get("error", None) is None for data in self.packagedata])

    return recipeok and packageok

  @property
  def built(self):
    return any([data.get("built", False) for data in self.packagedata])

  @property
  def package_id(self):
    return [data.get("id") for data in self.packagedata if "id" in data]

  @property
  def short_ref(self):
    return self.reference.split("@")[0]

  def __repr__(self):
    return f"<PackageInfo: {self.short_ref}, success: {self.success}, built: {self.built}>"

  def __str__(self):
    return self.short_ref

def parse_buildinfo(path):
  jsondata = None

  with open(path, "r") as jsonfile:
    jsondata = json.load(jsonfile)

  installed = []
  built = []
  failed = []

  for pkg in jsondata["installed"]:
    pack = PackageInfo(pkg)
    if pack.success:
      if pack.built:
        built.append(pack)
      else:
        installed.append(pack)
    else:
      failed.append(pack)

  return {"installed": installed, "built": built, "failed": failed}

if __name__ == '__main__':
  from argparse import ArgumentParser
  from pprint import pprint
  parser = ArgumentParser()
  parser.add_argument("json_file", default="buildinfo.json",
                      help="conan buildinfo json file")
  args = parser.parse_args()
  binfo = parse_buildinfo(args.json_file)
  pprint(binfo, indent=2)
