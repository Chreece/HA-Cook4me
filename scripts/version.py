#!/usr/bin/env python3
"""Validate or bump HA-Cook4me YYYY.M.D.BUILD versions."""
from __future__ import annotations
import argparse
from datetime import date
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "custom_components/cook4me/manifest.json"
VERSION_RE = re.compile(r"^(?P<year>20\d{2})\.(?P<month>\d{1,2})\.(?P<day>\d{1,2})\.(?P<build>[1-9]\d*)$")


def current() -> str:
    return str(json.loads(MANIFEST.read_text(encoding="utf-8"))["version"])


def validate(value: str) -> None:
    match = VERSION_RE.fullmatch(value)
    if not match:
        raise SystemExit(f"Invalid version {value!r}; expected YYYY.M.D.BUILD")
    try:
        date(int(match['year']), int(match['month']), int(match['day']))
    except ValueError as exc:
        raise SystemExit(f"Invalid calendar date in version {value!r}: {exc}") from exc


def next_version(today: date | None = None) -> str:
    today = today or date.today()
    cur = current()
    validate(cur)
    m = VERSION_RE.fullmatch(cur)
    assert m
    same = (int(m['year']), int(m['month']), int(m['day'])) == (today.year, today.month, today.day)
    build = int(m['build']) + 1 if same else 1
    return f"{today.year}.{today.month}.{today.day}.{build}"


def write_version(value: str) -> None:
    validate(value)
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data["version"] = value
    MANIFEST.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate")
    v.add_argument("--tag")
    n = sub.add_parser("next")
    n.add_argument("--write", action="store_true")
    s = sub.add_parser("set")
    s.add_argument("version")
    args = ap.parse_args()

    if args.cmd == "validate":
        value = current(); validate(value)
        if args.tag and args.tag != value:
            raise SystemExit(f"Tag {args.tag!r} does not match manifest version {value!r}")
        print(value)
    elif args.cmd == "next":
        value = next_version()
        if args.write: write_version(value)
        print(value)
    else:
        write_version(args.version); print(args.version)

if __name__ == "__main__":
    main()
