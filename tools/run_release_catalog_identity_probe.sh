#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${COOK4ME_CATALOG_STATE_DIR:-$ROOT/.catalog-build}"
VENV="$STATE_DIR/venv"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$STATE_DIR/identity-probes/$STAMP"
RESULT_DIR="$STATE_DIR/results"
mkdir -p "$RUN_DIR" "$RESULT_DIR"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

find_storage_home() {
  if [[ -n "${COOK4ME_STORAGE_HOME:-}" && -f "${COOK4ME_STORAGE_HOME}/.config/cook4me/tokens.json" ]]; then
    printf '%s\n' "$COOK4ME_STORAGE_HOME"
    return 0
  fi
  local candidates=()
  local ha_config="${COOK4ME_HA_CONFIG:-/home/chreece/homeassistant/config}"
  if [[ -d "$ha_config/.storage/cook4me" ]]; then
    while IFS= read -r -d '' path; do candidates+=("$path"); done < <(
      find "$ha_config/.storage/cook4me" -type f -path '*/.config/cook4me/tokens.json' -print0 2>/dev/null || true
    )
  fi
  [[ -f "$HOME/.config/cook4me/tokens.json" ]] && candidates+=("$HOME/.config/cook4me/tokens.json")
  ((${#candidates[@]})) || return 1
  local newest="" newest_mtime=0 path mtime
  for path in "${candidates[@]}"; do
    mtime="$(stat -c %Y "$path" 2>/dev/null || printf '0')"
    if ((mtime >= newest_mtime)); then newest_mtime="$mtime"; newest="$path"; fi
  done
  [[ -n "$newest" ]] || return 1
  printf '%s\n' "${newest%/.config/cook4me/tokens.json}"
}

find_catalog() {
  if [[ -n "${COOK4ME_CAPTURE_CATALOG:-}" && -s "${COOK4ME_CAPTURE_CATALOG}" ]]; then
    printf '%s\n' "$COOK4ME_CAPTURE_CATALOG"
    return 0
  fi
  find "$STATE_DIR/runs" -type f -name merged_catalog.v1.json -print0 2>/dev/null \
    | xargs -0 -r ls -1t 2>/dev/null \
    | head -1
}

STORAGE_HOME="$(find_storage_home || true)"
CATALOG="$(find_catalog || true)"
[[ -n "$STORAGE_HOME" ]] || fail "No existing Cook4Me token store was found."
[[ -n "$CATALOG" && -s "$CATALOG" ]] || fail "No prior release-catalog capture was found under $STATE_DIR/runs."
[[ -x "$VENV/bin/python" ]] || fail "Catalog capture venv not found. Run the exhaustive capture first."

OUT="$RUN_DIR/identity-probe.json"
LOG="$RUN_DIR/probe.log"
META="$RUN_DIR/run-meta.txt"
BUNDLE="$RESULT_DIR/cook4me-release-catalog-identity-probe-$STAMP.zip"

printf 'Cook4Me multilingual identity probe\n'
printf 'Using prior capture: %s\n' "$CATALOG"
printf 'Inspecting representative cross-language and unkeyed-ingredient recipes...\n'

set +e
"$VENV/bin/python" "$ROOT/tools/probe_release_catalog_identity.py" \
  --storage-home "$STORAGE_HOME" \
  --catalog "$CATALOG" \
  --output "$OUT" \
  --configured-language "${COOK4ME_CONFIGURED_LANGUAGE:-de}" \
  --configured-country "${COOK4ME_CONFIGURED_COUNTRY:-DE}" \
  >"$LOG" 2>&1
RC=$?
set -e
[[ "$RC" -eq 0 || "$RC" -eq 2 ]] || { tail -n 40 "$LOG" >&2 || true; fail "Identity probe failed (exit $RC)."; }
[[ -s "$OUT" ]] || fail "Identity probe produced no output."

{
  printf 'timestamp=%s\n' "$STAMP"
  printf 'branch=%s\n' "$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
  printf 'commit=%s\n' "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
  printf 'catalog=%s\n' "$CATALOG"
  printf 'token_material_in_bundle=no\n'
  printf 'read_only=yes\n'
} >"$META"

(
  cd "$RUN_DIR"
  zip -q "$BUNDLE" identity-probe.json probe.log run-meta.txt
)

"$VENV/bin/python" - "$OUT" "$BUNDLE" <<'PY'
import json, sys
report=json.load(open(sys.argv[1], encoding='utf-8'))
summary=report['summary']
selection=report['selection']
print(f"SELECTED_VARIANTS={summary['selectedVariants']}")
print(f"FETCHED={summary['fetched']}")
print(f"FAILED={summary['failed']}")
print(f"SIMPLE_COVER_CLUSTERS={selection['simpleClusterCandidates']}")
print(f"AMBIGUOUS_COVER_CLUSTERS={selection['ambiguousClusterCandidates']}")
print(f"CROSS_LANGUAGE_NO_ENGLISH={selection['crossLanguageNoEnglishCandidates']}")
print(f"RESULT_BUNDLE={sys.argv[2]}")
PY
