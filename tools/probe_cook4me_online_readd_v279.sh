#!/usr/bin/env bash
# Execute only tests and read-only device requests on the user's actual HA network.
# Does not modify the integration, OS DNS, VPN, routes or firewall; never exits SSH.
set -Eeuo pipefail
set +x
umask 077
if [[ $EUID -ne 0 ]]; then echo 'Run with sudo bash'; exit 1; fi
HA=homeassistant
COMMIT=5fbd75654610b84b835649c36b36d68c494d1f33
BASE=https://raw.githubusercontent.com/Chreece/HA-Cook4me/$COMMIT
WORK=$(mktemp -d /tmp/cook4me-online-XXXXXX)
REMOTE=/tmp/$(basename "$WORK")
OUT=/home/chreece/cook4me-online-readd-proof-$(date -u +%Y%m%d-%H%M%S).tar.gz
cleanup() {
    docker exec --user 0 "$HA" rm -rf -- "$REMOTE" >/dev/null 2>&1 || :
    rm -rf -- "$WORK"
    unset COOK4ME_EMAIL COOK4ME_PASSWORD 2>/dev/null || :
}
trap cleanup EXIT
[[ $(docker inspect -f '{{.State.Running}}' "$HA" 2>/dev/null) == true ]] || { echo 'Home Assistant container is not running'; exit 1; }
[[ -f /home/chreece/homeassistant/config/custom_components/cook4me/vendor/cook4me_plain_http_auth.py ]] || { echo 'Missing existing Cook4Me auth client'; exit 1; }
mkdir -p "$WORK/custom_components/cook4me/vendor" "$WORK/tests"
for file in custom_components/cook4me/vendor/adaptive_transport.py custom_components/cook4me/vendor/cook4me_phonefree.py custom_components/cook4me/vendor/cook4me_auto.py tests/test_adaptive_transport_v277.py tests/test_discovery_no_aws_v276.py; do
    curl -fLsS --retry 3 --connect-timeout 15 --max-time 90 "$BASE/$file" -o "$WORK/$file"
done
cp /home/chreece/homeassistant/config/custom_components/cook4me/vendor/cook4me_plain_http_auth.py \
    "$WORK/custom_components/cook4me/vendor/cook4me_plain_http_auth.py"
for spec in \
 'custom_components/cook4me/vendor/adaptive_transport.py c00951326b14e8a99909133c3710e7564088f592' \
 'custom_components/cook4me/vendor/cook4me_phonefree.py 4786eaf2d30a24448cf8c3c5cf075a3207443d6a' \
 'custom_components/cook4me/vendor/cook4me_auto.py cdbf155f59d0b4174655aceca72570fdf6fe1485' \
 'tests/test_adaptive_transport_v277.py 7188f09ffc3e15fc51a5bd572c0e0287ce1615b7' \
 'tests/test_discovery_no_aws_v276.py 4a21e8ecdd9f9134ccf4058b90c1aaec1acdcb80'; do
    read -r file expected <<<"$spec"
    [[ $(git hash-object "$WORK/$file") == "$expected" ]] || { echo "Source integrity failed: $file"; exit 1; }
done
python3 - "$WORK" <<'PY'
from pathlib import Path
import sys
root=Path(sys.argv[1])
for p in root.rglob("*.py"):
    compile(p.read_bytes(),str(p),"exec")
print("Candidate Python syntax: PASS")
PY
docker exec --user 0 "$HA" mkdir -p "$REMOTE/custom_components/cook4me/vendor" "$REMOTE/tests"
docker exec --user 0 "$HA" cp -a /config/custom_components/cook4me/vendor/. "$REMOTE/custom_components/cook4me/vendor/"
for file in custom_components/cook4me/vendor/adaptive_transport.py custom_components/cook4me/vendor/cook4me_phonefree.py custom_components/cook4me/vendor/cook4me_auto.py custom_components/cook4me/vendor/cook4me_plain_http_auth.py tests/test_adaptive_transport_v277.py tests/test_discovery_no_aws_v276.py; do
    docker cp "$WORK/$file" "$HA:$REMOTE/$file" >/dev/null
done
echo 'Running actual adapter regression tests inside Home Assistant...'
set +e
docker exec --user 0 "$HA" python3 -B -m unittest discover -s "$REMOTE/tests" -p 'test_*_v27*.py' -v \
    >"$WORK/regressions.txt" 2>&1
TEST_RC=$?
set -e
echo "REGRESSION_RESULT=$TEST_RC"
tail -3 "$WORK/regressions.txt"
if (( TEST_RC != 0 )); then
    printf 'RESULT=REGRESSION_FAIL\n' >"$WORK/status.txt"
    tar -czf "$OUT" -C "$WORK" regressions.txt status.txt
    if [[ -n $(printenv SUDO_USER || true) ]]; then chown "$(printenv SUDO_USER)" "$OUT" || :; fi
    echo "Evidence: $OUT"
    exit 0
fi

cat >"$WORK/runner.py" <<'PY'
"""Owned-account and signed AWS IoT proof; deliberately omits secret output."""
from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import hashlib
import signal

def _deadline(_signal, _frame):
    print("RESULT PROBE_DEADLINE_EXCEEDED", flush=True)
    raise SystemExit(124)

signal.signal(signal.SIGALRM, _deadline)
signal.alarm(260)
ROOT = Path(__file__).resolve().parent
VENDOR = ROOT / "custom_components/cook4me/vendor"

def event(*parts):
    print(*parts,flush=True)

def stage(name, work):
    begin=time.monotonic()
    event("START",name)
    try:
        obj=work()
    except Exception as ex:
        match=re.search(r'HTTP (\d{3})',str(ex))
        event("FAIL",name,type(ex).__name__,"http",match.group(1) if match else "none",
              "seconds",round(time.monotonic()-begin,2))
        return None
    event("PASS",name,"seconds",round(time.monotonic()-begin,2))
    return obj

def classify_auth_log(home):
    files=sorted((Path(home)/"cook4me-re").glob("krups-plain-http-auth-*.log"))
    if not files:
        event("AUTH_REASON","no_sanitized_log")
        return
    try:
        raw=files[-1].read_text()
        data=json.loads(raw[raw.index("\n{")+1:])
        stages=[str(v) for v in (data.get("stages") or []) if isinstance(v,str) and re.fullmatch(r'[A-Za-z0-9_:-]{1,80}',v)]
        event("AUTH_STAGES",",".join(stages) or "none")
        history=data.get("http") or []
        statuses=[str(row.get("status")) for row in history if isinstance(row,dict) and isinstance(row.get("status"),int)]
        event("AUTH_HTTP_STATUS_CHAIN",",".join(statuses[-15:]) or "none")
        excerpt=str(data.get("login_a4j_excerpt") or "")
        event("AUTH_A4J_STRUCTURE",
              "redirect_tag",bool(re.search(r'<redirect',excerpt,re.I)),
              "frontdoor_mentioned","frontdoor" in excerpt.lower(),
              "login_page_mentioned","loginpage" in excerpt.lower(),
              "size",len(excerpt))
        message=str(data.get("error") or "")
        category=("login_a4j_redirect" if "no frontdoor redirect" in message.lower()
           else "oauth_callback" if "final approval action" in message.lower()
           else "loginflow_redirect" if "redirect could not be extracted" in message.lower()
           else "transport_error" if "transport error" in message.lower()
           else "missing_tokens" if not data.get("tokens_saved") else "other")
        event("AUTH_REASON",category)
    except Exception as exc:
        event("AUTH_REASON","log_parse_failed",type(exc).__name__)

with tempfile.TemporaryDirectory(prefix="cook4me-online-readd-proof-") as home:
    os.environ["HOME"]=home
    sys.path.insert(0,str(VENDOR))
    import cook4me_phonefree as client
    version="36.0.0-RC3"
    cfg=client.read_apk_config(None)
    cache=Path(home)/".config/cook4me"
    cache.mkdir(parents=True,exist_ok=True)
    tokens=None
    for p in Path("/config/.storage/cook4me").glob("*/.config/cook4me/tokens.json"):
        try:
            data=json.loads(p.read_text())
            expiry=client.jwt_exp(data.get("id_token"))
            if data.get("access_token") and expiry and expiry>time.time()+120:
                tokens=data
                break
        except Exception:
            continue
    if tokens:
        event("AUTH_SOURCE","valid_cached")
    elif os.getenv("COOK4ME_EMAIL") and os.getenv("COOK4ME_PASSWORD"):
        event("AUTH_SOURCE","live_krups_login")
        command=[sys.executable, "-u", str(VENDOR/"cook4me_plain_http_auth.py"),
                 "--country","DE","--language","de","--app-version",version,
                 "--no-save-credentials"]
        begin=time.monotonic()
        try:
            result=subprocess.run(command,env=os.environ.copy(),cwd=VENDOR,
                                  stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,timeout=165,check=False)
            event("AUTH_COMMAND_EXIT",result.returncode,"seconds",round(time.monotonic()-begin,2))
        except subprocess.TimeoutExpired:
            event("AUTH_COMMAND_TIMEOUT",165)
        classify_auth_log(home)
        try:
            tokens=json.loads((cache/"tokens.json").read_text())
        except Exception:
            tokens=None
    else:
        event("AUTH_SOURCE","missing_credentials")
    if not tokens or not tokens.get("access_token") or not tokens.get("id_token"):
        event("RESULT","INCOMPLETE_NO_KRUPS_TOKEN")
        sys.exit(0)
    expiry=client.jwt_exp(tokens.get("id_token"))
    if expiry is None or expiry <= time.time()+60:
        event("RESULT","INCOMPLETE_EXPIRED_TOKEN")
        sys.exit(0)
    (cache/"tokens.json").write_text(json.dumps(tokens))
    os.chmod(cache/"tokens.json",0o600)
    # Execute the same vendor discovery command used by HA's config flow.
    # Account-owned device JSON remains in memory; only result counts are logged.
    def candidate_discovery():
        command=[sys.executable,"-u",str(VENDOR/"cook4me_auto.py"),
                 "--country","DE","--language","de","--app-version",version,
                 "--json-lines","--no-save-credentials","discover"]
        result=subprocess.run(command,stdin=subprocess.DEVNULL,cwd=VENDOR,
                              stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              timeout=75,check=False)
        devices=[]
        for line in result.stdout.decode("utf-8","replace").splitlines():
            if not line.startswith("{"):continue
            try:
                obj=json.loads(line)
            except ValueError:continue
            if isinstance(obj,dict) and isinstance(obj.get("appliances"),list):
                devices=obj["appliances"]
        stages=[line.partition("=")[2] for line in result.stderr.decode("utf-8","replace").splitlines()
                if line.startswith("COOK4ME_BOOT_PHASE=")]
        no_aws="aws_credentials" not in stages
        event("DISCOVERY_NO_AWS",no_aws)
        if result.returncode!=0 or not no_aws or not devices:
            raise RuntimeError("CandidateDiscoveryFailed")
        return devices

    found=stage("REAL_HA_CONFIG_FLOW_DISCOVERY",candidate_discovery)
    if found is None:
        event("RESULT","INCOMPLETE_DISCOVERY")
        sys.exit(0)
    event("OWNED_DEVICES",len(found))
    if not found:
        event("RESULT","INCOMPLETE_NO_OWNED_DEVICE")
        sys.exit(0)
    creds=stage("COGNITO_REAL_CREDENTIALS",
        lambda: client.aws_credentials(cfg,tokens["id_token"]))
    if creds is None:
        event("RESULT","INCOMPLETE_AWS_CREDENTIALS")
        sys.exit(0)
    outcomes=[]
    for item in found[:2]:
        device_uuid=str(item.get("uuid") or "")
        if not device_uuid:continue
        event("DEVICE_HASH",hashlib.sha256(device_uuid.encode()).hexdigest()[:12])
        client.set_device_uuid(device_uuid)

        # Shadow GET authenticates MQTT and reads cloud device availability.
        # The separate signed CONNECT proved OK in the previous run.
        shadow=stage("SIGNED_SHADOW_GET",lambda:client.shadow_get(cfg,creds,timeout=12))
        if shadow is None:
            outcomes.append("SIGNED_SHADOW_FAILED")
            continue
        def cloud_state(reply):
            reported=client._shadow_reported_from_payload(reply)
            status=reported.get("status") if isinstance(reported,dict) else None
            raw=status.get("connected") if isinstance(status,dict) else None
            return raw if isinstance(raw,bool) else None
        connected=cloud_state(shadow)
        event("SHADOW_DEVICE_CONNECTED",connected if connected is not None else "unknown")
        for attempt in range(3):
            if connected is True:break
            event("WAITING_FOR_COOKER_ONLINE",attempt+1)
            time.sleep(8)
            fresh=stage("SHADOW_RECHECK",lambda:client.shadow_get(cfg,creds,timeout=12))
            if fresh is None:break
            shadow=fresh
            connected=cloud_state(shadow)
            event("SHADOW_DEVICE_CONNECTED",connected if connected is not None else "unknown")
        if connected is not True:
            outcomes.append("COOKER_OFFLINE_OR_STATUS_UNKNOWN")
            continue

        cooking=stage("ONLINE_COOKING_STATUS",lambda:client.cooking_status(cfg,creds,timeout=12))
        if cooking is not None:
            event("COOKING_RESPONSE_TYPE",type(cooking).__name__)
            combined=client.combined_state(cooking,shadow)
            event("INTEGRATION_AVAILABLE",combined.get("available"))
            outcomes.append("ONLINE_OK" if combined.get("available") is True else "STATE_NOT_AVAILABLE")
            continue

        # Only when cooker claims online but the response is missing: check
        # actual SUBACK permissions and receive a single read-only publish.
        def diagnose_topic():
            base="COO001/"+device_uuid
            ws=client.mqtt_open(cfg,creds,client_prefix="cook4me-online-check")
            try:
                ws.send_binary(client.mqtt_subscribe_packet(1,[(base+"/cookingStatus",0)]))
                ptype,_flags,body=client.mqtt_read_packet(ws,8)
                if ptype!=9 or len(body)<3:
                    event("COOKING_SUBACK","INVALID")
                    return False
                grant=body[2]
                event("COOKING_SUBACK_GRANT",grant)
                if int.from_bytes(body[:2],"big")!=1 or grant==128:
                    return False
                ws.send_binary(client.mqtt_publish_packet(base+"/getCookingStatus","{}"))
                expires=time.monotonic()+10
                while time.monotonic()<expires:
                    try:
                        ptype,flags,raw=client.mqtt_read_packet(ws,min(3,max(.2,expires-time.monotonic())))
                    except Exception as exc:
                        if client._is_ws_timeout(exc):continue
                        raise
                    if ptype!=3:continue
                    topic,_payload,_pid=client.mqtt_decode_publish(flags,raw)
                    if topic==base+"/cookingStatus":
                        event("COOKING_PUBLISH","RECEIVED")
                        return True
                event("COOKING_PUBLISH","MISSING_10S")
                return False
            finally:
                ws.close()
        recovered=stage("ONLINE_COOKING_TOPIC_DIAG",diagnose_topic)
        outcomes.append("TOPIC_RECOVERED" if recovered else "ONLINE_BUT_NO_COOKING_STATUS")
    if outcomes and all(x=="ONLINE_OK" for x in outcomes):
        event("RESULT","READY_FOR_HA_READD")
    else:
        event("RESULT",",".join(outcomes) if outcomes else "NO_USABLE_DEVICE_UUID")
PY
python3 - "$WORK/runner.py" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1])
compile(path.read_bytes(),str(path),'exec')
print("Signed-probe Python preflight: PASS")
PY
docker cp "$WORK/runner.py" "$HA:$REMOTE/runner.py" >/dev/null
CACHED=$(docker exec -i --user 0 "$HA" python3 - <<'PY'
import base64,json,time
from pathlib import Path
valid=False
for p in Path("/config/.storage/cook4me").glob("*/.config/cook4me/tokens.json"):
 try:
  d=json.loads(p.read_text())
  b=d["id_token"].split(".")[1]
  b+="="*((4-len(b)%4)%4)
  if json.loads(base64.urlsafe_b64decode(b))["exp"]>time.time()+120 and d.get("access_token"):
   valid=True;break
 except Exception:pass
print("yes" if valid else "no")
PY
)
COOK4ME_EMAIL=''
COOK4ME_PASSWORD=''
if [[ "$CACHED" != yes ]]; then
    echo 'No unexpired cached KRUPS token. Enter the account credentials for one temporary login test.'
    read -r -p 'KRUPS email (empty skips authenticated test): ' COOK4ME_EMAIL || :
    if [[ -n "$COOK4ME_EMAIL" ]]; then
        read -rs -p 'KRUPS password (hidden): ' COOK4ME_PASSWORD || :
        echo
    fi
fi
export COOK4ME_EMAIL COOK4ME_PASSWORD
echo 'Testing candidate discovery and powered-on cooker status (read-only)...'
set +e
timeout --signal=TERM --kill-after=5s 275s \
    docker exec --user 0 -e COOK4ME_EMAIL -e COOK4ME_PASSWORD "$HA" \
    python3 -B "$REMOTE/runner.py" >"$WORK/live.txt" 2>/dev/null
RC=$?
set -e
unset COOK4ME_EMAIL COOK4ME_PASSWORD
printf 'regression_exit=0\nlive_exit=%s\n' "$RC" > "$WORK/status.txt"
cat "$WORK/live.txt"
tar -czf "$OUT" -C "$WORK" regressions.txt live.txt status.txt
if [[ -n $(printenv SUDO_USER || true) ]]; then chown "$(printenv SUDO_USER)" "$OUT" || :; fi
printf '\nEvidence: %s\n' "$OUT"
echo 'Upload only the archive. It omits passwords, tokens, signed URLs, raw MQTT payloads and device IDs.'
