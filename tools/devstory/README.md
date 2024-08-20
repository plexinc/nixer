# devstory

`devstory` is a set of commands designed to be a useful companion for our
intended developer workflows (stories). If the tool is standing in your way
or you need to bend it too much to achieve what you want then file a bug report.

This tool will detect which plex repo you are in and will take extra steps
to accomodate that project.

# Installation

First make sure you have artifactory added as a PIP source: https://infra-docs.plex.bz/build-tools-docs/pms/python/#install-the-plex-pypi-repository

Then: `pip install devstory`


# How to use

`ds --help` to list all available commands.

A typical development flow should look like this:

```
$ mkdir build && cd build
$ ds bootstrap
$ ds install
$ ds dev
```

# FAQ

TBD

# Development

In the cloned repo, use

```
pip3 install -e .
```

`-e` means "editable", i.e. the package is symlinked to your repo so you can make
live changes to it.

