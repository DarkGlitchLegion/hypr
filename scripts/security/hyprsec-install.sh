#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
CONFIG_HOME="${XDG_CONFIG_HOME:-${HOME}/.config}/hyprsec"

confirm() {
    local answer
    [[ -t 0 ]] || return 1
    printf '%s [y/N] ' "$1" >&2
    read -r answer
    [[ "${answer}" == [yY] || "${answer}" == [yY][eE][sS] ]]
}

mkdir -p -- "${CONFIG_HOME}"
for file in config.example.sh tools.conf keybind.conf; do
    case "${file}" in
        config.example.sh) target="${CONFIG_HOME}/config.sh" ;;
        keybind.conf) target="${CONFIG_HOME}/keybind" ;;
        *) target="${CONFIG_HOME}/${file}" ;;
    esac
    if [[ ! -e "${target}" ]]; then
        install -m 600 "${CONFIG_ROOT}/hyprsec/${file}" "${target}"
        printf 'Installed %s\n' "${target}"
    else
        printf 'Kept existing %s\n' "${target}"
    fi
done

if ! command -v podman >/dev/null 2>&1; then
    if command -v pacman >/dev/null 2>&1 && confirm "Install rootless Podman with pacman?"; then
        sudo pacman -S --needed podman
    else
        printf 'Podman is required. Install it with: sudo pacman -S podman\n' >&2
        exit 1
    fi
fi

if (( EUID == 0 )); then
    printf 'Run this installer as your regular user, not with sudo.\n' >&2
    exit 1
fi

if podman info --format '{{.Host.Security.Rootless}}' 2>/dev/null | grep -qx true; then
    "${SCRIPT_DIR}/hyprsec-box.sh" init
    if confirm "Create the Kali container now? This downloads the image."; then
        "${SCRIPT_DIR}/hyprsec-box.sh" create
    fi
else
    printf 'Podman is installed but rootless setup is not ready. See hyprsec/README.md troubleshooting.\n' >&2
    exit 1
fi

printf 'HyprSec Box setup complete. Open it with Super+Shift+H or from Control Center.\n'
