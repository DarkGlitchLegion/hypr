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
import secrets
from pathlib import Path
import dbus
import dbus.service
import dbus.exceptions
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

AGENT_PATH = "/org/hyprland/bluetooth/agent"
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
PID_FILE = RUNTIME_DIR / "hypr-rice" / "hypr_bt_agent.pid"
PAIRABLE_TIMEOUT_SECONDS = 120


def reject_request():
    raise dbus.exceptions.DBusException(
        "org.bluez.Error.Rejected",
        "Rejected by the laptop user.",
    )


def ask_user(title: str, message: str) -> bool:
    choices = "Approve\nReject"
    try:
        result = subprocess.run(
            [
                "rofi",
                "-dmenu",
                "-p",
                "Bluetooth Approval",
                "-mesg",
                f"<b>{title}</b>\n{message}",
            ],
            input=choices,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
            env=os.environ,
        )
        return result.returncode == 0 and result.stdout.strip() == "Approve"
    except (OSError, subprocess.TimeoutExpired):
        return False

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
        name = get_device_name(self.bus, device)
        if not ask_user(
            "Authorize Bluetooth Service",
            f"Allow <b>{name}</b> to use Bluetooth service <b>{uuid}</b>?",
        ):
            reject_request()
        notify("Bluetooth Service Authorized", f"Allowed {name} to use {uuid}.", "low")

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        name = get_device_name(self.bus, device)
        if not ask_user(
            "Approve Bluetooth Pairing",
            f"Allow <b>{name}</b> to pair using a PIN?",
        ):
            reject_request()
        pin = f"{secrets.randbelow(1000000):06d}"
        notify("Bluetooth PIN", f"Enter PIN <b>{pin}</b> on <b>{name}</b>", "normal")
        return pin

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        name = get_device_name(self.bus, device)
        if not ask_user(
            "Approve Bluetooth Pairing",
            f"Allow <b>{name}</b> to pair using a passkey?",
        ):
            reject_request()
        passkey = secrets.randbelow(1000000)
        notify("Bluetooth Passkey", f"Enter passkey <b>{passkey:06d}</b> on <b>{name}</b>", "normal")
        return dbus.UInt32(passkey)

    @dbus.service.method("org.bluez.Agent1", in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        name = get_device_name(self.bus, device)
        notify("Bluetooth Passkey", f"Passkey for <b>{name}</b>: <b>{passkey:06d}</b>", "normal")

    @dbus.service.method("org.bluez.Agent1", in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        name = get_device_name(self.bus, device)
        if not ask_user(
            "Confirm Bluetooth Passkey",
            f"<b>{name}</b> is requesting to pair.\nDoes it show passkey <b>{passkey:06d}</b>?",
        ):
            reject_request()
        notify("Bluetooth Pairing", f"Confirmed pairing with {name}.", "low")

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        name = get_device_name(self.bus, device)
        if not ask_user(
            "Approve Incoming Pairing",
            f"Allow <b>{name}</b> to pair with this laptop?",
        ):
            reject_request()
        notify("Pairing Authorized", f"Accepted incoming pairing from {name}.", "low")

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
                adapter_props.Set("org.bluez.Adapter1", "PairableTimeout", dbus.UInt32(PAIRABLE_TIMEOUT_SECONDS))
                adapter_props.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(True))
                adapter_props.Set("org.bluez.Adapter1", "DiscoverableTimeout", dbus.UInt32(PAIRABLE_TIMEOUT_SECONDS))
    except Exception:
        pass


def disable_adapter_pairable(bus):
    try:
        manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        objects = manager.GetManagedObjects()
        for path, interfaces in objects.items():
            if "org.bluez.Adapter1" in interfaces:
                adapter_props = dbus.Interface(bus.get_object("org.bluez", path), "org.freedesktop.DBus.Properties")
                adapter_props.Set("org.bluez.Adapter1", "Pairable", dbus.Boolean(False))
                adapter_props.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(False))
    except Exception:
        pass

def main():
    bus = None
    # Single instance enforcement
    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(PID_FILE.parent, 0o700)
    if PID_FILE.exists() or PID_FILE.is_symlink():
        try:
            if PID_FILE.is_symlink():
                PID_FILE.unlink(missing_ok=True)
            with PID_FILE.open("r", encoding="ascii") as f:
                old_pid = int(f.read().strip())
            os.kill(old_pid, 0)
            sys.exit(0)
        except (ValueError, OSError):
            pass
    try:
        fd = os.open(PID_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "w", encoding="ascii") as file:
            file.write(str(os.getpid()))
    except OSError as exc:
        print(f"Could not create secure Bluetooth agent PID file: {exc}", file=sys.stderr)
        return

    def cleanup(*args):
        if bus is not None:
            disable_adapter_pairable(bus)
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        raise SystemExit(0)

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
    GLib.timeout_add_seconds(
        PAIRABLE_TIMEOUT_SECONDS,
        lambda: (disable_adapter_pairable(bus), False)[1],
    )

    loop = GLib.MainLoop()
    try:
        loop.run()
    except (KeyboardInterrupt, SystemExit):
        cleanup()

if __name__ == "__main__":
    main()
