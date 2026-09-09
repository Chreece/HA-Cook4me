#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${COOK4ME_CATALOG_STATE_DIR:-$ROOT/.catalog-build}"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$STATE_DIR/assembly-v2/$STAMP"
RESULT_DIR="$STATE_DIR/results"
PREP="$RUN_DIR/assembly-prep-v2.json.gz"
QUEUE="$RUN_DIR/translation-queue-v2.json"
SUMMARY="$RUN_DIR/summary.json"
AUGMENTED_PROVIDER="$RUN_DIR/provider-with-taxonomy-v2.json.gz"
CLASSIFICATION="$RUN_DIR/recipe-classification-v2.json.gz"
CLASSIFICATION_REVIEW="$RUN_DIR/recipe-classification-review-v2.json"
CLASSIFICATION_SUMMARY="$RUN_DIR/classification-summary.json"
META="$RUN_DIR/run-meta.txt"
BUNDLE="$RESULT_DIR/cook4me-release-assembly-prep-v2-$STAMP.zip"
mkdir -p "$RUN_DIR" "$RESULT_DIR"

fail() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

latest_file() {
  local pattern="$1"
  shift
  local base path newest="" newest_mtime=0 mtime
  for base in "$@"; do
    [[ -d "$base" ]] || continue
    while IFS= read -r -d '' path; do
      mtime="$(stat -c %Y "$path" 2>/dev/null || printf '0')"
      if ((mtime >= newest_mtime)); then
        newest_mtime="$mtime"
        newest="$path"
      fi
    done < <(find "$base" -type f -name "$pattern" -print0 2>/dev/null || true)
  done
  [[ -n "$newest" ]] || return 1
  printf '%s\n' "$newest"
}

PROVIDER="${COOK4ME_PROVIDER_CAPTURE:-}"
if [[ -z "$PROVIDER" ]]; then
  PROVIDER="$(latest_file 'provider-capture-v2.json.gz' "$STATE_DIR/v2-runs" || true)"
fi
if [[ -z "$PROVIDER" ]]; then
  PROVIDER="$(latest_file 'cook4me-release-catalog-v2-capture-*.zip' "$RESULT_DIR" || true)"
fi
[[ -n "$PROVIDER" && -f "$PROVIDER" ]] || fail "No reviewed provider-capture v2 was found. Set COOK4ME_PROVIDER_CAPTURE if needed."

MARKETING="${COOK4ME_MARKETING_FOODS:-}"
if [[ -z "$MARKETING" ]]; then
  MARKETING="$(latest_file 'marketing-foods-v3.json' "$STATE_DIR/marketing-food-runs" || true)"
fi
if [[ -z "$MARKETING" ]]; then
  MARKETING="$(latest_file 'cook4me-marketing-foods-v3-*.zip' "$RESULT_DIR" || true)"
fi
[[ -n "$MARKETING" && -f "$MARKETING" ]] || fail "No reviewed marketing-food v3 capture was found. Set COOK4ME_MARKETING_FOODS if needed."

TAXONOMY="${COOK4ME_PROVIDER_TAXONOMY:-}"
if [[ -z "$TAXONOMY" ]]; then
  TAXONOMY="$(latest_file 'provider-taxonomy-v2.json.gz' "$STATE_DIR/taxonomy-runs" || true)"
fi
if [[ -z "$TAXONOMY" ]]; then
  TAXONOMY="$(latest_file 'cook4me-release-taxonomy-v2-*.zip' "$RESULT_DIR" || true)"
fi

printf 'Cook4Me offline release assembly preparation\n'
printf 'No provider/network calls are made in this stage.\n'

python3 "$ROOT/tools/prepare_release_catalog_v2_assembly.py" \
  --provider-capture "$PROVIDER" \
  --marketing-foods "$MARKETING" \
  --output "$PREP" \
  --queue "$QUEUE" \
  --summary "$SUMMARY" \
  >"$RUN_DIR/prepare.log" 2>&1 || {
    tail -n 80 "$RUN_DIR/prepare.log" >&2 || true
    fail "Offline assembly preparation failed."
  }

CLASS_PROVIDER="$PROVIDER"
TAXONOMY_AVAILABLE=false
if [[ -n "$TAXONOMY" && -f "$TAXONOMY" ]]; then
  python3 "$ROOT/tools/augment_provider_capture_taxonomy_v2.py" \
    --provider-capture "$PROVIDER" \
    --taxonomy "$TAXONOMY" \
    --output "$AUGMENTED_PROVIDER" \
    >"$RUN_DIR/augment-taxonomy.log" 2>&1 || {
      tail -n 80 "$RUN_DIR/augment-taxonomy.log" >&2 || true
      fail "Reviewed taxonomy could not be overlaid onto the provider capture."
    }
  CLASS_PROVIDER="$AUGMENTED_PROVIDER"
  TAXONOMY_AVAILABLE=true
else
  printf 'No complete taxonomy capture found; meal types will remain review-required where provider taxonomy is unavailable.\n'
  : >"$RUN_DIR/augment-taxonomy.log"
fi

python3 "$ROOT/tools/classify_release_catalog_v2.py" \
  --provider-capture "$CLASS_PROVIDER" \
  --marketing-foods "$MARKETING" \
  --output "$CLASSIFICATION" \
  --review "$CLASSIFICATION_REVIEW" \
  --summary "$CLASSIFICATION_SUMMARY" \
  >"$RUN_DIR/classify.log" 2>&1 || {
    tail -n 80 "$RUN_DIR/classify.log" >&2 || true
    fail "Offline diet/meal classification failed."
  }

python3 - "$SUMMARY" "$CLASSIFICATION_SUMMARY" "$TAXONOMY_AVAILABLE" <<'PY'
import json, sys
s=json.load(open(sys.argv[1], encoding='utf-8'))
c=json.load(open(sys.argv[2], encoding='utf-8'))
print(f'TAXONOMY_AVAILABLE={sys.argv[3]}')
for key in (
    'providerDetails',
    'staleSearchOnly',
    'providerRecipeGroups',
    'providerFoodCatalogKeys',
    'recipeUsedProviderFoodKeys',
    'recipeUsedProviderFoodKeysCoveredByDictionary',
    'providerFoodsWithSebEnglish',
    'usedProviderFoodsWithSebEnglish',
    'providerFoodsMissingSebEnglish',
    'usedProviderFoodsMissingSebEnglish',
    'unkeyedUniqueLabels',
    'unkeyedRowsWithStructuredPrefixCleaned',
    'unkeyedExactProviderFoodCandidates',
    'uniqueRecipeTitleTranslationTasks',
    'unkeyedIngredientTranslationClassificationTasks',
    'translationTasks',
):
    print(f'{key.upper()}={s[key]}')
for key in (
    'dietResolved', 'dietReviewRequired', 'vegan', 'vegetarian',
    'pescatarian', 'omnivore', 'mealTypeResolvedFromProvider',
    'mealTypeReviewRequired', 'reviewQueue',
):
    print(f'{key.upper()}={c[key]}')
for meal in ('breakfast','starter','salad','soup','main','side','dessert','snack'):
    print(f'MEALTYPE_{meal.upper()}={c.get("mealType_"+meal, 0)}')
PY

{
  printf 'timestamp=%s\n' "$STAMP"
  printf 'branch=%s\n' "$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
  printf 'commit=%s\n' "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
  printf 'provider_capture=%s\n' "$PROVIDER"
  printf 'marketing_foods=%s\n' "$MARKETING"
  printf 'provider_taxonomy=%s\n' "$TAXONOMY"
  printf 'taxonomy_available=%s\n' "$TAXONOMY_AVAILABLE"
  printf 'diet_classification=yes\n'
  printf 'meal_type_classification=yes\n'
  printf 'provider_taxonomy_preferred=yes\n'
  printf 'network_used=no\n'
  printf 'read_only=yes\n'
  printf 'secrets_persisted=no\n'
} >"$META"

(
  cd "$RUN_DIR"
  zip -q "$BUNDLE" \
    assembly-prep-v2.json.gz \
    translation-queue-v2.json \
    summary.json \
    recipe-classification-v2.json.gz \
    recipe-classification-review-v2.json \
    classification-summary.json \
    prepare.log classify.log augment-taxonomy.log run-meta.txt
)

printf 'RESULT_BUNDLE=%s\n' "$BUNDLE"
