#!/usr/bin/env bash
# Deep, read-only multi-page Groupe SEB recipe-program audit. Run in existing SSH.
# No Home Assistant restarts, HACS file changes, inventory writes or SSH exits.
set -Eeuo pipefail
set +x
umask 077
[[ "$EUID" != 0 ]] || { echo "Run in the existing normal-user SSH shell (not sudo bash)"; exit 1; }
for exe in curl docker git python3 sudo tar mktemp date mkdir; do
  command -v "$exe" >/dev/null || { echo "Missing required command: $exe"; exit 1; }
done
HA=homeassistant
SOURCE_COMMIT=98089349fcb1ce735e6ac43a1b5ee84653c1681c
SOURCE_BLOB=d058850f750d4cad5d91d096f645893258a32bdf
SRC=$(mktemp /tmp/cook4me-seb-names.XXXXXX.py)
TMP=$(mktemp /tmp/cook4me-seb-out.XXXXXX.json)
CONTAINER_PATH="/tmp/cook4me-seb-programs-$USER-$$.py"
OUTDIR="$HOME/projects/cook4me/logs"
STAMP=$(date -u +%Y%m%d-%H%M%S)
REPORT="$OUTDIR/cook4me-seb-deep-programs-$STAMP.tar.gz"
JSON_OUT="$OUTDIR/cook4me-seb-deep-programs-$STAMP.json"
cleanup(){
  rm -f "$SRC" "$TMP"
  sudo docker exec --user 0 "$HA" rm -f "$CONTAINER_PATH" >/dev/null 2>&1 || :
}
trap cleanup EXIT
mkdir -p "$OUTDIR"
echo "Verifying official-SEB audit source and Home Assistant container..."
curl -fLsS --retry 3 --connect-timeout 12 --max-time 80 \
 "https://raw.githubusercontent.com/Chreece/HA-Cook4me/$SOURCE_COMMIT/tools/audit_seb_official_programs_v286.py" \
 -o "$SRC"
[[ "$(git hash-object "$SRC")" == "$SOURCE_BLOB" ]] || {
 echo "Source content verification failed"; exit 1;
}
python3 -B - "$SRC" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1])
compile(p.read_bytes(),str(p),'exec')
print('SOURCE_SYNTAX=PASS')
PY
sudo -v
[[ "$(sudo docker inspect -f '{{.State.Running}}' "$HA" 2>/dev/null)" == true ]] || {
 echo "Home Assistant must already be running"; exit 1;
}
sudo docker cp "$SRC" "$HA:$CONTAINER_PATH"
sudo docker exec --user 0 "$HA" python3 -B "$CONTAINER_PATH" --offline-self-test
echo "Querying official SEB recipe program metadata (read-only and rate-limited)..."
set +e
sudo docker exec --user 0 "$HA" python3 -B "$CONTAINER_PATH" \
  --root /config --max-actions 120 --max-seconds 780 \
  --markets DE:de,FR:fr,ES:es,IT:it,PL:pl,CZ:cs,GB:en,TR:tr \
  --page-indices 1,5,12 --details-per-market 3 --page-size 20 --delay 0.8 \
  >"$TMP" 2>/dev/null
rc=$?
set -e
if [[ "$rc" != 0 && "$rc" != 2 ]]; then
  echo "Official SEB audit could not complete (status $rc). No Home Assistant data was modified."
  if [[ -s "$TMP" ]]; then
    python3 - "$TMP" <<'PY'
import json,sys
try:
 o=json.load(open(sys.argv[1]))
 print('ERROR_CLASS='+str(o.get('errorClass','unavailable')))
except Exception:
 print('ERROR_CLASS=unavailable')
PY
  fi
  exit 1
fi
python3 - "$TMP" "$JSON_OUT" <<'PY'
import json,sys
from pathlib import Path
src,dst=map(Path,sys.argv[1:])
obj=json.loads(src.read_text(encoding='utf-8'))
assert obj['origin'].startswith('Groupe SEB ')
assert obj['sensitiveDataIncluded'] is False
assert obj['completeSeBCatalog'] is False
dst.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
dst.chmod(0o600)
count=obj.get('counts') or {}
print('SEB_AUDIT=PASS')
print('SEB_MARKETS_WITH_DETAILS='+str(count.get('marketsWithDetails',0)))
print('SEB_DISTINCT_PROGRAM_KEYS='+str(count.get('programKeys',0)))
print('SEB_DISTINCT_PROGRAM_NAMES='+str(count.get('programNames',0)))
print('SEB_PROGRAM_PAIRS='+str(obj.get('uniqueProgramPairs',0)))
print('SEB_REQUESTS='+str(count.get('requestsBudgeted',0)))
print('SEB_WARNINGS='+','.join(obj.get('warnings') or []))
PY
tar -czf "$REPORT" -C "$OUTDIR" "$(basename "$JSON_OUT")"
chmod 600 "$REPORT"
echo "SANITIZED_REPORT=$REPORT"
echo "Upload the SANITIZED_REPORT archive. Do not upload any token files."
