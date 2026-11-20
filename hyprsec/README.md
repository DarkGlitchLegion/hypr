# HyprSec Box

HyprSec Box is an optional rootless Kali Rolling container integrated with the
Hyprland rice. It is intended for defensive learning, diagnostics, analysis of
local files, and authorized lab work. It does not configure a target or run
scans automatically.

## Safety model

- The manager refuses to run as root and verifies Podman's rootless mode.
- Containers start on a dedicated Podman `--internal` network with no external
  route, all Linux capabilities dropped, and `no-new-privileges`; no privileged
  flag is used. This permits a separate, explicitly enabled egress bridge to be
  attached later.
- Only `~/HyprSec/workspace/{targets,captures,scans,reports,scripts,projects}`
  is bind-mounted. Host home, SSH, browser profiles, and credentials are not
  mounted.
- Network access is opt-in. The **Enable network** action confirms before
  attaching a dedicated rootless Podman bridge; disable it after package work.
  Containers made by the earlier `--network=none` implementation must be
  rebuilt before a bridge can be attached. Rebuild resets installed container
  packages but preserves workspace data.
- The package catalog is metadata-driven and separates category coverage from
  installation-ready packages. Scope-only categories do not contain installable
  package entries; the default catalog avoids packages that automate attacks
  against third-party systems.
- APT runs as root inside the container because all Linux capabilities are
  dropped; APT's default `_apt` sandbox needs `CAP_SETGID`. The manager sets
  `APT::Sandbox::User=root` and uses a root-owned cache in the container's
  `/tmp` instead of adding capabilities or changing the image's `_apt` cache
  ownership. Host isolation defaults remain unchanged.
- Cleanup is interactive and project-scoped; the manager never removes the
  workspace automatically. Container removal preserves all workspace data.

Rootless containers are an isolation layer, not a substitute for keeping
Podman and the host kernel patched. Use only systems and data you are
authorized to assess.

## Installation

From the dotfiles checkout, run as your normal user:

```sh
~/.config/hypr/scripts/hyprsec-install.sh
```

The installer asks before installing Podman or pulling/creating the Kali
container. It creates `~/.config/hyprsec/` configuration files only when they
do not already exist. Review `~/.config/hyprsec/config.sh` and
`~/.config/hyprsec/tools.conf` after installation.

For rootless Podman on Arch, the host package is `podman`. The existing rice
provides Kitty, Rofi, Thunar, and Dunst; the feature does not install Kali
packages on the host.

## Usage

- **Super + Shift + H** opens the HyprSec menu. Change the key in
  `~/.config/hyprsec/keybind`, then reload Hyprland.
- Open it from the Control Center's quick actions or Developer menu.
- The optional Waybar indicator shows setup/running/stopped state. Left click
  opens the manager; right click asks before stopping the container.
- **Container shell** opens an interactive Bash session in Kali.
- **Workspace** opens the host workspace in Kitty or Thunar. Inside the
  container the mounted folders are under `/workspace`.
- Create and list project workspaces from the menu or CLI:

```sh
~/.config/hypr/scripts/hyprsec-box.sh workspace create-project lab-notes
~/.config/hypr/scripts/hyprsec-box.sh workspace list-projects
```

- **Tool manager** shows configured packages by category and whether each is
  installed. Install/update requires the bridge to be explicitly enabled and
  confirmed. APT commands run only inside the container.
- Enable or disable networking from the menu, or use:

```sh
~/.config/hypr/scripts/hyprsec-box.sh network-status
~/.config/hypr/scripts/hyprsec-box.sh network-enable
~/.config/hypr/scripts/hyprsec-box.sh network-disable
```

The CLI also supports `status`, `create`, `start`, `stop`, `restart`, `shell`,
`tools`, `update`, `rebuild`, and `remove`. Destructive actions require
confirmation. `stop --yes` is intended for explicit scripted shutdown.

## Configuration

`~/.config/hyprsec/config.sh` controls the container name/image, workspace,
terminal, launcher, file manager, Waybar visibility, network profile, bridge
name, and optional container capabilities. Keep `NETWORK_PROFILE="none"` and
`CONTAINER_CAPABILITIES=()` for the strongest default isolation. A configured
bridge or capability is shown/confirmed before the container is created or
started.

`~/.config/hyprsec/tools.conf` uses pipe-delimited metadata rows:

```text
category|tool name|APT package|description|source|method|availability|dependencies|compatibility|documentation URL|risk|usage notes|prerequisites
```

Three-column legacy rows remain supported. Catalog categories include
information gathering, assessment, web, wireless, Bluetooth, password auditing,
exploit research, forensics, incident response, reverse engineering, mobile,
fuzzing, cryptography, cloud/container, hardware/RFID/SDR, VoIP, operating
system auditing, malware analysis, databases, recovery, and reporting. A
category marked `scope-only` is visible but has no installation-ready package
entries in the default catalog.

The repository catalog is merged with `~/.config/hyprsec/tools.conf`; user
entries are preserved and take precedence for duplicate package names. The
installer does not overwrite that file.

The manager supports searching all tools, category filtering, metadata and
documentation viewing, installed-state checks, and live APT-index availability
checks. `verified` means the package was checked in the Kali Rolling index;
availability is rechecked after updating package indexes before installation.
Package dependencies are resolved by APT. Installation/removal requires explicit
selection and runs only inside the container. Catalog presence never executes
a tool. Review tool documentation and use network-facing tools only within an
authorized lab. Forensic tools operate on supplied workspace files; host disks,
credentials, radio devices, and host runtime sockets are not mounted by
default.

## Troubleshooting

- **Podman missing:** run the installer or `sudo pacman -S podman`.
- **Rootless setup not ready:** verify `/etc/subuid` and `/etc/subgid` entries
  for your user, then check `podman info --format
  '{{.Host.Security.Rootless}}'`. Do not run this manager with `sudo`.
- **Image pull fails:** check host connectivity and image name in
  `config.sh`; the container has no network until explicitly enabled.
- **An older container cannot enable networking:** choose **Rebuild container**.
  Podman cannot attach a bridge to its special `none` network mode. Rebuild
  preserves `~/HyprSec/workspace` but resets packages installed in that
  container.
- **APT/update fails:** confirm the bridge from the menu, check
  `network-status`, then review `~/.local/state/hyprsec/manager.log` for APT
  output and the underlying error. The manager keeps container capabilities
  dropped and uses a container-local writable download cache. Disable
  networking when finished.
- **Workspace permission error:** check that `WORKSPACE_ROOT` is absolute and
  writable by your user. Only that directory's named subfolders are mounted.
- **Waybar module absent:** ensure `WAYBAR_ENABLED=1`, restart Waybar, and
  verify the configured scripts path is valid.
- **Inspect logs:** `~/.local/state/hyprsec/manager.log`.

## Removal

Run `~/.config/hypr/scripts/hyprsec-uninstall.sh`. It confirms removal of the
container and keeps workspace files, config, the Podman image, and host
packages. To remove the image separately, inspect it with `podman images`
first and remove only the reviewed image with `podman rmi`.
