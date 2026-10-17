#!/usr/bin/env bash
# Cook4Me frontend-only v284 preview; run with sudo bash, never source into SSH.
set -Eeuo pipefail
set +x
umask 077
[[ $EUID == 0 ]] || { echo "Run using sudo bash"; exit 1; }
for exe in curl docker git python3 node flock mktemp cp mv rm chmod chown stat tar tee grep ln; do
  command -v "$exe" >/dev/null || { echo "Required command $exe missing; nothing changed"; exit 1; }
done
CONFIG=/home/chreece/homeassistant/config
RUNTIME="$CONFIG/custom_components/cook4me"
HA=homeassistant
GITHUB="https://raw.githubusercontent.com/Chreece/HA-Cook4me/cef1ea50272ad35b9e5a78de95a28cd64c7512c6"
LOGROOT=/home/chreece/projects/cook4me/logs
BACKUPROOT=/home/chreece/projects/cook4me/recovery
[[ -f "$RUNTIME/panel.py" && -d "$RUNTIME/frontend" ]] || { echo "Cook4Me frontend missing"; exit 1; }
[[ "$(docker inspect -f '{{.State.Running}}' "$HA" 2>/dev/null)" == true ]] || { echo "Home Assistant must already be running"; exit 1; }
python3 - "$CONFIG" "$(docker inspect -f '{{json .Mounts}}' "$HA")" <<'PY'
import json,os,sys
rows=[row for row in json.loads(sys.argv[2]) if row.get('Destination')=='/config']
if len(rows)!=1 or rows[0].get('Type')!='bind' or not rows[0].get('RW') or os.path.realpath(rows[0]['Source'])!=os.path.realpath(sys.argv[1]):
 raise SystemExit('Home Assistant config mount mismatch')
print('Home Assistant mount: PASS')
PY
mkdir -p "$LOGROOT" "$BACKUPROOT" "$CONFIG/.cook4me-deploy"
exec 9>"$CONFIG/.cook4me-deploy/deploy.lock"
flock -n 9 || { echo "Another Cook4Me deployment is in progress"; exit 1; }
STAMP=$(date -u +%Y%m%d-%H%M%S)
STAGE=$(mktemp -d "$CONFIG/.cook4me-deploy/recipe-v284-$STAMP-XXXXXX")
BACKUP="$BACKUPROOT/PRIVATE-DO-NOT-UPLOAD-frontend-v284-$STAMP"
REPORT="$LOGROOT/cook4me-recipe-v284-$STAMP.tar.gz"
mkdir -p "$BACKUP"
LOG="$BACKUP/install.log"
CHANGED=0
STOPPED=0
HAD_MODULE=0
[[ -f "$RUNTIME/frontend/loaded-device-recipe-v284.js" ]] && HAD_MODULE=1
record_report(){
  local status="$1"
  printf 'RESULT=%s\nSOURCE_COMMIT=cef1ea50272ad35b9e5a78de95a28cd64c7512c6\n' "$status" >"$BACKUP/status.txt"
  tar -czf "$REPORT" -C "$BACKUP" status.txt install.log || :
  local owner
  owner=$(printenv SUDO_USER || true)
  if [[ -n "$owner" ]]; then chown "$owner" "$REPORT" || :; fi
  echo "SANITIZED_REPORT=$REPORT"
}
restore_previous(){
  for path in frontend/recipe-step-modes-v259.js frontend/cook4me-panel-v81.js frontend/cook4me-panel-v180.js panel.py; do
    cp -a "$BACKUP/$path" "$RUNTIME/$path"
  done
  if (( HAD_MODULE )); then
    cp -a "$BACKUP/frontend/loaded-device-recipe-v284.js" "$RUNTIME/frontend/loaded-device-recipe-v284.js"
  else
    rm -f "$RUNTIME/frontend/loaded-device-recipe-v284.js"
  fi
}
rollback(){
  local code="$1"
  trap - ERR INT TERM HUP
  set +e
  echo "Cook4Me v284 preview failed ($code); restoring previous frontend files"
  if (( CHANGED )); then
    if [[ "$(docker inspect -f '{{.State.Running}}' "$HA" 2>/dev/null)" == true ]]; then docker stop --time 120 "$HA" >/dev/null 2>&1 || :; fi
    restore_previous
  fi
  if (( CHANGED || STOPPED )); then docker start "$HA" >/dev/null 2>&1 || echo "Please check Home Assistant startup"; fi
  record_report FAIL
  rm -rf "$STAGE"
  exit "$code"
}
trap 'rollback $?' ERR
trap 'rollback 130' INT TERM HUP
exec > >(tee -a "$LOG") 2>&1
echo "Staging exact v284 candidate and regression tests; Home Assistant untouched"
while read -r path expected; do
  [[ -z "$path" ]] && continue
  mkdir -p "$STAGE/$(dirname "$path")"
  if [[ "$path" == tests/* ]]; then url="$GITHUB/$path"
  else url="$GITHUB/custom_components/cook4me/$path"; fi
  curl -fLsS --retry 3 --connect-timeout 12 --max-time 80 "$url" -o "$STAGE/$path"
  [[ "$(git hash-object "$STAGE/$path")" == "$expected" ]] || { echo "Candidate hash mismatch: $path"; false; }
done <<'MANIFEST'
frontend/loaded-device-recipe-v284.js 41b8d7ebfb1b4a223e52e5bc565b195746817b66
frontend/recipe-step-modes-v259.js eef1f1c1f5ffa29689f5399a97e8f244e0dea2f1
frontend/cook4me-panel-v81.js d0ec4929c1aba5a3ff93853fe3b0b34cde3a06f7
frontend/cook4me-panel-v180.js 7e12f641d1cf1321107b9f5602623b10172fdbdc
panel.py 385f7eef7cd2905d29d3e5ddb2bebd0b3c5eb660
tests/test_loaded_device_recipe_v284.mjs 620d8ec8cf3108b607059734b0119bed9cf37041
tests/test_recipe_step_modes_v259.mjs edab6a3d4551150455aaa3654eb2982387e5afb4
MANIFEST
# Retain repository-relative imports for the exact node:test files.
mkdir -p "$STAGE/custom_components/cook4me"
ln -s "$STAGE/frontend" "$STAGE/custom_components/cook4me/frontend"
ln -s "$STAGE/panel.py" "$STAGE/custom_components/cook4me/panel.py"
printf '{"type":"module"}\n' >"$STAGE/package.json"
python3 - "$STAGE/panel.py" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
compile(p.read_bytes(),str(p),"exec")
print('Python registration syntax: PASS')
PY
echo "Checking candidate JavaScript syntax before running focused tests"
for path in frontend/loaded-device-recipe-v284.js frontend/recipe-step-modes-v259.js frontend/cook4me-panel-v81.js frontend/cook4me-panel-v180.js; do
  node --check "$STAGE/$path"
done
echo "Running v284 navigation/mode tests and retained v259 mode tests"
node --test "$STAGE/tests/test_loaded_device_recipe_v284.mjs" "$STAGE/tests/test_recipe_step_modes_v259.mjs"
echo "RECIPE_REGRESSIONS=PASS"
echo "Verifying current installed files before any write..."
while read -r path baseline candidate; do
  current=$(git hash-object "$RUNTIME/$path")
  [[ "$current" == "$baseline" || "$current" == "$candidate" ]] || { echo "Refusing unexpected local file: $path"; false; }
done <<'BASELINES'
frontend/recipe-step-modes-v259.js 107d0f6a293ed9aa51f3737126ece18b7fd7b5ca eef1f1c1f5ffa29689f5399a97e8f244e0dea2f1
frontend/cook4me-panel-v81.js cfbf48194abe53c21d5118cd91888efc64bbee89 d0ec4929c1aba5a3ff93853fe3b0b34cde3a06f7
frontend/cook4me-panel-v180.js 0bcbbb579ba483fee4ad48788c61c527f740959f 7e12f641d1cf1321107b9f5602623b10172fdbdc
panel.py 28a680e25014813efec4dd370bb686126c9225a5 385f7eef7cd2905d29d3e5ddb2bebd0b3c5eb660
BASELINES
if (( HAD_MODULE )); then
  [[ "$(git hash-object "$RUNTIME/frontend/loaded-device-recipe-v284.js")" == 41b8d7ebfb1b4a223e52e5bc565b195746817b66 ]] || { echo "Unknown existing v284 source"; false; }
fi
[[ "$(stat -c %d "$STAGE")" == "$(stat -c %d "$RUNTIME")" ]] || { echo "Staging filesystem mismatch"; false; }
for path in frontend/recipe-step-modes-v259.js frontend/cook4me-panel-v81.js frontend/cook4me-panel-v180.js panel.py; do
  mkdir -p "$BACKUP/$(dirname "$path")"
  cp -a "$RUNTIME/$path" "$BACKUP/$path"
done
if (( HAD_MODULE )); then cp -a "$RUNTIME/frontend/loaded-device-recipe-v284.js" "$BACKUP/frontend/loaded-device-recipe-v284.js";fi
echo "Stopping only Home Assistant for frontend source replacement..."
STOPPED=1
docker stop --time 120 "$HA" >/dev/null
CHANGED=1
while read -r path expected; do
  [[ -z "$path" ]] && continue
  [[ "$path" == tests/* ]] && continue
  if [[ -f "$RUNTIME/$path" ]]; then
    chmod --reference="$RUNTIME/$path" "$STAGE/$path"
    chown --reference="$RUNTIME/$path" "$STAGE/$path"
  else
    chmod --reference="$RUNTIME/panel.py" "$STAGE/$path"
    chown --reference="$RUNTIME/panel.py" "$STAGE/$path"
  fi
  mv -f "$STAGE/$path" "$RUNTIME/$path"
done <<'MANIFEST'
frontend/loaded-device-recipe-v284.js 41b8d7ebfb1b4a223e52e5bc565b195746817b66
frontend/recipe-step-modes-v259.js eef1f1c1f5ffa29689f5399a97e8f244e0dea2f1
frontend/cook4me-panel-v81.js d0ec4929c1aba5a3ff93853fe3b0b34cde3a06f7
frontend/cook4me-panel-v180.js 7e12f641d1cf1321107b9f5602623b10172fdbdc
panel.py 385f7eef7cd2905d29d3e5ddb2bebd0b3c5eb660
tests/test_loaded_device_recipe_v284.mjs 620d8ec8cf3108b607059734b0119bed9cf37041
tests/test_recipe_step_modes_v259.mjs edab6a3d4551150455aaa3654eb2982387e5afb4
MANIFEST
docker start "$HA" >/dev/null
ready=0
for ((i=0;i<120;i++)); do
  if [[ "$(docker inspect -f '{{.State.Running}}' "$HA" 2>/dev/null)" == true ]] && curl -fsS --max-time 5 http://127.0.0.1:8123/ >/dev/null 2>&1; then ready=1;break;fi
  sleep 2
done
(( ready )) || { echo "Home Assistant did not become ready; restoring files"; false; }
while read -r path expected; do
  [[ -z "$path" || "$path" == tests/* ]] && continue
  [[ "$(git hash-object "$RUNTIME/$path")" == "$expected" ]] || { echo "Installed file mismatch: $path"; false; }
done <<'MANIFEST'
frontend/loaded-device-recipe-v284.js 41b8d7ebfb1b4a223e52e5bc565b195746817b66
frontend/recipe-step-modes-v259.js eef1f1c1f5ffa29689f5399a97e8f244e0dea2f1
frontend/cook4me-panel-v81.js d0ec4929c1aba5a3ff93853fe3b0b34cde3a06f7
frontend/cook4me-panel-v180.js 7e12f641d1cf1321107b9f5602623b10172fdbdc
panel.py 385f7eef7cd2905d29d3e5ddb2bebd0b3c5eb660
tests/test_loaded_device_recipe_v284.mjs 620d8ec8cf3108b607059734b0119bed9cf37041
tests/test_recipe_step_modes_v259.mjs edab6a3d4551150455aaa3654eb2982387e5afb4
MANIFEST
STOPPED=0
CHANGED=0
trap - ERR INT TERM HUP
echo "FRONTEND_PREVIEW_DEPLOY=PASS"
record_report PASS
rm -rf "$STAGE"
echo "Refresh the Cook4Me panel, open device information and click the loaded recipe title."
