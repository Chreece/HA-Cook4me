#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${COOK4ME_CATALOG_STATE_DIR:-$ROOT/.catalog-build}"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$STATE_DIR/translation-v2/$STAMP"
RESULT_DIR="$STATE_DIR/results"
CACHE_DB="$STATE_DIR/local-translation-cache-v2.sqlite3"
OUT="$RUN_DIR/translation-results-v2.json.gz"
SUMMARY="$RUN_DIR/summary.json"
FAILURES="$RUN_DIR/failures.json"
META="$RUN_DIR/run-meta.txt"
BUNDLE="$RESULT_DIR/cook4me-local-translation-v2-$STAMP.zip"
mkdir -p "$RUN_DIR" "$RESULT_DIR"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

latest_queue() {
  local path newest="" newest_mtime=0 mtime
  [[ -d "$STATE_DIR/assembly-v2" ]] || return 1
  while IFS= read -r -d '' path; do
    mtime="$(stat -c %Y "$path" 2>/dev/null || printf '0')"
    if ((mtime >= newest_mtime)); then
      newest_mtime="$mtime"
      newest="$path"
    fi
  done < <(find "$STATE_DIR/assembly-v2" -type f -name 'translation-queue-v2.json' -print0 2>/dev/null || true)
  [[ -n "$newest" ]] || return 1
  printf '%s\n' "$newest"
}

QUEUE="${COOK4ME_TRANSLATION_QUEUE:-}"
if [[ -z "$QUEUE" ]]; then
  QUEUE="$(latest_queue || true)"
fi
[[ -n "$QUEUE" && -f "$QUEUE" ]] || fail "No translation-queue-v2.json found. Run tools/run_release_catalog_v2_assembly_prep.sh first."

OLLAMA_URL="${COOK4ME_OLLAMA_URL:-http://127.0.0.1:11434}"
MODEL="${COOK4ME_OLLAMA_MODEL:-}"
BATCH_SIZE="${COOK4ME_TRANSLATION_BATCH_SIZE:-12}"
LIMIT="${COOK4ME_TRANSLATION_LIMIT:-0}"

printf 'Cook4Me local-only catalog canonicalization\n'
printf 'No cloud fallback is permitted; successful tasks are resumable from SQLite.\n'

ARGS=(
  --queue "$QUEUE"
  --cache-db "$CACHE_DB"
  --output "$OUT"
  --summary "$SUMMARY"
  --failures "$FAILURES"
  --ollama-url "$OLLAMA_URL"
  --batch-size "$BATCH_SIZE"
  --limit "$LIMIT"
)
if [[ -n "$MODEL" ]]; then
  ARGS+=(--model "$MODEL")
fi

set +e
python3 "$ROOT/tools/translate_release_catalog_local.py" "${ARGS[@]}" \
  > >(tee "$RUN_DIR/translate.log") \
  2> >(tee "$RUN_DIR/translate.err" >&2)
RC=$?
set -e

[[ "$RC" -eq 0 || "$RC" -eq 2 ]] || fail "Local Ollama translation failed before producing a review result. Completed cache entries are preserved; rerun the same command after fixing Ollama/model availability."
[[ -s "$OUT" && -s "$SUMMARY" ]] || fail "Local translation produced no review output."

python3 - "$SUMMARY" <<'PY'
import json, sys
s=json.load(open(sys.argv[1], encoding='utf-8'))
for key in ('model','tasks','cachedAtStart','pendingAtStart','completed','failed'):
    print(f'{key.upper()}={s[key]}')
PY

{
  printf 'timestamp=%s\n' "$STAMP"
  printf 'branch=%s\n' "$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
  printf 'commit=%s\n' "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
  printf 'queue=%s\n' "$QUEUE"
  printf 'ollama_url=%s\n' "$OLLAMA_URL"
  printf 'cloud_fallback=no\n'
  printf 'credentials_in_prompt=no\n'
  printf 'translation_cache_bundled=no\n'
} >"$META"

(
  cd "$RUN_DIR"
  zip -q "$BUNDLE" translation-results-v2.json.gz summary.json failures.json translate.log translate.err run-meta.txt
)

printf 'RESULT_BUNDLE=%s\n' "$BUNDLE"
exit "$RC"
