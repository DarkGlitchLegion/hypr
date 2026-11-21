# Copy to ~/.config/hyprsec/config.sh; the installer never overwrites it.
CONTAINER_NAME="hyprsec-kali"
CONTAINER_IMAGE="docker.io/kalilinux/kali-rolling@sha256:12e581978942a815b35ab2406725c274a4f28825650595d2ec2b7fb7668b039d"
WORKSPACE_ROOT="${HOME}/HyprSec/workspace"
TERMINAL="kitty"
LAUNCHER="rofi"
FILE_MANAGER="thunar"
WAYBAR_ENABLED=1
NETWORK_PROFILE="none" # none or bridge; bridge networking requires confirmation.
NETWORK_NAME="hyprsec-bridge"
ISOLATED_NETWORK_NAME="hyprsec-isolated"
CONTAINER_CAPABILITIES=() # Keep empty unless a reviewed workflow requires more access.
