#!/usr/bin/env python3
import argparse, base64, datetime as dt, hashlib, hmac, json, locale, os, pathlib, shutil, struct, subprocess, sys, time, urllib.error, urllib.parse, urllib.request, webbrowser, zipfile

try:
    from curl_cffi import requests as curl_requests
except Exception:
    curl_requests = None

DEFAULT_APK = None
STATIC_CONFIG = {
    'platform_base_url': 'https://sebplatform.api.groupe-seb.com',
    'region': 'eu-west-1',
    'cognito_pool_id': 'eu-west-1:f25c4598-48da-4fda-9c1a-27fe30bd2ffe',
    'attach_policies_endpoint': 'https://iot.api.groupe-seb.com',
    'api_key': '460d1bd232b95f5aa04a60b07bdca353',
}
LOGIN_PROVIDER = 'consumers.api.groupe-seb.com'
DEVICE_UUID = '00000000-0000-0000-0000-000000000000'
THING = f'COO001-{DEVICE_UUID}'
MQTT_ENDPOINT = 'a1p8u39dc9ign8-ats.iot.eu-west-1.amazonaws.com'
REGION = 'eu-west-1'
TOKENS_FILE = pathlib.Path.home()/'.config/cook4me/tokens.json'
AWS_FILE = pathlib.Path.home()/'.config/cook4me/aws.json'
RCU_FILE = pathlib.Path.home()/'.config/cook4me/rcu.json'

APP_VERSION_DEFAULT = '36.0.0-RC3'


def read_apk_config(apk=None):
    if apk is None or not pathlib.Path(apk).exists():
        return dict(STATIC_CONFIG)
    with zipfile.ZipFile(apk) as z:
        raw = z.read('assets/domain.json')
    cfg = json.loads(raw)
    env = next(x for x in cfg['environments'] if x['name']=='PROD')
    kru = next(x for x in cfg['domains'] if x['name']=='PRO_KRU')
    key = next(x['value'] for x in kru['apiKeys'] if x['environment']=='PROD')
    return {
        'platform_base_url': env['url'],
        'region': env['iot']['region'],
        'cognito_pool_id': env['iot']['cognitoPoolId'],
        'attach_policies_endpoint': env['iot']['attachPoliciesEndpoint'],
        'api_key': key,
    }


def set_device_uuid(value):
    global DEVICE_UUID, THING
    DEVICE_UUID = str(value).strip().lower()
    THING = f"COO001-{DEVICE_UUID}"

def save_json(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2))
    os.chmod(path, 0o600)


def load_json(path):
    return json.loads(path.read_text())


def jwt_exp(token):
    try:
        p=token.split('.')[1]; p += '='*((4-len(p)%4)%4)
        return json.loads(base64.urlsafe_b64decode(p))['exp']
    except Exception:
        return None


def detect_locale():
    candidates=[]
    try:
        loc=locale.getlocale()[0]
        if loc: candidates.append(loc)
    except Exception:
        pass
    for name in ('LC_ALL','LC_MESSAGES','LANG'):
        v=os.environ.get(name)
        if v: candidates.append(v)
    for v in candidates:
        core=v.split('.',1)[0].split('@',1)[0].replace('-', '_')
        parts=core.split('_')
        if len(parts)>=2 and len(parts[0])==2 and len(parts[1])==2:
            return parts[1].upper(), parts[0].lower()
    return None, None


def _http_json_browser(url, headers=None, timeout=25):
    """GET JSON using an in-process browser-compatible TLS stack."""
    if curl_requests is None:
        raise RuntimeError("curl-cffi is not available; Home Assistant requirement installation failed")
    try:
        r = curl_requests.get(
            url, headers=headers or {}, timeout=timeout,
            allow_redirects=True, impersonate="chrome",
        )
    except Exception as exc:
        raise RuntimeError(
            f"Network error contacting {urllib.parse.urlsplit(url).netloc}: "
            f"{type(exc).__name__}: {exc}"
        ) from None
    if not (200 <= int(r.status_code) < 300):
        text=(r.text or '')[:1000]
        raise RuntimeError(
            f"HTTP {r.status_code} from {urllib.parse.urlsplit(url).netloc}: {text[:500]}"
        )
    try:
        return r.json()
    except Exception as exc:
        raise RuntimeError(
            f"Invalid JSON from {urllib.parse.urlsplit(url).netloc}: {type(exc).__name__}: {exc}"
        ) from None


def http_json(url, headers=None, timeout=25):
    return _http_json_browser(url, headers, timeout)


def app_headers(cfg, app_version, apim_url=None, apim_key=None, request_url=None):
    h={
        'Accept':'application/json',
        'Content-Type':'application/json',
        'Gseb-App-Version':app_version,
        'ApiKey':cfg['api_key'],
    }
    # Android only sends the APIM subscription key when the request URL matches
    # the configured APIM base URL. Do not leak it to unrelated destinations.
    if apim_url and apim_key and request_url and request_url.startswith(apim_url.rstrip('/')):
        h['Ocp-Apim-Subscription-Key']=apim_key
    return h


def fetch_platform_configuration(cfg, country, language, app_version):
    base=cfg['platform_base_url'].rstrip('/')
    path='/common-api/v3/configurations/'+urllib.parse.quote(cfg['api_key'], safe='')
    # The APK exposes DeviceCountry / DeviceLanguage and deviceCountry /
    # deviceLanguage alongside this Retrofit endpoint. Query parameters are
    # harmless if the backend ignores them and let it perform its normal
    # locale-specific configuration selection when supported.
    query=urllib.parse.urlencode({'deviceCountry':country, 'deviceLanguage':language})
    url=base+path+'?'+query
    return http_json(url, app_headers(cfg, app_version, request_url=url))


def _iter_dicts(obj):
    if isinstance(obj, dict):
        yield obj
        for v in obj.values():
            yield from _iter_dicts(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _iter_dicts(v)


def _find_first(obj, *keys):
    wanted={k.lower() for k in keys}
    for d in _iter_dicts(obj):
        for k,v in d.items():
            if k.lower() in wanted and isinstance(v,str) and v:
                return v
    return None


def _market_candidates(obj):
    out=[]
    for d in _iter_dicts(obj):
        keys={str(k).lower() for k in d}
        if 'rcubrand' in keys and ('rcumarket' in keys or 'rcubaseurl' in keys):
            out.append(d)
    return out


def _score_market(d, country, language):
    score=0
    country=country.lower(); language=language.lower()
    scalar=' '.join(str(v).lower() for v in d.values() if isinstance(v,(str,int,float,bool)))
    if country in scalar: score += 4
    if language in scalar: score += 2
    locales=d.get('locales') or d.get('Locales') or []
    if isinstance(locales,list):
        for loc in locales:
            if not isinstance(loc,dict): continue
            c=str(loc.get('country','')).lower(); l=str(loc.get('lang','')).lower()
            if c==country: score += 8
            if l==language: score += 4
            if c==country and l==language: score += 8
    return score


def parse_platform_configuration(obj, country, language):
    candidates=_market_candidates(obj)
    if not candidates:
        raise RuntimeError('Platform configuration did not contain an RCU market object')
    market=max(candidates, key=lambda d:_score_market(d,country,language))

    def pick(d, *names):
        lut={str(k).lower():v for k,v in d.items()}
        for n in names:
            v=lut.get(n.lower())
            if isinstance(v,str) and v:
                return v
        return None

    rcu_brand=pick(market,'rcuBrand')
    rcu_market=pick(market,'rcuMarket')
    locale_market=pick(market,'name','market')
    rcu_base_url=pick(market,'rcuBaseUrl')
    profile_perimeter=pick(market,'profilePerimeter')

    # These live on the global DcpConfiguration rather than DcpMarket.
    rcu_client_id=_find_first(obj,'rcuClientId','clientId')
    apim_url=_find_first(obj,'apimUrl')
    apim_key=_find_first(obj,'apimSubscriptionKey')

    if not rcu_brand:
        raise RuntimeError('Selected market has no rcuBrand')
    if not locale_market:
        # The Android url-connexion call uses LocalePacket.market, sourced from
        # bestMatchMarket.getName(), not rcuMarket.
        locale_market=rcu_market
    if not locale_market:
        raise RuntimeError('Selected market has neither name nor rcuMarket')

    return {
        'country':country,
        'language':language,
        'rcu_brand':rcu_brand,
        'rcu_market':rcu_market,
        'locale_market':locale_market,
        'rcu_base_url':rcu_base_url,
        'rcu_client_id':rcu_client_id,
        'profile_perimeter':profile_perimeter,
        'apim_url':apim_url,
        'apim_subscription_key':apim_key,
    }


def discover_rcu(cfg, country, language, app_version, save=True):
    platform=fetch_platform_configuration(cfg,country,language,app_version)
    pcfg=parse_platform_configuration(platform,country,language)

    base=cfg['platform_base_url'].rstrip('/')
    query=urllib.parse.urlencode({'brand':pcfg['rcu_brand'], 'market':pcfg['locale_market']})
    url=base+'/common-api/v3/contents/url-connexion?'+query
    data=http_json(url, app_headers(cfg, app_version, pcfg['apim_url'], pcfg['apim_subscription_key'], url))
    rcu_url=None
    if isinstance(data,dict):
        rcu_url=data.get('brandRcuBaseUrl') or data.get('rcuBrandBaseUrl')
    if not rcu_url:
        rcu_url=_find_first(data,'brandRcuBaseUrl','rcuBrandBaseUrl')
    if not rcu_url:
        raise RuntimeError('url-connexion response did not contain brandRcuBaseUrl')
    pcfg['brand_rcu_base_url']=rcu_url.rstrip('/')+'/'
    pcfg['discovered_at']=int(time.time())
    if save:
        save_json(RCU_FILE,pcfg)
    return pcfg


def resolve_country_language(args):
    dc,dl=detect_locale()
    country=(getattr(args,'country',None) or dc or 'DE').upper()
    language=(getattr(args,'language',None) or dl or 'de').lower()
    return country,language


def browser_auth(args, cfg):
    if args.auth_base_url:
        base=args.auth_base_url.rstrip('/')+'/'
    else:
        country,language=resolve_country_language(args)
        rcu=discover_rcu(cfg,country,language,args.app_version,save=True)
        base=rcu['brand_rcu_base_url']
        print('RCU authentication endpoint discovered automatically:', urllib.parse.urlsplit(base).netloc)
    redirect='gsmoduser://tokens'
    path=('ContinuationForExpId?apikey=%s&redirect_uri=%s&state=STATE&response_type='
          'token+id_token+refresh_token&nonce=NONCE&isUserName=%s&version=%s')
    url=urllib.parse.urljoin(base, path % (
        urllib.parse.quote(cfg['api_key'], safe=''), urllib.parse.quote(redirect, safe=''),
        'true', urllib.parse.quote(args.app_version, safe='')))
    print('Opening Groupe SEB authentication in your desktop browser.')
    print('After login the browser may say it cannot open gsmoduser://tokens — that is expected.')
    print('Copy the COMPLETE gsmoduser://tokens?... URL from the address bar into THIS terminal.')
    # Never print the login URL: it contains the embedded app API key.
    webbrowser.open(url)
    cb=input('Callback URL: ').strip()
    u=urllib.parse.urlparse(cb)
    if u.scheme!='gsmoduser' or u.netloc!='tokens':
        raise SystemExit('Unexpected callback URL')
    q=urllib.parse.parse_qs(u.query)
    def one(k):
        v=q.get(k); return v[0] if v else None
    tokens={'access_token':one('access_token'),'refresh_token':one('refresh_token'),'id_token':one('id_token'),'obtained_at':int(time.time()),'auth_base_url':base}
    if not tokens['id_token']:
        q=urllib.parse.parse_qs(u.fragment)
        for k in ('access_token','refresh_token','id_token'):
            v=q.get(k); tokens[k]=tokens[k] or (v[0] if v else None)
    if not tokens['id_token']:
        raise SystemExit('Callback did not contain id_token')
    tokens['id_token_exp']=jwt_exp(tokens['id_token'])
    save_json(TOKENS_FILE,tokens)
    print('Saved tokens securely to', TOKENS_FILE)


def cognito_call(region, target, body):
    url=f'https://cognito-identity.{region}.amazonaws.com/'
    data=json.dumps(body,separators=(',',':')).encode()
    req=urllib.request.Request(url,data=data,method='POST',headers={
        'Content-Type':'application/x-amz-json-1.1',
        'X-Amz-Target':f'AWSCognitoIdentityService.{target}',
        'Accept':'application/json',
    })
    try:
        with urllib.request.urlopen(req,timeout=20) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        txt=e.read().decode('utf-8','replace')
        raise RuntimeError(f'Cognito {target} HTTP {e.code}: {txt}') from None


def jwt_claims(token):
    try:
        p=token.split('.')[1]
        p += '='*((4-len(p)%4)%4)
        return json.loads(base64.urlsafe_b64decode(p))
    except Exception:
        return {}


def cognito_provider_candidates(id_token):
    """
    Cognito's Logins map key for a generic OIDC token must match the token issuer
    provider name.  The old reverse-engineering bootstrap incorrectly used the
    app configuration's `cognitoEndpoint` value as that key.

    Never print the token; only derive non-secret provider-name candidates from
    its `iss` claim.
    """
    claims=jwt_claims(id_token)
    iss=str(claims.get('iss') or '').strip()
    candidates=[]

    if iss:
        try:
            u=urllib.parse.urlsplit(iss)
            # AWS Cognito OIDC Logins keys conventionally use the issuer host.
            if u.hostname:
                candidates.append(u.hostname)
            # Keep a scheme-less issuer/path candidate for providers whose
            # configured ProviderName includes a path.
            scheme_less=(u.netloc + u.path).rstrip('/')
            if scheme_less:
                candidates.append(scheme_less)
        except Exception:
            pass

        raw=iss.removeprefix('https://').removeprefix('http://').rstrip('/')
        if raw:
            candidates.append(raw)

    # Retain the APK/config-derived legacy value only as a final compatibility
    # fallback; it is not assumed to be the token issuer.
    candidates.append(LOGIN_PROVIDER)

    out=[]
    for value in candidates:
        if value and value not in out:
            out.append(value)
    return out


def aws_credentials(cfg, id_token):
    last_error=None
    provider=None
    ident=None

    for candidate in cognito_provider_candidates(id_token):
        logins={candidate:id_token}
        try:
            gid=cognito_call(
                cfg['region'],
                'GetId',
                {'IdentityPoolId':cfg['cognito_pool_id'],'Logins':logins}
            )
            ident=gid['IdentityId']
            provider=candidate
            break
        except RuntimeError as exc:
            msg=str(exc)
            last_error=exc
            # A wrong OIDC provider key produces exactly the error observed in
            # v8.  Try the next issuer-derived representation. Other Cognito
            # failures are real failures and should not be hidden.
            if ('Issuer doesn' in msg and 'providerName' in msg) or (
                'NotAuthorizedException' in msg and 'login token' in msg
            ):
                continue
            raise

    if not provider or not ident:
        raise RuntimeError(
            'Cognito rejected every provider name derived from the id_token issuer'
        ) from last_error

    print('Cognito provider    :', provider)
    logins={provider:id_token}
    got=cognito_call(
        cfg['region'],
        'GetCredentialsForIdentity',
        {'IdentityId':ident,'Logins':logins}
    )
    c=got['Credentials']
    out={
        'IdentityId':ident,
        'ProviderName':provider,
        'AccessKeyId':c['AccessKeyId'],
        'SecretKey':c['SecretKey'],
        'SessionToken':c['SessionToken'],
        'Expiration':c['Expiration']
    }
    save_json(AWS_FILE,out)
    return out


def sign(key,msg): return hmac.new(key,msg.encode(),hashlib.sha256).digest()
def signing_key(secret,date,region,service):
    k=sign(('AWS4'+secret).encode(),date); k=hmac.new(k,region.encode(),hashlib.sha256).digest(); k=hmac.new(k,service.encode(),hashlib.sha256).digest(); return hmac.new(k,b'aws4_request',hashlib.sha256).digest()


def signed_wss(endpoint,region,creds, now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    amz=now.strftime('%Y%m%dT%H%M%SZ'); date=now.strftime('%Y%m%d'); service='iotdevicegateway'
    scope=f'{date}/{region}/{service}/aws4_request'
    host=f'{endpoint}:443'
    params={'X-Amz-Algorithm':'AWS4-HMAC-SHA256','X-Amz-Credential':f"{creds['AccessKeyId']}/{scope}",'X-Amz-Date':amz,'X-Amz-SignedHeaders':'host'}
    def enc(s): return urllib.parse.quote(str(s),safe='-_.~')
    cq='&'.join(f'{enc(k)}={enc(params[k])}' for k in sorted(params))
    canonical='GET\n/mqtt\n'+cq+'\nhost:'+host+'\n\nhost\n'+hashlib.sha256(b'').hexdigest()
    sts='AWS4-HMAC-SHA256\n'+amz+'\n'+scope+'\n'+hashlib.sha256(canonical.encode()).hexdigest()
    sig=hmac.new(signing_key(creds['SecretKey'],date,region,service),sts.encode(),hashlib.sha256).hexdigest()
    params['X-Amz-Signature']=sig; params['X-Amz-Security-Token']=creds['SessionToken']
    query='&'.join(f'{enc(k)}={enc(params[k])}' for k in sorted(params))
    return f'wss://{endpoint}:443/mqtt?{query}', host


def enc_rl(n):
    out=bytearray()
    while True:
        d=n%128; n//=128
        if n:d|=0x80
        out.append(d)
        if not n:return bytes(out)
def enc_utf8(s):
    b=s.encode(); return struct.pack('!H',len(b))+b
def mqtt_connect(cid,keepalive=1200):
    vh=enc_utf8('MQTT')+b'\x04\x02'+struct.pack('!H',keepalive)
    body=vh+enc_utf8(cid)
    return b'\x10'+enc_rl(len(body))+body



def mqtt_publish_packet(topic, payload=b'', packet_id=None, qos=0):
    if isinstance(payload, str): payload=payload.encode()
    flags = 2 if qos == 1 else 0
    body = enc_utf8(topic)
    if qos == 1:
        if packet_id is None: raise ValueError('packet_id required for QoS 1')
        body += struct.pack('!H', packet_id)
    body += payload
    return bytes([(3 << 4) | flags]) + enc_rl(len(body)) + body


def mqtt_subscribe_packet(packet_id, topics):
    body=struct.pack('!H',packet_id)
    for topic,qos in topics:
        body += enc_utf8(topic)+bytes([qos])
    return b'\x82'+enc_rl(len(body))+body


def mqtt_read_packet(ws, timeout=15):
    ws.settimeout(timeout)
    raw=ws.recv()
    if isinstance(raw,str): raw=raw.encode()
    if not raw: raise RuntimeError('MQTT connection closed')
    pos=1; mult=1; remaining=0
    while True:
        b=raw[pos]; pos+=1; remaining += (b & 127)*mult
        if not b & 128: break
        mult*=128
    return raw[0]>>4, raw[0]&15, raw[pos:pos+remaining]


def mqtt_decode_publish(flags, body):
    n=struct.unpack('!H',body[:2])[0]; pos=2
    topic=body[pos:pos+n].decode('utf-8','replace'); pos+=n
    qos=(flags>>1)&3
    packet_id=None
    if qos:
        packet_id=struct.unpack('!H',body[pos:pos+2])[0]; pos+=2
    return topic, body[pos:], packet_id


def mqtt_open(cfg, creds, client_prefix='cook4me-phonefree', keepalive=1200):
    try:
        import websocket
    except ImportError:
        raise SystemExit('Install websocket-client in this venv: pip install websocket-client')
    url,host=signed_wss(MQTT_ENDPOINT,cfg['region'],creds)
    ws=websocket.create_connection(url,timeout=15,subprotocols=['mqtt'],suppress_origin=True,host=host)
    ws.send_binary(mqtt_connect(f'{client_prefix}-{int(time.time())}', keepalive=keepalive))
    ptype,_,body=mqtt_read_packet(ws)
    if ptype != 2 or len(body)<2 or body[-1] != 0:
        ws.close(); raise RuntimeError('MQTT broker rejected connection')
    return ws


def mqtt_json_request(cfg, creds, subscriptions, publish_topic, payload, response_topics, timeout=15):
    ws=mqtt_open(cfg,creds)
    try:
        ws.send_binary(mqtt_subscribe_packet(1,[(x,0) for x in subscriptions]))
        ptype,_,body=mqtt_read_packet(ws)
        if ptype != 9: raise RuntimeError('Expected MQTT SUBACK')
        ws.send_binary(mqtt_publish_packet(publish_topic,json.dumps(payload,separators=(',',':'))))
        deadline=time.time()+timeout
        while time.time()<deadline:
            ptype,flags,body=mqtt_read_packet(ws,max(1,deadline-time.time()))
            if ptype==3:
                topic,data,_=mqtt_decode_publish(flags,body)
                if topic in response_topics:
                    try: return topic,json.loads(data)
                    except json.JSONDecodeError: return topic,{'raw':data.decode('utf-8','replace')}
            elif ptype==13:
                continue
        raise TimeoutError('Timed out waiting for Cook4Me MQTT response')
    finally:
        ws.close()


def cooking_status(cfg, creds, timeout=15):
    base=f'COO001/{DEVICE_UUID}'
    return mqtt_json_request(cfg,creds,[f'{base}/cookingStatus'],f'{base}/getCookingStatus',{}, {f'{base}/cookingStatus'},timeout)[1]


def shadow_get(cfg, creds, timeout=15):
    base=f'$aws/things/{THING}/shadow'
    topic,obj=mqtt_json_request(cfg,creds,[f'{base}/get/accepted',f'{base}/get/rejected'],f'{base}/get',{}, {f'{base}/get/accepted',f'{base}/get/rejected'},timeout)
    if topic.endswith('/rejected'): raise RuntimeError('Shadow GET rejected: '+json.dumps(obj,separators=(',',':'))[:500])
    return obj


def send_recipe(cfg, creds, functional_id, variant_id, timeout=15):
    base=f'$aws/things/{THING}/shadow'
    desired={'state':{'desired':{'recipe':{'functionalId':str(functional_id),'variant':{'functionalId':str(variant_id)}}}}}
    topic,obj=mqtt_json_request(cfg,creds,[f'{base}/update/accepted',f'{base}/update/rejected'],f'{base}/update',desired,{f'{base}/update/accepted',f'{base}/update/rejected'},timeout)
    if topic.endswith('/rejected'): raise RuntimeError('Shadow recipe update rejected: '+json.dumps(obj,separators=(',',':'))[:500])
    return obj


def _is_ws_timeout(exc):
    # Avoid importing websocket at module import time so the rest of the client
    # remains usable before websocket-client is installed.
    return exc.__class__.__name__ in {'WebSocketTimeoutException', 'TimeoutError'}


def _decode_json_payload(data):
    try:
        return json.loads(data)
    except json.JSONDecodeError:
        return {'raw':data.decode('utf-8','replace')}


def merge_cooking_status(previous, update):
    """Merge Cook4Me cookingStatus updates while honoring the idle clear marker.

    The appliance can end a session by publishing only eventDate + version.
    Treat that as an explicit active-session clear; otherwise merge recursively
    so smaller patches do not erase unchanged fields.
    """
    if not isinstance(update, dict):
        return update
    keys=set(update)
    if keys and keys.issubset({'eventDate','version'}):
        return dict(update)
    out=dict(previous) if isinstance(previous,dict) else {}
    def deep(dst, src):
        for k,v in src.items():
            if isinstance(v,dict) and isinstance(dst.get(k),dict):
                d=dict(dst[k]); deep(d,v); dst[k]=d
            else:
                dst[k]=v
    deep(out,update)
    return out


def watch_topics(cfg, creds, include_shadow=False, ping_interval=30, ping_timeout=10):
    """Yield timestamped MQTT events and keep the AWS IoT connection alive.

    Normal receive-idle timeouts trigger MQTT PINGREQ rather than terminating
    the watcher. A genuine dead socket raises so the caller can refresh AWS
    credentials and reconnect.
    """
    base=f'COO001/{DEVICE_UUID}'
    cooking=f'{base}/cookingStatus'
    alert=f'{base}/alert'
    topics=[(cooking,0),(alert,0)]
    if include_shadow:
        sb=f'$aws/things/{THING}/shadow'
        topics += [
            (f'{sb}/update/accepted',0),
            (f'{sb}/update/rejected',0),
            (f'{sb}/update/delta',0),
            (f'{sb}/update/documents',0),
        ]
    ws=mqtt_open(cfg,creds,'cook4me-watch',keepalive=max(60,int(ping_interval*2)))
    try:
        ws.send_binary(mqtt_subscribe_packet(1,topics))
        if mqtt_read_packet(ws,15)[0] != 9:
            raise RuntimeError('Expected MQTT SUBACK')
        ws.send_binary(mqtt_publish_packet(f'{base}/getCookingStatus','{}'))
        while True:
            try:
                ptype,flags,body=mqtt_read_packet(ws,ping_interval)
            except Exception as exc:
                if not _is_ws_timeout(exc):
                    raise
                ws.send_binary(b'\xc0\x00')  # MQTT PINGREQ
                try:
                    ptype,flags,body=mqtt_read_packet(ws,ping_timeout)
                except Exception as ping_exc:
                    if _is_ws_timeout(ping_exc):
                        raise ConnectionError('MQTT keepalive timed out') from ping_exc
                    raise
            if ptype==3:
                topic,data,_=mqtt_decode_publish(flags,body)
                yield {
                    '_topic':topic,
                    '_receivedAt':dt.datetime.now(dt.timezone.utc).isoformat(),
                    'payload':_decode_json_payload(data),
                }
            elif ptype==13:
                continue
            elif ptype==12:
                ws.send_binary(b'\xd0\x00')  # MQTT PINGRESP
    finally:
        try: ws.close()
        except Exception: pass


def watch_cooking(cfg, creds, ping_interval=30, ping_timeout=10):
    base=f'COO001/{DEVICE_UUID}'
    topic=f'{base}/cookingStatus'
    state={}
    for event in watch_topics(cfg,creds,False,ping_interval,ping_timeout):
        if event.get('_topic') != topic:
            continue
        payload=event.get('payload')
        if isinstance(payload,dict) and 'raw' not in payload:
            state=merge_cooking_status(state,payload)
            yield state
        else:
            yield payload

def mqtt_test(cfg, creds):
    try: import websocket
    except ImportError: raise SystemExit('Install websocket-client in this venv: pip install websocket-client')
    url,host=signed_wss(MQTT_ENDPOINT,cfg['region'],creds)
    print('Signed URL generated locally [REDACTED]')
    print('Host header:',host)
    ws=websocket.create_connection(url,timeout=15,subprotocols=['mqtt'],suppress_origin=True,host=host)
    try:
        ws.send_binary(mqtt_connect(f'cook4me-phonefree-{int(time.time())}'))
        raw=ws.recv()
        if isinstance(raw,str): raw=raw.encode()
        if not raw or raw[0]>>4 != 2: raise RuntimeError('Expected MQTT CONNACK')
        rc=raw[-1]
        print('MQTT CONNACK:',rc, 'ACCEPTED' if rc==0 else 'REJECTED')
        if rc!=0: return 2
        ws.send_binary(b'\xc0\x00')
        raw=ws.recv()
        if isinstance(raw,str): raw=raw.encode()
        print('MQTT PINGRESP:', bool(raw and raw[0]>>4==13))
        return 0
    finally: ws.close()


def main():
    ap=argparse.ArgumentParser(description='Phone-free Groupe SEB/KRUPS → Cognito → AWS IoT bootstrap')
    ap.add_argument('--apk',type=pathlib.Path,default=DEFAULT_APK)
    sub=ap.add_subparsers(dest='cmd',required=True)
    sub.add_parser('show-config')
    p=sub.add_parser('discover-rcu')
    p.add_argument('--country'); p.add_argument('--language'); p.add_argument('--app-version',default=APP_VERSION_DEFAULT)
    p=sub.add_parser('browser-auth')
    p.add_argument('--auth-base-url',help='Optional override; normally auto-discovered')
    p.add_argument('--country'); p.add_argument('--language'); p.add_argument('--app-version',default=APP_VERSION_DEFAULT)
    sub.add_parser('aws-creds')
    sub.add_parser('mqtt-test')
    args=ap.parse_args(); cfg=read_apk_config(args.apk)
    if args.cmd=='show-config':
        print(json.dumps({k:('[FROM APK]' if k=='api_key' else v) for k,v in cfg.items()},indent=2)); return
    if args.cmd=='discover-rcu':
        country,language=resolve_country_language(args)
        r=discover_rcu(cfg,country,language,args.app_version,save=True)
        print('Platform URL :',cfg['platform_base_url'])
        print('Country/lang :',country+'/'+language)
        print('RCU brand    :',r['rcu_brand'])
        print('Market       :',r['locale_market'])
        print('RCU host     :',urllib.parse.urlsplit(r['brand_rcu_base_url']).netloc)
        print('Saved        :',RCU_FILE)
        return
    if args.cmd=='browser-auth': browser_auth(args,cfg); return
    if args.cmd=='aws-creds':
        t=load_json(TOKENS_FILE); c=aws_credentials(cfg,t['id_token']); print('AWS credentials obtained and stored securely. IdentityId:',c['IdentityId']); return
    if args.cmd=='mqtt-test':
        c=load_json(AWS_FILE); raise SystemExit(mqtt_test(cfg,c))

if __name__=='__main__': main()


def _shadow_reported_from_payload(payload):
    """Return reported shadow state from GET/update/documents payload shapes."""
    if not isinstance(payload, dict):
        return None
    state = payload.get('state')
    if isinstance(state, dict) and isinstance(state.get('reported'), dict):
        return state['reported']
    current = payload.get('current')
    if isinstance(current, dict):
        state = current.get('state')
        if isinstance(state, dict) and isinstance(state.get('reported'), dict):
            return state['reported']
    return None


def normalize_shadow(payload, previous=None):
    """Normalize the appliance shadow into stable fields for HA-style consumers."""
    out = dict(previous or {})
    reported = _shadow_reported_from_payload(payload)
    if not isinstance(reported, dict):
        return out

    status = reported.get('status')
    if isinstance(status, dict):
        if 'connected' in status:
            out['connected'] = bool(status.get('connected'))
        if 'lastConnection' in status:
            out['lastConnection'] = status.get('lastConnection')
        if 'lastDisconnection' in status:
            out['lastDisconnection'] = status.get('lastDisconnection')
        if 'updating' in status:
            out['updating'] = bool(status.get('updating'))
        if 'reset' in status:
            out['reset'] = status.get('reset')

    firmware = reported.get('firmware')
    if isinstance(firmware, dict):
        for item in firmware.get('files') or []:
            if not isinstance(item, dict):
                continue
            typ = str(item.get('type') or '').strip().lower()
            version = item.get('version')
            if typ == 'ui':
                out['uiFirmware'] = version
            elif typ == 'wifi':
                out['wifiFirmware'] = version
        out['firmwarePriority'] = firmware.get('priority')
        out['firmwareUpdateDate'] = firmware.get('updateDate')

    if 'nextFirmware' in reported:
        out['nextFirmware'] = reported.get('nextFirmware')
    if 'recipe' in reported:
        out['shadowRecipe'] = reported.get('recipe')

    # Shadow version is useful for ordering. update/documents carries it under
    # current.version while accepted/get payloads carry it at top level.
    ver = payload.get('version')
    if ver is None and isinstance(payload.get('current'), dict):
        ver = payload['current'].get('version')
    if ver is not None:
        out['shadowVersion'] = ver
    return out


def normalize_cooking(state):
    """Return a flat, stable representation of merged cookingStatus state."""
    state = state if isinstance(state, dict) else {}
    recipe = state.get('currentRecipe') if isinstance(state.get('currentRecipe'), dict) else {}
    variant = recipe.get('variant') if isinstance(recipe.get('variant'), dict) else {}
    step = state.get('currentStep') if isinstance(state.get('currentStep'), dict) else {}
    step_type = step.get('type') if isinstance(step.get('type'), dict) else {}
    operation = state.get('currentOperation') if isinstance(state.get('currentOperation'), dict) else {}
    program = operation.get('program') if isinstance(operation.get('program'), dict) else {}

    active = bool(recipe or step or operation or state.get('mode') == 'recipe')
    if not active:
        phase = 'idle'
    else:
        status = str(state.get('currentStatus') or '').strip().lower()
        typ = str(step_type.get('key') or '').strip().upper()
        if status == 'depressurization':
            phase = 'depressurization'
        elif status == 'keep warm':
            phase = 'keep_warm'
        elif status == 'warming':
            phase = 'warming'
        elif status == 'cooking':
            phase = 'cooking'
        elif status == 'ready':
            phase = 'ready'
        elif status == 'done':
            phase = 'done'
        elif typ == 'ADD_INGREDIENT':
            phase = 'add_ingredient'
        elif typ == 'PREPARATION':
            phase = 'preparation'
        elif status == 'stopped':
            phase = 'stopped'
        else:
            phase = status or typ.lower() or 'active'

    return {
        'active': active,
        'phase': phase,
        'status': state.get('currentStatus'),
        'mode': state.get('mode'),
        'recipeTitle': recipe.get('title'),
        'recipeFunctionalId': recipe.get('functionalId'),
        'variantFunctionalId': variant.get('functionalId'),
        'stepFunctionalId': step.get('functionalId'),
        'stepIndex': step.get('stepIndex'),
        'stepTypeKey': step_type.get('key'),
        'stepTypeName': step_type.get('name'),
        'programKey': program.get('key'),
        'programName': program.get('name'),
        'progress': state.get('progress'),
        'remainingTime': state.get('remainingTime'),
        'elapsedTime': state.get('elapsedTime'),
        'operationStart': state.get('operationStart'),
        'eventDate': state.get('eventDate'),
        'cookingVersion': state.get('version'),
        'operationParameters': operation.get('parameters') or [],
    }


def combined_state(cooking=None, shadow=None):
    """Build a single HA-ready state object from normalized shadow/cooking data."""
    c = normalize_cooking(cooking or {})
    s = normalize_shadow(shadow or {}) if shadow else {}
    return {
        'available': s.get('connected') is True,
        'connected': s.get('connected'),
        'updating': s.get('updating'),
        'lastConnection': s.get('lastConnection'),
        'lastDisconnection': s.get('lastDisconnection'),
        'uiFirmware': s.get('uiFirmware'),
        'wifiFirmware': s.get('wifiFirmware'),
        'shadowVersion': s.get('shadowVersion'),
        **c,
    }


def appliance_state(cfg, creds, timeout=15):
    """One-shot HA-ready snapshot from cookingStatus + AWS IoT shadow."""
    cooking = cooking_status(cfg, creds, timeout)
    shadow = shadow_get(cfg, creds, timeout)
    reported = _shadow_reported_from_payload(shadow)
    return combined_state(cooking, {'state': {'reported': reported}, 'version': shadow.get('version')} if reported else shadow)


def watch_state(cfg, creds, ping_interval=30, ping_timeout=10):
    """Yield one normalized state stream covering availability and cooking."""
    base = f'COO001/{DEVICE_UUID}'
    cooking_topic = f'{base}/cookingStatus'
    sb = f'$aws/things/{THING}/shadow'
    cooking = {}
    shadow = {}

    # Seed both halves before the long-running subscription. A failure to seed
    # one half must not prevent the other half from becoming live.
    try:
        cooking = merge_cooking_status({}, cooking_status(cfg, creds, 15))
    except Exception:
        cooking = {}
    try:
        shadow = normalize_shadow(shadow_get(cfg, creds, 15), {})
    except Exception:
        shadow = {}

    out = dict(shadow)
    out.update(normalize_cooking(cooking))
    out['available'] = shadow.get('connected') is True
    yield out

    for event in watch_topics(cfg, creds, include_shadow=True, ping_interval=ping_interval, ping_timeout=ping_timeout):
        topic = event.get('_topic')
        payload = event.get('payload')
        changed = False
        if topic == cooking_topic and isinstance(payload, dict) and 'raw' not in payload:
            cooking = merge_cooking_status(cooking, payload)
            changed = True
        elif isinstance(topic, str) and topic.startswith(sb + '/update/') and isinstance(payload, dict):
            old = dict(shadow)
            shadow = normalize_shadow(payload, shadow)
            changed = shadow != old
        if changed:
            out = dict(shadow)
            out.update(normalize_cooking(cooking))
            out['available'] = shadow.get('connected') is True
            out['_receivedAt'] = event.get('_receivedAt')
            out['_topic'] = topic
            yield out

# ---------------------------------------------------------------------------
# Recipe metadata / step instruction retrieval
# ---------------------------------------------------------------------------
def _normalize_functional_id(value):
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    # DCP recipes sometimes return identifiers as /v1/variants/123/ or
    # /v1/steps/456/.  MQTT uses the terminal numeric/string functional id.
    bits = [x for x in text.split('/') if x]
    return bits[-1] if bits else text


def _step_instruction(step):
    if not isinstance(step, dict):
        return None, []
    values = []
    for key in ('instruction', 'instructions', 'text', 'description'):
        value = step.get(key)
        if isinstance(value, str) and value.strip():
            values.append(value.strip())
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item.strip():
                    values.append(item.strip())
                elif isinstance(item, dict):
                    for subkey in ('instruction', 'text', 'description', 'label', 'value'):
                        sub = item.get(subkey)
                        if isinstance(sub, str) and sub.strip():
                            values.append(sub.strip())
                            break
    # preserve order while de-duplicating
    uniq = []
    seen = set()
    for value in values:
        if value not in seen:
            uniq.append(value)
            seen.add(value)
    return ('\n'.join(uniq) if uniq else None), uniq


def _step_functional_id(step):
    if not isinstance(step, dict):
        return None
    for key in ('functionalId', 'functional_id', 'id'):
        if step.get(key) is not None:
            return _normalize_functional_id(step.get(key))
    ident = step.get('identifier')
    if isinstance(ident, dict):
        for key in ('functionalId', 'functional_id', 'id'):
            if ident.get(key) is not None:
                return _normalize_functional_id(ident.get(key))
    elif isinstance(ident, str):
        return _normalize_functional_id(ident)
    return None


def _extract_recipe_steps(payload):
    """Extract ordered recipe steps from several DCP mobile response shapes."""
    candidates = []

    def walk(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if str(key).lower() == 'steps' and isinstance(value, list):
                    candidates.append(value)
                walk(value)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(payload)
    raw_steps = max(candidates, key=len, default=[])
    if not raw_steps:
        # Backend variants have changed before. Fall back to step-looking dicts,
        # but only if they contain both an id and instruction-like content.
        raw_steps = []
        for item in _iter_dicts(payload):
            fid = _step_functional_id(item)
            instruction, _ = _step_instruction(item)
            if fid and instruction:
                raw_steps.append(item)

    out = []
    seen = set()
    for pos, step in enumerate(raw_steps):
        if not isinstance(step, dict):
            continue
        fid = _step_functional_id(step)
        instruction, instructions = _step_instruction(step)
        typ = step.get('type')
        if isinstance(typ, dict):
            type_key = typ.get('key') or typ.get('name')
        else:
            type_key = typ
        idx = None
        for key in ('stepIndex', 'index', 'position', 'order', 'rank'):
            if step.get(key) is not None:
                try:
                    idx = int(step.get(key))
                except Exception:
                    idx = step.get(key)
                break
        if idx is None:
            idx = pos
        dedupe = (str(fid), str(idx), instruction or '')
        if dedupe in seen:
            continue
        seen.add(dedupe)
        out.append({
            'functionalId': fid,
            'stepIndex': idx,
            'type': type_key,
            'instruction': instruction,
            'instructions': instructions,
        })

    # Only sort when all indices are numeric; otherwise preserve backend order.
    if out and all(isinstance(x.get('stepIndex'), int) for x in out):
        out.sort(key=lambda x: x['stepIndex'])
    return out


def _extract_recipe_cover(payload):
    for item in _iter_dicts(payload):
        if item.get('isCover') is True and isinstance(item.get('media'), dict):
            media = item['media']
            return media.get('thumbnail') or media.get('original')
    for item in _iter_dicts(payload):
        cover = item.get('cover')
        if isinstance(cover, dict):
            media = cover.get('media') if isinstance(cover.get('media'), dict) else cover
            if isinstance(media, dict):
                value = media.get('thumbnail') or media.get('original')
                if value:
                    return value
    return None



def _fid_from(value):
    if isinstance(value, dict):
        return _normalize_functional_id(value.get('functionalId') or value.get('functional_id') or value.get('id'))
    return _normalize_functional_id(value)


def _extract_recipe_ingredients(payload):
    raw = None
    if isinstance(payload, dict) and isinstance(payload.get('ingredients'), list):
        raw = payload.get('ingredients')
    if raw is None:
        for item in _iter_dicts(payload):
            if isinstance(item.get('ingredients'), list):
                raw = item.get('ingredients')
                break
    out=[]
    for item in raw or []:
        if not isinstance(item, dict):
            continue
        food=item.get('food') if isinstance(item.get('food'), dict) else {}
        unit=item.get('unit') if isinstance(item.get('unit'), dict) else {}
        weight=item.get('weight') if isinstance(item.get('weight'), dict) else {}
        wunit=weight.get('unit') if isinstance(weight.get('unit'), dict) else {}
        name=(food.get('name') or item.get('applianceDescription') or item.get('applicationDescription'))
        if not name:
            continue
        row={
            'name': str(name),
            'applicationDescription': item.get('applicationDescription'),
            'applianceDescription': item.get('applianceDescription'),
            'quantity': item.get('quantity'),
            'unit': unit.get('abbreviation') or unit.get('name'),
            'unitKey': unit.get('key'),
            'foodKey': food.get('key'),
            'foodName': food.get('name'),
            'functionalId': _fid_from(item.get('fid')),
        }
        if weight:
            row['weight']={
                'quantity': weight.get('quantity'),
                'unit': wunit.get('abbreviation') or wunit.get('name'),
                'unitKey': wunit.get('key'),
            }
        out.append({k:v for k,v in row.items() if v is not None})
    return out


def _extract_key_name_list(payload, key):
    if not isinstance(payload, dict):
        return []
    value=payload.get(key)
    if not isinstance(value, list):
        return []
    out=[]
    for item in value:
        if isinstance(item, dict):
            row={k:item.get(k) for k in ('key','name') if item.get(k) is not None}
            if row: out.append(row)
        elif item is not None:
            out.append({'name':str(item)})
    return out


def _extract_durations(payload):
    d=payload.get('durations') if isinstance(payload, dict) and isinstance(payload.get('durations'), dict) else {}
    out={k:d.get(k) for k in ('prepTime','cookingTime','offApplianceCookingTime','restingTime','totalTime') if d.get(k) is not None}
    quick=d.get('isQuickRecipe', d.get('quickRecipe'))
    if quick is not None: out['isQuickRecipe']=quick
    return out


def _extract_yield(payload):
    y=payload.get('yield') if isinstance(payload, dict) and isinstance(payload.get('yield'), dict) else {}
    unit=y.get('unit') if isinstance(y.get('unit'), dict) else {}
    return {k:v for k,v in {
        'quantity':y.get('quantity'), 'quantityDisplay':y.get('quantityDisplay'),
        'unit':unit.get('abbreviation') or unit.get('name'), 'unitKey':unit.get('key')
    }.items() if v is not None}


def _recipe_ids(payload, requested_variant=None):
    root=payload if isinstance(payload, dict) else {}
    grouping=_fid_from(root.get('groupingId')) or _normalize_functional_id(root.get('topRecipeId'))
    recipe=_fid_from(root.get('fid')) or _fid_from(root.get('identifier')) or _normalize_functional_id(requested_variant)
    return grouping, recipe

def _recipe_request_headers(cfg, tokens, country, language, app_version, url, pcfg=None):
    """Yield safe header candidates matching the app's DCP interceptor behavior."""
    pcfg = pcfg or discover_rcu(cfg, country, language, app_version, save=True)
    base = app_headers(cfg, app_version, pcfg.get('apim_url'), pcfg.get('apim_subscription_key'), url)
    # Recipe content is often readable using only ApiKey/app headers. Try the
    # exact content request first and only add account tokens if required.
    yield 'app', dict(base)
    context = pcfg.get('profile_perimeter')
    access = (tokens or {}).get('access_token')
    ident = (tokens or {}).get('id_token')
    for name, token, rcu, remote in (
        ('access_rcu', access, True, False),
        ('access_rcu_remote', access, True, True),
        ('id_rcu', ident, True, False),
        ('id_rcu_remote', ident, True, True),
        ('access_bearer', access, False, False),
        ('id_bearer', ident, False, False),
    ):
        if not token:
            continue
        h = dict(base)
        h['Authorization'] = 'Bearer ' + token + ('.REMOTE' if remote else '')
        if rcu and context:
            h['Grant-Type'] = 'RCUToken'
            h['DCP-Context'] = context
        yield name, h


def recipe_metadata(cfg, tokens, recipe_functional_id, variant_functional_id,
                    country='DE', language='de', app_version='36.0.0-RC3', pcfg=None):
    """Fetch a Cook4Me recipe mobile definition and normalize its step text.

    The RC3 APK contains the Retrofit path:
      /common-api/v3/recipes/PRO/{variantId}/?format=mobile
    MQTT supplies the matching variant functional id and current step id.
    """
    if curl_requests is None:
        raise RuntimeError('curl-cffi is not available')
    variant = _normalize_functional_id(variant_functional_id)
    recipe = _normalize_functional_id(recipe_functional_id)
    if not variant:
        raise RuntimeError('Recipe metadata requires a variant functional id')
    base = cfg['platform_base_url'].rstrip('/')
    url = base + '/common-api/v3/recipes/PRO/' + urllib.parse.quote(str(variant), safe='') + '/?format=mobile'
    errors = []
    payload = None
    auth_mode = None
    for name, headers in _recipe_request_headers(cfg, tokens, country, language, app_version, url, pcfg=pcfg):
        try:
            r = curl_requests.get(url, headers=headers, timeout=25, allow_redirects=True, impersonate='chrome')
        except Exception as exc:
            errors.append(f'{name}=network:{type(exc).__name__}')
            continue
        if 200 <= int(r.status_code) < 300:
            try:
                payload = r.json()
            except Exception as exc:
                raise RuntimeError(f'Cook4Me recipe metadata returned invalid JSON: {type(exc).__name__}') from None
            auth_mode = name
            break
        errors.append(f'{name}=HTTP{int(r.status_code)}')
    if payload is None:
        raise RuntimeError('Cook4Me recipe metadata request failed (tokens redacted): ' + ' | '.join(errors))

    # The mobile response can be either one recipe object, a wrapper, or a list.
    root = payload
    if isinstance(root, list) and len(root) == 1:
        root = root[0]
    title = _find_first(root, 'title', 'name')
    steps = _extract_recipe_steps(root)
    grouping_id, actual_recipe_id = _recipe_ids(root, variant)
    ingredients = _extract_recipe_ingredients(root)
    return {
        # Exact app send semantics: groupingId.functionalId goes in recipe.functionalId,
        # while the fetched recipe fid goes in recipe.variant.functionalId.
        'groupingFunctionalId': grouping_id or recipe,
        'recipeFunctionalId': actual_recipe_id or variant,
        'variantFunctionalId': actual_recipe_id or variant,  # backwards-compatible name
        'searchVariantId': variant,
        'title': title,
        'cover': _extract_recipe_cover(root),
        'stepCount': len(steps),
        'steps': steps,
        'ingredients': ingredients,
        'excludedFoods': _extract_key_name_list(root, 'excludedFoods'),
        'detectedExcludedFoods': _extract_key_name_list(root, 'detectedExcludedFoods'),
        'courses': _extract_key_name_list(root, 'courses'),
        'occasions': _extract_key_name_list(root, 'occasions'),
        'durations': _extract_durations(root),
        'yield': _extract_yield(root),
        'difficulty': root.get('difficulty') if isinstance(root, dict) else None,
        'recipeType': (root.get('recipeType') if isinstance(root, dict) else None),
        'isAutomaticallyGenerated': bool(root.get('isAutomaticallyGenerated')) if isinstance(root, dict) else False,
        'isPremium': bool(root.get('isPremium')) if isinstance(root, dict) else False,
        'sendable': bool(grouping_id and actual_recipe_id),
        'source': 'sebplatform_mobile_recipe',
        'authMode': auth_mode,
    }


def search_recipes(cfg, tokens, query='', page=0, size=20, include_details=True, max_details=20,
                   country='DE', language='de', app_version='36.0.0-RC3'):
    """Search the proven SEB recipe endpoint and optionally enrich results."""
    if curl_requests is None:
        raise RuntimeError('curl-cffi is not available')
    page=max(0,int(page)); size=max(1,min(int(size),50)); max_details=max(0,min(int(max_details),50))
    base=cfg['platform_base_url'].rstrip('/')
    url=base+'/common-api/v4/search/recipes'
    # Resolve platform/RCU configuration once per search. Detail enrichment
    # reuses this immutable config instead of repeating discovery for every recipe.
    pcfg=discover_rcu(cfg, country, language, app_version, save=True)
    params={
        'lang':language, 'market':f'GS_{str(country).upper()}', 'page':page, 'size':size,
        'q':str(query or ''), 'groupBy':'', 'myUniverse':'false', 'myOwnRecipe':'false',
        'withAutomaticSpellcheck':'true',
    }
    payload=None; auth_mode=None; errors=[]
    for name, headers in _recipe_request_headers(cfg, tokens, country, language, app_version, url, pcfg=pcfg):
        try:
            r=curl_requests.post(url, params=params, headers=headers, json={}, timeout=30,
                                 allow_redirects=True, impersonate='chrome')
        except Exception as exc:
            errors.append(f'{name}=network:{type(exc).__name__}')
            continue
        if 200 <= int(r.status_code) < 300:
            try: payload=r.json()
            except Exception as exc: raise RuntimeError(f'Cook4Me recipe search returned invalid JSON: {type(exc).__name__}') from None
            auth_mode=name; break
        errors.append(f'{name}=HTTP{int(r.status_code)}')
    if not isinstance(payload, dict):
        raise RuntimeError('Cook4Me recipe search failed (tokens redacted): '+' | '.join(errors))
    content=payload.get('content') if isinstance(payload.get('content'), list) else []
    items=[]
    for raw in content:
        if not isinstance(raw, dict): continue
        variant=_fid_from(raw.get('identifier')) or _fid_from(raw.get('fid')) or _normalize_functional_id(raw.get('functionalId'))
        if not variant: continue
        row={'searchVariantId':variant,'variantFunctionalId':variant,'source':'sebplatform_search'}
        # Preserve any useful search fields if the backend starts returning them.
        for key in ('title','shortTitle','normalizedTitle','difficulty','rating'):
            if raw.get(key) is not None: row[key]=raw.get(key)
        items.append(row)
    if include_details and max_details:
        # Independent HTTP GETs can be enriched concurrently. No shared mutable
        # HTTP session is used, and all calls reuse the already-resolved pcfg.
        from concurrent.futures import ThreadPoolExecutor, as_completed
        enriched=[dict(row) for row in items]
        count=min(max_details,len(items))
        def load(index):
            row=items[index]
            return index, recipe_metadata(
                cfg,tokens,None,row['searchVariantId'],country,language,app_version,pcfg=pcfg
            )
        if count:
            with ThreadPoolExecutor(max_workers=min(4,count)) as pool:
                future_to_index={pool.submit(load,index):index for index in range(count)}
                for future in as_completed(future_to_index):
                    index=future_to_index[future]
                    try:
                        _,detail=future.result()
                    except Exception as exc:
                        # Keep the lightweight search row; details can be retried on open.
                        enriched[index]['detailError']=type(exc).__name__
                        continue
                    detail['searchVariantId']=items[index]['searchVariantId']
                    enriched[index]=detail
        items=enriched
    page_obj=payload.get('page') if isinstance(payload.get('page'), dict) else {}
    facets=payload.get('facets') if isinstance(payload.get('facets'), list) else []
    return {
        'query':str(query or ''), 'page':page_obj or {'number':page,'size':size},
        'items':items, 'facets':facets, 'authMode':auth_mode,
    }

# ---------------------------------------------------------------------------
# Account-owned appliance discovery (HA integration)
# ---------------------------------------------------------------------------
def _uuid_from_thing_name(value):
    if not isinstance(value, str):
        return None
    value=value.strip()
    if value.startswith('COO001-'):
        value=value[7:]
    import re
    if re.fullmatch(r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}', value):
        return value.lower()
    return None


def _collect_owned_cook4me_ids(obj, out=None, in_iot=False):
    """Collect IoT UUIDs only from an account-owned product/profile object.

    This deliberately does NOT enumerate AWS IoT things and does NOT subscribe
    to wildcard Cook4Me topics. A UUID is accepted only when it is present in
    data returned for the authenticated user's profile/products.
    """
    import re
    out = out if out is not None else set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k).lower()
            child_iot = in_iot or key in ('iot', 'dcpiot', 'iotdata', 'iot_data')
            if isinstance(v, str):
                # Strongest signal: an explicit Cook4Me thing name in owned data.
                for m in re.findall(r'COO001-([0-9a-fA-F-]{36})', v):
                    u = _uuid_from_thing_name(m)
                    if u:
                        out.add(u)
                # Within a product's IoT block the backend may expose the same
                # UUID as functionalId/serialNumber/deviceId rather than thingName.
                if child_iot and key in (
                    'functionalid', 'functional_id', 'serialnumber', 'serial_number',
                    'deviceid', 'device_id', 'uuid', 'deviceuuid', 'device_uuid',
                    'applianceuuid', 'appliance_uuid', 'iotuuid', 'iot_uuid',
                    'thingname', 'thing_name',
                ):
                    u = _uuid_from_thing_name(v)
                    if u:
                        out.add(u)
            _collect_owned_cook4me_ids(v, out, child_iot)
    elif isinstance(obj, list):
        for v in obj:
            _collect_owned_cook4me_ids(v, out, in_iot)
    return out


def _profile_products(profile):
    if not isinstance(profile, dict):
        return []
    household = profile.get('household')
    if not isinstance(household, dict):
        return []
    products = household.get('products')
    return products if isinstance(products, list) else []


def _account_headers(cfg, app_version, pcfg, url, tokens):
    """Build the authenticated DCP/RCU profile headers used by the APK.

    The Salesforce callback access_token is the RCU token.  In the remote RCU
    flow the Android interceptor appends ``.REMOTE`` before sending it.  This
    also explains the backend's earlier "expected 3 parts, got 2" response
    when the raw access token was sent.  The id_token is reserved for OpenID /
    Cognito and is *not* the DCP profile bearer token.
    """
    h = app_headers(
        cfg, app_version,
        pcfg.get('apim_url'), pcfg.get('apim_subscription_key'), url,
    )
    token = tokens.get('access_token')
    context = pcfg.get('profile_perimeter')
    if token and context:
        h['Authorization'] = 'Bearer ' + token + '.REMOTE'
        h['Grant-Type'] = 'RCUToken'
        h['DCP-Context'] = context
    return h


def _fetch_owned_profile(cfg, tokens, country='DE', language='de', app_version='36.0.0-RC3'):
    """Fetch the account profile, with a redacted live auth matrix for backend drift."""
    pcfg = discover_rcu(cfg, country, language, app_version, save=True)
    access = tokens.get('access_token')
    ident = tokens.get('id_token')
    context = pcfg.get('profile_perimeter')
    if not access:
        raise RuntimeError('Cook4Me authentication did not return an RCU access token')
    if not context:
        raise RuntimeError('Cook4Me platform configuration did not contain a DCP profile perimeter')

    base = cfg['platform_base_url'].rstrip('/')
    url = base + '/common-api/profiles/me'
    base_headers = app_headers(
        cfg, app_version,
        pcfg.get('apim_url'), pcfg.get('apim_subscription_key'), url,
    )

    # Never log token values.  This matrix exists because the current KRUPS
    # backend has returned materially different validation errors for the
    # Salesforce access token and OpenID id_token.  Stop at the first 2xx.
    candidates = [
        ('access_rcu', access, True, False),
        ('access_rcu_remote', access, True, True),
        ('id_rcu', ident, True, False),
        ('id_rcu_remote', ident, True, True),
        ('access_bearer', access, False, False),
        ('id_bearer', ident, False, False),
    ]
    results = []
    for name, token, rcu, remote in candidates:
        if not token:
            continue
        h = dict(base_headers)
        h['Authorization'] = 'Bearer ' + token + ('.REMOTE' if remote else '')
        if rcu:
            h['Grant-Type'] = 'RCUToken'
            h['DCP-Context'] = context
        try:
            r = curl_requests.get(
                url, headers=h, timeout=25,
                allow_redirects=True, impersonate='chrome',
            )
        except Exception as exc:
            results.append(f'{name}=network:{type(exc).__name__}')
            continue
        status = int(r.status_code)
        if 200 <= status < 300:
            try:
                return r.json()
            except Exception as exc:
                raise RuntimeError(f'Cook4Me profile {name} returned HTTP {status} but invalid JSON: {type(exc).__name__}') from None
        try:
            body = r.json()
            code = body.get('errorCode') if isinstance(body, dict) else None
            msg = body.get('message') if isinstance(body, dict) else None
            detail = ':'.join(str(x) for x in (code, msg) if x)
        except Exception:
            detail = (r.text or '').replace('\n', ' ')[:160]
        results.append(f'{name}=HTTP{status}' + (f':{detail}' if detail else ''))

    raise RuntimeError('Cook4Me profile authentication matrix failed (tokens redacted): ' + ' | '.join(results))


def discover_appliances(cfg, creds, tokens=None, country='DE', language='de', app_version='36.0.0-RC3'):
    """Return only Cook4Me appliances proven to belong to the logged-in account."""
    tokens = tokens or {}
    profile = _fetch_owned_profile(cfg, tokens, country, language, app_version)
    products = _profile_products(profile)

    found = {}
    for product in products:
        if not isinstance(product, dict):
            continue
        ids = _collect_owned_cook4me_ids(product)
        for uuid in ids:
            name = product.get('nickname') or product.get('name') or 'Cook4Me'
            found[uuid] = {
                'uuid': uuid,
                'thing_name': f'COO001-{uuid}',
                'name': str(name),
                'source': 'account_profile',
                'appliance': product.get('appliance'),
                'rcu_asset_id': product.get('rcuAssetId'),
            }

    # Some backend revisions put the IoT identifier directly on the profile or
    # household instead of inside products. This is still account-owned data.
    if not found:
        for uuid in _collect_owned_cook4me_ids(profile):
            found[uuid] = {
                'uuid': uuid,
                'thing_name': f'COO001-{uuid}',
                'name': 'Cook4Me',
                'source': 'account_profile',
            }

    if not found:
        # Do not fall back to AWS ListThings or wildcard MQTT. Those can expose
        # devices belonging to other Groupe SEB users when IAM is too broad.
        raise RuntimeError(
            'Authenticated account profile contains no Cook4Me IoT UUID; '
            'unsafe global AWS discovery is intentionally disabled'
        )
    return sorted(found.values(), key=lambda x: x['uuid'])
