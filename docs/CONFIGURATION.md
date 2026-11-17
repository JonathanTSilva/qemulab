# Configuration and operations

Everything you need to run qemulab on a real host: how it handles sudo, where images and scenarios live, how to clean up and how to configure it.

## Sudo

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

## Image layout

By default qemulab looks for images under `~/qemulab/images`:

```text
~/qemulab/images/<board>/images/<board>-bzImage-<version>
~/qemulab/images/<board>/images/<board>-rootfs.cpio-<version>
```

Every part of this (directory pattern, file name templates, base path) is a setting.

## Scenarios

A scenario is a directory under your scenarios path with a `scenario.json` and one `cfg_dutN`
file per node. The default path is `${XDG_CONFIG_HOME:-~/.config}/qemulab/scenarios`. Set
`scenarios_path` in your config or `QEMULAB_SCENARIOS_PATH` to use another location. Scenario
commands are typed into the guest consoles, so point it only at a directory that you alone can
write to; the current directory is never searched. Before sending scenario commands, qemulab
checks that the pane is running QEMU (`qemu-system-*`, or the `sudo` wrapper that launched it)
and aborts the scenario with an error otherwise. See [`scenarios/two-router-link`](../scenarios/two-router-link) for a minimal example
that uses addresses from the RFC 5737 documentation range (192.0.2.0/24).

## Cleanup

`scripts/cleanup_qemulab.sh` kills leftover QEMU processes and the tmux session, removes the
lab network interfaces (sudo) and deletes `$XDG_RUNTIME_DIR/qemulab/flash_*` (no sudo). A flash
directory is only removed if it is a plain directory you own inside a parent you own that is
not a symlink. Without `XDG_RUNTIME_DIR` the flash step is skipped; there is no `/tmp` fallback.

## Configuration

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
