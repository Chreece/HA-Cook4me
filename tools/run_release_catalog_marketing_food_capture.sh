#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${COOK4ME_CATALOG_STATE_DIR:-$ROOT/.catalog-build}"
VENV="$STATE_DIR/venv"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$STATE_DIR/marketing-food-runs/$STAMP"
RESULT_DIR="$STATE_DIR/results"
OUT="$RUN_DIR/marketing-foods-v2.json"
LOG="$RUN_DIR/capture.log"
META="$RUN_DIR/run-meta.txt"
BUNDLE="$RESULT_DIR/cook4me-marketing-foods-v2-$STAMP.zip"
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

STORAGE_HOME="$(find_storage_home || true)"
[[ -n "$STORAGE_HOME" ]] || fail "No existing Cook4Me token store was found."

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV" >/dev/null 2>&1 || fail "python3-venv is required."
fi
"$VENV/bin/python" -m pip install --disable-pip-version-check -q "curl-cffi==0.13.0" \
  >"$RUN_DIR/pip.log" 2>&1 || fail "Could not install the isolated curl-cffi dependency."

printf 'Cook4Me SEB marketing-food dictionary capture\n'
printf 'Querying all 28 audited language/market mappings...\n'

set +e
"$VENV/bin/python" "$ROOT/tools/capture_marketing_food_catalogs_v2.py" \
  --storage-home "$STORAGE_HOME" \
  --output "$OUT" \
  --configured-language "${COOK4ME_CONFIGURED_LANGUAGE:-de}" \
  --configured-country "${COOK4ME_CONFIGURED_COUNTRY:-DE}" \
  >"$LOG" 2>&1
RC=$?
set -e
[[ "$RC" -eq 0 || "$RC" -eq 2 ]] || { tail -n 60 "$LOG" >&2 || true; fail "Marketing-food capture failed (exit $RC)."; }
[[ -s "$OUT" ]] || fail "Marketing-food capture produced no output."

SUMMARY="$($VENV/bin/python - "$OUT" <<'PY'
import json, sys
p=json.load(open(sys.argv[1], encoding='utf-8'))
cs=p['catalogs']
print(f"CAPTURED_CATALOGS={len(cs)}")
print(f"POPULATED_CATALOGS={sum(r['state']=='POPULATED' for r in cs)}")
print(f"EMPTY_CATALOGS={sum(r['state']=='EMPTY' for r in cs)}")
print(f"TRUNCATED_CATALOGS={sum(r['state']=='TRUNCATED' for r in cs)}")
print(f"ERROR_CATALOGS={sum(r['state']=='ERROR' for r in cs)}")
print(f"LOCALIZED_FOOD_ROWS={sum(len(r.get('items') or []) for r in cs)}")
print(f"UNIQUE_FOOD_KEYS={len({i['key'] for r in cs for i in (r.get('items') or []) if i.get('key')})}")
print(f"ENGLISH_FOOD_KEYS={len({i['key'] for r in cs if r.get('language')=='en' for i in (r.get('items') or []) if i.get('key')})}")
PY
)"
printf '%s\n' "$SUMMARY"

{
  printf 'timestamp=%s\n' "$STAMP"
  printf 'branch=%s\n' "$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
  printf 'commit=%s\n' "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
  printf 'capture_exit=%s\n' "$RC"
  printf 'read_only=yes\n'
  printf 'token_material_in_bundle=no\n'
  printf 'secrets_persisted=no\n'
} >"$META"

(
  cd "$RUN_DIR"
  zip -q "$BUNDLE" marketing-foods-v2.json capture.log run-meta.txt
)

printf 'RESULT_BUNDLE=%s\n' "$BUNDLE"
