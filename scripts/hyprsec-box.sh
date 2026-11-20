#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd)"
USER_CONFIG="${HYPRSEC_CONFIG_FILE:-${XDG_CONFIG_HOME:-${HOME}/.config}/hyprsec/config.sh}"
USER_CATALOG="${HYPRSEC_TOOL_CATALOG:-${XDG_CONFIG_HOME:-${HOME}/.config}/hyprsec/tools.conf}"
DEFAULT_CATALOG="${CONFIG_ROOT}/hyprsec/tools.conf"
ROFI_THEME="${CONFIG_ROOT}/rofi/command-center.rasi"

CONTAINER_NAME="hyprsec-kali"
CONTAINER_IMAGE="docker.io/kalilinux/kali-rolling:latest"
WORKSPACE_ROOT="${HOME}/HyprSec/workspace"
TERMINAL="kitty"
LAUNCHER="rofi"
FILE_MANAGER="thunar"
WAYBAR_ENABLED=1
NETWORK_PROFILE="none"
NETWORK_NAME="hyprsec-bridge"
ISOLATED_NETWORK_NAME="hyprsec-isolated"
CONTAINER_CAPABILITIES=()

if [[ -f "${CONFIG_ROOT}/hyprsec/config.example.sh" ]]; then
    # shellcheck source=/dev/null
    source "${CONFIG_ROOT}/hyprsec/config.example.sh"
fi
if [[ -f "${USER_CONFIG}" ]]; then
    # shellcheck source=/dev/null
    source "${USER_CONFIG}"
fi

STATE_DIR="${XDG_STATE_HOME:-${HOME}/.local/state}/hyprsec"
LOG_FILE="${STATE_DIR}/manager.log"
readonly -a WORKSPACE_DIRS=(targets captures scans reports scripts projects)

log() {
    mkdir -p -- "${STATE_DIR}"
    chmod 700 "${STATE_DIR}"
    printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" | tee -a "${LOG_FILE}" >&2
}

fail() {
    log "ERROR: $*"
    notify "HyprSec Box" "$*"
    return 1
}

notify() {
    if command -v dunstify >/dev/null 2>&1; then
        dunstify -a "HyprSec Box" -u normal "$1" "$2" >/dev/null 2>&1 || true
    elif command -v notify-send >/dev/null 2>&1; then
        notify-send "$1" "$2" >/dev/null 2>&1 || true
    fi
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || {
        fail "Required command is missing: $1"
        return 1
    }
}

confirm() {
    local prompt="$1" choice
    if command -v "${LAUNCHER}" >/dev/null 2>&1 && [[ -n "${WAYLAND_DISPLAY:-}" ]]; then
        choice="$(printf 'Cancel\n%s\n' "$2" | "${LAUNCHER}" -dmenu -i -no-custom \
            -config "${ROFI_THEME}" -p "HyprSec confirmation" -mesg "$prompt")" || return 1
        [[ "${choice}" == "$2" ]]
        return
    fi
    if [[ -t 0 ]]; then
        printf '%s [y/N] ' "${prompt}" >&2
        read -r choice
        [[ "${choice}" == [yY] || "${choice}" == [yY][eE][sS] ]]
        return
    fi
    return 1
}

require_podman() {
    command -v podman >/dev/null 2>&1 || {
        fail "Podman is missing. Run scripts/hyprsec-install.sh to install it."
        return 1
    }
    (( EUID != 0 )) || {
        fail "HyprSec Box must run rootless; do not invoke it with sudo."
        return 1
    }
    local rootless
    rootless="$(podman info --format '{{.Host.Security.Rootless}}' 2>/dev/null)" || {
        fail "Podman is not ready for this user. Check rootless Podman setup."
        return 1
    }
    [[ "${rootless}" == "true" ]] || {
        fail "Podman reports a non-rootless engine. Refusing to continue."
        return 1
    }
}

validate_config() {
    [[ "${CONTAINER_NAME}" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,62}$ ]] || {
        fail "Invalid container name in HyprSec config."
        return 1
    }
    [[ "${NETWORK_PROFILE}" == "none" || "${NETWORK_PROFILE}" == "bridge" ]] || {
        fail "NETWORK_PROFILE must be 'none' or 'bridge'."
        return 1
    }
    [[ "${NETWORK_NAME}" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,62}$ ]] || {
        fail "Invalid Podman network name in HyprSec config."
        return 1
    }
    [[ "${ISOLATED_NETWORK_NAME}" =~ ^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,62}$ ]] || {
        fail "Invalid isolated Podman network name in HyprSec config."
        return 1
    }
    [[ "${WORKSPACE_ROOT}" == /* ]] || {
        fail "WORKSPACE_ROOT must be an absolute path."
        return 1
    }
}

workspace_path() {
    realpath -m -- "${WORKSPACE_ROOT}"
}

ensure_workspace() {
    validate_config || return
    local root dir
    root="$(workspace_path)"
    mkdir -p -- "${root}"
    [[ -d "${root}" && -w "${root}" ]] || {
        fail "Workspace is not writable: ${root}"
        return 1
    }
    for dir in "${WORKSPACE_DIRS[@]}"; do
        [[ ! -L "${root}/${dir}" ]] || {
            fail "Workspace subdirectory must not be a symlink: ${root}/${dir}"
            return 1
        }
        mkdir -p -- "${root}/${dir}"
        [[ -d "${root}/${dir}" && -w "${root}/${dir}" \
            && "$(realpath -e -- "${root}/${dir}")" == "${root}/${dir}" ]] || {
            fail "Workspace directory is not writable: ${root}/${dir}"
            return 1
        }
    done
}

container_exists() {
    podman container exists "${CONTAINER_NAME}" >/dev/null 2>&1
}

container_running() {
    container_exists && [[ "$(podman inspect --format '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null)" == "true" ]]
}

ensure_network() {
    if ! podman network exists "${NETWORK_NAME}" >/dev/null 2>&1; then
        podman network create "${NETWORK_NAME}" >/dev/null || {
            fail "Could not create Podman bridge network '${NETWORK_NAME}'."
            return 1
        }
    fi
}

ensure_isolated_network() {
    if ! podman network exists "${ISOLATED_NETWORK_NAME}" >/dev/null 2>&1; then
        podman network create --internal "${ISOLATED_NETWORK_NAME}" >/dev/null || {
            fail "Could not create isolated Podman network '${ISOLATED_NETWORK_NAME}'."
            return 1
        }
    fi
}

has_bridge() {
    podman inspect --format '{{json .NetworkSettings.Networks}}' "${CONTAINER_NAME}" 2>/dev/null \
        | grep -Fq "\"${NETWORK_NAME}\""
}

uses_legacy_none_network() {
    local networks
    networks="$(podman inspect --format '{{json .NetworkSettings.Networks}}' "${CONTAINER_NAME}" 2>/dev/null)" \
        || return 1
    [[ "${networks}" == *'"none"'* ]]
}

create_container() {
    require_podman && ensure_workspace || return
    if container_exists; then
        notify "HyprSec Box" "Container '${CONTAINER_NAME}' already exists."
        return 0
    fi

    ensure_isolated_network || return

    local capability
    if ((${#CONTAINER_CAPABILITIES[@]})); then
        confirm "Configured capabilities weaken isolation: ${CONTAINER_CAPABILITIES[*]}" "Add capabilities" || {
            fail "Container creation cancelled; no capabilities were added."
            return 1
        }
        for capability in "${CONTAINER_CAPABILITIES[@]}"; do
            [[ "${capability}" =~ ^[A-Z_]+$ ]] || {
                fail "Invalid container capability in configuration: ${capability}"
                return 1
            }
        done
    fi

    if ! podman image exists "${CONTAINER_IMAGE}" >/dev/null 2>&1; then
        log "Pulling container image ${CONTAINER_IMAGE}"
        podman pull "${CONTAINER_IMAGE}" || {
            fail "Could not pull ${CONTAINER_IMAGE}. Check the image name and network."
            return 1
        }
    fi

    local root dir
    root="$(workspace_path)"
    local -a args=(create --name "${CONTAINER_NAME}" --network "${ISOLATED_NETWORK_NAME}"
        --cap-drop=ALL --security-opt=no-new-privileges --pids-limit=512
        --label "io.hyprsec.managed=true")
    for dir in "${WORKSPACE_DIRS[@]}"; do
        args+=(--volume "${root}/${dir}:/workspace/${dir}:rw")
    done
    for capability in "${CONTAINER_CAPABILITIES[@]}"; do
        args+=(--cap-add "${capability}")
    done
    args+=(--entrypoint /bin/sleep "${CONTAINER_IMAGE}" infinity)
    if podman "${args[@]}"; then
        log "Created rootless container '${CONTAINER_NAME}' on isolated network '${ISOLATED_NETWORK_NAME}'."
        notify "HyprSec Box" "Container created offline on a private internal network."
    else
        fail "Container creation failed. See ${LOG_FILE}."
        return 1
    fi
}

start_container() {
    require_podman || return
    container_exists || {
        fail "Container is not created. Choose Create container first."
        return 1
    }
    local connect_bridge=0
    if [[ "${NETWORK_PROFILE}" == "bridge" ]] && ! has_bridge; then
        confirm "The configured profile enables network access. Continue?" "Start with network" || return 1
        ensure_network || return
        connect_bridge=1
    fi
    if podman start "${CONTAINER_NAME}" >/dev/null; then
        if ((connect_bridge)) && ! podman network connect "${NETWORK_NAME}" "${CONTAINER_NAME}"; then
            fail "Container started, but network connection failed. It remains isolated."
            return 1
        fi
        log "Started '${CONTAINER_NAME}'."
        notify "HyprSec Box" "Container is running."
    else
        fail "Container startup failed. See ${LOG_FILE}."
        return 1
    fi
}

stop_container() {
    require_podman || return
    container_exists || {
        notify "HyprSec Box" "Container is not created."
        return 0
    }
    if ! container_running; then
        notify "HyprSec Box" "Container is already stopped."
        return 0
    fi
    if podman stop --time 10 "${CONTAINER_NAME}" >/dev/null; then
        log "Stopped '${CONTAINER_NAME}'."
        notify "HyprSec Box" "Container stopped."
    else
        fail "Container stop failed. See ${LOG_FILE}."
        return 1
    fi
}

status() {
    require_podman || return
    if ! container_exists; then
        printf 'Container: %s (not created)\nImage: %s\nNetwork: none\nWorkspace: %s\n' \
            "${CONTAINER_NAME}" "${CONTAINER_IMAGE}" "$(workspace_path)"
        return
    fi
    local state networks
    state="$(podman inspect --format '{{.State.Status}}' "${CONTAINER_NAME}")" || {
        fail "Could not inspect container status."
        return 1
    }
    networks="$(podman inspect --format '{{json .NetworkSettings.Networks}}' "${CONTAINER_NAME}" 2>/dev/null || printf '{}')"
    printf 'Container: %s (%s)\nImage: %s\nNetwork: %s\nWorkspace: %s\n' \
        "${CONTAINER_NAME}" "${state}" "${CONTAINER_IMAGE}" "${networks}" "$(workspace_path)"
}

waybar_status() {
    local text class tooltip
    if [[ "${WAYBAR_ENABLED}" != "1" ]]; then
        printf '{"text":"","tooltip":"","class":"disabled"}\n'
        return
    fi
    if ! command -v podman >/dev/null 2>&1; then
        text="󰒃 Sec: unavailable"
        class="unavailable"
        tooltip="Podman is not installed"
    elif ! podman info --format '{{.Host.Security.Rootless}}' >/dev/null 2>&1; then
        text="󰒃 Sec: unavailable"
        class="unavailable"
        tooltip="Rootless Podman is not ready"
    elif container_running; then
        text="󰒃 Sec: on"
        class="running"
        tooltip="HyprSec Kali container is running"
    elif container_exists; then
        text="󰒃 Sec: off"
        class="stopped"
        tooltip="HyprSec Kali container is stopped"
    else
        text="󰒃 Sec: setup"
        class="stopped"
        tooltip="HyprSec container has not been created"
    fi
    printf '{"text":"%s","tooltip":"%s","class":"%s"}\n' "${text}" "${tooltip}" "${class}"
}

shell_container() {
    require_command "${TERMINAL}" || return
    if ! container_running; then
        start_container || return
    fi
    terminal_exec podman exec -it "${CONTAINER_NAME}" /bin/bash
}

terminal_exec() {
    if [[ "${TERMINAL##*/}" == "kitty" ]]; then
        "${TERMINAL}" --config "${CONFIG_ROOT}/kitty/kitty.conf" -e "$@"
    else
        "${TERMINAL}" -e "$@"
    fi
}

open_workspace_terminal() {
    ensure_workspace || return
    require_command "${TERMINAL}" || return
    terminal_exec bash -lc 'cd -- "$1"; exec bash' bash "$(workspace_path)"
}

open_workspace_files() {
    ensure_workspace || return
    require_command "${FILE_MANAGER}" || return
    "${FILE_MANAGER}" "$(workspace_path)" >/dev/null 2>&1 &
}

create_project() {
    ensure_workspace || return
    local name root
    if [[ -n "${1:-}" ]]; then
        name="$1"
    elif command -v "${LAUNCHER}" >/dev/null 2>&1; then
        name="$(printf '' | "${LAUNCHER}" -dmenu -config "${ROFI_THEME}" -p "New project name")" || return
    else
        read -r -p "New project name: " name
    fi
    [[ "${name}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]] || {
        fail "Project name must use letters, numbers, dot, underscore, or hyphen."
        return 1
    }
    root="$(workspace_path)/projects/${name}"
    if [[ -e "${root}" ]]; then
        fail "Project already exists: ${name}"
        return 1
    fi
    local dir
    mkdir -p -- "${root}"
    for dir in targets captures scans reports scripts; do
        mkdir -p -- "${root}/${dir}"
    done
    log "Created project workspace '${name}'."
    notify "HyprSec Box" "Created project workspace: ${name}"
}

list_projects() {
    local projects
    projects="$(workspace_path)/projects"
    [[ -d "${projects}" ]] || ensure_workspace
    find "${projects}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort
}

cleanup_project() {
    ensure_workspace || return
    require_command "${LAUNCHER}" || return
    require_command "${TERMINAL}" || return
    local projects selection
    projects="$(workspace_path)/projects"
    selection="$(find "${projects}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort \
        | "${LAUNCHER}" -dmenu -i -no-custom -config "${ROFI_THEME}" -p "Project to clean")" || return
    [[ -n "${selection}" ]] || return 0
    [[ "${selection}" =~ ^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$ ]] || {
        fail "Invalid project selection."
        return 1
    }
    confirm "Delete project '${selection}'? Contents are user data and will be removed." "Delete project" || return 1
    terminal_exec bash -lc 'rm -ri -- "$1"; read -r -p "Press Enter to close..."' bash "${projects}/${selection}"
}

network_status() {
    if ! container_exists; then
        printf 'Network profile: none (container not created)\n'
    else
        printf 'Network profile: %s\n' "$(podman inspect --format '{{json .NetworkSettings.Networks}}' "${CONTAINER_NAME}")"
    fi
}

network_enable() {
    require_podman || return
    container_exists || {
        fail "Create the container before changing its network."
        return 1
    }
    if uses_legacy_none_network; then
        fail "This older container uses Podman's special 'none' mode, which cannot be attached to a bridge. Choose Rebuild container to migrate it; workspace files stay, but container-installed packages are reset."
        return 1
    fi
    confirm "This enables network access from the container through a rootless Podman bridge. Continue only on trusted networks." \
        "Enable network" || return 1
    ensure_network || return
    if ! container_running; then
        podman start "${CONTAINER_NAME}" >/dev/null || {
            fail "Container startup failed."
            return 1
        }
    fi
    if has_bridge; then
        notify "HyprSec Box" "Network is already enabled."
        return 0
    fi
    local error
    if ! error="$(podman network connect "${NETWORK_NAME}" "${CONTAINER_NAME}" 2>&1)"; then
        fail "Could not enable network: ${error:-Podman returned an unspecified error.}"
        return 1
    fi
    log "Enabled explicit bridge network '${NETWORK_NAME}'."
    notify "HyprSec Box" "Network enabled. Disable it after package updates."
}

network_disable() {
    require_podman || return
    container_exists || return 0
    if ! has_bridge; then
        notify "HyprSec Box" "No HyprSec bridge network is connected."
        return 0
    fi
    podman network disconnect "${NETWORK_NAME}" "${CONTAINER_NAME}" || {
        fail "Could not disconnect the container network."
        return 1
    }
    log "Disabled bridge network '${NETWORK_NAME}'."
    notify "HyprSec Box" "Container network disabled."
}

apt_in_container() {
    log "Running APT in '${CONTAINER_NAME}': $*"
    podman exec "${CONTAINER_NAME}" sh -c \
        'mkdir -p /tmp/hyprsec-apt-cache && exec apt-get -o APT::Sandbox::User=root -o Dir::Cache::archives=/tmp/hyprsec-apt-cache "$@"' \
        hyprsec-apt "$@" 2>&1 | tee -a "${LOG_FILE}"
}

load_tool_rows() {
    local catalog="${USER_CATALOG}"
    [[ -f "${catalog}" ]] || catalog="${DEFAULT_CATALOG}"
    [[ -r "${catalog}" ]] || {
        fail "Tool catalog is missing or unreadable."
        return 1
    }
    awk -F'|' '!/^[[:space:]]*#/ && NF >= 3 && $1 != "" && $2 != "" {print $1 "|" $2 "|" $3}' "${catalog}"
}

tool_installed() {
    podman exec "${CONTAINER_NAME}" dpkg-query -W -f='${db:Status-Abbrev}' "$1" 2>/dev/null \
        | grep -q '^ii'
}

tool_menu() {
    require_command "${LAUNCHER}" || return
    require_podman || return
    container_running || {
        fail "Start the container before opening the tool manager."
        return 1
    }
    local rows categories category selected package description action
    rows="$(load_tool_rows)" || return
    categories="$(printf '%s\n' "${rows}" | cut -d'|' -f1 | sort -u)"
    category="$(printf '%s\n' "${categories}" | "${LAUNCHER}" -dmenu -i -no-custom \
        -config "${ROFI_THEME}" -p "HyprSec tools")" || return
    [[ -n "${category}" ]] || return
    local -a options=()
    while IFS='|' read -r row_category package description; do
        [[ "${row_category}" == "${category}" ]] || continue
        [[ "${package}" =~ ^[a-z0-9][a-z0-9+.-]*$ ]] || continue
        if tool_installed "${package}"; then
            options+=("${package} | installed | ${description}")
        else
            options+=("${package} | available | ${description}")
        fi
    done <<< "${rows}"
    if ((${#options[@]} == 0)); then
        notify "HyprSec Box" "No curated packages are configured for ${category}."
        return 0
    fi
    selected="$(printf '%s\n' "${options[@]}" | "${LAUNCHER}" -dmenu -i -no-custom \
        -config "${ROFI_THEME}" -p "${category}")" || return
    [[ -n "${selected}" ]] || return
    package="${selected%% | *}"
    description=""
    while IFS='|' read -r row_category action description; do
        [[ "${action}" == "${package}" ]] && break
    done <<< "${rows}"
    if tool_installed "${package}"; then
        action="$(printf 'Cancel\nRemove %s\n' "${package}" | "${LAUNCHER}" -dmenu -i -no-custom \
            -config "${ROFI_THEME}" -p "Installed tool")" || return
        [[ "${action}" == "Remove ${package}" ]] || return 0
        confirm "Remove ${package} from the container?" "Remove tool" || return 1
        apt_in_container remove -y "${package}" || {
            fail "Could not remove ${package} inside the container."
            return 1
        }
    else
        install_tool "${package}"
    fi
}

require_network_and_running() {
    require_podman || return
    container_running || {
        fail "Start the container first."
        return 1
    }
    has_bridge || {
        fail "Container has no network. Use Network → Enable network, then retry."
        return 1
    }
}

install_tool() {
    local package="$1"
    [[ "${package}" =~ ^[a-z0-9][a-z0-9+.-]*$ ]] || {
        fail "Invalid package name in tool catalog."
        return 1
    }
    local catalog_rows row_category row_package row_description found=0
    catalog_rows="$(load_tool_rows)" || return
    while IFS='|' read -r row_category row_package row_description; do
        if [[ "${row_package}" == "${package}" ]]; then
            found=1
            break
        fi
    done <<< "${catalog_rows}"
    ((found)) || {
        fail "Package '${package}' is not in the configured HyprSec tool catalog."
        return 1
    }
    require_network_and_running || return
    confirm "Install '${package}' inside the container only? Network access is enabled." "Install tool" || return 1
    apt_in_container update || {
        fail "APT index update failed inside the container."
        return 1
    }
    podman exec "${CONTAINER_NAME}" apt-cache show "${package}" >/dev/null 2>&1 || {
        fail "Package '${package}' is unavailable from the configured APT repositories."
        return 1
    }
    if apt_in_container install -y --no-install-recommends "${package}"; then
        log "Installed package '${package}' inside '${CONTAINER_NAME}'."
        notify "HyprSec Box" "Installed ${package} in the container."
    else
        fail "Package installation failed inside the container: ${package}. See ${LOG_FILE} for APT details."
        return 1
    fi
}

update_container() {
    require_network_and_running || return
    confirm "Update APT packages inside the container? Network access is enabled." "Update packages" || return 1
    apt_in_container update || {
        fail "APT index update failed inside the container."
        return 1
    }
    apt_in_container upgrade -y || {
        fail "Package upgrade failed inside the container."
        return 1
    }
    log "Updated packages inside '${CONTAINER_NAME}'."
    notify "HyprSec Box" "Container package update completed."
}

remove_container() {
    require_podman || return
    if ! container_exists; then
        notify "HyprSec Box" "Container is not created."
        return 0
    fi
    confirm "Remove '${CONTAINER_NAME}'? Container packages will be lost; workspace data is retained." \
        "Remove container" || return 1
    if container_running; then
        podman stop --time 10 "${CONTAINER_NAME}" >/dev/null || {
            fail "Could not stop the container."
            return 1
        }
    fi
    podman rm "${CONTAINER_NAME}" >/dev/null || {
        fail "Could not remove the container."
        return 1
    }
    log "Removed '${CONTAINER_NAME}'; workspace files were preserved."
    notify "HyprSec Box" "Container removed. Workspace data was kept."
}

rebuild_container() {
    require_podman || return
    confirm "Rebuild '${CONTAINER_NAME}'? Container-installed packages will be reset; workspace files are retained." \
        "Rebuild container" || return 1
    podman pull "${CONTAINER_IMAGE}" || {
        fail "Could not update the image; existing container was left intact."
        return 1
    }
    if container_exists; then
        if container_running; then
            podman stop --time 10 "${CONTAINER_NAME}" >/dev/null || {
                fail "Could not stop container; rebuild aborted."
                return 1
            }
        fi
        podman rm "${CONTAINER_NAME}" >/dev/null || {
            fail "Could not remove old container; rebuild aborted."
            return 1
        }
    fi
    create_container
}

open_menu() {
    require_command "${LAUNCHER}" || return
    require_command "${LAUNCHER}" || return
    require_podman || true
    local state="not created"
    if command -v podman >/dev/null 2>&1 && container_exists; then
        state="$(podman inspect --format '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || printf 'unknown')"
    fi
    local choice
    choice="$(cat <<EOF | "${LAUNCHER}" -dmenu -i -no-custom -config "${ROFI_THEME}" \
        -p "HyprSec Box" -mesg "Container: ${state} • Network: $(network_status 2>/dev/null | head -n1 | cut -d: -f2-)"
Status
Create container
Start container
Stop container
Restart container
Container shell
Tool manager
Update packages
Enable network
Disable network
Open workspace in terminal
Open workspace in file manager
Create project workspace
List projects
Clean up a project
Rebuild container
Remove container
Quit
EOF
)" || return
    case "${choice}" in
        "Status") terminal_exec bash -lc '"$1" status; read -r -p "Press Enter to close..."' bash "${SCRIPT_DIR}/hyprsec-box.sh" ;;
        "Create container") create_container ;;
        "Start container") start_container ;;
        "Stop container") stop_container ;;
        "Restart container") stop_container && start_container ;;
        "Container shell") shell_container ;;
        "Tool manager") tool_menu ;;
        "Update packages") update_container ;;
        "Enable network") network_enable ;;
        "Disable network") network_disable ;;
        "Open workspace in terminal") open_workspace_terminal ;;
        "Open workspace in file manager") open_workspace_files ;;
        "Create project workspace") create_project ;;
        "List projects") terminal_exec bash -lc '"$1" workspace list-projects; read -r -p "Press Enter to close..."' bash "${SCRIPT_DIR}/hyprsec-box.sh" ;;
        "Clean up a project") cleanup_project ;;
        "Rebuild container") rebuild_container ;;
        "Remove container") remove_container ;;
        *) return 0 ;;
    esac
}

main() {
    validate_config || return
    case "${1:-menu}" in
        menu) open_menu ;;
        init) ensure_workspace ;;
        status) status ;;
        waybar-status) waybar_status ;;
        waybar-stop)
            confirm "Stop the HyprSec container?" "Stop container" && stop_container
            ;;
        create) create_container ;;
        start) start_container ;;
        stop)
            if [[ "${2:-}" == "--yes" ]]; then
                require_podman && container_exists && podman stop --time 10 "${CONTAINER_NAME}"
            else
                stop_container
            fi
            ;;
        restart) stop_container && start_container ;;
        shell) require_podman && shell_container ;;
        tools) tool_menu ;;
        install-tool) install_tool "${2:-}" ;;
        update) update_container ;;
        remove) remove_container ;;
        rebuild) rebuild_container ;;
        network-status) network_status ;;
        network-enable) network_enable ;;
        network-disable) network_disable ;;
        workspace)
            case "${2:-terminal}" in
                terminal) open_workspace_terminal ;;
                files) open_workspace_files ;;
                create-project) create_project "${3:-}" ;;
                list-projects) list_projects ;;
                cleanup) cleanup_project ;;
                *) fail "Unknown workspace action: ${2}" ;;
            esac
            ;;
        *)
            printf 'Usage: %s {menu|status|create|start|stop|restart|shell|tools|update|remove|rebuild|network-*|workspace}\n' "$0" >&2
            return 2
            ;;
    esac
}

main "$@"
