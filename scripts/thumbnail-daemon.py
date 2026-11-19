#!/usr/bin/env python3
"""
Hyprland Rice — User-Space Thumbnailer Daemon
Implements org.freedesktop.thumbnails.Thumbnailer1 D-Bus service for Thunar.
Enables instant real image thumbnails in file manager without requiring system-level daemons.
"""

import sys
import os
import signal
import hashlib
import urllib.parse
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

try:
    import gi
    gi.require_version('GdkPixbuf', '2.0')
    from gi.repository import GdkPixbuf
except Exception as e:
    GdkPixbuf = None

BUS_NAME = "org.freedesktop.thumbnails.Thumbnailer1"
OBJECT_PATH = "/org/freedesktop/thumbnails/Thumbnailer1"
PID_FILE = "/tmp/hypr_thumbnailer.pid"

SUPPORTED_MIMES = [
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
    "image/bmp",
    "image/svg+xml",
    "image/tiff",
    "image/x-icon",
    "image/vnd.microsoft.icon",
]

FLAVOR_DIMS = {
    "normal": 128,
    "large": 256,
    "x-large": 512,
    "xx-large": 1024,
}

class ThumbnailerService(dbus.service.Object):
    def __init__(self, bus):
        super().__init__(bus, OBJECT_PATH)
        self.bus = bus
        self.job_counter = 0

    @dbus.service.method(BUS_NAME, in_signature="", out_signature="asas")
    def GetSupported(self):
        return (["file"], SUPPORTED_MIMES)

    @dbus.service.method(BUS_NAME, in_signature="", out_signature="as")
    def GetSchedulers(self):
        return ["default", "foreground", "background"]

    @dbus.service.method(BUS_NAME, in_signature="", out_signature="as")
    def GetFlavors(self):
        return ["normal", "large", "x-large", "xx-large"]

    @dbus.service.method(BUS_NAME, in_signature="asasssu", out_signature="u")
    def Queue(self, uris, mime_types, flavor, scheduler, handle_to_unqueue):
        self.job_counter += 1
        handle = self.job_counter

        # Schedule processing on GLib main loop so Queue returns immediately
        GLib.idle_add(self._process_queue, handle, list(uris), str(flavor))
        return handle

    @dbus.service.method(BUS_NAME, in_signature="u", out_signature="")
    def Dequeue(self, handle):
        pass

    @dbus.service.signal(BUS_NAME, signature="u")
    def Started(self, handle):
        pass

    @dbus.service.signal(BUS_NAME, signature="uas")
    def Ready(self, handle, uris):
        pass

    @dbus.service.signal(BUS_NAME, signature="u")
    def Finished(self, handle):
        pass

    @dbus.service.signal(BUS_NAME, signature="uasi")
    def Error(self, handle, uris, error_code):
        pass

    def _process_queue(self, handle, uris, flavor):
        self.Started(handle)
        dim = FLAVOR_DIMS.get(flavor, 256)
        cache_dir = os.path.expanduser(f"~/.cache/thumbnails/{flavor}")
        os.makedirs(cache_dir, exist_ok=True)
        # Also ensure normal/large fallback directories exist
        os.makedirs(os.path.expanduser("~/.cache/thumbnails/normal"), exist_ok=True)
        os.makedirs(os.path.expanduser("~/.cache/thumbnails/large"), exist_ok=True)

        ready_uris = []

        for uri in uris:
            try:
                uri_str = str(uri)
                if uri_str.startswith("file://"):
                    file_path = urllib.parse.unquote(urllib.parse.urlparse(uri_str).path)
                else:
                    file_path = uri_str

                if not os.path.isfile(file_path):
                    continue

                mtime = str(int(os.path.getmtime(file_path)))
                size = str(os.path.getsize(file_path))

                # Canonical URI hashing per FreeDesktop specification
                digest = hashlib.md5(uri_str.encode("utf-8")).hexdigest()
                out_path = os.path.join(cache_dir, f"{digest}.png")

                # Check if up-to-date thumbnail already exists
                need_gen = True
                if os.path.isfile(out_path):
                    try:
                        thumb_mtime = os.path.getmtime(out_path)
                        if thumb_mtime >= float(mtime):
                            need_gen = False
                    except Exception:
                        pass

                if need_gen and GdkPixbuf is not None:
                    try:
                        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(file_path, dim, dim, True)
                        pixbuf.savev(
                            out_path,
                            "png",
                            ["tEXt::Thumb::URI", "tEXt::Thumb::MTime", "tEXt::Thumb::Size"],
                            [uri_str, mtime, size]
                        )
                        # Also save to large if flavor is different to maximize Thunar compatibility
                        if flavor != "large":
                            large_path = os.path.expanduser(f"~/.cache/thumbnails/large/{digest}.png")
                            if not os.path.exists(large_path):
                                pixbuf_large = GdkPixbuf.Pixbuf.new_from_file_at_scale(file_path, 256, 256, True)
                                pixbuf_large.savev(
                                    large_path,
                                    "png",
                                    ["tEXt::Thumb::URI", "tEXt::Thumb::MTime", "tEXt::Thumb::Size"],
                                    [uri_str, mtime, size]
                                )
                    except Exception:
                        continue

                ready_uris.append(uri_str)
            except Exception:
                continue

        if ready_uris:
            self.Ready(handle, ready_uris)
        self.Finished(handle)
        return False  # Do not re-run in GLib loop

def main():
    # Write PID
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    def cleanup(*args):
        try:
            os.remove(PID_FILE)
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    DBusGMainLoop(set_as_default=True)
    try:
        bus = dbus.SessionBus()
        # Request name on session bus
        bus_name = dbus.service.BusName(BUS_NAME, bus)
        service = ThumbnailerService(bus)
    except Exception as e:
        # Service might already be provided by another instance or tumbler
        sys.exit(0)

    loop = GLib.MainLoop()
    try:
        loop.run()
    except (KeyboardInterrupt, SystemExit):
        cleanup()

if __name__ == "__main__":
    main()
