#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STAMP="$(date +%Y%m%d-%H%M%S)"
STATE_DIR="${COOK4ME_CATALOG_STATE_DIR:-$ROOT/.catalog-build}"
RUN_DIR="$STATE_DIR/marketing-food-body-probes/$STAMP"
RESULT_DIR="$STATE_DIR/results"
OUT="$RUN_DIR/marketing-food-body-contract.txt"
META="$RUN_DIR/run-meta.txt"
BUNDLE="$RESULT_DIR/cook4me-marketing-food-body-contract-$STAMP.zip"
mkdir -p "$RUN_DIR" "$RESULT_DIR"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

find_jadx_root() {
  local candidates=(
    "${COOK4ME_JADX_ROOT:-}"
    "/home/chreece/cook4me-re/jadx-phonefree"
    "/home/chreece/cook4me-re/jadx"
    "/home/chreece/krups-apk/jadx-phonefree"
  )
  local p
  for p in "${candidates[@]}"; do
    [[ -n "$p" && -d "$p/sources" ]] || continue
    printf '%s\n' "$p"
    return 0
  done
  return 1
}

JADX_ROOT="$(find_jadx_root || true)"
[[ -n "$JADX_ROOT" ]] || fail "Could not find the existing Cook4Me JADX sources. Set COOK4ME_JADX_ROOT if they moved."
SOURCES="$JADX_ROOT/sources"
BODY="$SOURCES/th0/d.java"
[[ -f "$BODY" ]] || fail "Expected APK body model not found: $BODY"

{
  printf '=== th0/d.java ===\n'
  cat "$BODY"
  printf '\n=== th0 package siblings ===\n'
  for f in "$SOURCES"/th0/*.java; do
    [[ -f "$f" ]] || continue
    printf '\n--- %s ---\n' "${f#$SOURCES/}"
    cat "$f"
  done

  printf '\n=== Retrofit contract ===\n'
  if [[ -f "$SOURCES/rd0/c.java" ]]; then
    cat "$SOURCES/rd0/c.java"
  fi

  printf '\n=== exact th0.d imports/usages ===\n'
  grep -R -n -C 12 --include='*.java' -E 'import th0\.d;|th0\.d|marketingFoodSearchBody' "$SOURCES" 2>/dev/null || true

  printf '\n=== rd0.c usages ===\n'
  grep -R -n -C 15 --include='*.java' -E 'import rd0\.c;|rd0\.c' "$SOURCES" 2>/dev/null || true

  printf '\n=== marketingFoods/search usages ===\n'
  grep -R -n -C 15 --include='*.java' -F 'marketingFoods/search' "$SOURCES" 2>/dev/null || true
} >"$OUT"

{
  printf 'timestamp=%s\n' "$STAMP"
  printf 'branch=%s\n' "$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
  printf 'commit=%s\n' "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
  printf 'jadx_root=%s\n' "$JADX_ROOT"
  printf 'read_only=yes\n'
  printf 'network_used=no\n'
  printf 'token_material_in_bundle=no\n'
} >"$META"

(
  cd "$RUN_DIR"
  zip -q "$BUNDLE" marketing-food-body-contract.txt run-meta.txt
)

printf 'RESULT_BUNDLE=%s\n' "$BUNDLE"
