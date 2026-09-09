#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${COOK4ME_CATALOG_STATE_DIR:-$ROOT/.catalog-build}"
VENV="$STATE_DIR/venv"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$STATE_DIR/v2-runs/$STAMP"
RESULT_DIR="$STATE_DIR/results"
CACHE_DB="$STATE_DIR/provider-cache-v2.sqlite3"
CAPTURE="$RUN_DIR/provider-capture-v2.json.gz"
FAILURES="$RUN_DIR/failures.json"
LOG="$RUN_DIR/crawl.log"
META="$RUN_DIR/run-meta.txt"
BUNDLE="$RESULT_DIR/cook4me-release-catalog-v2-capture-$STAMP.zip"
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

printf 'Cook4Me release catalog v2 provider capture\n'
printf 'Auditing all 28 language/market mappings.\n'
printf 'Detail cache: %s\n' "$CACHE_DB"
printf 'The crawl is resumable; successful details are not downloaded again.\n'

ARGS=(
  "$ROOT/tools/crawl_release_catalog_v2.py"
  --storage-home "$STORAGE_HOME"
  --cache-db "$CACHE_DB"
  --output "$CAPTURE"
  --failures "$FAILURES"
  --configured-language "${COOK4ME_CONFIGURED_LANGUAGE:-de}"
  --configured-country "${COOK4ME_CONFIGURED_COUNTRY:-DE}"
  --workers "${COOK4ME_CATALOG_WORKERS:-4}"
  --verbose
)
[[ "${COOK4ME_REFRESH_V2_DETAILS:-0}" == "1" ]] && ARGS+=(--refresh-details)

set +e
"$VENV/bin/python" "${ARGS[@]}" >"$LOG" 2>&1
RC=$?
set -e
[[ "$RC" -eq 0 || "$RC" -eq 2 ]] || { tail -n 60 "$LOG" >&2 || true; fail "v2 provider crawl failed (exit $RC)."; }
[[ -s "$CAPTURE" ]] || fail "v2 provider crawl produced no capture."

SUMMARY="$($VENV/bin/python - "$CAPTURE" <<'PY'
import gzip, json, sys
with gzip.open(sys.argv[1], 'rt', encoding='utf-8') as f:
    p=json.load(f)
cs=p['source']['catalogs']
print(f"AUDITED_CATALOGS={len(cs)}")
print(f"POPULATED_CATALOGS={sum(r['state']=='POPULATED' for r in cs)}")
print(f"EMPTY_CATALOGS={sum(r['state']=='EMPTY' for r in cs)}")
print(f"SEARCH_ROWS={sum(int(r['searchRows']) for r in cs)}")
print(f"HYDRATED_DETAILS={len(p['details'])}")
print(f"STALE_SEARCH_ONLY={len(p['staleSearchOnly'])}")
print(f"UNRESOLVED={sum(int(r['unresolvedVariants']) for r in cs)}")
weights=0
keyed=0
unkeyed=0
for d in p['details']:
    for i in d.get('ingredients') or []:
        if i.get('foodKey'): keyed += 1
        else: unkeyed += 1
        w=i.get('weight') or {}
        u=w.get('unit') or {}
        if w.get('quantity') is not None and (u.get('key')=='UNIT_27' or str(u.get('abbreviation') or '').lower()=='g'):
            weights += 1
print(f"INGREDIENT_LINES_KEYED={keyed}")
print(f"INGREDIENT_LINES_UNKEYED={unkeyed}")
print(f"INGREDIENT_LINES_WITH_SEB_GRAMS={weights}")
PY
)"
printf '%s\n' "$SUMMARY"

{
  printf 'timestamp=%s\n' "$STAMP"
  printf 'branch=%s\n' "$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
  printf 'commit=%s\n' "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
  printf 'cache_db=%s\n' "$CACHE_DB"
  printf 'crawler_exit=%s\n' "$RC"
  printf 'read_only=yes\n'
  printf 'token_material_in_bundle=no\n'
  printf 'secrets_persisted=no\n'
} >"$META"

# The SQLite cache remains local because it is a resumable maintenance cache.
# The gzip capture contains only provider recipe/catalog facts and no secrets.
(
  cd "$RUN_DIR"
  files=(provider-capture-v2.json.gz crawl.log run-meta.txt)
  [[ -s failures.json ]] && files+=(failures.json)
  zip -q "$BUNDLE" "${files[@]}"
)

printf 'RESULT_BUNDLE=%s\n' "$BUNDLE"
