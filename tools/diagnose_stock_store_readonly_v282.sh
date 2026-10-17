#!/usr/bin/env bash
# Read-only Cook4Me inventory-store forensics with private point-in-time copies.
# Never modifies Home Assistant config, stores, services, VPN, or SSH.
set -Eeuo pipefail
set +x
umask 077
if [[ $EUID -eq 0 ]]; then
  echo "Run as your normal SSH user, not as root; sudo is used only for protected store reads."
  exit 1
fi
for command in python3 sudo tar date mktemp chmod chown mkdir; do
  command -v "$command" >/dev/null || { echo "Missing command: $command"; exit 1; }
done
CONFIG=/home/chreece/homeassistant/config
STORAGE="$CONFIG/.storage"
[[ -d "$STORAGE" && -f "$CONFIG/configuration.yaml" ]] || {
  echo "Cook4Me audit cannot locate the expected Home Assistant configuration."
  exit 1
}
LOG_DIR="$HOME/projects/cook4me/logs"
PRIVATE_DIR="$HOME/projects/cook4me/recovery"
mkdir -p "$LOG_DIR" "$PRIVATE_DIR"
chmod 700 "$PRIVATE_DIR"
STAMP=$(date -u +%Y%m%d-%H%M%S)
REPORT="$LOG_DIR/cook4me-stock-diagnostic-$STAMP.tar.gz"
SNAPSHOT="$PRIVATE_DIR/PRIVATE-DO-NOT-UPLOAD-stock-snapshot-$STAMP.tar.gz"
WORK=$(mktemp -d /tmp/cook4me-stock-audit-XXXXXX)
trap 'rm -rf -- "$WORK"' EXIT

echo "Reading Home Assistant Cook4Me stores; no storage files will be changed."
sudo -v || exit 1
sudo python3 - "$CONFIG" "$SNAPSHOT" > "$WORK/diagnostic.txt" <<'PY'
from __future__ import annotations
from collections import defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import os
import re
import stat
import sys
import tarfile

config = Path(sys.argv[1])
storage = config / ".storage"
private_snapshot = Path(sys.argv[2])
MAX_STORE_BYTES = 80 * 1024 * 1024
MAX_STORES = 200

def note(*parts):
    print(*parts, flush=True)

def fingerprint(s):
    return sha256(str(s).encode()).hexdigest()[:12]

def modified(ts):
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")

entries = []
try:
    obj = json.loads((storage / "core.config_entries").read_bytes())
    records = obj.get("data", {}).get("entries", [])
    entries = [r for r in records if isinstance(r, dict) and r.get("domain") == "cook4me"]
    note("CURRENT_COOK4ME_CONFIG_ENTRIES", len(entries))
except Exception as e:
    note("CURRENT_CONFIG_ENTRY_STATUS", "UNREADABLE", type(e).__name__)

current_ids = set()
for record in entries:
    ident = str(record.get("entry_id") or "")
    if not ident:
        continue
    current_ids.add(ident)
    has_device = isinstance(record.get("data"), dict) and bool(record["data"].get("device_uuid"))
    note("ACTIVE_ENTRY", "id_hash="+fingerprint(ident), "device_id_present="+str(has_device),
         "disabled="+str(bool(record.get("disabled_by"))))

paths = sorted(
    (
        p for p in storage.iterdir()
        if p.name.startswith("cook4me.") and p.name.endswith(".recipe_hub")
    ),
    key=lambda p: p.name,
)
note("RECIPE_HUB_STORES_FOUND",len(paths))
note("AUDIT_READ_ONLY_HA", True)
if len(paths) > MAX_STORES:
    note("ERROR", "Too many Cook4Me stores; no snapshot taken")
    sys.exit(2)

counts = defaultdict(lambda: {"files": 0, "items": 0, "lots": 0})
snapshot_count = 0
errors = 0
with tarfile.open(private_snapshot, mode="w:gz", format=tarfile.PAX_FORMAT) as archive:
    for path in paths:
        ident = path.name[len("cook4me."):-len(".recipe_hub")]
        marker = "CURRENT" if ident in current_ids else "OTHER_OR_OLD"
        try:
            st = path.lstat()
            if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_STORE_BYTES:
                note("STORE_SKIPPED", "id_hash="+fingerprint(ident), "reason=unsafe_type_or_size")
                errors += 1
                continue
            flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(path, flags)
            with os.fdopen(fd, "rb") as infile:
                raw = infile.read(MAX_STORE_BYTES + 1)
            if len(raw) > MAX_STORE_BYTES:
                raise ValueError("Store exceeds safe read size")
            ti = tarfile.TarInfo(path.name)
            ti.size = len(raw)
            ti.mtime = int(st.st_mtime)
            ti.mode = 0o600
            ti.uid = ti.gid = 0
            archive.addfile(ti, BytesIO(raw))
            snapshot_count += 1

            record = json.loads(raw)
            body = record.get("data") if isinstance(record, dict) else None
            profile = body.get("profile") if isinstance(body, dict) else None
            product_rows = profile.get("houseIngredients") if isinstance(profile, dict) else None
            pantry = profile.get("pantry") if isinstance(profile, dict) else None
            storage_places = profile.get("storageLocations") if isinstance(profile, dict) else None
            count = len(product_rows) if isinstance(product_rows, list) else -1
            lots = sum(
                len(row.get("lots") or [])
                for row in (product_rows if isinstance(product_rows, list) else [])
                if isinstance(row, dict) and isinstance(row.get("lots"), list)
            )
            unlimited = sum(
                row.get("unlimited") is True
                for row in (product_rows if isinstance(product_rows, list) else [])
                if isinstance(row, dict)
            )
            menu_recipes = len(body.get("recipes") or []) if isinstance(body, dict) else 0
            key = marker
            counts[key]["files"] += 1
            counts[key]["items"] += max(count, 0)
            counts[key]["lots"] += lots
            note(
                "STORE",
                "id_hash="+fingerprint(ident),
                "role="+marker,
                "mtime_utc="+modified(st.st_mtime),
                "bytes="+str(len(raw)),
                "items="+str(count),
                "lots="+str(lots),
                "unlimited="+str(unlimited),
                "pantry_count="+str(len(pantry) if isinstance(pantry,list) else -1),
                "storage_places="+str(len(storage_places) if isinstance(storage_places,list) else -1),
                "saved_recipes="+str(menu_recipes),
                "file_sha12="+sha256(raw).hexdigest()[:12],
            )
        except Exception as e:
            errors += 1
            note("STORE_ERROR", "id_hash="+fingerprint(ident), "kind="+type(e).__name__)
    note("SNAPSHOT_COPIED_STORES",snapshot_count)
    note("STORE_READ_ERRORS",errors)

current = counts["CURRENT"]
old = counts["OTHER_OR_OLD"]
note("TOTAL_CURRENT_PRODUCTS",current["items"])
note("TOTAL_OTHER_OR_OLD_PRODUCTS",old["items"])
if old["items"] and not current["items"]:
    note("DIAGNOSIS_HINT", "OLD_STORE_HAS_PRODUCTS_CURRENT_STORE_EMPTY")
elif current["items"]:
    note("DIAGNOSIS_HINT", "CURRENT_STORE_HAS_PRODUCTS_CHECK_UI_AND_ACTIVE_ENTRY")
elif snapshot_count:
    note("DIAGNOSIS_HINT", "STORES_EXIST_BUT_NO_INVENTORY_ROWS_CHECK_BACKUPS")
else:
    note("DIAGNOSIS_HINT", "NO_STORES_FOUND_CHECK_BACKUPS_OR_CONFIG_ROOT")

# Report metadata about other stores, not account/passwords or product names.
other = [
    p for p in storage.iterdir()
    if p.name.startswith("cook4me") and
    not (p.name.startswith("cook4me.") and p.name.endswith(".recipe_hub"))
]
note("OTHER_COOK4ME_STORAGE_OBJECTS",len(other))
note("RAW_SNAPSHOT_STAYS_ON_SERVER",True)
note("NO_USER_PRODUCT_NAMES_IN_REPORT",True)
PY
sudo chown "$(id -u):$(id -g)" "$SNAPSHOT"
chmod 600 "$SNAPSHOT"
tar -czf "$REPORT" -C "$WORK" diagnostic.txt
chmod 600 "$REPORT"
cat "$WORK/diagnostic.txt"
printf '\nSANITIZED_REPORT=%s\n' "$REPORT"
printf 'PRIVATE_LOCAL_SNAPSHOT=%s\n' "$SNAPSHOT"
echo 'Upload ONLY the SANITIZED_REPORT .tar.gz here. Keep the PRIVATE_LOCAL_SNAPSHOT on your server.'
