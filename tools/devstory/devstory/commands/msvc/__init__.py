from devstory.common import DsConfig, using_new_toolchain

plex_dev = DsConfig.load_plex_dev()
multiconfig = (
  plex_dev.load_setting("compatibility", "msvc", "multiconfig") == "multiconfig"
)

if using_new_toolchain():
  from .newtoolchain import do_msvc
elif multiconfig:
  from .multiconfig import do_msvc
else:
  from .singleconfig import do_msvc
