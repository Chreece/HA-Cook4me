#!/usr/bin/env bash
# Read-only cloud transport diagnostics. Does not modify VPN, DNS, routes, HA or credentials.
(
  set -Eeuo pipefail
  sudo -v || exit 1
  WORK=$(mktemp -d) || exit 1
  trap 'rm -rf -- "$WORK"' EXIT
  OUT="$HOME/cook4me-vpn-path-$(date -u +%Y%m%d-%H%M%S).tar.gz"
  echo 'Checking AWS IoT transport from inside Home Assistant (no login required)...'
  set +e
  sudo -n docker exec -i homeassistant python3 - > "$WORK/transport.txt" <<'PY'
import base64
import os
import re
import socket
import ssl
import subprocess
import time

IOT = 'a1p8u39dc9ign8-ats.iot.eu-west-1.amazonaws.com'
COGNITO = 'cognito-identity.eu-west-1.amazonaws.com'


def note(*args):
    print(*args, flush=True)


def timed(name, callback):
    start = time.monotonic()
    try:
        result = callback()
    except Exception as exc:
        note(name, 'FAIL', type(exc).__name__, 'seconds', round(time.monotonic() - start, 2))
        return None
    note(name, 'DONE', result, 'seconds', round(time.monotonic() - start, 2))
    return result


def family_name(af):
    return 'IPv6' if af == socket.AF_INET6 else 'IPv4' if af == socket.AF_INET else 'other'


def dns_summary(host):
    res = socket.getaddrinfo(host, 443, socket.AF_UNSPEC, socket.SOCK_STREAM, socket.IPPROTO_TCP)
    sequence = [family_name(item[0]) for item in res]
    note('DNS', 'iot' if host == IOT else 'cognito', 'order', ','.join(sequence))
    return next((item[4][0] for item in res if item[0] == socket.AF_INET), None)


def tls(host, ipv4_only):
    if ipv4_only:
        records = socket.getaddrinfo(host, 443, socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
        if not records:
            raise OSError('Missing IPv4 result')
        family, kind, protocol, _, address = records[0]
        raw = socket.socket(family, kind, protocol)
        raw.settimeout(7)
        try:
            raw.connect(address)
        except BaseException:
            raw.close()
            raise
    else:
        raw = socket.create_connection((host, 443), timeout=7)
    with raw:
        raw.settimeout(7)
        with ssl.create_default_context().wrap_socket(raw, server_hostname=host) as secure:
            return secure.version()


def route_summary(ip):
    if not ip:
        return 'no_ipv4_dns'
    try:
        p = subprocess.run(['ip', '-4', 'route', 'get', ip], capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.TimeoutExpired):
        return 'unavailable'
    if p.returncode:
        return 'unavailable'
    interface = re.search(r'\bdev\s+(\S+)', p.stdout)
    mtu = re.search(r'\bmtu\s+(\d+)', p.stdout)
    return 'interface=' + (interface.group(1) if interface else 'unknown') + ' mtu=' + (mtu.group(1) if mtu else 'unknown')


note('PROBE', 'no_credentials_no_network_changes')
for key in ('HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'NO_PROXY'):
    note('PROXY_ENV', key, 'set' if os.environ.get(key) else 'unset')

for hostname in (IOT, COGNITO):
    label = 'IOT' if hostname == IOT else 'COGNITO'
    ipv4 = timed('DNS_' + label, lambda host=hostname: dns_summary(host))
    note('ROUTE_' + label, route_summary(ipv4))
    timed('TLS_DEFAULT_' + label, lambda host=hostname: tls(host, False))
    timed('TLS_IPV4_' + label, lambda host=hostname: tls(host, True))

try:
    import websocket
except ImportError:
    note('WS_LIBRARY', 'missing')
else:
    note('WS_LIBRARY', getattr(websocket, '__version__', 'unknown'))
    original = socket.getaddrinfo

    def ipv4_dns(host, port, family=0, socktype=0, proto=0, flags=0):
        if host == IOT:
            return original(host, port, socket.AF_INET, socktype, proto, flags)
        return original(host, port, family, socktype, proto, flags)

    def unsigned_ws(force_ipv4):
        if force_ipv4:
            socket.getaddrinfo = ipv4_dns
        connection = None
        try:
            connection = websocket.create_connection(
                'wss://' + IOT + ':443/mqtt',
                timeout=7,
                subprotocols=['mqtt'],
                suppress_origin=True,
                host=IOT + ':443',
            )
            return 'HTTP101_UNEXPECTED_WITHOUT_AUTH'
        except Exception as exc:
            code = getattr(exc, 'status_code', None)
            if isinstance(code, int):
                return 'HTTP_' + str(code) + '_UNSIGNED'
            raise
        finally:
            if connection is not None:
                connection.close()
            socket.getaddrinfo = original

    timed('WS_DEFAULT_UNSIGNED', lambda: unsigned_ws(False))
    timed('WS_IPV4_UNSIGNED', lambda: unsigned_ws(True))

note('END', 'no_configuration_changed')
PY
  CODE=$?
  set -e
  printf 'docker_probe_exit=%s\n' "$CODE" > "$WORK/status.txt"
  tar -czf "$OUT" -C "$WORK" transport.txt status.txt
  echo "Evidence: $OUT"
  echo 'Upload this archive. It contains no tokens, passwords, raw HTTP responses or public IPs.'
)
