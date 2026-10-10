#!/usr/bin/env bash
# Cook4Me live proof, read-only HA config and KRUPS API/MQTT state. No HA restarts.
set -Eeuo pipefail
set +x
umask 077
[[ $EUID == 0 ]] || { echo 'Run with sudo bash'; exit 1; }
HA=homeassistant
CONFIG=/home/chreece/homeassistant/config
[[ $(docker inspect -f '{{.State.Running}}' "$HA" 2>/dev/null) == true ]] || { echo 'Home Assistant is not running'; exit 1; }
[[ -f "$CONFIG/custom_components/cook4me/bridge.py" ]] || { echo 'Cook4Me files missing'; exit 1; }
WORK=$(mktemp -d /tmp/cook4me-live-XXXXXX)
FILE="/home/chreece/cook4me-mqtt-phases-$(date -u +%Y%m%d-%H%M%S).tar.gz"
trap 'unset COOK4ME_EMAIL COOK4ME_PASSWORD 2>/dev/null || :; rm -rf -- "$WORK"' EXIT
python3 - "$CONFIG" >"$WORK/installation.txt" <<'PY'
import json,hashlib,pathlib,sys
p=pathlib.Path(sys.argv[1]); component=p/'custom_components/cook4me'
for f in ('bridge.py','vendor/cook4me_auto.py','vendor/cook4me_phonefree.py'):
 try:print(f,'sha256',hashlib.sha256((component/f).read_bytes()).hexdigest())
 except Exception as e:print(f,'error',type(e).__name__)
try:
 entries=json.loads((p/'.storage/core.config_entries').read_text())['data']['entries']
 print('cook4me_entries',sum(e.get('domain')=='cook4me' for e in entries))
except Exception as e:print('entries_error',type(e).__name__)
PY
# Docker stderr is not archived. Only known, non-sensitive message categories.
docker logs --since 72h --tail 9000 "$HA" 2>&1 | python3 -c '
import collections,sys
terms={"config-flow discovery starting":"discovery_started","appliance discovery timed out":"discovery_timeout","initial cloud state missing":"initial_cloud_state_missing","cloud MQTT reconnecting":"mqtt_reconnect","cloud unavailable during config flow":"cloud_unavailable","Cook4Me watcher exited":"watcher_exited"}
c=collections.Counter()
for line in sys.stdin:
 for term,name in terms.items():
  if term.lower() in line.lower():c[name]+=1
for k,v in sorted(c.items()):print(k,v)
' > "$WORK/homeassistant-summary.txt" || true

printf 'Checking for an existing, unexpired KRUPS account token...\n'
CACHED=$(docker exec -i "$HA" python3 - <<'PY'
import pathlib,base64,json,time
valid=False
for p in pathlib.Path('/config/.storage/cook4me').glob('*/.config/cook4me/tokens.json'):
 try:
  d=json.loads(p.read_text()); t=d['id_token'].split('.')[1]; t+='='*((4-len(t)%4)%4)
  exp=json.loads(base64.urlsafe_b64decode(t))['exp']
  if exp>time.time()+120 and d.get('access_token'):valid=True;break
 except Exception:continue
print('yes' if valid else 'no')
PY
)
COOK4ME_EMAIL=''; COOK4ME_PASSWORD=''
if [[ "$CACHED" == yes ]]; then
 echo 'Valid cached token exists; no password needed.'
else
 echo 'No valid cached token. Enter credentials for ONE real login test, or leave email empty to skip.'
 read -r -p 'KRUPS email: ' COOK4ME_EMAIL || :
 if [[ -n "$COOK4ME_EMAIL" ]]; then
  read -rs -p 'KRUPS password (hidden): ' COOK4ME_PASSWORD || :
  echo
 fi
fi
export COOK4ME_EMAIL COOK4ME_PASSWORD
printf 'Testing KRUPS account API and AWS IoT from inside Home Assistant...\n'
set +e
timeout --signal=TERM --kill-after=10s 300s docker exec -i --user 0 -e COOK4ME_EMAIL -e COOK4ME_PASSWORD "$HA" python3 - > "$WORK/live.txt" 2>/dev/null <<'PY'
import contextlib,hashlib,io,json,os,pathlib,re,signal,socket,subprocess,sys,tempfile,time,urllib.parse

def event(*items):print(*items,file=sys.__stdout__,flush=True)
def _deadline(_signal,_frame):
 event('STOP','probe_deadline_280s');raise SystemExit(124)
signal.signal(signal.SIGALRM,_deadline);signal.alarm(280)
def phase(name,fn):
 t=time.monotonic();event('START',name)
 try:r=fn()
 except Exception as e:
  m=re.search(r'HTTP\s*(\d{3})',str(e));event('FAIL',name,type(e).__name__,'http='+str(m.group(1) if m else 'none'),'seconds='+str(round(time.monotonic()-t,2)));return None
 event('PASS',name,'seconds='+str(round(time.monotonic()-t,2)));return r

# Previous live proof already established that these three TCP endpoints are reachable.
# Do not repeat those broad tests; investigate only the MQTT connection.
# Separate DNS/address-family reachability from WebSocket and MQTT protocol.
mqtt_host='a1p8u39dc9ign8-ats.iot.eu-west-1.amazonaws.com'
for family_name, family in (('ipv4',socket.AF_INET),('ipv6',socket.AF_INET6)):
 try:
  records=socket.getaddrinfo(mqtt_host,443,family,socket.SOCK_STREAM)
  event('MQTT_DNS',family_name,'addresses',len(records))
  if not records:continue
  _,kind,proto,_,address=records[0]
  start=time.monotonic()
  try:
   with socket.socket(family,kind,proto) as connection:
    connection.settimeout(5)
    connection.connect(address)
   event('MQTT_TCP',family_name,'PASS','seconds',round(time.monotonic()-start,2))
  except Exception as e:event('MQTT_TCP',family_name,'FAIL',type(e).__name__,'seconds',round(time.monotonic()-start,2))
 except Exception as e:event('MQTT_DNS',family_name,'FAIL',type(e).__name__)
root=pathlib.Path('/config/custom_components/cook4me')
with tempfile.TemporaryDirectory(prefix='cook4me-live-proof-') as home:
 os.environ['HOME']=home;sys.path.insert(0,str(root/'vendor'))
 try:import cook4me_phonefree as c4m
 except Exception as e:event('STOP','client_import',type(e).__name__);sys.exit(0)
 cfg=c4m.read_apk_config(None)
 td=pathlib.Path(home)/'.config/cook4me';td.mkdir(parents=True)
 tokens=None
 candidates=list(pathlib.Path('/config/.storage/cook4me').glob('*/.config/cook4me/tokens.json'))
 candidates.sort(key=lambda p:(p.parent.parent.parent.name!='config_flow',-p.stat().st_mtime))
 event('TOKEN_CACHE_FILES',len(candidates))
 for p in candidates:
  try:
   x=json.loads(p.read_text()); exp=c4m.jwt_exp(x.get('id_token'))
   if exp and exp>time.time()+120 and x.get('access_token'):tokens=x;break
  except Exception:pass
 if tokens:
  event('TOKEN_SOURCE','valid_cached');(td/'tokens.json').write_text(json.dumps(tokens))
 elif os.getenv('COOK4ME_EMAIL') and os.getenv('COOK4ME_PASSWORD'):
  event('START','real_krups_login')
  cmd=[sys.executable,str(root/'vendor/cook4me_plain_http_auth.py'),'--country','DE','--language','de','--app-version','36.0.0-RC3','--no-save-credentials']
  auth_started=time.monotonic()
  p=subprocess.Popen(cmd,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,start_new_session=True)
  try:
   out,err=p.communicate(timeout=110)
   event('AUTH_EXIT',p.returncode,'stdout_bytes',len(out),'stderr_bytes',len(err),'seconds',round(time.monotonic()-auth_started,2))
  except subprocess.TimeoutExpired:
   os.killpg(p.pid,signal.SIGKILL);p.communicate();event('AUTH_TIMEOUT',110)
  try:tokens=json.loads((td/'tokens.json').read_text())
  except Exception:tokens=None
  for q in (pathlib.Path(home)/'cook4me-re').glob('krups-plain-http-auth-*.log'):
   try:
    s=q.read_text();d=json.loads(s[s.index('\n{')+1:]); names=[v for v in d.get('stages',[]) if isinstance(v,str) and re.fullmatch('[a-zA-Z0-9_:-]{1,60}',v)]
    event('AUTH_STAGES',','.join(names) or 'none','callback',bool(d.get('callback_observed')))
   except Exception:event('AUTH_DIAGNOSTIC','not_parseable')
 if not tokens or not tokens.get('access_token') or not tokens.get('id_token'):
  event('STOP','no_authenticated_account');sys.exit(0)
 try:old=c4m.curl_requests.get
 except AttributeError:event('STOP','curl_cffi_missing');sys.exit(0)
 n=[0]
 def observed(url,*a,**kw):
  n[0]+=1;k=n[0];path=urllib.parse.urlsplit(url).path
  label='profile' if path.endswith('/profiles/me') else 'platform' if '/configurations/' in path else 'url_connexion' if '/url-connexion' in path else 'other'
  t=time.monotonic();event('HTTP_START',k,label)
  try:r=old(url,*a,**kw);event('HTTP_DONE',k,label,'status',r.status_code,'seconds',round(time.monotonic()-t,2));return r
  except Exception as e:event('HTTP_FAIL',k,label,type(e).__name__,'seconds',round(time.monotonic()-t,2));raise
 c4m.curl_requests.get=observed
 devices=phase('real_owned_device_discovery',lambda:c4m.discover_appliances(cfg,None,tokens,'DE','de','36.0.0-RC3'))
 if devices is None:event('STOP','discovery_failed');sys.exit(0)
 event('ACCOUNT_DEVICE_COUNT',len(devices))
 if not devices:sys.exit(0)
 # Distinguish Cognito GetId from GetCredentialsForIdentity, without
 # exposing identity IDs, tokens, endpoint headers, or response bodies.
 raw_cognito=c4m.cognito_call
 def tracked_cognito(region,target,body):
  safe_target=target if target in ('GetId','GetCredentialsForIdentity') else 'other'
  started=time.monotonic();event('COGNITO_START',safe_target)
  try:
   result=raw_cognito(region,target,body)
   event('COGNITO_PASS',safe_target,'seconds',round(time.monotonic()-started,2))
   return result
  except Exception as exc:
   match=re.search(r'HTTP\s*(\d{3})',str(exc))
   event('COGNITO_FAIL',safe_target,type(exc).__name__,'http',match.group(1) if match else 'none','seconds',round(time.monotonic()-started,2))
   raise
 c4m.cognito_call=tracked_cognito
 creds=phase('real_aws_cognito_credentials',lambda:c4m.aws_credentials(cfg,tokens['id_token']))
 if creds is None:event('STOP','aws_credentials_failed');sys.exit(0)

 # MQTT wire-stage instrumentation: distinguish WebSocket upgrade, CONNACK,
 # SUBACK, and response. Never log signed URLs, raw packets, or credentials.
 try:
  import websocket
 except ImportError:
  event('STOP','websocket_client_missing');sys.exit(0)
 raw_ws_connect=websocket.create_connection
 def tracked_ws_connect(*args,**kwargs):
  started=time.monotonic();event('MQTT_WS_START')
  try:
   result=raw_ws_connect(*args,**kwargs)
   event('MQTT_WS_PASS','seconds',round(time.monotonic()-started,2))
   return result
  except Exception as exc:
   event('MQTT_WS_FAIL',type(exc).__name__,'seconds',round(time.monotonic()-started,2))
   raise
 websocket.create_connection=tracked_ws_connect
 raw_read=c4m.mqtt_read_packet
 packet_counter=[0]
 def tracked_read(ws,timeout=15):
  packet_counter[0]+=1
  kind=('connack','suback','response' if packet_counter[0]>=3 else 'unknown')[min(packet_counter[0]-1,2)]
  started=time.monotonic();event('MQTT_READ_START',kind,'timeout',int(timeout))
  try:
   packet=raw_read(ws,timeout)
   event('MQTT_READ_PASS',kind,'packet_type',packet[0],'seconds',round(time.monotonic()-started,2))
   return packet
  except Exception as exc:
   event('MQTT_READ_FAIL',kind,type(exc).__name__,'seconds',round(time.monotonic()-started,2))
   raise
 c4m.mqtt_read_packet=tracked_read
 event('PROXY_ENV_FLAGS',*(key+':'+str(bool(os.environ.get(key))) for key in ('HTTP_PROXY','HTTPS_PROXY','ALL_PROXY','NO_PROXY')))
 for device in devices[:2]:
  value=str(device.get('uuid') or '')
  if not value:continue
  alias=hashlib.sha256(value.encode()).hexdigest()[:10];c4m.set_device_uuid(value)
  event('DEVICE_HASH',alias)
  packet_counter[0]=0
  shadow=phase('iot_shadow_get_'+alias,lambda:c4m.shadow_get(cfg,creds,timeout=13))
  if shadow is not None:
   state=c4m._shadow_reported_from_payload(shadow)
   status=state.get('status') if isinstance(state,dict) else None
   event('SHADOW_CONNECTED',alias, status.get('connected') if isinstance(status,dict) else 'not_reported')
  packet_counter[0]=0
  cooking=phase('iot_cooking_get_'+alias,lambda:c4m.cooking_status(cfg,creds,timeout=13))
  if cooking is not None:event('COOKING_RESPONSE_TYPE',type(cooking).__name__)
 event('LIVE_TEST_COMPLETE','No HA configuration modified')
PY
RC=$?
set -e
unset COOK4ME_EMAIL COOK4ME_PASSWORD
printf 'probe_exit_code=%s\n' "$RC" >>"$WORK/installation.txt"
tar -czf "$FILE" -C "$WORK" .
if [[ -n "${SUDO_USER:-}" && "$SUDO_USER" != root ]]; then chown "$SUDO_USER" "$FILE" || :;fi
printf '\nEvidence archive: %s\n' "$FILE"
echo 'Upload the .tar.gz here; it has status and timings, not raw credentials, tokens or cloud response bodies.'
