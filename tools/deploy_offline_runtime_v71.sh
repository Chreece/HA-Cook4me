#!/usr/bin/env bash
# Run as a standalone script: sudo bash deploy_offline_runtime_v71.sh
# Do not source this file into an interactive shell.
set -Eeuo pipefail

SOURCE_COMMIT=9751a8a5e0209d59b090c226cd89a9b98c2424ac
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
RUN=$(mktemp -d "$CONFIG/.cook4me-deploy/v71-$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")
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

printf 'Fetching tested Cook4me commit %s...\n' "$SOURCE_COMMIT"
git init --quiet "$SOURCE"
git -C "$SOURCE" remote add origin "$SOURCE_REPO"
git -C "$SOURCE" fetch --quiet --depth 1 origin "$SOURCE_COMMIT"
git -C "$SOURCE" checkout --quiet --detach FETCH_HEAD
[[ $(git -C "$SOURCE" rev-parse HEAD) == "$SOURCE_COMMIT" ]] || die 'Fetched commit does not match the tested source.'
STAGED=$SOURCE/custom_components/cook4me
[[ -s $STAGED/query_vocabulary.json && -s $STAGED/frontend/cook4me-panel-v71-bundle.js ]] || die 'Source is missing v71 runtime files.'

printf 'Validating with the Python version in your Home Assistant container...\n'
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -m compileall -q custom_components/cook4me
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_offline_multilingual_runtime_v61.py -v
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_catalog_presentation_v62.py -v
printf 'Using the bundled assistant-authored Greek ingredient translations...\n'
[[ -s $STAGED/catalog_ui_locales/el.json ]] || die 'The bundled Greek ingredient names are missing.'
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_shared_catalog_v63.py -v
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_catalog_flow_v64.py -v
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_multilingual_catalog_v65.py -v
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_recipe_cards_v66.py -v
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_rolling_week_v67.py -v
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_recipe_actions_v68.py -v
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_weekly_variety_v69.py -v
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_translation_v70.py -v
docker exec --user 0 --workdir "$CONTAINER_SOURCE" "$CONTAINER" python -B -m unittest discover -s tests -p test_recipe_removal_v71.py -v
# Restore ordinary readable code permissions after the private checkout above.
chmod -R a+rX "$STAGED"
chown -R --reference="$TARGET" "$STAGED"

printf 'Preflight passed. Stopping Home Assistant and installing the complete integration...\n'
NEEDS_START=1
docker stop --time 120 "$CONTAINER" >/dev/null
mv "$TARGET" "$BACKUP"
mv "$STAGED" "$TARGET"
docker start "$CONTAINER" >/dev/null

printf 'Waiting for Home Assistant and the v71 Recipe Hub panel...\n'
deadline=$((SECONDS + HEALTH_SECONDS))
panel_ready=0
while (( SECONDS < deadline )); do
    if curl --fail --silent --max-time 5 "${HA_URL%/}/" >/dev/null &&
       curl --fail --silent --max-time 5 "${HA_URL%/}/cook4me_static/2026.9.15.13/cook4me-panel-v71-bundle.js" -o "$RUN/served-panel.js" &&
       cmp -s "$RUN/served-panel.js" "$TARGET/frontend/cook4me-panel-v71-bundle.js"; then
        panel_ready=1
        break
    fi
    sleep 2
done
(( panel_ready )) || die 'Home Assistant did not serve the installed v71 panel within the startup timeout.'

printf 'Checking installed offline queries and nutrition...\n'
docker exec --user 0 --interactive "$CONTAINER" python -B - /config/custom_components/cook4me "${COOK4ME_UI_LANGUAGE:-el}" <<'PY'
import importlib
import socket
import sys
import types
from unittest.mock import patch

package = types.ModuleType("cook4me_deploy_check")
package.__path__ = [sys.argv[1]]
sys.modules[package.__name__] = package
release = importlib.import_module(f"{package.__name__}.release_catalog")
with patch.object(socket, "socket", side_effect=AssertionError("offline catalog opened network")):
    recipes = release.load_release_catalog()["recipes"]
    assert len(recipes) == 16952, f"Unexpected recipe count: {len(recipes)}"
    cases = [("ριζότο", None, 205), ("ριζότο ντομάτα", None, 25), ("σούπα με φακές", None, 77), ("ριζότο", ["de"], 11)]
    for query, languages, expected in cases:
        result = release.search_release_recipes(query, language="el", configured_language="de", country="DE", catalog_languages=languages, size=50)
        count = result["page"]["totalElements"]
        assert count == expected, f"{query}: expected {expected}, got {count}"
        print(f"  {query} ({'all catalogs' if languages is None else 'German'}): {count}")
    rows = [row for row in result["items"] if row["catalogNutrition"].get("perServing")]
    assert rows, "No nutrition available for the German risotto results"
    for row in rows:
        detail = release.recipe_by_variant(row["searchVariantId"], language="de", configured_language="de", country="DE")
        assert detail["catalogNutrition"] == row["catalogNutrition"], "Search/detail nutrition mismatch"
        assert detail["sendVariantId"] == row["sendVariantId"], "Search/detail device identity mismatch"
    print(f"  {len(recipes)} recipes; offline nutrition and device identity checks passed")
    ingredient = release.ingredient_nutrition_profile({"ingredientId": "M_FOOD_246"})
    assert ingredient is not None, "Ingredient popup catalog profile is missing"
    assert (ingredient["basisQuantity"], ingredient["basisUnit"]) == (100, "g"), "Ingredient nutrient basis mismatch"
    assert ingredient["values"]["energyKcal"] == 884, "Ingredient nutrient value mismatch"
    assert release.ingredient_nutrition_profile({"ingredientId": "unknown", "name": "Olive oil"}) is None, "Ingredient identity was guessed"
    print("  Ingredient popup reference: olive oil, 884 kcal per 100 g")
    grouped = release.search_release_recipes("arroz", language="el", configured_language="de", country="DE", group_families=True)
    rice = grouped["items"][0]
    assert rice["publicationCount"] == 60 and rice["availableServings"] == [200, 300, 400, 500, 600], "Rice family grouping failed"
    rice_id = {"ingredientId": "M_FOOD_421"}
    assert release.ingredient_nutrition_profile(rice_id) is None, "Generic rice must not acquire a guessed nutrient profile"
    assert release.ingredient_nutrition_references(rice_id, "el"), "Rice reference comparisons are missing"
    choices = release.ingredient_choices(sys.argv[2])
    assert choices and len({row["displayGroupId"] for row in choices}) == len(choices), "Ingredient choices contain duplicates"
    if sys.argv[2] == "el":
        import re
        assert all(re.search(r"[\u0370-\u03ff\u1f00-\u1fff]", row["name"]) for row in choices), "Greek ingredient locale is incomplete"
    print(f"  Rice: 60 publications grouped; {len(choices)} clean ingredient choices in {sys.argv[2]}")
PY

printf '%s\n' "$SOURCE_COMMIT" > "$RUN/installed-commit.txt"
trap - ERR INT TERM HUP
printf '\nDEPLOYMENT PASSED\nCommit: %s\nBackup: %s\n' "$SOURCE_COMMIT" "$BACKUP"
printf 'Reopen Cook4Me (reload the browser/app) for centered controls, whole-card opening, fitted titles and saved-recipe removal fixes.\n'
