from devstory.common import using_new_toolchain

if using_new_toolchain():
  from .v2 import do_clion
else:
  from .v1 import do_clion
