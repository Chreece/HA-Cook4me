#!/usr/bin/env bash
# Live proof of the proposed network adapter. No config writes or HA restarts.
set -Eeuo pipefail
set +x
umask 077
[[ $EUID -eq 0 ]] || { echo 'Run via sudo bash'; exit 1; }
HA=homeassistant
BRANCH_COMMIT=c203e082348020e9133a70202e124e05d6b0d426
ROOT=https://raw.githubusercontent.com/Chreece/HA-Cook4me/$BRANCH_COMMIT/custom_components/cook4me/vendor
OUT=/home/chreece/cook4me-adaptive-proof-$(date -u +%Y%m%d-%H%M%S).tar.gz
WORK=$(mktemp -d /tmp/cook4me-adapter-test-XXXXXX)
DIR=/tmp/$(basename "$WORK")
cleanup() {
  docker exec "$HA" rm -rf -- "$DIR" >/dev/null 2>&1 || :
  rm -rf -- "$WORK"
}
trap cleanup EXIT
[[ $(docker inspect -f '{{.State.Running}}' "$HA") == true ]] || { echo 'Home Assistant is not running'; exit 1; }
for file in adaptive_transport.py cook4me_phonefree.py; do
  curl -fLsS --retry 3 --connect-timeout 12 --max-time 60 "$ROOT/$file" -o "$WORK/$file"
done
[[ $(git hash-object "$WORK/adaptive_transport.py") == c00951326b14e8a99909133c3710e7564088f592 ]] || { echo 'Adapter source hash failed'; exit 1; }
[[ $(git hash-object "$WORK/cook4me_phonefree.py") == 4786eaf2d30a24448cf8c3c5cf075a3207443d6a ]] || { echo 'Cognito source hash failed'; exit 1; }
python3 -m py_compile "$WORK/adaptive_transport.py" "$WORK/cook4me_phonefree.py"
cat > "$WORK/runner.py" <<'PY'
import importlib
import os
import re
import socket
import sys
from time import monotonic

host = 'a1p8u39dc9ign8-ats.iot.eu-west-1.amazonaws.com'


def display(*args):
    print(*args, flush=True)


def test(label, task):
    started = monotonic()
    display('START', label)
    try:
        value = task()
    except Exception as exc:
        msg = str(exc)
        code = re.search(r'HTTP (\d{3})', msg)
        display('FAIL', label, type(exc).__name__, 'http', code.group(1) if code else 'none',
                'seconds', round(monotonic() - started, 2))
        return None
    display('PASS', label, str(value), 'seconds', round(monotonic() - started, 2))
    return value


def mqtt_dns():
    addrs = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    return ','.join('IPv6' if a[0] == socket.AF_INET6 else 'IPv4' for a in addrs)


def cloud_mqtt():
    transport = importlib.import_module('adaptive_transport')
    connection = transport.create_mqtt_websocket(f'wss://{host}:443/mqtt', host, timeout=9)
    try:
        return 'HTTP_' + str(connection.handshake_response.status)
    finally:
        connection.close()


def cognito_http():
    vendor = importlib.import_module('cook4me_phonefree')
    try:
        # Deliberately invalid pool ID: tests real Cognito HTTP transport,
        # not account permissions or credentials.
        vendor.cognito_call('eu-west-1', 'GetId', {'IdentityPoolId': 'not-a-valid-pool-id'})
    except RuntimeError as exc:
        status = re.search(r'HTTP (\d{3})', str(exc))
        if status:
            return 'HTTP_' + status.group(1) + '_REACHABLE'
        raise
    return 'UNEXPECTED_ACCEPTANCE'


display('PROBE', 'unsigned_websocket_and_cognito_transport_only')
display('PYTHON', sys.version.split()[0])
for key in ('HTTPS_PROXY', 'https_proxy', 'WSS_PROXY', 'wss_proxy', 'ALL_PROXY', 'all_proxy', 'NO_PROXY', 'no_proxy'):
    display('PROXY_SETTING', key, bool(os.getenv(key)))
test('DNS_ORDER', mqtt_dns)
test('CANDIDATE_UNSIGNED_MQTT_WEBSOCKET', cloud_mqtt)
test('CANDIDATE_COGNITO_HTTPS', cognito_http)
display('END', 'no_home_assistant_configuration_modified')
PY
python3 -m py_compile "$WORK/runner.py"
docker exec "$HA" mkdir -p "$DIR"
for file in adaptive_transport.py cook4me_phonefree.py runner.py; do
  docker cp "$WORK/$file" "$HA:$DIR/$file" >/dev/null
done
set +e
docker exec "$HA" python3 -B "$DIR/runner.py" > "$WORK/report.txt" 2>/dev/null
rc=$?
set -e
printf 'probe_exit=%s\n' "$rc" > "$WORK/status.txt"
cat "$WORK/report.txt"
tar -czf "$OUT" -C "$WORK" report.txt status.txt
if [[ -n $(printenv SUDO_USER || true) ]]; then chown "$(printenv SUDO_USER)" "$OUT" || :; fi
printf '\nEvidence: %s\n' "$OUT"
echo 'Upload the report; no credentials, signed URLs, or account data are collected.'
