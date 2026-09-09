#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${COOK4ME_CATALOG_STATE_DIR:-$ROOT/.catalog-build}"
VENV="$STATE_DIR/venv"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$STATE_DIR/failure-probes/$STAMP"
RESULT_DIR="$STATE_DIR/results"
OUTPUT="$RUN_DIR/failure-probe.json"
LOG="$RUN_DIR/probe.log"
BUNDLE="$RESULT_DIR/cook4me-release-catalog-failure-probe-$STAMP.zip"

mkdir -p "$RUN_DIR" "$RESULT_DIR"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

LATEST_CAPTURE="${COOK4ME_PREVIOUS_CATALOG_RUN:-}"
if [[ -z "$LATEST_CAPTURE" ]]; then
  LATEST_CAPTURE="$(find "$STATE_DIR/runs" -mindepth 1 -maxdepth 1 -type d -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2- || true)"
fi
[[ -n "$LATEST_CAPTURE" && -f "$LATEST_CAPTURE/build.log" ]] \
  || fail "No previous catalog capture with build.log was found."

find_storage_home() {
  if [[ -n "${COOK4ME_STORAGE_HOME:-}" && -f "${COOK4ME_STORAGE_HOME}/.config/cook4me/tokens.json" ]]; then
    printf '%s\n' "$COOK4ME_STORAGE_HOME"
    return 0
  fi
  local candidates=()
  local ha_config="${COOK4ME_HA_CONFIG:-/home/chreece/homeassistant/config}"
  if [[ -d "$ha_config/.storage/cook4me" ]]; then
    while IFS= read -r -d '' path; do
      candidates+=("$path")
    done < <(find "$ha_config/.storage/cook4me" -type f -path '*/.config/cook4me/tokens.json' -print0 2>/dev/null || true)
  fi
  [[ -f "$HOME/.config/cook4me/tokens.json" ]] && candidates+=("$HOME/.config/cook4me/tokens.json")
  ((${#candidates[@]})) || return 1

  local newest="" newest_mtime=0 path mtime
  for path in "${candidates[@]}"; do
    mtime="$(stat -c %Y "$path" 2>/dev/null || printf '0')"
    if ((mtime >= newest_mtime)); then
      newest_mtime="$mtime"
      newest="$path"
    fi
  done
  [[ -n "$newest" ]] || return 1
  printf '%s\n' "${newest%/.config/cook4me/tokens.json}"
}

STORAGE_HOME="$(find_storage_home || true)"
[[ -n "$STORAGE_HOME" ]] || fail "No existing Cook4Me token store was found."
[[ -x "$VENV/bin/python" ]] || fail "Catalog capture venv is missing. Run tools/run_release_catalog_capture.sh first."

printf 'Cook4Me failed-publication probe\n'
printf 'Rechecking only the detail IDs that failed the first exhaustive crawl...\n'

"$VENV/bin/python" "$ROOT/tools/probe_release_catalog_failures.py" \
  --storage-home "$STORAGE_HOME" \
  --build-log "$LATEST_CAPTURE/build.log" \
  --output "$OUTPUT" \
  --configured-language "${COOK4ME_CONFIGURED_LANGUAGE:-de}" \
  --configured-country "${COOK4ME_CONFIGURED_COUNTRY:-DE}" \
  --workers "${COOK4ME_PROBE_WORKERS:-6}" \
  >"$LOG" 2>&1 || {
    tail -n 40 "$LOG" >&2 || true
    fail "Failure probe did not complete. Full log: $LOG"
  }

python3 - "$OUTPUT" <<'PY'
import json, sys
r=json.load(open(sys.argv[1], encoding='utf-8'))['summary']
print(f"AFFECTED_CATALOGS={r['affectedCatalogs']}")
print(f"FAILED_IDS={r['failedVariantIds']}")
print(f"SEARCH_ROWS_RECOVERED={r['searchRowsRecovered']}")
print(f"DETAIL_RECOVERED={r['detailRecovered']}")
print(f"DETAIL_STILL_UNAVAILABLE={r['detailStillUnavailable']}")
print("STATUS_SIGNATURES=" + json.dumps(r['statusSignatures'], ensure_ascii=False, separators=(',',':')))
PY

cat >"$RUN_DIR/run-meta.txt" <<EOF
capture_run=$(basename "$LATEST_CAPTURE")
branch=$(git -C "$ROOT" branch --show-current 2>/dev/null || true)
commit=$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)
token_material_in_bundle=no
read_only=yes
EOF

(
  cd "$RUN_DIR"
  zip -q "$BUNDLE" failure-probe.json probe.log run-meta.txt
)

printf 'RESULT_BUNDLE=%s\n' "$BUNDLE"
