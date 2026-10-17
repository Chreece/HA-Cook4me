#!/usr/bin/env bash
# Hash-verified, read-only candidate scan. Never deploy or change stock.
set -Eeuo pipefail
set +x
umask 077
[[ "$EUID" != 0 ]] || { echo 'Run in normal user SSH (not root)'; exit 1; }
for c in curl git node python3 tar mktemp mkdir date; do
 command -v "$c" >/dev/null || { echo "Missing: $c"; exit 1; }
done
ROOT="${COOK4ME_HA_CONFIG:-$HOME/homeassistant/config}"
OUTDIR="$HOME/projects/cook4me/logs"
BASE="https://raw.githubusercontent.com/Chreece/HA-Cook4me/ea9e29c0c8aac3362c2801dba1a0d9135925f291"
SCANNER_SHA="0d2b803568757404996e1a930d6d30efca7a43b8"
CANDIDATE_SHA="4eeeb2a2e82d8aa16a8be8040fb745c67703719e"
WORK=$(mktemp -d /tmp/cook4me-programs-v288.XXXXXXXX)
trap 'rm -rf "$WORK"' EXIT
[[ -d "$ROOT/.storage" ]] || { echo "Missing Home Assistant .storage: $ROOT"; exit 1; }
curl -fLsS --retry 3 --connect-timeout 12 --max-time 80 "$BASE/tools/audit_cook4me_program_modes_v285.mjs" -o "$WORK/audit.mjs"
curl -fLsS --retry 3 --connect-timeout 12 --max-time 80 "$BASE/custom_components/cook4me/frontend/recipe-step-modes-v259.js" -o "$WORK/candidate.mjs"
[[ "$(git hash-object "$WORK/audit.mjs")" == "$SCANNER_SHA" ]] || { echo 'Scanner content hash mismatch'; exit 1; }
[[ "$(git hash-object "$WORK/candidate.mjs")" == "$CANDIDATE_SHA" ]] || { echo 'Mode candidate content hash mismatch'; exit 1; }
node --check "$WORK/audit.mjs"
node --check "$WORK/candidate.mjs"
mkdir -p "$OUTDIR"
REPORT="$OUTDIR/cook4me-recipe-programs-full-$(date -u +%Y%m%d-%H%M%S).tar.gz"
set +e
node "$WORK/audit.mjs" --root "$ROOT" --resolver "$WORK/candidate.mjs" --json "$WORK/programs.json" > "$WORK/stdout.json" 2> "$WORK/errors.log"
rc=$?
set -e
if [[ "$rc" != 0 && "$rc" != 2 ]] || [[ ! -s "$WORK/programs.json" ]]; then
 echo "AUDIT_FAILED exit=$rc"
 tail -n 12 "$WORK/errors.log" || :
 exit 1
fi
python3 - "$WORK/programs.json" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding='utf8'))
s=d.get('scan',{})
print('AUDIT=PASS (unresolved modes give a diagnostic exit code)')
for k in ['recipesWithSteps','steps','programReferences','resolved','unknownNamed','unknownKeyOnly','noStepProgramEvidence']:
 print(k.upper()+'='+str(s.get(k)))
print('COVERAGE_PERCENT='+str(d.get('coverage',{}).get('resolvedPercent')))
print('UNKNOWN_PAIRS='+str(d.get('uniqueUnknownPrograms')))
print('WARNINGS='+','.join(d.get('warnings',[])))
PY
tar -czf "$REPORT" -C "$WORK" programs.json
chmod 600 "$REPORT"
echo "FULL_SANITIZED_REPORT=$REPORT"
echo 'Upload the archive. Home Assistant, your cooker, and SSH were not modified.'
