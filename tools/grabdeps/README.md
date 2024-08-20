# grabdeps

## What is this?

`grabdeps` grew from the frustration over using conan on developer machines. Conan proved great at building the dependencies, but for fetching them at the end users it turned out to be a heavy and unreliable dependency on the build (not to mention Python itself, though we still depend on that). 

`grabdeps` solves this by fetching zstandard-compressed tarballs that are produced during the plex-conan build for each configuration. Since then, we started to use multiple tarballs and that is how the `gd2` entry point emerged which reads the requirements from a yaml file. In the end, grabdeps needs to compute URLs for tarballs. Due to different requirements between projects, there are many different ways to specify the configurations which is detailed below. 

## Using gd2 and deps.yaml

The new `gd2` entry point allow specifying multiple dependencies and their configs in a
deps.yaml file. An example of that is the following

```yml
!version: 1.0

plex-media-server:
  sha: 545806ed772f5db75ce77958dad7e1a8ca973d4b

web-client:
  sha: 5153655df25232fa40c110fccffa5b05f2562755
  configs:
    - noarch
```

`gd2` takes a list of configs as optional positional arguments. The `configs` key under each
dependency takes precedence to what is passed on the command line. For example,

```
$ gd2 x86_64-linux-musl
```

will download the `plex-media-server` deps for the given sha in the `x86_64-linux-musl` config,
and the web-client will be in the `noarch` config (no matter what is passed on the CLI).

It is also possible to omit the configuration from the command line and simply run

```
$ gd2
```

In this case, you will have to list all valid configurations in deps.yml, e.g.:

```yml
!version: 1.0

android-client:
  sha: 545806ed772f5db75ce77958dad7e1a8ca973d4b
  configs:
    - aarch64-linux-android21
    - arm-linux-androideabi21
    - i686-linux-android21
    - x86_64-linux-android21

pms-nano:
  sha: 5153655df25232fa40c110fccffa5b05f2562755
  configs:
    - aarch64-linux-android21
    - arm-linux-androideabi21
    - i686-linux-android21
    - x86_64-linux-android21
```

### Conditional deps for variants

We support conditional dependencies for variants:

```yml
!version: 1.0

web-client:
  sha: fd1af68ffb52c86f401059931f05303bb5939cac
  for-variant: desktop

web-tv-client:
  sha: 363bac744cb54ff0d94684505a2b577325aa7096
  for-variant: pmp

pms-nano:
  sha: f667a49bcdf408e575fe1c024df946eb329b6ca5

plex-desktop:
  sha: 41018407907d69359c6ad6d1799342345cfb8138
```

If `for-variant` is specified, the command line option `--variant` will be compared against it and
the tarball will only be pulled if they match. For example:

```
$ gd2 --variant pmp
```

will pull the following:

  - `web-tv-client`
  - `pms-nano`
  - `plex-desktop`

(but not `web-client` because the variant is different there). The items that don't have a
`for-variant` filter will always be pulled.

### Naming scheme for tarballs

Dependencies may specify a naming scheme:

```yml
!version: 1.1

plex-desktop:
  sha: 41018407907d69359c6ad6d1799342345cfb8138
  scheme: "{variant}-{config}"
```

Grabdeps will take the python-style format string specified here and use it to calculate the filename
(without extension). The default scheme is `{config}`. Currently, only `config` and `variant` are
supported.

### Controlling the output directory layout

```yml
!version: 1.2

web-client:
  sha: 41018407907d69359c6ad6d1799342345cfb8138
  directory: WebClient.bundle
```

By default, tarballs are extracted to `output_dir / dependency / configuration`. The `directory`
property allows setting a top-level directory structure inside the default extraction path, i.e.
it becomes `output_dir / dependency / configuration / WebClient.bundle` in the above example.

### Remapping configuration names

```yml
plex-relay:
  sha: 914f72559768e8f09eecb7bb6ccf6e6c56e1d28b
  config-map:
    x86_64-windows-msvc: x86_64-w64-mingw32
    i686-windows-msvc: i686-w64-mingw32
```

This is used to remap a config name for a specific dependency. In the example above it allows
grabdeps to fetch `x86_64-w64-mingw32` when asking for `x86_64-windows-msvc`.

### Filter configurations (exclude some configurations for a dependency)

```yml
easyaudioencoder:
  sha: 914f72559768e8f09eecb7bb6ccf6e6c56e1d28b
  config-exclude:
    - nano/aarch64-linux-android21
    - nano/arm-linux-androideabi21
    - nano/i686-linux-android21
    - nano/x86_64-linux-android21
```

Download easyaudioencoder for all configurations except the ones listed here. The format is
`{variant}/{config}`. This filter is performed before the remapping in `config-map` is done.

### Yaml config versioning

Each grabdeps release tracks a `MAJOR.MINOR` version for the config file format it understands.

The version is used as follows:

  * If a new grabdeps version introduces changes that don't break existing files (i.e. only expands
    upon them), the MINOR component will be incremented.
  * If a new grabdeps version introduces a breaking change, the MAJOR component will be incremented.

When reading the configuration, grabdeps will:

  * Reject config where the MAJOR version in the config is not exactly the same as the one it understands.
  * Reject config where the MINOR version in the config is greater than the one it understands.
  * Accept config where the MINOR version is less than or equal to the MINOR version it understands.
  * Accept config where the MAJOR.MINOR version is the same in the config as the one it understands.
