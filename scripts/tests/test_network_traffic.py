from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "network_traffic", ROOT / "scripts" / "network-traffic.py"
)
assert SPEC is not None and SPEC.loader is not None
traffic = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = traffic
SPEC.loader.exec_module(traffic)


class TrafficMonitorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.state_file = Path(self.temp_dir.name) / "network-traffic.json"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_rates_and_totals_use_counter_deltas_and_elapsed_time(self) -> None:
        monitor = traffic.TrafficMonitor(self.state_file)
        first = monitor.sample({"wlan0": (1000, 500)}, "wlan0", now=10.0)
        second = monitor.sample({"wlan0": (3000, 1500)}, "wlan0", now=12.0)

        self.assertEqual(first["download_bps"], 0)
        self.assertEqual(second["download_bps"], 1000)
        self.assertEqual(second["upload_bps"], 500)
        self.assertEqual(second["downloaded_bytes"], 2000)
        self.assertEqual(second["uploaded_bytes"], 1000)
        persisted = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.assertEqual(persisted["downloaded_bytes"], 2000)
        self.assertEqual(persisted["uploaded_bytes"], 1000)

    def test_interface_switch_rebaselines_without_double_counting(self) -> None:
        monitor = traffic.TrafficMonitor(self.state_file)
        monitor.sample({"eth0": (100, 100), "wlan0": (200, 200)}, "eth0", now=1)
        switched = monitor.sample(
            {"eth0": (1100, 1100), "wlan0": (800, 700)}, "wlan0", now=2
        )
        self.assertEqual(switched["downloaded_bytes"], 0)
        self.assertEqual(switched["uploaded_bytes"], 0)
        next_sample = monitor.sample(
            {"eth0": (1500, 1400), "wlan0": (1100, 900)}, "wlan0", now=3
        )
        self.assertEqual(next_sample["downloaded_bytes"], 300)
        self.assertEqual(next_sample["uploaded_bytes"], 200)

    def test_counter_reset_and_disconnect_do_not_add_bytes(self) -> None:
        monitor = traffic.TrafficMonitor(self.state_file)
        monitor.sample({"eth0": (1000, 1000)}, "eth0", now=1)
        reset = monitor.sample({"eth0": (100, 1200)}, "eth0", now=2)
        self.assertEqual(reset["downloaded_bytes"], 0)
        self.assertEqual(reset["uploaded_bytes"], 200)

        disconnected = monitor.sample({}, None, now=3)
        self.assertFalse(disconnected["connected"])
        self.assertEqual(disconnected["interface"], "")
        self.assertEqual(disconnected["download_bps"], 0)
        self.assertEqual(disconnected["uploaded_bytes"], 200)

    def test_restart_preserves_totals_and_baselines_counters(self) -> None:
        monitor = traffic.TrafficMonitor(self.state_file)
        monitor.sample({"wlan0": (100, 50)}, "wlan0", now=1)
        before_restart = monitor.sample({"wlan0": (500, 250)}, "wlan0", now=2)

        restarted = traffic.TrafficMonitor(self.state_file)
        after_restart = restarted.sample({"wlan0": (9000, 6000)}, "wlan0", now=3)
        self.assertEqual(after_restart["downloaded_bytes"], before_restart["downloaded_bytes"])
        self.assertEqual(after_restart["uploaded_bytes"], before_restart["uploaded_bytes"])
        self.assertEqual(after_restart["download_bps"], 0)

        following = restarted.sample({"wlan0": (10000, 6500)}, "wlan0", now=4)
        self.assertEqual(following["downloaded_bytes"], 1400)
        self.assertEqual(following["uploaded_bytes"], 700)

    def test_default_route_selection_handles_wifi_ethernet_and_ipv6(self) -> None:
        ipv4 = (
            "Iface Destination Gateway Flags RefCnt Use Metric Mask\n"
            "wlan0 00000000 0100000A 0003 0 0 600 00000000\n"
            "eth0 00000000 0100000A 0003 0 0 100 00000000\n"
        )
        self.assertEqual(
            traffic.default_route_interface({"wlan0", "eth0"}, ipv4, ""),
            "eth0",
        )
        ipv6 = (
            f"{'0' * 32} 00 {'0' * 32} 00 {'0' * 32} 00000020 "
            "00000000 00000000 00000001 wlan0\n"
        )
        self.assertEqual(
            traffic.default_route_interface({"wlan0"}, "", ipv6),
            "wlan0",
        )
        self.assertIsNone(traffic.default_route_interface({"eth0"}, "", ""))

    def test_invalid_persisted_state_is_not_silently_reset(self) -> None:
        self.state_file.write_text("{bad json", encoding="utf-8")
        with self.assertRaises(traffic.TrafficError):
            traffic.TrafficMonitor(self.state_file)


if __name__ == "__main__":
    unittest.main()
