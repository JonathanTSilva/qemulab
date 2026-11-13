<!-- brand:header:start -->
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/brand/header-265fdc26-dark.svg">
  <img alt="qemulab: A modern TUI for managing QEMU development environments" src="assets/brand/header-265fdc26-light.svg" width="100%">
</picture>
<!-- brand:header:end -->

<!-- badges:start -->
[![Status](https://img.shields.io/badge/status-wip-yellow?style=flat-square)](https://www.repostatus.org/#wip)
[![CI](https://img.shields.io/github/actions/workflow/status/JonathanTSilva/qemulab/ci.yml?branch=main&style=flat-square&label=ci)](https://github.com/JonathanTSilva/qemulab/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/JonathanTSilva/qemulab/graph/badge.svg)](https://codecov.io/gh/JonathanTSilva/qemulab)
[![Quality](https://sonarcloud.io/api/project_badges/measure?project=JonathanTSilva_qemulab&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=JonathanTSilva_qemulab)
[![Scorecard](https://img.shields.io/ossf-scorecard/github.com/JonathanTSilva/qemulab?style=flat-square&label=scorecard)](https://scorecard.dev/viewer/?uri=github.com/JonathanTSilva/qemulab)
[![License](https://img.shields.io/badge/license-MIT-blue?style=flat-square)](LICENSE)
[![Codespaces](https://img.shields.io/badge/codespaces-open-181717?style=flat-square&logo=github)](https://codespaces.new/JonathanTSilva/qemulab)
<!-- badges:end -->

## What it is

qemulab is a terminal UI built with [Textual](https://textual.textualize.io/) that
orchestrates small QEMU labs of network appliances. It provisions the Linux bridges and tap
interfaces, boots several guest images side by side in tmux panes, and injects per-node
configuration from a scenario. Image layout, guest login and config-mode commands are all
configurable, so it works with any kernel and initrd pair.

## Quick start

```sh
git clone https://github.com/JonathanTSilva/qemulab.git
cd qemulab
uv sync
uv run pytest
```

Or open it in a dev container or GitHub Codespaces. Running a lab needs `qemu-system-x86_64`,
`ip`, `tmux`, `sudo` and `/dev/kvm` on the host.

## Usage

```sh
uv run -m qemulab start    # launch the TUI wizard
uv run -m qemulab check    # verify host requirements
```

The wizard walks through board, image version, scenario and node count, then launches the
environment. Press the documented keys to view logs or clean up (see the docs).

### Sudo

qemulab asks for your sudo password once and validates it from Python (`sudo -S -v`), so the
tmux panes reuse the cached sudo timestamp and the password is never typed into a pane.

If your sudoers config uses `tty_tickets` (the default on many distros), a pane cannot share
that timestamp. qemulab then falls back to sending the password with a leading space and
`HISTCONTROL=ignorespace`, redacted from logs. A narrow sudoers rule avoids this and is
recommended, for example (adjust paths with `command -v`):

```text
youruser ALL=(root) NOPASSWD: /usr/bin/qemu-system-x86_64, /usr/bin/ip, /usr/bin/tunctl
```

Per-node flash dirs and configs are created as your user (mode 0700) under
`$XDG_RUNTIME_DIR/qemulab`, or a private `qemulab-*` temp dir when that is unset. Set
`flash_base_path` to override the location. sudo is only used to remove dirs that QEMU filled
with root-owned files, and only after checking the path has no symlink components and is owned
by you.

### Image layout

By default qemulab looks for images under `~/qemulab/images`:

```text
~/qemulab/images/<board>/images/<board>-bzImage-<version>
~/qemulab/images/<board>/images/<board>-rootfs.cpio-<version>
```

Every part of this (directory pattern, file name templates, base path) is a setting.

### Scenarios

A scenario is a directory under your scenarios path with a `scenario.json` and one `cfg_dutN`
file per node. The default path is `${XDG_CONFIG_HOME:-~/.config}/qemulab/scenarios`. Set
`scenarios_path` in your config or `QEMULAB_SCENARIOS_PATH` to use another location. Scenario
commands are typed into the guest consoles, so point it only at a directory that you alone can
write to; the current directory is never searched. Before sending scenario commands, qemulab
checks that the pane is running QEMU (`qemu-system-*`, or the `sudo` wrapper that launched it)
and aborts the scenario with an error otherwise. See [`scenarios/two-router-link`](scenarios/two-router-link) for a minimal example
that uses addresses from the RFC 5737 documentation range (192.0.2.0/24).

### Cleanup

`scripts/cleanup_qemulab.sh` kills leftover QEMU processes and the tmux session, removes the
lab network interfaces (sudo) and deletes `$XDG_RUNTIME_DIR/qemulab/flash_*` (no sudo). A flash
directory is only removed if it is a plain directory you own inside a parent you own that is
not a symlink. Without `XDG_RUNTIME_DIR` the flash step is skipped; there is no `/tmp` fallback.

### Configuration

Settings are read, in order of precedence, from `QEMULAB_*` environment variables, a user
config file (`~/.config/qemulab/config.yaml`, or the path in `QEMULAB_CONFIG`), and the packaged
`defaults.yaml`. Nothing sensitive ships by default. Guest credentials and any commands that
need a password are yours to supply:

```yaml
# ~/.config/qemulab/config.yaml
images_base_path: ~/qemulab/images
guest:
  login_prompt: "login:"
  username: labuser
  password: labpass
  enter_config_command: configure
  load_config_command: "load {file}"
  commit_command: commit
  exit_config_command: exit
common_commands:
  - command: enable-debug
    password_env: QEMULAB_DEBUG_PASSWORD   # read from the environment, never stored
    description: Enable debug features
```

## Docs

More guides live in [`docs/`](docs): [quick reference](docs/QUICK_REFERENCE.md),
[navigation](docs/NAVIGATION_AND_STATUS_GUIDE.md), [cleanup](docs/CLEANUP_AND_EXIT_GUIDE.md),
[troubleshooting](docs/TROUBLESHOOTING.md), [FAQ](docs/FAQ.md) and [testing](docs/TESTING.md).
The conventions this repository follows are in the
[handbook](https://github.com/JonathanTSilva/.github/blob/main/handbook/README.md).

## Contributing

See the [contributing guide](https://github.com/JonathanTSilva/.github/blob/main/CONTRIBUTING.md).
Branches are named `<type>/<issue>-<slug>`, commits and PR titles follow Conventional Commits,
and PRs are squash-merged.

## License

MIT. See [LICENSE](LICENSE).

<!-- brand:footer:start -->
<p align="right"><a href="https://www.jontobias.com"><picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/JonathanTSilva/.github/main/assets/brand/jontobias-dark.svg">
  <img alt="jontobias.com" src="https://raw.githubusercontent.com/JonathanTSilva/.github/main/assets/brand/jontobias-light.svg" width="200">
</picture></a></p>
<!-- brand:footer:end -->
