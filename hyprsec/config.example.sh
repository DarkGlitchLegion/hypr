# Copy to ~/.config/hyprsec/config.sh; the installer never overwrites it.
CONTAINER_NAME="hyprsec-kali"
CONTAINER_IMAGE="docker.io/kalilinux/kali-rolling:latest"
WORKSPACE_ROOT="${HOME}/HyprSec/workspace"
TERMINAL="kitty"
LAUNCHER="rofi"
FILE_MANAGER="thunar"
WAYBAR_ENABLED=1
NETWORK_PROFILE="none" # none or bridge; bridge networking requires confirmation.
NETWORK_NAME="hyprsec-bridge"
CONTAINER_CAPABILITIES=() # Keep empty unless a reviewed workflow requires more access.
