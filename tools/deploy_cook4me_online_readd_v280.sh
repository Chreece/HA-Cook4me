#!/usr/bin/env bash
# Staged, reversible Cook4Me re-add acceptance install.
# Pin to the exact source whose live discovery, signed MQTT, and 17 regressions
# passed on 2026-10-10. Does not alter VPN, DNS, routes, credentials or HA storage.
# Execute as "sudo bash <file>", never source into your SSH shell.
set -Eeuo pipefail
set +x
umask 077
[[ $EUID -eq 0 ]] || { echo "Use sudo bash, not source"; exit 1; }
for executable in docker curl git python3 flock cmp stat readlink mktemp chown chmod mv cp tar tee; do
  command -v "$executable" >/dev/null || { echo "Missing command: $executable"; exit 1; }
done

SOURCE_SHA=d91b40b3c09289d497f2e7f355d6a17229d82a7c
GITHUB_ROOT="https://raw.githubusercontent.com/Chreece/HA-Cook4me/$SOURCE_SHA/custom_components/cook4me/vendor"
CONFIG=/home/chreece/homeassistant/config
LIVE="$CONFIG/custom_components/cook4me/vendor"
HA=homeassistant
BACKUP_ROOT=/home/chreece/.local/state/ha-integration-backups/cook4me
HEALTH_URL=http://127.0.0.1:8123/
[[ -d "$LIVE" && ! -L "$LIVE" ]] || { echo "Cook4Me vendor installation missing or symlinked"; exit 1; }
[[ -f "$LIVE/cook4me_auto.py" && -f "$LIVE/cook4me_phonefree.py" ]] || { echo "Current vendor files missing"; exit 1; }
[[ "$(docker inspect -f '{{.State.Running}}' "$HA" 2>/dev/null)" == true ]] || {
  echo "Home Assistant must already be running"; exit 1;
}
mount_json=$(docker inspect -f '{{json .Mounts}}' "$HA")
python3 - "$mount_json" "$CONFIG" <<'PY'
import json, os, sys
mounts=json.loads(sys.argv[1])
target=os.path.realpath(sys.argv[2])
matches=[m for m in mounts if m.get("Destination")=="/config"]
if len(matches)!=1 or matches[0].get("Type")!="bind" or not matches[0].get("RW") or os.path.realpath(matches[0].get("Source",""))!=target:
    raise SystemExit("Preflight FAIL: unexpected HA /config bind mount; no files changed")
if any(m.get("Destination","").startswith("/config/custom_components/") for m in mounts):
    raise SystemExit("Preflight FAIL: nested component mount; no files changed")
print("Home Assistant bind mount: verified")
PY

mkdir -p "$BACKUP_ROOT" "$CONFIG/.cook4me-deploy"
exec 9>"$CONFIG/.cook4me-deploy/deploy.lock"
flock -n 9 || { echo "Another Cook4Me deployment is running"; exit 1; }
STAMP=$(date -u +%Y%m%d-%H%M%S)
STAGE=$(mktemp -d "$CONFIG/.cook4me-deploy/online-$STAMP-XXXXXX")
BACKUP="$BACKUP_ROOT/online-readd-$STAMP-$$"
mkdir -p "$BACKUP"
LOG="$BACKUP/deploy.log"
changed=0
stopped=0
was_adaptive=0
[[ -f "$LIVE/adaptive_transport.py" ]] && was_adaptive=1
cleanup() { rm -rf -- "$STAGE"; }
rollback() {
  local code="$1"
  trap - ERR INT TERM HUP
  set +e
  printf 'Deployment failed (exit %s). Restoring previous files...\n' "$code"
  if (( stopped )); then
    docker stop --time 90 "$HA" >/dev/null 2>&1 || :
  fi
  if (( changed )); then
    for file in cook4me_auto.py cook4me_phonefree.py; do
      [[ -f "$BACKUP/$file" ]] && cp -a "$BACKUP/$file" "$LIVE/$file"
    done
    if (( was_adaptive )); then
      cp -a "$BACKUP/adaptive_transport.py" "$LIVE/adaptive_transport.py"
    else
      rm -f -- "$LIVE/adaptive_transport.py"
    fi
  fi
  if (( stopped )); then
    docker start "$HA" >/dev/null 2>&1 || echo "Recovery needs attention: docker start $HA"
  fi
  cleanup
  echo "COOK4ME_DEPLOY_RESULT=FAIL"
  printf 'COOK4ME_DEPLOY_RESULT=FAIL\n' > "$BACKUP/status.txt"
  PROOF="/home/chreece/cook4me-deploy-proof-$STAMP.tar.gz"
  if [[ -f "$BACKUP/deploy.log" ]]; then
    tar -czf "$PROOF" -C "$BACKUP" status.txt deploy.log 2>/dev/null || :
    if [[ -n $(printenv SUDO_USER || true) ]]; then chown "$(printenv SUDO_USER)" "$PROOF" || :; fi
    echo "DEPLOYMENT_EVIDENCE=$PROOF"
  fi
  echo "BACKUP=$BACKUP"
  echo "LOG=$LOG"
  exit "$code"
}
trap 'rollback $?' ERR
trap 'rollback 130' INT TERM HUP

# All stage-to-live renames must remain on the same filesystem.
[[ "$(stat -c %d "$LIVE")" == "$(stat -c %d "$STAGE")" ]] || {
  echo "Unsafe staging filesystem"; false;
}
exec > >(tee -a "$LOG") 2>&1
# Do not overwrite unknown local work, even when the source download is pinned.
# Allow both the known released main baseline and the exact tested candidate.
for spec in \
  'cook4me_auto.py 10c85d217e0d876e8f05afd00a94ce7e4751f6f8 cdbf155f59d0b4174655aceca72570fdf6fe1485' \
  'cook4me_phonefree.py 9d6ba72930bd6cd23ef2c6341332a834ca4b4e77 4786eaf2d30a24448cf8c3c5cf075a3207443d6a'; do
  read -r name known_baseline candidate <<<"$spec"
  installed=$(git hash-object "$LIVE/$name")
  if [[ "$installed" != "$known_baseline" && "$installed" != "$candidate" ]]; then
    echo "Refusing to overwrite unexpected locally installed code: $name (blob $installed)"
    false
  fi
done
if [[ -f "$LIVE/adaptive_transport.py" ]]; then
  installed=$(git hash-object "$LIVE/adaptive_transport.py")
  [[ "$installed" == c00951326b14e8a99909133c3710e7564088f592 ]] || {
    echo "Refusing to overwrite unknown adaptive_transport.py (blob $installed)"; false;
  }
fi
echo "Installed-file baseline verification: PASS"
echo "Preparing exact live-tested Cook4Me files, source commit $SOURCE_SHA"
for spec in \
  'cook4me_auto.py cdbf155f59d0b4174655aceca72570fdf6fe1485' \
  'cook4me_phonefree.py 4786eaf2d30a24448cf8c3c5cf075a3207443d6a' \
  'adaptive_transport.py c00951326b14e8a99909133c3710e7564088f592'; do
  read -r name expected <<<"$spec"
  curl -fLsS --retry 3 --connect-timeout 15 --max-time 90 "$GITHUB_ROOT/$name" -o "$STAGE/$name"
  [[ "$(git hash-object "$STAGE/$name")" == "$expected" ]] || {
    echo "Exact source hash mismatch: $name"; false;
  }
  chmod --reference="$LIVE/cook4me_auto.py" "$STAGE/$name"
  chown --reference="$LIVE/cook4me_auto.py" "$STAGE/$name"
done
python3 - "$STAGE" <<'PY'
from pathlib import Path
import sys
folder=Path(sys.argv[1])
for name in ("cook4me_auto.py","cook4me_phonefree.py","adaptive_transport.py"):
    p=folder/name
    compile(p.read_bytes(),str(p),"exec")
print("Candidate syntax and exact-source preflight: PASS")
PY
echo "Backing up current files outside custom_components..."
for file in cook4me_auto.py cook4me_phonefree.py; do
  cp -a "$LIVE/$file" "$BACKUP/$file"
done
if (( was_adaptive )); then cp -a "$LIVE/adaptive_transport.py" "$BACKUP/adaptive_transport.py"; fi
printf 'source_commit=%s\nprevious_adaptive_present=%s\n' "$SOURCE_SHA" "$was_adaptive" >"$BACKUP/metadata.txt"

# The real tested vendor code, not a mixture of preview bundle changes.
echo "Stopping only Home Assistant, installing the three verified files..."
stopped=1
docker stop --time 120 "$HA" >/dev/null
changed=1
for file in cook4me_auto.py cook4me_phonefree.py adaptive_transport.py; do
  mv -f "$STAGE/$file" "$LIVE/$file"
done
docker start "$HA" >/dev/null
echo "Verifying Home Assistant starts and serves its frontend..."
healthy=0
for ((iteration=0;iteration<120;iteration++)); do
  if [[ "$(docker inspect -f '{{.State.Running}}' "$HA" 2>/dev/null)" == true ]] &&
     curl -fsS --max-time 5 "$HEALTH_URL" >/dev/null 2>&1; then
    healthy=1; break
  fi
  sleep 2
done
(( healthy )) || { echo "HA health check failed: rolling back"; false; }
for spec in \
  'cook4me_auto.py cdbf155f59d0b4174655aceca72570fdf6fe1485' \
  'cook4me_phonefree.py 4786eaf2d30a24448cf8c3c5cf075a3207443d6a' \
  'adaptive_transport.py c00951326b14e8a99909133c3710e7564088f592'; do
  read -r name expected <<<"$spec"
  [[ "$(git hash-object "$LIVE/$name")" == "$expected" ]] || {
    echo "Installed file mismatch: $name"; false;
  }
done
stopped=0
changed=0
trap - ERR INT TERM HUP
cleanup
echo
echo "COOK4ME_DEPLOY_RESULT=PASS"
printf 'COOK4ME_DEPLOY_RESULT=PASS\nCANDIDATE_SOURCE=%s\n' "$SOURCE_SHA" > "$BACKUP/status.txt"
PROOF="/home/chreece/cook4me-deploy-proof-$STAMP.tar.gz"
tar -czf "$PROOF" -C "$BACKUP" metadata.txt status.txt deploy.log
if [[ -n $(printenv SUDO_USER || true) ]]; then
  chown "$(printenv SUDO_USER)" "$PROOF" || :
fi
echo "DEPLOYMENT_EVIDENCE=$PROOF"
echo "CANDIDATE_SOURCE=$SOURCE_SHA"
echo "BACKUP=$BACKUP"
echo "LOG=$LOG"
echo "Home Assistant responds. No config entries or cooker data were changed."
echo "Next: Settings > Devices & services > Add integration > Cook4Me."
