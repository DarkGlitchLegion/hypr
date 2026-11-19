# Rice Maintenance and Hardware Test Checklist

Use the CLI from a terminal:

```sh
~/.config/hypr/scripts/rice doctor --full
~/.config/hypr/scripts/rice validate
~/.config/hypr/scripts/rice dependencies --full
~/.config/hypr/scripts/rice test
```

The automated suite only reports tests it actually ran. Hardware items below remain manual and are not included as passed tests.
`rice reload` validates the Hyprland/Lua configuration before reloading and does not restart Waybar.

## HDMI displays and recovery

- [ ] Connect HDMI and run `rice doctor --module display`.
- [ ] Apply Extend and External Display Only; verify active monitors and geometry.
- [ ] Switch External Only → Laptop Only → Extend → Mirror (mirror remains guarded on affected Hyprland versions).
- [ ] Disconnect HDMI while Extended and while External Only; verify the laptop display and workspaces remain accessible.
- [ ] Reconnect HDMI and verify only an explicitly saved profile is restored.
- [ ] Repeat docking/undocking with a USB-C dock or multiple external outputs, if available.

## HDMI audio

- [ ] Connect an HDMI display that has speakers and run `pactl -f json list sinks`.
- [ ] Choose its output from Waybar → Audio; test playback and active streams.
- [ ] Enable automatic HDMI switching; verify it does not switch for a display with no audio sink.
- [ ] Disconnect HDMI while playing audio; verify fallback to a connected output.
- [ ] Reconnect HDMI and confirm switching only when the opt-in setting is enabled.

## Bluetooth

- [ ] Toggle Bluetooth off and on from the existing manager; verify Waybar shows disabled/powered/connected states.
- [ ] Connect and disconnect a paired headset; verify audio routing and Waybar status.
- [ ] Verify `rice logs --module bluetooth` records actions without device credentials.

## Snapshots and recovery

- [ ] Create a snapshot, modify a harmless test config, and run `rice snapshot diff ID`.
- [ ] Restore one selected component; review the preview and confirm.
- [ ] Verify a pre-restore snapshot exists and the restored config validates; test recovery from an already-invalid config using a disposable configuration copy.
- [ ] Change a saved display/audio/session preference and verify a `pre-*` snapshot is created.
- [ ] Test rollback only with a disposable copy or a controlled invalid configuration; never deliberately break the active desktop.

## Notes

- Layout transitions require a live Hyprland session and connected displays.
- HDMI audio and Bluetooth routing require their respective hardware.
- `rice validate` checks the installed Hyprland parser, Lua syntax, shell/Python syntax, and Waybar JSONC. It does not reload Hyprland or restart Waybar.
- Snapshot restoration applies files additively; it intentionally does not delete extra files in the live configuration.
