"""The diagnostic observes only the selected appliance and cannot send controls."""
from contextlib import redirect_stdout
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("control_observer", ROOT / "tools/capture_device_controls_v1.py")
probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(probe)
DEVICE = "01234567-89ab-cdef-0123-456789abcdef"


class ObserverTests(unittest.TestCase):
    def test_publish_guard_allows_only_selected_device_empty_read_requests(self):
        calls = []
        client = types.SimpleNamespace(mqtt_publish_packet=lambda topic, payload: calls.append((topic, payload)))
        probe.guard_publishes(client, DEVICE)
        base, shadow, allowed = probe.read_topics(DEVICE)
        for topic in allowed:
            client.mqtt_publish_packet(topic, "{}")
        self.assertEqual(len(calls), 2)
        for topic, payload in ((shadow + "/update", '{}'), (base + "/startCooking", '{}'),
                               (base + "/getCookingStatus", '{"command":"start"}'),
                               ("COO001/other/getCookingStatus", '{}'), (shadow + '/get', '[]')):
            with self.subTest(topic=topic), self.assertRaises(ValueError):
                client.mqtt_publish_packet(topic, payload)
        self.assertEqual(len(calls), 2)

    def test_redaction_preserves_setting_values_but_removes_personal_data(self):
        raw = {"state": {"reported": {"brightness": 2, "volume": 0, "language": "de",
            "firmware": {"version": "5.3.1", "url": "https://signed/private?token=secret"},
            "email": "cook@example.test", "token": "secret-value", "wifiSSID": "private wifi",
            "title": "Private recipe", "account": {"name": "private person"}, "device_uuid": DEVICE}}}
        safe = probe.sanitize(raw)
        reported = safe["state"]["reported"]
        self.assertEqual((reported["brightness"], reported["volume"], reported["language"]), (2, 0, "de"))
        self.assertEqual(reported["firmware"]["version"], "5.3.1")
        encoded = json.dumps(safe)
        for secret in ("signed/private", "secret-value", "cook@example", "private wifi", "Private recipe", "private person", DEVICE):
            self.assertNotIn(secret, encoded)
        self.assertEqual(probe.sanitize(raw), safe, "Stable digests permit before/after comparison")

    def test_source_scan_retains_command_context_and_skips_symlinks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "device.java").write_text('public void sendOK() {\n  String password="do-not-copy";\n  mqtt.getCookingStatus();\n}\n')
            (root / "ignored.java").symlink_to(root / "device.java")
            (root / "link").symlink_to(root, target_is_directory=True)
            result = probe.source_clues(root)
            self.assertEqual(result["filesScanned"], 1)
            self.assertEqual(len(result["matches"]), 1)
            encoded = json.dumps(result)
            self.assertIn("sendOK", encoded)
            self.assertNotIn("do-not-copy", encoded)
            self.assertFalse(result["truncated"])

    def test_ambiguous_device_selection_is_explicit_and_not_guessed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / ".storage").mkdir()
            (root / ".storage/core.config_entries").write_text(json.dumps({"data": {"entries": [
                {"domain": "other"}, {"domain": "cook4me", "entry_id": "one"}, {"domain": "cook4me", "entry_id": "two"}]}}))
            with self.assertRaisesRegex(ValueError, "Found 2"):
                probe.choose_entry(root, None)
            self.assertEqual(probe.choose_entry(root, 2)["entry_id"], "two")
            with self.assertRaises(ValueError):
                probe.choose_entry(root, 0)

    def test_observer_falls_back_when_wildcards_are_denied_and_keeps_device_scope(self):
        class Socket:
            def __init__(self): self.sent = []; self.closed = False
            def send_binary(self, value): self.sent.append(value)
            def close(self): self.closed = True
        first, second = Socket(), Socket()
        sockets = iter((first, second))
        clock = iter(range(100))
        packets = iter([(9, 0, b"\x00\x01\x80\x80"), (9, 0, b"\x00\x01" + b"\x00" * 8),
                        (3, 0, b"event")])
        published, subscribed = [], []
        def read(_ws, _timeout):
            try: return next(packets)
            except StopIteration: raise TimeoutError()
        def subscribe(packet, topics):
            subscribed.append(topics)
            return b"subscribe"
        def encode(topic, payload):
            published.append((topic, payload))
            return b"read-request"
        client = types.SimpleNamespace(mqtt_open=lambda *_a, **_k: next(sockets),
            mqtt_subscribe_packet=subscribe, mqtt_read_packet=read, mqtt_publish_packet=encode,
            mqtt_decode_publish=lambda *_a: (f"COO001/{DEVICE}/cookingStatus", b'{"volume":2,"token":"private"}', None),
            _is_ws_timeout=lambda exc: isinstance(exc, TimeoutError))
        probe.guard_publishes(client, DEVICE)
        output = io.StringIO()
        with patch.object(probe.time, "monotonic", side_effect=lambda: next(clock)), redirect_stdout(output):
            self.assertTrue(probe.observe(client, {}, {}, DEVICE, 10))
        self.assertTrue(first.closed and second.closed)
        self.assertEqual({topic for topic, _payload in published}, probe.read_topics(DEVICE)[2])
        self.assertTrue(all(DEVICE in topic for topics in subscribed for topic, _qos in topics))
        events = [json.loads(line) for line in output.getvalue().splitlines()]
        self.assertEqual(next(row for row in events if row["event"] == "subscriptions")["scope"], "known-topics")
        self.assertEqual(next(row for row in events if row["event"] == "mqtt")["payload"]["volume"], 2)
        self.assertNotIn(DEVICE, output.getvalue())
        self.assertNotIn("private", output.getvalue())

    def test_host_wrapper_creates_only_review_files_and_discards_vendor_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fake = root / "docker"
            fake.write_text('#!' + sys.executable + '\nimport sys,json\nsys.stdin.read()\n'
                            'print("unstructured-secret")\nprint("stderr-secret",file=sys.stderr)\n'
                            'print(json.dumps({"event":"observing","seconds":30}))\n'
                            'for i in range(500): print(json.dumps({"event":"mqtt","topic":"<device>","payload":{"brightness":i%3}}))\n'
                            'print(json.dumps({"event":"finished","messages":500}))\n')
            fake.chmod(0o755)
            result = subprocess.run([sys.executable, str(ROOT / "tools/capture_device_controls_v1.py"),
                "--seconds", "30", "--source-root", str(root / "missing-source"), "--output-dir", str(root / "output")],
                env={**os.environ, "PATH": str(root) + os.pathsep + os.environ.get("PATH", "")}, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            with zipfile.ZipFile(next((root / "output").glob("*.zip"))) as archive:
                self.assertEqual(set(archive.namelist()), {"events.jsonl", "app-source-clues.json", "report.json"})
                raw = archive.read("events.jsonl").decode()
                self.assertEqual(len(raw.splitlines()), 502)
                self.assertNotIn("secret", raw)
                report = json.loads(archive.read("report.json"))
                self.assertEqual(report["deviceMutations"], 0)
                self.assertFalse(report["remoteControlVerified"])

    def test_credential_expiry_accepts_existing_wire_formats(self):
        expected = 1800000000
        self.assertEqual(probe.expiration_timestamp(expected), expected)
        self.assertEqual(probe.expiration_timestamp(expected * 1000), expected)
        self.assertEqual(probe.expiration_timestamp("2027-01-15T08:00:00Z"), expected)


if __name__ == "__main__":
    unittest.main()
