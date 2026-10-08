#!/usr/bin/env bash
# Pinned Cook4Me startup-resilience deployment. Never source into a live SSH shell.
set -Eeuo pipefail
SHA=74adb9bc43ec2359323c567030a3308bbeb6cc90
CONFIG=/home/chreece/homeassistant/config
LIVE="$CONFIG/custom_components/cook4me"
BACKUPS=/home/chreece/.local/state/ha-integration-backups/cook4me
CONTAINER=homeassistant
umask 077
[[ $EUID -eq 0 ]] || { echo 'Run with sudo bash'; exit 1; }
for cmd in curl tar python3 docker flock mv stat cmp readlink; do
    command -v "$cmd" >/dev/null || { echo "Missing: $cmd"; exit 1; }
done
[[ -d "$LIVE" && ! -L "$LIVE" ]] || { echo "Invalid Cook4Me installation: $LIVE"; exit 1; }
[[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER")" == true ]] || { echo "Container $CONTAINER not running"; exit 1; }
MOUNT=$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/config"}}{{.Source}}{{end}}{{end}}' "$CONTAINER")
[[ "$(readlink -f "$MOUNT")" == "$(readlink -f "$CONFIG")" ]] || { echo "Refusing unexpected /config mount: $MOUNT"; exit 1; }
mkdir -p "$BACKUPS" "$CONFIG/.cook4me-deploy"
exec 9>"$CONFIG/.cook4me-deploy/deploy.lock"
flock -n 9 || { echo 'Another Cook4Me deployment is active'; exit 1; }
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
WORK=$(mktemp -d "$CONFIG/.cook4me-deploy/startup-$STAMP-XXXXXX")
BACKUP="$BACKUPS/pre-startup-$STAMP-$$"
LOG="$BACKUPS/startup-deploy-$STAMP.log"
exec > >(tee -a "$LOG") 2>&1
CHANGED=0
rollback() {
    local rc=${1:-1}
    trap - ERR INT TERM HUP
    set +e
    echo "Deployment failure (code=$rc)"
    if (( CHANGED )); then
        docker stop --time 90 "$CONTAINER" >/dev/null 2>&1 || true
        if [[ -d "$BACKUP" ]]; then
            [[ ! -d "$LIVE" ]] || mv "$LIVE" "$WORK/failed-cook4me"
            if mv "$BACKUP" "$LIVE"; then echo 'Previous Cook4Me files restored.'
            else echo "Manual recovery required: previous files in $BACKUP"; fi
        fi
        docker start "$CONTAINER" >/dev/null 2>&1 || true
    fi
    echo 'COOK4ME_DEPLOY_RESULT=FAIL'
    echo "LOG=$LOG"
    exit "$rc"
}
trap 'rollback $?' ERR
trap 'rollback 130' INT TERM HUP
[[ "$(stat -c %d "$LIVE")" == "$(stat -c %d "$WORK")" &&
   "$(stat -c %d "$LIVE")" == "$(stat -c %d "$BACKUPS")" ]] || {
    echo 'Staging and backup must be on the same filesystem'; false;
}
echo "Fetching pinned, tested GitHub commit $SHA..."
curl -fLsS --retry 3 --connect-timeout 15 --max-time 240 "https://codeload.github.com/Chreece/HA-Cook4me/tar.gz/$SHA" -o "$WORK/source.tar.gz"
mkdir -p "$WORK/extract"
tar -xzf "$WORK/source.tar.gz" -C "$WORK/extract"
mapfile -t roots < <(find "$WORK/extract" -mindepth 1 -maxdepth 1 -type d)
[[ ${#roots[@]} == 1 ]] || { echo 'Unexpected archive layout'; false; }
SOURCE=${roots[0]}
STAGED="$WORK/staged-cook4me"
[[ -f "$SOURCE/custom_components/cook4me/bridge.py" &&
   -f "$SOURCE/custom_components/cook4me/vendor/cook4me_auto.py" &&
   -f "$SOURCE/tests/test_bridge_offline_startup.py" ]] || { echo 'Required source files missing'; false; }
echo 'Running bridge regression tests and syntax checks...'
python3 -B "$SOURCE/tests/test_bridge_offline_startup.py"
PYTHONPYCACHEPREFIX="$WORK/pycache" python3 -m compileall -q "$SOURCE/custom_components/cook4me"
cp -a "$SOURCE/custom_components/cook4me" "$STAGED"
chown -R --reference="$LIVE" "$STAGED"
chmod -R a+rX "$STAGED"
echo "Backing up installed integration externally to $BACKUP"
CHANGED=1
docker stop --time 120 "$CONTAINER" >/dev/null
mv "$LIVE" "$BACKUP"
mv "$STAGED" "$LIVE"
docker start "$CONTAINER" >/dev/null
cmp -s "$SOURCE/custom_components/cook4me/bridge.py" "$LIVE/bridge.py"
cmp -s "$SOURCE/custom_components/cook4me/vendor/cook4me_auto.py" "$LIVE/vendor/cook4me_auto.py"
echo 'Checking that Home Assistant becomes responsive...'
HEALTHY=0
for ((i=0;i<60;i++)); do
    if [[ "$(docker inspect -f '{{.State.Running}}' "$CONTAINER")" == true ]] &&
       curl -fsS --max-time 4 http://127.0.0.1:8123/ >/dev/null 2>&1; then
        HEALTHY=1; break
    fi
    sleep 2
done
(( HEALTHY )) || { echo 'Home Assistant frontend health check failed'; false; }
CHANGED=0
trap - ERR INT TERM HUP
echo 'COOK4ME_DEPLOY_RESULT=PASS'
echo "COMMIT=$SHA"
echo "BACKUP=$BACKUP"
echo "LOG=$LOG"
echo 'Home Assistant is responding. Cloud connectivity is not yet verified.'
echo 'Recent Cook4Me log lines:'
docker logs --since 3m "$CONTAINER" 2>&1 | grep -Ei '(cook4me|initial cloud state|mqtt reconnect)' | tail -35 || true
rm -rf "$WORK" || true
