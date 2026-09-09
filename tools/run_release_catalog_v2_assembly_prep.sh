#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="${COOK4ME_CATALOG_STATE_DIR:-$ROOT/.catalog-build}"
STAMP="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="$STATE_DIR/assembly-v2/$STAMP"
RESULT_DIR="$STATE_DIR/results"
RAW_PREP="$RUN_DIR/assembly-prep-raw-v2.json.gz"
RAW_QUEUE="$RUN_DIR/translation-queue-raw-v2.json"
RAW_SUMMARY="$RUN_DIR/summary-raw.json"
PREP="$RUN_DIR/assembly-prep-v2.json.gz"
QUEUE="$RUN_DIR/translation-queue-v2.json"
SUMMARY="$RUN_DIR/summary.json"
AUGMENTED_PROVIDER="$RUN_DIR/provider-with-taxonomy-v2.json.gz"
CLASSIFICATION_V2="$RUN_DIR/recipe-classification-v2.json.gz"
CLASSIFICATION_V2_REVIEW="$RUN_DIR/recipe-classification-review-v2.json"
CLASSIFICATION_V2_SUMMARY="$RUN_DIR/classification-v2-summary.json"
CLASSIFICATION="$RUN_DIR/recipe-classification-v3.json.gz"
CLASSIFICATION_REVIEW="$RUN_DIR/recipe-classification-review-v3.json"
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
      if ((mtime >= newest_mtime)); then newest_mtime="$mtime"; newest="$path"; fi
    done < <(find "$base" -type f -name "$pattern" -print0 2>/dev/null || true)
  done
  [[ -n "$newest" ]] || return 1
  printf '%s\n' "$newest"
}

PROVIDER="${COOK4ME_PROVIDER_CAPTURE:-}"
if [[ -z "$PROVIDER" ]]; then PROVIDER="$(latest_file 'provider-capture-v2.json.gz' "$STATE_DIR/v2-runs" || true)"; fi
if [[ -z "$PROVIDER" ]]; then PROVIDER="$(latest_file 'cook4me-release-catalog-v2-capture-*.zip' "$RESULT_DIR" || true)"; fi
[[ -n "$PROVIDER" && -f "$PROVIDER" ]] || fail "No reviewed provider-capture v2 was found. Set COOK4ME_PROVIDER_CAPTURE if needed."

MARKETING="${COOK4ME_MARKETING_FOODS:-}"
if [[ -z "$MARKETING" ]]; then MARKETING="$(latest_file 'marketing-foods-v3.json' "$STATE_DIR/marketing-food-runs" || true)"; fi
if [[ -z "$MARKETING" ]]; then MARKETING="$(latest_file 'cook4me-marketing-foods-v3-*.zip' "$RESULT_DIR" || true)"; fi
[[ -n "$MARKETING" && -f "$MARKETING" ]] || fail "No reviewed marketing-food v3 capture was found. Set COOK4ME_MARKETING_FOODS if needed."

TAXONOMY="${COOK4ME_PROVIDER_TAXONOMY:-}"
if [[ -z "$TAXONOMY" ]]; then TAXONOMY="$(latest_file 'provider-taxonomy-v2.json.gz' "$STATE_DIR/taxonomy-runs" || true)"; fi
if [[ -z "$TAXONOMY" ]]; then TAXONOMY="$(latest_file 'cook4me-release-taxonomy-v2-*.zip' "$RESULT_DIR" || true)"; fi
[[ -n "$TAXONOMY" && -f "$TAXONOMY" ]] || fail "No complete provider taxonomy capture was found. Run tools/run_release_catalog_taxonomy_capture.sh first."

printf 'Cook4Me offline release assembly preparation\n'
printf 'No provider/network calls are made in this stage.\n'
printf 'Reviewed canonical English/keyless semantics are applied before the remaining work queue is emitted.\n'

python3 "$ROOT/tools/prepare_release_catalog_v2_assembly.py" \
  --provider-capture "$PROVIDER" \
  --marketing-foods "$MARKETING" \
  --output "$RAW_PREP" \
  --queue "$RAW_QUEUE" \
  --summary "$RAW_SUMMARY" \
  >"$RUN_DIR/prepare.log" 2>&1 || {
    tail -n 80 "$RUN_DIR/prepare.log" >&2 || true
    fail "Offline assembly preparation failed."
  }

python3 "$ROOT/tools/apply_release_catalog_reviews_v2.py" \
  --prep "$RAW_PREP" \
  --queue "$RAW_QUEUE" \
  --output-prep "$PREP" \
  --output-queue "$QUEUE" \
  --summary "$SUMMARY" \
  >"$RUN_DIR/apply-reviews.log" 2>&1 || {
    tail -n 80 "$RUN_DIR/apply-reviews.log" >&2 || true
    fail "Reviewed catalog semantics could not be applied."
  }

python3 "$ROOT/tools/augment_provider_capture_taxonomy_v2.py" \
  --provider-capture "$PROVIDER" \
  --taxonomy "$TAXONOMY" \
  --output "$AUGMENTED_PROVIDER" \
  >"$RUN_DIR/augment-taxonomy.log" 2>&1 || {
    tail -n 80 "$RUN_DIR/augment-taxonomy.log" >&2 || true
    fail "Reviewed taxonomy could not be overlaid onto the provider capture."
  }

python3 "$ROOT/tools/classify_release_catalog_v2.py" \
  --provider-capture "$AUGMENTED_PROVIDER" \
  --marketing-foods "$MARKETING" \
  --output "$CLASSIFICATION_V2" \
  --review "$CLASSIFICATION_V2_REVIEW" \
  --summary "$CLASSIFICATION_V2_SUMMARY" \
  >"$RUN_DIR/classify-v2.log" 2>&1 || {
    tail -n 80 "$RUN_DIR/classify-v2.log" >&2 || true
    fail "Offline diet/meal classification failed."
  }

python3 "$ROOT/tools/refine_release_catalog_classification_v3.py" \
  --classification "$CLASSIFICATION_V2" \
  --provider-capture "$AUGMENTED_PROVIDER" \
  --output "$CLASSIFICATION" \
  --review "$CLASSIFICATION_REVIEW" \
  --summary "$CLASSIFICATION_SUMMARY" \
  >"$RUN_DIR/classify-v3.log" 2>&1 || {
    tail -n 80 "$RUN_DIR/classify-v3.log" >&2 || true
    fail "Entry/meal classification refinement failed."
  }

python3 - "$SUMMARY" "$CLASSIFICATION_SUMMARY" <<'PY'
import json, sys
s=json.load(open(sys.argv[1], encoding='utf-8'))
c=json.load(open(sys.argv[2], encoding='utf-8'))
print('TAXONOMY_AVAILABLE=true')
for key in (
    'providerDetails', 'staleSearchOnly', 'providerRecipeGroups',
    'providerFoodCatalogKeys', 'recipeUsedProviderFoodKeys',
    'recipeUsedProviderFoodKeysCoveredByDictionary',
    'providerFoodsCanonicalEnglishResolved', 'usedProviderFoodsCanonicalEnglishResolved',
    'reviewedProviderFoodEnglishApplied', 'reviewedKeylessIngredientSemanticsApplied',
    'translationTasksRemaining', 'providerFoodTranslationTasksRemaining',
    'recipeTitleTranslationTasksRemaining', 'unkeyedIngredientTasksRemaining',
):
    print(f'{key.upper()}={s.get(key, 0)}')
for key in (
    'dietResolved', 'dietReviewRequired', 'vegan', 'vegetarian', 'pescatarian',
    'omnivore', 'mealTypeResolved', 'mealTypeNotApplicable',
    'mealTypeReviewRequired', 'entryType_recipe', 'entryType_ingredient_preparation',
    'entryType_beverage', 'entryType_non_food', 'providerDietHintConflicts',
    'reviewQueue',
):
    print(f'{key.upper()}={c.get(key, 0)}')
PY

{
  printf 'timestamp=%s\n' "$STAMP"
  printf 'branch=%s\n' "$(git -C "$ROOT" branch --show-current 2>/dev/null || true)"
  printf 'commit=%s\n' "$(git -C "$ROOT" rev-parse HEAD 2>/dev/null || true)"
  printf 'provider_capture=%s\n' "$PROVIDER"
  printf 'marketing_foods=%s\n' "$MARKETING"
  printf 'provider_taxonomy=%s\n' "$TAXONOMY"
  printf 'taxonomy_available=true\n'
  printf 'reviewed_provider_food_english=yes\n'
  printf 'reviewed_keyless_semantics=yes\n'
  printf 'entry_classification=yes\n'
  printf 'diet_classification=yes\n'
  printf 'meal_type_classification=yes\n'
  printf 'provider_taxonomy_preferred=yes\n'
  printf 'provider_diet_hints_authoritative=no\n'
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
    recipe-classification-v3.json.gz \
    recipe-classification-review-v3.json \
    classification-summary.json \
    prepare.log apply-reviews.log augment-taxonomy.log classify-v2.log classify-v3.log run-meta.txt
)

printf 'RESULT_BUNDLE=%s\n' "$BUNDLE"
