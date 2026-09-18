#!/usr/bin/env python3
"""Observe Cook4Me cloud state and collect bounded, redacted app-source clues.

Run on the HA Docker host. No installation, restart, credential refresh,
shadow update, recipe send or cooking command is performed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import selectors
import subprocess
import sys
import tempfile
import time
from uuid import uuid4
import zipfile

KIND = "cook4me-device-control-observation-v1"
SENSITIVE = re.compile(r"token|password|secret|credential|authorization|cookie|certificate|apikey|email|ssid|bssid|macaddress|identity|account|userid|deviceid|deviceuuid|serial|clientid|url", re.I)
UUID = re.compile(r"\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b", re.I)
SAFE_VALUES = {"version", "key", "type", "status", "currentstatus", "mode", "language", "country", "command", "cmd", "action", "method", "phase"}
SOURCE_MATCH = re.compile(r"getCookingStatus|cookingStatus|sendOK|startCooking|stopCooking|pauseCooking|setTemperature|setBrightness|setVolume|COO001|Cookeo.*(?:command|setting)|(?:command|setting).*Cookeo", re.I)


def normalized(key):
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def sanitize(value, key="", depth=0):
    """Retain structure, numbers and protocol enums, not personal string values."""
    if SENSITIVE.search(normalized(key)):
        return "[redacted]"
    if depth > 20:
        return "[depth limit]"
    if isinstance(value, dict):
        return {UUID.sub("<id>", str(k)[:120]): sanitize(v, str(k), depth + 1)
                for k, v in list(value.items())[:500]}
    if isinstance(value, list):
        return [sanitize(v, key, depth + 1) for v in value[:500]]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        if normalized(key) in SAFE_VALUES and len(value) <= 80 and re.fullmatch(r"[A-Za-z0-9_. /:+-]*", value) and not UUID.search(value):
            return value
        return {"stringLength": len(value), "sha256": hashlib.sha256(value.encode()).hexdigest()[:16]}
    return "[unsupported value]"


def scrub_source(line):
    line = UUID.sub("<id>", line)
    line = re.sub(r"https?://[^\s\"'<>]+", "<url>", line)
    line = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "<email>", line)
    line = re.sub(r"\beyJ[A-Za-z0-9_-]+(?:\.[A-Za-z0-9_-]+){1,2}\b", "<token>", line)
    line = re.sub(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b", "<access-key>", line)
    line = re.sub(r"([\"'])([^\"'\n]{32,})\1", '"<long string>"', line)
    if re.search(r"(?i)(password|secret|token|api.?key|authorization|cookie)\s*[\"']?\s*[:=]", line):
        return "[sensitive assignment omitted]"
    return line[:1000]


def source_clues(root):
    result = {"present": root.is_dir(), "filesScanned": 0, "matches": [], "truncated": False}
    if not result["present"]:
        return result
    started = time.monotonic()
    for directory, dirs, names in os.walk(root, followlinks=False):
        dirs[:] = sorted(d for d in dirs if not (Path(directory) / d).is_symlink())
        for name in sorted(names):
            if not name.endswith((".java", ".kt", ".smali")):
                continue
            if result["filesScanned"] >= 80000 or time.monotonic() - started > 30 or len(result["matches"]) >= 200:
                result["truncated"] = True
                return result
            path = Path(directory) / name
            try:
                if path.is_symlink() or path.stat().st_size > 1500000:
                    continue
                result["filesScanned"] += 1
                lines = path.read_text(errors="replace").splitlines()
            except OSError:
                continue
            hits = [i for i, line in enumerate(lines) if SOURCE_MATCH.search(line)][:12]
            if hits:
                indices = sorted({j for i in hits for j in range(max(0, i - 3), min(len(lines), i + 4))})
                result["matches"].append({"path": str(path.relative_to(root)),
                    "lines": [{"line": i + 1, "text": scrub_source(lines[i])} for i in indices]})
    return result


def read_topics(device_uuid):
    base = f"COO001/{device_uuid}"
    shadow = f"$aws/things/COO001-{device_uuid}/shadow"
    return base, shadow, {f"{base}/getCookingStatus", f"{shadow}/get"}


def guard_publishes(client, device_uuid):
    """Fail closed if this observer ever attempts an appliance mutation."""
    _, _, allowed = read_topics(device_uuid)
    encode = client.mqtt_publish_packet
    def read_packet(topic, payload):
        decoded = json.loads(payload)
        if topic not in allowed or decoded != {}:
            raise ValueError("Observer may only publish empty status/shadow GET requests")
        return encode(topic, payload)
    client.mqtt_publish_packet = read_packet


def expiration_timestamp(value):
    if isinstance(value, (int, float)):
        return value / 1000 if value > 1e10 else value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
    return 0


def choose_entry(config, device):
    raw = json.loads((config / ".storage/core.config_entries").read_text())
    entries = [row for row in raw.get("data", {}).get("entries", []) if row.get("domain") == "cook4me"]
    if not entries:
        raise ValueError("No Cook4Me entry is installed in this HA container")
    if device is None and len(entries) != 1:
        raise ValueError(f"Found {len(entries)} Cook4Me entries; select --device 1 through --device {len(entries)}")
    selected = 1 if device is None else device
    if selected < 1 or selected > len(entries):
        raise ValueError("The selected device number is outside the installed entry list")
    return entries[selected - 1]


def emit(kind, **values):
    print(json.dumps({"event": kind, "at": datetime.now(timezone.utc).isoformat(), **values}), flush=True)


def observe(client, cfg, credentials, device_uuid, seconds):
    base, shadow, _ = read_topics(device_uuid)
    alias = lambda topic: topic.replace(device_uuid, "<device>")
    # Known exact subscriptions provide a fallback if own-device wildcards
    # are not permitted. No other appliance or account namespace is requested.
    exact = [f"{base}/cookingStatus", f"{base}/alert", *[f"{shadow}/{tail}" for tail in
        ("get/accepted", "get/rejected", "update/accepted", "update/rejected", "update/delta", "update/documents")]]
    ws = None
    for broad in (True, False):
        topics = [f"{base}/#", f"{shadow}/#"] if broad else exact
        try:
            ws = client.mqtt_open(cfg, credentials, f"cook4me-observe-{uuid4().hex[:10]}", keepalive=60)
            ws.send_binary(client.mqtt_subscribe_packet(1, [(topic, 0) for topic in topics]))
            ptype, _flags, body = client.mqtt_read_packet(ws, 15)
            if ptype != 9 or len(body) != len(topics) + 2 or body[:2] != b"\x00\x01" or any(code not in (0, 1, 2) for code in body[2:]):
                raise ValueError("Subscription was not accepted")
            emit("subscriptions", scope="device-wildcards" if broad else "known-topics", topics=[alias(t) for t in topics])
            break
        except Exception as exc:
            if ws is not None:
                ws.close()
                ws = None
            emit("subscription-unavailable", scope="device-wildcards" if broad else "known-topics", errorType=type(exc).__name__)
    if ws is None:
        return False
    count = 0
    try:
        ws.send_binary(client.mqtt_publish_packet(f"{shadow}/get", "{}"))
        ws.send_binary(client.mqtt_publish_packet(f"{base}/getCookingStatus", "{}"))
        deadline = time.monotonic() + seconds
        last_ping = time.monotonic()
        emit("observing", seconds=seconds)
        while time.monotonic() < deadline and count < 3000:
            if time.monotonic() - last_ping >= 25:
                ws.send_binary(b"\xc0\x00")
                last_ping = time.monotonic()
            try:
                ptype, flags, packet = client.mqtt_read_packet(ws, min(5, max(.1, deadline - time.monotonic())))
            except Exception as exc:
                if client._is_ws_timeout(exc):
                    continue
                raise
            if ptype == 3:
                topic, payload, packet_id = client.mqtt_decode_publish(flags, packet)
                if flags >> 1 & 3 == 1 and packet_id is not None:
                    ws.send_binary(b"\x40\x02" + packet_id.to_bytes(2, "big"))
                if not (topic.startswith(base + "/") or topic.startswith(shadow + "/")):
                    continue
                count += 1
                if len(payload) > 1000000:
                    emit("oversized-event", topic=alias(topic), bytes=len(payload))
                    continue
                try:
                    data = json.loads(payload)
                except (ValueError, UnicodeError):
                    data = {"nonJsonBytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}
                emit("mqtt", topic=alias(topic), payload=sanitize(data))
            elif ptype == 12:
                ws.send_binary(b"\xd0\x00")
        emit("finished", messages=count, eventLimitReached=count >= 3000)
        return True
    except Exception as exc:
        emit("capture-error", errorType=type(exc).__name__)
        return False
    finally:
        ws.close()


def inside(args):
    config = Path("/config")
    try:
        entry = choose_entry(config, args.device)
    except (ValueError, OSError) as exc:
        # These are our own setup messages. Other failures never print exception
        # text, which could contain tokens, a signed URL or provider response.
        emit("setup-error", message=str(exc) if isinstance(exc, ValueError) else "HA configuration is unreadable")
        return 2
    identifier = str(entry.get("data", {}).get("device_uuid", "")).lower()
    entry_id = str(entry.get("entry_id", ""))
    if not UUID.fullmatch(identifier) or not re.fullmatch(r"[A-Za-z0-9_-]+", entry_id):
        emit("setup-error", message="Installed device identity is invalid")
        return 2
    try:
        path = config / ".storage/cook4me" / entry_id / ".config/cook4me/aws.json"
        credentials = json.loads(path.read_text())
        if expiration_timestamp(credentials.get("Expiration")) <= time.time() + args.seconds + 30:
            emit("setup-error", message="Cached cloud credentials expire too soon. Let the HA connection refresh, then rerun.")
            return 2
        source = config / "custom_components/cook4me/vendor/cook4me_phonefree.py"
        spec = importlib.util.spec_from_file_location("cook4me_observer_client", source)
        client = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(client)
        client.set_device_uuid(identifier)
        guard_publishes(client, identifier)
        emit("client", sha256=hashlib.sha256(source.read_bytes()).hexdigest(), appVersion=entry.get("data", {}).get("app_version", "unknown"))
        return 0 if observe(client, client.read_apk_config(None), credentials, identifier, args.seconds) else 2
    except Exception as exc:
        emit("setup-error", message="Cannot use the installed client's cached credentials", errorType=type(exc).__name__)
        return 2


def capture_host(args, run):
    command = ["docker", "exec", "--user", "0", "--interactive", args.container, "python", "-B", "-", "--inside", "--seconds", str(args.seconds)]
    if args.device is not None:
        command += ["--device", str(args.device)]
    # stdin is the reviewed observer source, never credentials or shell code.
    with tempfile.TemporaryFile() as source, tempfile.TemporaryFile() as errors:
        source.write(Path(__file__).read_bytes())
        source.seek(0)
        process = subprocess.Popen(command, stdin=source, stdout=subprocess.PIPE, stderr=errors, bufsize=0)
        selector = selectors.DefaultSelector()
        selector.register(process.stdout, selectors.EVENT_READ)
        deadline = time.monotonic() + args.seconds + 70
        buffered = b""
        with (run / "events.jsonl").open("w") as output:
            while time.monotonic() < deadline:
                ready = selector.select(timeout=1)
                if not ready and process.poll() is not None:
                    break
                for _key, _mask in ready:
                    chunk = os.read(process.stdout.fileno(), 65536)
                    if not chunk:
                        selector.unregister(process.stdout)
                        break
                    buffered += chunk
                    while b"\n" in buffered:
                        line, buffered = buffered.split(b"\n", 1)
                        try:
                            item = json.loads(line)
                        except (ValueError, UnicodeError):
                            continue  # Discard unstructured vendor output.
                        if not isinstance(item, dict) or item.get("event") not in {
                            "client", "subscriptions", "subscription-unavailable", "observing", "mqtt",
                            "oversized-event", "finished", "capture-error", "setup-error"}:
                            continue
                        output.write(json.dumps(item) + "\n")
                        output.flush()
                        if item.get("event") == "observing":
                            print(f"Observing for {args.seconds} seconds. On the cooker, change brightness, wait 15 seconds, then restore it.", flush=True)
                            print("If sound volume is available, change it, wait 15 seconds, then restore it. Leave cooking stopped.", flush=True)
                        elif item.get("event") == "setup-error":
                            print(item.get("message", "Probe setup failed"), flush=True)
                    if len(buffered) > 2000000:
                        buffered = b""  # Drop an oversized incomplete record.
                if not selector.get_map():
                    break
        selector.close()
        if process.poll() is None:
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
        return process.returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inside", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--container", default="homeassistant")
    parser.add_argument("--seconds", type=int, default=180)
    parser.add_argument("--device", type=int)
    parser.add_argument("--source-root", type=Path, default=Path("/home/chreece/cook4me-re/jadx-phonefree/sources"))
    parser.add_argument("--output-dir", type=Path, default=Path("/home/chreece/project/cook4me/downloads"))
    args = parser.parse_args()
    if not 30 <= args.seconds <= 300:
        parser.error("--seconds must be between 30 and 300")
    if args.inside:
        return inside(args)
    os.umask(0o077)
    created_dirs = []
    parent = args.output_dir
    while not parent.exists():
        created_dirs.append(parent)
        parent = parent.parent
    args.output_dir.mkdir(parents=True, exist_ok=True)
    if os.geteuid() == 0 and os.environ.get("SUDO_UID", "").isdigit() and os.environ.get("SUDO_GID", "").isdigit():
        for directory in created_dirs:
            os.chown(directory, int(os.environ["SUDO_UID"]), int(os.environ["SUDO_GID"]))
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    bundle = args.output_dir / f"cook4me-device-controls-{stamp}-{uuid4().hex[:6]}.zip"
    print("Reading the installed Cook4Me connection. No installation or restart is needed.", flush=True)
    with tempfile.TemporaryDirectory(prefix="cook4me-observe-") as temp:
        run = Path(temp)
        try:
            result = capture_host(args, run)
        except (OSError, subprocess.SubprocessError) as exc:
            result = 2
            print(f"Cannot run the HA-container observer ({type(exc).__name__}). Collecting available app-source clues.", flush=True)
        print("Collecting bounded app-source clues...", flush=True)
        clues = source_clues(args.source_root)
        (run / "app-source-clues.json").write_text(json.dumps(clues, indent=2))
        report = {"kind": KIND, "deviceMutations": 0, "captureExit": result,
                  "requestedSeconds": args.seconds, "appSourcePresent": clues["present"],
                  "sourceMatches": len(clues["matches"]), "sourceScanTruncated": clues["truncated"],
                  "remoteControlVerified": False,
                  "interpretation": "Observed fields and app symbols are candidates only. Cloud acceptance is not proof of appliance execution."}
        (run / "report.json").write_text(json.dumps(report, indent=2))
        with zipfile.ZipFile(bundle, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for name in ("events.jsonl", "app-source-clues.json", "report.json"):
                if (run / name).exists():
                    archive.write(run / name, name)
    # sudo-created result should be readable by the invoking user.
    if os.geteuid() == 0 and os.environ.get("SUDO_UID", "").isdigit() and os.environ.get("SUDO_GID", "").isdigit():
        os.chown(bundle, int(os.environ["SUDO_UID"]), int(os.environ["SUDO_GID"]))
    print(f"Upload this ZIP: {bundle}", flush=True)
    return 0 if result == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
