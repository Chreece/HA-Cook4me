#!/usr/bin/env bash
set -euo pipefail

BUILD_DIR="${1:-.catalog-build/v60-release}"
REFERENCE_DIR="${2:-.catalog-build/fdc-reference-v60}"
TARGETS="$BUILD_DIR/nutrition-review-targets.v60.json"

if [[ ! -f "$TARGETS" ]]; then
  echo "Missing nutrition review targets: $TARGETS" >&2
  exit 1
fi

python3 tools/prepare_fdc_reference_data_v60.py \
  --output-dir "$REFERENCE_DIR"

python3 tools/snapshot_release_catalog_fdc_target_candidates_offline_v60.py \
  --targets "$TARGETS" \
  --reference-manifest "$REFERENCE_DIR/reference-manifest.v60.json" \
  --output "$BUILD_DIR/fdc-target-candidates-offline.v60.json" \
  --summary "$BUILD_DIR/fdc-target-candidates-offline-summary.v60.json"

cat "$BUILD_DIR/fdc-target-candidates-offline-summary.v60.json"
