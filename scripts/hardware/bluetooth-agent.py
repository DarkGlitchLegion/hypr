#!/usr/bin/env python3
"""
Hyprland Minimal Dark Rice — Persistent Bluetooth Pairing Agent
Implements org.bluez.Agent1 D-Bus interface with Dunst notifications.
Ensures seamless pairing with phones, headphones, keyboards, and other devices
without 'No agent available' or 'Connection refused' errors.
"""

import sys
import os
import signal
import subprocess
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

AGENT_PATH = "/org/hyprland/bluetooth/agent"
PID_FILE = "/tmp/hypr_bt_agent.pid"

def notify(title, msg, urgency="low", icon="bluetooth"):
    try:
        subprocess.run(
            ["dunstify", "-a", "Bluetooth", "-u", urgency, "-i", icon, title, msg],
            timeout=2,
            check=False
        )
    except Exception:
        pass

def get_device_name(bus, device_path):
    try:
        dev_obj = bus.get_object("org.bluez", device_path)
        props = dbus.Interface(dev_obj, "org.freedesktop.DBus.Properties")
        return str(props.Get("org.bluez.Device1", "Alias"))
    except Exception:
        # Fallback to formatting device path (/org/bluez/hci0/dev_XX_XX_XX_XX_XX_XX)
        parts = device_path.split("/")[-1].replace("dev_", "").replace("_", ":")
        return parts

class BluetoothAgent(dbus.service.Object):
    def __init__(self, bus, path):
        super().__init__(bus, path)
        self.bus = bus

    @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
    def Release(self):
        pass

    @dbus.service.method("org.bluez.Agent1", in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        # Automatically authorize connecting Bluetooth services (A2DP, HFP, HID, OBEX)
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        name = get_device_name(self.bus, device)
        notify("Pairing Requested", f"Using default PIN 0000 for <b>{name}</b>", "normal")
        return "0000"

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        return dbus.UInt32(0)

    @dbus.service.method("org.bluez.Agent1", in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        name = get_device_name(self.bus, device)
        notify("Bluetooth Passkey", f"Passkey for <b>{name}</b>: <b>{passkey:06d}</b>", "normal")

    @dbus.service.method("org.bluez.Agent1", in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        name = get_device_name(self.bus, device)
        notify("Bluetooth Pairing", f"Auto-confirmed pairing with <b>{name}</b>\nPasskey: <b>{passkey:06d}</b>", "normal")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        name = get_device_name(self.bus, device)
        notify("Pairing Authorized", f"Accepted incoming pairing from <b>{name}</b>", "low")
        return

    @dbus.service.method("org.bluez.Agent1", in_signature="", out_signature="")
    def Cancel(self):
        pass

def ensure_adapter_pairable(bus):
    try:
        manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        objects = manager.GetManagedObjects()
        for path, interfaces in objects.items():
            if "org.bluez.Adapter1" in interfaces:
                adapter_props = dbus.Interface(bus.get_object("org.bluez", path), "org.freedesktop.DBus.Properties")
                adapter_props.Set("org.bluez.Adapter1", "Pairable", dbus.Boolean(True))
                # Set pairable timeout to 0 (unlimited)
                adapter_props.Set("org.bluez.Adapter1", "PairableTimeout", dbus.UInt32(0))
    except Exception:
        pass

def main():
    # Single instance enforcement
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            sys.exit(0)
        except (ValueError, OSError):
            pass

    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    def cleanup(*args):
        try:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    agent = BluetoothAgent(bus, AGENT_PATH)
    obj = bus.get_object("org.bluez", "/org/bluez")
    manager = dbus.Interface(obj, "org.bluez.AgentManager1")

    # Register KeyboardDisplay agent and make it system default
    manager.RegisterAgent(AGENT_PATH, "KeyboardDisplay")
    manager.RequestDefaultAgent(AGENT_PATH)

    ensure_adapter_pairable(bus)

    loop = GLib.MainLoop()
    try:
        loop.run()
    except (KeyboardInterrupt, SystemExit):
        cleanup()

if __name__ == "__main__":
    main()
