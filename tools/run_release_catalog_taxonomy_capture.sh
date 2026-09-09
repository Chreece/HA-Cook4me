#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${COOK4ME_CATALOG_STATE_DIR:-$ROOT/.catalog-build}"
VENV="$STATE_DIR/venv"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$STATE_DIR/taxonomy-runs/$STAMP"
RESULT_DIR="$STATE_DIR/results"
CACHE_DB="$STATE_DIR/provider-taxonomy-v2.sqlite3"
OUT="$RUN_DIR/provider-taxonomy-v2.json.gz"
FAILURES="$RUN_DIR/failures.json"
LOG="$RUN_DIR/capture.log"
META="$RUN_DIR/run-meta.txt"
BUNDLE="$RESULT_DIR/cook4me-release-taxonomy-v2-$STAMP.zip"
mkdir -p "$RUN_DIR" "$RESULT_DIR"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

latest_file() {
  local pattern="$1" base path newest="" newest_mtime=0 mtime
  shift
  for base in "$@"; do
    [[ -d "$base" ]] || continue
    while IFS= read -r -d '' path; do
      mtime="$(stat -c %Y "$path" 2>/dev/null || printf '0')"
      if ((mtime >= newest_mtime)); then newest_mtime="$mtime"; newest="$path"; fi
    done < <(find "$base" -type f -name "$pattern" -print0 2>/dev/null || true)
  done
  [[ -n "$newest" ]] || return 1
  printf '%s\n' "$newest"
}

find_storage_home() {
  if [[ -n "${COOK4ME_STORAGE_HOME:-}" && -f "${COOK4ME_STORAGE_HOME}/.config/cook4me/tokens.json" ]]; then
    printf '%s\n' "$COOK4ME_STORAGE_HOME"; return 0
  fi
  local candidates=() newest="" newest_mtime=0 path mtime
  local ha_config="${COOK4ME_HA_CONFIG:-/home/chreece/homeassistant/config}"
  if [[ -d "$ha_config/.storage/cook4me" ]]; then
    while IFS= read -r -d '' path; do candidates+=("$path"); done < <(
      find "$ha_config/.storage/cook4me" -type f -path '*/.config/cook4me/tokens.json' -print0 2>/dev/null || true
    )
  fi
  [[ -f "$HOME/.config/cook4me/tokens.json" ]] && candidates+=("$HOME/.config/cook4me/tokens.json")
  ((${#candidates[@]})) || return 1
  for path in "${candidates[@]}"; do
    mtime="$(stat -c %Y "$path" 2>/dev/null || printf '0')"
    if ((mtime >= newest_mtime)); then newest_mtime="$mtime"; newest="$path"; fi
  done
  [[ -n "$newest" ]] || return 1
  printf '%s\n' "${newest%/.config/cook4me/tokens.json}"
}

PROVIDER="${COOK4ME_PROVIDER_CAPTURE:-}"
if [[ -z "$PROVIDER" ]]; then
  PROVIDER="$(latest_file 'provider-capture-v2.json.gz' "$STATE_DIR/v2-runs" || true)"
fi
if [[ -z "$PROVIDER" ]]; then
  PROVIDER="$(latest_file 'cook4me-release-catalog-v2-capture-*.zip' "$RESULT_DIR" || true)"
fi
[[ -n "$PROVIDER" && -f "$PROVIDER" ]] || fail "No reviewed provider-capture v2 was found."

STORAGE_HOME="$(find_storage_home || true)"
[[ -n "$STORAGE_HOME" ]] || fail "No existing Cook4Me token store was found."

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV" >/dev/null 2>&1 || fail "python3-venv is required."
fi
"$VENV/bin/python" -m pip install --disable-pip-version-check -q "curl-cffi==0.13.0" \
  >"$RUN_DIR/pip.log" 2>&1 || fail "Could not install isolated curl-cffi dependency."

printf 'Cook4Me recipe taxonomy capture\n'
printf 'Reusing reviewed provider variant IDs; only taxonomy fields are persisted.\n'
printf 'The SQLite cache makes this pass resumable.\n'

ARGS=(
  --provider-capture "$PROVIDER"
  --storage-home "$STORAGE_HOME"
  --cache-db "$CACHE_DB"
  --output "$OUT"
  --failures "$FAILURES"
  --configured-language "${COOK4ME_CONFIGURED_LANGUAGE:-de}"
  --configured-country "${COOK4ME_CONFIGURED_COUNTRY:-DE}"
  --workers "${COOK4ME_TAXONOMY_WORKERS:-4}"
  --limit "${COOK4ME_TAXONOMY_LIMIT:-0}"
)
[[ "${COOK4ME_TAXONOMY_REFRESH:-0}" == "1" ]] && ARGS+=(--refresh)

set +e
"$VENV/bin/python" "$ROOT/tools/capture_release_catalog_taxonomy_v2.py" "${ARGS[@]}" >"$LOG" 2>&1
RC=$?
set -e
[[ "$RC" -eq 0 || "$RC" -eq 2 ]] || { tail -n 80 "$LOG" >&2 || true; fail "Taxonomy capture failed (exit $RC)."; }
[[ -s "$OUT" ]] || fail "Taxonomy capture produced no output."

SUMMARY="$($VENV/bin/python - "$OUT" "$FAILURES" <<'PY'
import gzip,json,sys
with gzip.open(sys.argv[1],'rt',encoding='utf-8') as f: p=json.load(f)
fail=json.load(open(sys.argv[2],encoding='utf-8'))
rows=p.get('variants') or []
print(f"SOURCE_VARIANTS={p.get('sourceVariantCount',0)}")
print(f"CAPTURED_VARIANTS={p.get('capturedVariantCount',0)}")
print(f"FAILURES={len(fail)}")
print(f"COMPLETE={str(bool(p.get('complete'))).lower()}")
print(f"WITH_COURSES={sum(bool(r.get('courses')) for r in rows)}")
print(f"WITH_OCCASIONS={sum(bool(r.get('occasions')) for r in rows)}")
print(f"WITH_EXCLUDED_FOODS={sum(bool(r.get('excludedFoods')) for r in rows)}")
print(f"WITH_DETECTED_EXCLUDED_FOODS={sum(bool(r.get('detectedExcludedFoods')) for r in rows)}")
print(f"WITH_CLASSIFICATIONS={sum(bool(r.get('classifications')) for r in rows)}")
PY
)"
printf '%s\n' "$SUMMARY"

{
  printf 'timestamp=%s\n' "$STAMP"
  printf 'branch=%s\n' "$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
  printf 'commit=%s\n' "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
  printf 'provider_capture=%s\n' "$PROVIDER"
  printf 'taxonomy_cache=%s\n' "$CACHE_DB"
  printf 'read_only=yes\n'
  printf 'full_recipe_detail_persisted=no\n'
  printf 'token_material_in_bundle=no\n'
  printf 'secrets_persisted=no\n'
} >"$META"

(
  cd "$RUN_DIR"
  zip -q "$BUNDLE" provider-taxonomy-v2.json.gz failures.json capture.log run-meta.txt
)

printf 'RESULT_BUNDLE=%s\n' "$BUNDLE"
exit "$RC"
