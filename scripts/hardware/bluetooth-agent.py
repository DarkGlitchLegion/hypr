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
CONFIG_ROOT = Path(__file__).resolve().parents[2]
APPROVAL_THEME = CONFIG_ROOT / "rofi" / "bluetooth-approval.rasi"
STATE_DIR = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local" / "state")) / "hypr"
LOG_FILE = STATE_DIR / "bluetooth-agent.log"
PAIRABLE_TIMEOUT_SECONDS = 180


def reject_request():
    raise dbus.exceptions.DBusException(
        "org.bluez.Error.Rejected",
        "Rejected by the laptop user.",
    )


def log(message: str) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(STATE_DIR, 0o700)
        fd = os.open(LOG_FILE, os.O_WRONLY | os.O_CREAT | os.O_APPEND | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, "a", encoding="utf-8") as file:
            file.write(f"{message}\n")
    except OSError as exc:
        print(f"Bluetooth agent: could not write log: {exc}", file=sys.stderr)


def notify(title: str, message: str, urgency: str = "low", icon: str = "bluetooth") -> None:
    try:
        subprocess.run(
            ["dunstify", "-a", "Bluetooth", "-u", urgency, "-i", icon, title, message],
            timeout=2,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        log(f"Notification could not be displayed: {exc}")


def plain_text(value: str) -> str:
    return value.replace("&", "＆").replace("<", "‹").replace(">", "›")


def ask_user(title: str, message: str) -> bool:
    choices = "Approve\nReject"
    log(f"Approval requested: {title} — {message}")
    notify("Bluetooth approval needed", f"{title}: {message}", "normal")
    try:
        result = subprocess.run(
            [
                "rofi",
                "-dmenu",
                "-config",
                str(APPROVAL_THEME),
                "-p",
                "󰂯 Bluetooth",
                "-mesg",
                f"{plain_text(title)}\n{plain_text(message)}",
            ],
            input=choices,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
            env=os.environ,
        )
        approved = result.returncode == 0 and result.stdout.strip() == "Approve"
        log(f"Approval decision for {title}: {'approved' if approved else 'rejected or cancelled'}")
        return approved
    except (OSError, subprocess.TimeoutExpired) as exc:
        log(f"Approval UI failed for {title}: {exc}")
        notify("Bluetooth approval unavailable", "Could not open the approval dialog. The request was rejected.", "critical")
        return False


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
            f"Allow {name} to use Bluetooth service {uuid}?",
        ):
            reject_request()
        notify("Bluetooth Service Authorized", f"Allowed {name} to use {uuid}.", "low")

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        name = get_device_name(self.bus, device)
        if not ask_user(
            "Approve Bluetooth Pairing",
            f"Allow {name} to pair using a PIN?",
        ):
            reject_request()
        pin = f"{secrets.randbelow(1000000):06d}"
        notify("Bluetooth PIN", f"Enter PIN {pin} on {name}", "normal")
        return pin

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        name = get_device_name(self.bus, device)
        if not ask_user(
            "Approve Bluetooth Pairing",
            f"Allow {name} to pair using a passkey?",
        ):
            reject_request()
        passkey = secrets.randbelow(1000000)
        notify("Bluetooth Passkey", f"Enter passkey {passkey:06d} on {name}", "normal")
        return dbus.UInt32(passkey)

    @dbus.service.method("org.bluez.Agent1", in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        name = get_device_name(self.bus, device)
        notify("Bluetooth Passkey", f"Passkey for {name}: {passkey:06d}", "normal")

    @dbus.service.method("org.bluez.Agent1", in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        name = get_device_name(self.bus, device)
        if not ask_user(
            "Confirm Bluetooth Passkey",
            f"{name} is requesting to pair.\nDoes it show passkey {passkey:06d}?",
        ):
            reject_request()
        notify("Bluetooth Pairing", f"Confirmed pairing with {name}.", "low")

    @dbus.service.method("org.bluez.Agent1", in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        name = get_device_name(self.bus, device)
        if not ask_user(
            "Approve Incoming Pairing",
            f"Allow {name} to pair with this laptop?",
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
        found_adapter = False
        for path, interfaces in objects.items():
            if "org.bluez.Adapter1" in interfaces:
                found_adapter = True
                adapter_props = dbus.Interface(bus.get_object("org.bluez", path), "org.freedesktop.DBus.Properties")
                adapter_props.Set("org.bluez.Adapter1", "Pairable", dbus.Boolean(True))
                adapter_props.Set("org.bluez.Adapter1", "PairableTimeout", dbus.UInt32(PAIRABLE_TIMEOUT_SECONDS))
                adapter_props.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(True))
                adapter_props.Set("org.bluez.Adapter1", "DiscoverableTimeout", dbus.UInt32(PAIRABLE_TIMEOUT_SECONDS))
        if not found_adapter:
            raise RuntimeError("BlueZ did not report a Bluetooth adapter.")
        log(f"Bluetooth adapter is pairable and discoverable for {PAIRABLE_TIMEOUT_SECONDS} seconds.")
    except (dbus.DBusException, RuntimeError) as exc:
        log(f"Could not enable Bluetooth pairing mode: {exc}")
        notify("Bluetooth pairing unavailable", str(exc), "critical")


def disable_adapter_pairable(bus):
    try:
        manager = dbus.Interface(bus.get_object("org.bluez", "/"), "org.freedesktop.DBus.ObjectManager")
        objects = manager.GetManagedObjects()
        for path, interfaces in objects.items():
            if "org.bluez.Adapter1" in interfaces:
                adapter_props = dbus.Interface(bus.get_object("org.bluez", path), "org.freedesktop.DBus.Properties")
                adapter_props.Set("org.bluez.Adapter1", "Pairable", dbus.Boolean(False))
                adapter_props.Set("org.bluez.Adapter1", "Discoverable", dbus.Boolean(False))
        log("Bluetooth pairing mode disabled.")
    except dbus.DBusException as exc:
        log(f"Could not disable Bluetooth pairing mode: {exc}")

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
    try:
        bus = dbus.SystemBus()
        agent = BluetoothAgent(bus, AGENT_PATH)
        obj = bus.get_object("org.bluez", "/org/bluez")
        manager = dbus.Interface(obj, "org.bluez.AgentManager1")

        manager.RegisterAgent(AGENT_PATH, "KeyboardDisplay")
        manager.RequestDefaultAgent(AGENT_PATH)
        log("Bluetooth agent registered with BlueZ as the default KeyboardDisplay agent.")
        notify("Bluetooth ready", "Pairing requests will show an approval dialog.", "low")
    except dbus.DBusException as exc:
        log(f"Could not register the Bluetooth approval agent: {exc}")
        notify("Bluetooth agent error", str(exc), "critical")
        try:
            PID_FILE.unlink(missing_ok=True)
        except OSError as cleanup_error:
            log(f"Could not remove the agent PID file: {cleanup_error}")
        raise

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
