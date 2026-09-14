#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${COOK4ME_CATALOG_STATE_DIR:-$ROOT/.catalog-build}"
VENV="$STATE_DIR/venv"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$STATE_DIR/family-identity-probes/$STAMP"
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

find_identity_probe() {
  if [[ -n "${COOK4ME_IDENTITY_PROBE:-}" && -s "${COOK4ME_IDENTITY_PROBE}" ]]; then
    printf '%s\n' "$COOK4ME_IDENTITY_PROBE"
    return 0
  fi
  find "$STATE_DIR/identity-probes" -type f -name identity-probe.json -print0 2>/dev/null \
    | xargs -0 -r ls -1t 2>/dev/null \
    | head -1
}

STORAGE_HOME="$(find_storage_home || true)"
IDENTITY_PROBE="$(find_identity_probe || true)"
[[ -n "$STORAGE_HOME" ]] || fail "No existing Cook4Me token store was found."
[[ -n "$IDENTITY_PROBE" && -s "$IDENTITY_PROBE" ]] || fail "No prior identity probe was found under $STATE_DIR/identity-probes."
[[ -x "$VENV/bin/python" ]] || fail "Catalog capture venv not found. Run the exhaustive capture first."

OUT="$RUN_DIR/family-identity-probe.json"
LOG="$RUN_DIR/probe.log"
META="$RUN_DIR/run-meta.txt"
BUNDLE="$RESULT_DIR/cook4me-release-catalog-family-identity-probe-$STAMP.zip"

printf 'Cook4Me family identity probe\n'
printf 'Using prior identity probe: %s\n' "$IDENTITY_PROBE"
printf 'Inspecting provider-native parent/reference IDs and media identities...\n'

set +e
"$VENV/bin/python" "$ROOT/tools/probe_release_catalog_family_identity.py" \
  --storage-home "$STORAGE_HOME" \
  --identity-probe "$IDENTITY_PROBE" \
  --output "$OUT" \
  --configured-language "${COOK4ME_CONFIGURED_LANGUAGE:-de}" \
  --configured-country "${COOK4ME_CONFIGURED_COUNTRY:-DE}" \
  >"$LOG" 2>&1
RC=$?
set -e
[[ "$RC" -eq 0 || "$RC" -eq 2 ]] || { tail -n 40 "$LOG" >&2 || true; fail "Family identity probe failed (exit $RC)."; }
[[ -s "$OUT" ]] || fail "Family identity probe produced no output."

{
  printf 'timestamp=%s\n' "$STAMP"
  printf 'branch=%s\n' "$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
  printf 'commit=%s\n' "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
  printf 'identity_probe=%s\n' "$IDENTITY_PROBE"
  printf 'token_material_in_bundle=no\n'
  printf 'read_only=yes\n'
} >"$META"

(
  cd "$RUN_DIR"
  zip -q "$BUNDLE" family-identity-probe.json probe.log run-meta.txt
)

"$VENV/bin/python" - "$OUT" "$BUNDLE" <<'PY'
import json, sys
r=json.load(open(sys.argv[1], encoding='utf-8'))
s=r['summary']
print(f"SELECTED_VARIANTS={s['selectedVariants']}")
print(f"FETCHED={s['fetched']}")
print(f"FAILED={s['failed']}")
for key, value in s.get('fieldRelations', {}).items():
    print(f"FIELD_{key.replace(':','_').upper()}={value}")
print(f"RESULT_BUNDLE={sys.argv[2]}")
PY
