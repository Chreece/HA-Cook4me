#!/usr/bin/env bash
# Run as a standalone script: sudo bash deploy_offline_runtime_v106.sh
# Do not source this file into an interactive shell.
set -Eeuo pipefail

SOURCE_COMMIT=dd8c369d0eae3bcd287631b25fc228bbfd162a43
SOURCE_REPO=https://github.com/Chreece/HA-Cook4me.git
CONFIG=${COOK4ME_CONFIG:-/home/chreece/homeassistant/config}
CONTAINER=${COOK4ME_CONTAINER:-homeassistant}
HA_URL=${COOK4ME_HA_URL:-http://127.0.0.1:8123}
HEALTH_SECONDS=${COOK4ME_HEALTH_SECONDS:-240}

die() { printf 'ERROR: %s\n' "$*" >&2; return 1; }
[[ $EUID == 0 ]] || die 'Run this script with sudo bash.'
[[ $HEALTH_SECONDS =~ ^[1-9][0-9]*$ ]] || die 'Health timeout must be a positive integer.'
for command in git docker curl python3 cmp mktemp stat readlink flock chmod chown mv; do
    command -v "$command" >/dev/null || die "Required command is missing: $command"
done
[[ -d $CONFIG && ! -L $CONFIG ]] || die "Expected a real config directory: $CONFIG"
CONFIG=$(readlink -f "$CONFIG")
TARGET=$CONFIG/custom_components/cook4me
[[ -d $CONFIG/custom_components && ! -L $CONFIG/custom_components ]] || die 'custom_components must be a real directory.'
[[ -d $TARGET && ! -L $TARGET ]] || die "Expected an existing Cook4me integration: $TARGET"
[[ $(docker inspect --format '{{.State.Running}}' "$CONTAINER") == true ]] || die 'Home Assistant must be running for preflight checks.'
MOUNTS=$(docker inspect --format '{{json .Mounts}}' "$CONTAINER")
python3 -c '
import json, os, sys
mounts = json.loads(sys.argv[1])
matches = [m for m in mounts if m.get("Destination") == "/config"]
if len(matches) != 1 or matches[0].get("Type") != "bind" or not matches[0].get("RW") or os.path.realpath(matches[0].get("Source", "")) != sys.argv[2]:
    raise SystemExit("Refusing deployment: container /config is not the expected writable bind mount.")
if any(m.get("Destination", "").startswith("/config/custom_components") for m in mounts):
    raise SystemExit("Refusing deployment: a nested integration mount needs a different installation procedure.")
' "$MOUNTS" "$CONFIG"

umask 077
mkdir -p "$CONFIG/.cook4me-deploy"
exec 9> "$CONFIG/.cook4me-deploy/deploy.lock"
flock --nonblock 9 || die 'Another Cook4me deployment is already running.'
RUN=$(mktemp -d "$CONFIG/.cook4me-deploy/v106-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")
SOURCE=$RUN/source
BACKUP=$RUN/previous-cook4me
CONTAINER_SOURCE=/config/${RUN#"$CONFIG"/}/source
NEEDS_START=0
[[ $(stat -c %d "$TARGET") == "$(stat -c %d "$RUN")" ]] || die 'Staging and integration must be on the same filesystem.'

wait_frontend() {
    local deadline=$((SECONDS + HEALTH_SECONDS))
    while (( SECONDS < deadline )); do
        if curl --fail --silent --max-time 5 "${HA_URL%/}/" >/dev/null; then return 0; fi
        sleep 2
    done
    return 1
}

rollback() {
    local status=$?
    (( status != 0 )) || status=1
    trap - ERR INT TERM HUP
    set +e
    printf '\nDeployment failed. Diagnostics and source: %s\n' "$RUN" >&2
    if [[ -d $BACKUP ]]; then
        printf 'Restoring the previous Cook4me integration...\n' >&2
        if ! docker stop --time 120 "$CONTAINER" >/dev/null; then
            printf 'Automatic rollback could not stop Home Assistant. Backup: %s\n' "$BACKUP" >&2
            exit "$status"
        fi
        if [[ -e $TARGET ]] && ! mv "$TARGET" "$RUN/failed-cook4me"; then
            printf 'Automatic rollback could not move the failed integration. Backup: %s\n' "$BACKUP" >&2
            exit "$status"
        fi
        if ! mv "$BACKUP" "$TARGET"; then
            printf 'Automatic rollback could not restore the integration. Backup: %s\n' "$BACKUP" >&2
            exit "$status"
        fi
        NEEDS_START=1
    fi
    if (( NEEDS_START )); then
        if docker start "$CONTAINER" >/dev/null && wait_frontend; then
            printf 'Previous integration restored; Home Assistant is responding.\n' >&2
        else
            printf 'Previous files are in place, but Home Assistant needs attention: docker start %s\n' "$CONTAINER" >&2
        fi
    else
        printf 'Preflight failed; the installed integration was not changed.\n' >&2
    fi
    exit "$status"
}
trap rollback ERR
trap 'false' INT TERM HUP

# Run the same real offline probe against staged and installed files.
# Missing or invalid price evidence must fail before Home Assistant is stopped.
check_offline_runtime() {
    docker exec --user 0 --interactive "$CONTAINER" python -B - "$1" "${COOK4ME_UI_LANGUAGE:-el}" <<'PY'
import importlib
import json
from pathlib import Path
import socket
import sys
import types
from unittest.mock import patch

package = types.ModuleType("cook4me_deploy_check")
package.__path__ = [sys.argv[1]]
sys.modules[package.__name__] = package
with patch.object(socket, "socket", side_effect=AssertionError("offline prices opened network")):
    units = json.loads((Path(sys.argv[1]) / 'catalog/ui_units.v1.json').read_text(encoding='utf-8'))
    assert units['schemaVersion'] == 1 and len(units['unitKeys']) == 104, 'UI unit labels are missing'
    assert units['unitKeys']['UNIT_42'] == 'pinch' and units['labels']['pinch']['el'] == ['πρέζα', 'πρέζες'], 'Greek unit labels are invalid'
    assert all(all(units['labels'][kind].get(lang) for lang in ('en', 'de', 'el')) for kind in units['unitKeys'].values()), 'Incomplete UI unit translations'
    # These counts belong to SOURCE_COMMIT, not to a previous release.
    for filename, key, expected in (
        ("observed_prices.v1.json", "observations", 371),
        ("retail_prices.v1.json", "observations", 149),
        ("price_portions.v1.json", "portions", 123),
        ("price_reference_portions.v1.json", "portions", 6),
        ("price_densities.v1.json", "densities", 5),
        ("price_benchmarks.v1.json", "groups", 18),
    ):
        payload = json.loads((Path(sys.argv[1]) / "catalog" / filename).read_text(encoding="utf-8"))
        assert payload.get("schemaVersion") == 1, f"{filename}: unsupported schema"
        rows = payload.get(key, [])
        assert len(rows) == expected, f"{filename}: expected {expected} {key}, found {len(rows)}"
    prices = importlib.import_module(f"{package.__name__}.price_snapshot")
    evidence = prices._load()
    assert evidence.get("schemaVersion") == 1, "Offline price snapshot has an unsupported schema"
    count = len(evidence.get("observations", []))
    assert count == 520, f"Merged offline price snapshot: expected 520 observations, found {count}"
    measurements = importlib.import_module(f"{package.__name__}.price_measurements")
    for name, quantity, unit, expected in (("Swede", 1, "", 386), ("Caper", 1, "tbsp", 8.6),
                                            ("Peanut butter", 2, "tbsp", 32), ("Mayonnaise", 1, "tbsp", 13.8)):
        options = measurements.price_options({"name": name, "quantity": quantity, "unit": unit})
        assert any(row["unit"] == "g" and abs(row["quantity"] - expected) < .001 for row in options), f"{name}: portion conversion failed"
    options = measurements.price_options({"name": "Leaf gelatine", "quantity": 2, "unit": "Blatt", "unitKey": "UNIT_24"})
    assert any(row["unit"] == "pcs" and row["quantity"] == 2 for row in options), "Leaf gelatine: sheet count failed"
    for category, unit in (("cook4me:gelatine-sheets", "pcs"), ("cook4me:raw-swede", "g"),
                           ("cook4me:wasabi-paste", "g"), ("xx:sake", "ml"), ("en:mirin", "ml")):
        assert prices.snapshot_observations(category=category, country="DE", currency="EUR", unit=unit), f"{category}: reference missing"
    added = [row for row in evidence['observations'] if 'v103-20260917' in str(row['id'])]
    assert len(added) == 2, "v106 package references missing"
    for category in ("en:misos", "cook4me:fresh-shimeji"):
        assert prices.snapshot_observations(category=category, country="DE", currency="EUR", unit="g"), f"{category}: v106 reference missing"
    options = measurements.price_options({"name": "Miso", "quantity": 2, "unit": "tbsp"})
    assert any(row["unit"] == "g" and abs(row["quantity"] - 34) < .001 for row in options), "Miso: USDA spoon portion missing"
    options = measurements.price_options({"name": "Miso", "quantity": 600, "unit": "ml"})
    assert not any(row["unit"] == "g" for row in options), "Prepared miso volume became paste mass"
    options = measurements.price_options({"name": "Water", "quantity": 350, "unit": "g"})
    assert any(row["unit"] == "ml" and abs(row["quantity"] - 350) < .001 for row in options), "Water: USDA mass/volume reference missing"
    identities = importlib.import_module(f"{package.__name__}.price_identity")
    daikon = identities.reviewed_recipe_ingredient({"key": "M_FOOD_412", "name": "Radish", "quantity": .25}, {"variantId": "873706"})
    assert daikon["canonicalName"] == "daikon radish", "Daikon still shares the red-radish price identity"
    assert not any(row["unit"] == "g" for row in measurements.price_options(daikon)), "Daikon uses a red-radish piece weight"
    benchmarks = importlib.import_module(f"{package.__name__}.price_benchmarks")
    estimate = benchmarks.fallback_estimate({"name": "Salt and pepper", "quantity": 1, "unit": "g", "priceCatalogMatched": True}, country="DE", currency="EUR")
    assert estimate and estimate["amount"] > 0 and estimate["confidence"] == "low", "Budget fallback model is unavailable"
    assert estimate["sources"] and estimate["low"] <= estimate["amount"] <= estimate["high"], "Budget source range is invalid"
    for name in ('Mint', 'Fresh mint', 'Shimeji mushrooms', 'Daikon radish'):
        assert benchmarks.fallback_estimate({'name': name, 'quantity': 20, 'unit': 'pcs', 'priceCatalogMatched': True}, country='DE', currency='EUR') is None, f'{name}: unrelated piece budget still applied'
    allowances = importlib.import_module(f"{package.__name__}.price_allowances")
    for name in ("Salt", "Ground black pepper", "Water"):
        allowance = allowances.zero_cost_allowance({"name": name}, "EUR")
        assert allowance and allowance["amount"] == 0 and not allowance["quantityInferred"], f"{name}: zero allowance failed"
        assert allowances.zero_cost_allowance({"name": name, "quantity": 1}, "EUR") is None, f"{name}: measured amount became free"
    assert allowances.zero_cost_allowance({"name": "Olive oil"}, "EUR") is None, "Non-basic ingredient became free"
    selection = importlib.import_module(f"{package.__name__}.today_multilang")
    candidates = [{"title": str(index), "displayFamilyId": str(index), "mealTypes": ["main"],
                   "todayCatalogLanguage": "en", "match": {"score": 10-index}} for index in range(3)]
    plan, picked = {}, []
    for _ in range(3):
        plan = selection.select_today_categories(candidates, ["main"], ["en"], plan.get("items", []), plan.get("suggestionHistory", []))
        picked.append(plan["items"][0]["displayFamilyId"])
    assert len(set(picked)) == 3, "Today suggestion rotation failed"
    print(f"  Offline price snapshot: {len(evidence['observations'])} observations, built {evidence['generatedAt']}; expired evidence is excluded automatically")
PY
}

printf 'Fetching tested Cook4me v106 commit %s...\n' "$SOURCE_COMMIT"
git init --quiet "$SOURCE"
git -C "$SOURCE" remote add origin "$SOURCE_REPO"
git -C "$SOURCE" fetch --quiet --depth 1 origin "$SOURCE_COMMIT"
git -C "$SOURCE" checkout --quiet --detach FETCH_HEAD
[[ $(git -C "$SOURCE" rev-parse HEAD) == "$SOURCE_COMMIT" ]] || die 'Fetched commit does not match the tested source.'
STAGED=$SOURCE/custom_components/cook4me
[[ -s $STAGED/catalog/observed_prices.v1.json && -s $STAGED/catalog/price_portions.v1.json && -s $STAGED/catalog/retail_prices.v1.json && -s $STAGED/catalog/price_densities.v1.json && -s $STAGED/catalog/price_reference_portions.v1.json && -s $STAGED/catalog/price_benchmarks.v1.json && -s $STAGED/price_benchmarks.py && -s $STAGED/price_snapshot.py && -s $STAGED/price_allowances.py ]] || die 'Source is missing v106 price evidence.'
[[ -s $STAGED/websocket_v36.py && -s $STAGED/job_runtime.py && -s $STAGED/query_vocabulary.json && -s $STAGED/frontend/cook4me-panel-v106-bundle.js ]] || die 'Source is missing v106 runtime files.'

printf 'Checking staged offline price evidence and conversions...\n'
check_offline_runtime "$CONTAINER_SOURCE/custom_components/cook4me"

printf 'Validating with the Python version in your Home Assistant container...\n'
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -m compileall -q custom_components/cook4me
[[ -s $STAGED/catalog_ui_locales/el.json ]] || die 'The bundled Greek ingredient names are missing.'
printf 'Running price, entity and announcement fallback checks for this build...\n'
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_price_fixes_v104.py -v
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_entity_setup_v73.py -v
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_device_announcements_v72.py -v
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_announcement_fallback_v105.py -v
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_cross_language_send_v106.py -v
# Restore ordinary readable code permissions after the private checkout above.
chmod -R a+rX "$STAGED"
chown -R --reference="$TARGET" "$STAGED"

printf 'Preflight passed. Stopping Home Assistant and installing the complete integration...\n'
NEEDS_START=1
docker stop --time 120 "$CONTAINER" >/dev/null
mv "$TARGET" "$BACKUP"
mv "$STAGED" "$TARGET"
docker start "$CONTAINER" >/dev/null

printf 'Waiting for Home Assistant and the v106 Recipe Hub panel...\n'
deadline=$((SECONDS + HEALTH_SECONDS))
panel_ready=0
while (( SECONDS < deadline )); do
    if curl --fail --silent --max-time 5 "${HA_URL%/}/" >/dev/null &&
       curl --fail --silent --max-time 5 "${HA_URL%/}/cook4me_static/2026.9.17.10/cook4me-panel-v106-bundle.js" -o "$RUN/served-panel.js" &&
       cmp -s "$RUN/served-panel.js" "$TARGET/frontend/cook4me-panel-v106-bundle.js"; then
        panel_ready=1
        break
    fi
    sleep 2
done
(( panel_ready )) || die 'Home Assistant did not serve the installed v106 panel within the startup timeout.'

printf 'Checking installed offline price evidence and conversions...\n'
check_offline_runtime /config/custom_components/cook4me

printf '%s\n' "$SOURCE_COMMIT" > "$RUN/installed-commit.txt"
trap - ERR INT TERM HUP
printf '\nDEPLOYMENT PASSED\nCommit: %s\nBackup: %s\n' "$SOURCE_COMMIT" "$BACKUP"
printf 'Reopen Cook4Me and send the foreign-language recipe again. The original official edition is attempted when no device-language edition exists; success requires the cooker to report it loaded.\n'
