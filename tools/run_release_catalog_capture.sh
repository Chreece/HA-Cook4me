#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${COOK4ME_CATALOG_STATE_DIR:-$ROOT/.catalog-build}"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$STATE_DIR/runs/$STAMP"
RESULT_DIR="$STATE_DIR/results"
VENV="$STATE_DIR/venv"
NUTRITION_CACHE="$STATE_DIR/fdc-nutrition-cache.json"
OVERRIDES="$STATE_DIR/english-overrides.json"
CATALOG="$RUN_DIR/merged_catalog.v1.json"
REPORT="$RUN_DIR/review-report.json"
OVERRIDE_TEMPLATE="$RUN_DIR/english-overrides-template.json"
BUILD_LOG="$RUN_DIR/build.log"
META="$RUN_DIR/run-meta.txt"
BUNDLE="$RESULT_DIR/cook4me-release-catalog-capture-$STAMP.zip"

mkdir -p "$RUN_DIR" "$RESULT_DIR"

say() { printf '%s\n' "$*"; }
fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

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
  for path in \
    "$HOME/.config/cook4me/tokens.json" \
    "$HOME/cook4me-phonefree/.config/cook4me/tokens.json"; do
    [[ -f "$path" ]] && candidates+=("$path")
  done

  ((${#candidates[@]})) || return 1

  local newest=""
  local newest_mtime=0
  local path mtime
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

say "Cook4Me exhaustive catalog capture"
say "Catalog source: 28 audited language/market mappings"
say "Preparing isolated builder environment..."

if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV" >/dev/null 2>&1 || fail "python3-venv is required."
fi
"$VENV/bin/python" -m pip install --disable-pip-version-check -q "curl-cffi==0.13.0" \
  >"$RUN_DIR/pip.log" 2>&1 || fail "Could not install the isolated curl-cffi dependency."

ARGS=(
  "$ROOT/tools/build_release_catalog.py"
  --storage-home "$STORAGE_HOME"
  --configured-language "${COOK4ME_CONFIGURED_LANGUAGE:-de}"
  --configured-country "${COOK4ME_CONFIGURED_COUNTRY:-DE}"
  --catalog-version "capture-$STAMP"
  --output "$CATALOG"
  --nutrition-cache "$NUTRITION_CACHE"
  --workers "${COOK4ME_CATALOG_WORKERS:-4}"
  --verbose
)

if [[ -s "$OVERRIDES" ]]; then
  ARGS+=(--english-overrides "$OVERRIDES")
fi

# Nutrition resolution is intentionally opt-in for the capture runner until the
# catalog identity review is complete. This avoids bulk nutrient assignment to
# unresolved/non-English canonical labels. A later reviewed pass can set both
# COOK4ME_RESOLVE_NUTRITION=1 and FDC_API_KEY and reuse the persistent cache.
if [[ "${COOK4ME_RESOLVE_NUTRITION:-0}" == "1" ]]; then
  [[ -n "${FDC_API_KEY:-}" ]] || fail "COOK4ME_RESOLVE_NUTRITION=1 requires FDC_API_KEY."
  ARGS+=(--resolve-nutrition --fdc-key "$FDC_API_KEY")
fi

say "Running exhaustive catalog crawl..."
set +e
"$VENV/bin/python" "${ARGS[@]}" >"$BUILD_LOG" 2>&1
BUILD_RC=$?
set -e

# Exit 2 is the builder's expected 'catalog generated but not activation-ready'
# result. Anything else is a genuine capture failure.
if [[ "$BUILD_RC" -ne 0 && "$BUILD_RC" -ne 2 ]]; then
  tail -n 40 "$BUILD_LOG" >&2 || true
  fail "Catalog crawl failed (exit $BUILD_RC). Full log: $BUILD_LOG"
fi
[[ -s "$CATALOG" ]] || fail "Catalog builder produced no catalog file."

"$VENV/bin/python" "$ROOT/tools/summarize_release_catalog.py" \
  "$CATALOG" \
  --output "$REPORT" \
  --overrides-template "$OVERRIDE_TEMPLATE" \
  >"$RUN_DIR/summary-line.json" 2>"$RUN_DIR/summary-error.log" \
  || fail "Catalog summary generation failed."

{
  printf 'timestamp=%s\n' "$STAMP"
  printf 'repository=%s\n' "$ROOT"
  printf 'branch=%s\n' "$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
  printf 'commit=%s\n' "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
  printf 'storage_home=%s\n' "$STORAGE_HOME"
  printf 'builder_exit=%s\n' "$BUILD_RC"
  printf 'nutrition_resolution_requested=%s\n' "${COOK4ME_RESOLVE_NUTRITION:-0}"
  printf 'fdc_key_present=%s\n' "$([[ -n "${FDC_API_KEY:-}" ]] && printf yes || printf no)"
  printf 'token_material_in_bundle=no\n'
} >"$META"

sha256sum "$CATALOG" >"$RUN_DIR/catalog.sha256"

# Never include the persistent nutrition cache or any token files in the review
# bundle. The full candidate catalog is included because it contains no secrets
# and lets the review verify identities/merges rather than relying on counts.
(
  cd "$RUN_DIR"
  zip -q "$BUNDLE" \
    merged_catalog.v1.json \
    review-report.json \
    english-overrides-template.json \
    build.log \
    run-meta.txt \
    catalog.sha256 \
    summary-line.json \
    summary-error.log
)

SUMMARY="$($VENV/bin/python - "$REPORT" <<'PY'
import json, sys
r=json.load(open(sys.argv[1], encoding='utf-8'))
c=r['counts']
print(f"CATALOG_COMPLETE={str(r['complete']).lower()}")
print(f"ACTIVATION_READY={str(r['activationReady']).lower()}")
print(f"CATALOGS={c['populatedCatalogs']}/{c['auditedCatalogs']} populated")
print(f"RECIPES={c['recipes']} variants={c['recipeVariants']}")
print(f"INGREDIENTS={c['ingredients']}")
print(f"UNRESOLVED_ENGLISH_INGREDIENTS={c['unresolvedCanonicalIngredientNames']}")
print(f"UNRESOLVED_ENGLISH_RECIPES={c['unresolvedCanonicalRecipeNames']}")
print(f"NUTRITION_MISSING={c['nutritionMissing']}")
print(f"FAILED_DETAIL_CATALOGS={c['failedDetailCatalogs']}")
print(f"INTEGRITY_OK={str(r['integrity']['ok']).lower()}")
PY
)"

say "$SUMMARY"
say "RESULT_BUNDLE=$BUNDLE"
