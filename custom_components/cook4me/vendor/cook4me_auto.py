#!/usr/bin/env python3
import argparse, datetime as dt, json, os, subprocess, sys, time
from pathlib import Path
HERE=Path(__file__).resolve().parent; sys.path.insert(0,str(HERE))
import cook4me_phonefree as c4m
import cook4me_recipe_search_proven as proven_search
TOKENS=Path.home()/'.config/cook4me/tokens.json'; AWS=Path.home()/'.config/cook4me/aws.json'
def token_valid(skew=300):
    try:
        o=json.loads(TOKENS.read_text()); e=c4m.jwt_exp(o.get('id_token')); return bool(e and e>time.time()+skew)
    except Exception:return False
def aws_valid(skew=300):
    try:
        e=json.loads(AWS.read_text()).get('Expiration')
        if isinstance(e,(int,float)): return (e/1000 if e>1e10 else e)>time.time()+skew
        if isinstance(e,str): return dt.datetime.fromisoformat(e.replace('Z','+00:00')).timestamp()>time.time()+skew
    except Exception:pass
    return False
def run_auth(a):
    cmd=[sys.executable,str(HERE/'cook4me_plain_http_auth.py')]
    if a.apk: cmd += ['--apk',str(a.apk)]
    cmd += ['--country',a.country,'--language',a.language,'--app-version',a.app_version]
    if a.no_save_credentials:cmd.append('--no-save-credentials')
    print('KRUPS token          : missing/expired; running browserless login')
    if subprocess.run(cmd).returncode:raise SystemExit(1)
    if not token_valid(60):raise RuntimeError('Authentication produced no usable id_token')
def prepare(a):
    cfg=c4m.read_apk_config(a.apk)
    if a.force_login or not token_valid():run_auth(a)
    else:print('KRUPS token          : cached and valid')
    if a.auth_only:return cfg,None
    if not a.force_aws and aws_valid():
        print('AWS credentials      : cached and valid'); creds=c4m.load_json(AWS)
    else:
        print('AWS credentials      : obtaining temporary Cognito credentials')
        creds=c4m.aws_credentials(cfg,c4m.load_json(TOKENS)['id_token']); print('AWS credentials      : ready')
    return cfg,creds
def dump(o):
    print(json.dumps(o, ensure_ascii=False, sort_keys=True) if JSON_LINES else json.dumps(o,indent=2,ensure_ascii=False,sort_keys=True), flush=True)
JSON_LINES=False
def main():
    ap=argparse.ArgumentParser(description='Phone-free Cook4Me cloud client')
    ap.add_argument('--apk',type=Path); ap.add_argument('--device-uuid'); ap.add_argument('--json-lines',action='store_true'); ap.add_argument('--country',default='DE'); ap.add_argument('--language',default='de'); ap.add_argument('--app-version',default='36.0.0-RC3'); ap.add_argument('--force-login',action='store_true'); ap.add_argument('--force-aws',action='store_true'); ap.add_argument('--no-save-credentials',action='store_true'); ap.add_argument('--auth-only',action='store_true')
    sub=ap.add_subparsers(dest='command'); sub.add_parser('test'); sub.add_parser('status'); sub.add_parser('shadow'); sub.add_parser('watch'); sub.add_parser('watch-all'); sub.add_parser('state'); sub.add_parser('watch-state'); sub.add_parser('discover'); m=sub.add_parser('recipe-metadata'); m.add_argument('recipe_id'); m.add_argument('variant_id'); sr=sub.add_parser('search-recipes'); sr.add_argument('query', nargs='?', default=''); sr.add_argument('--page',type=int,default=0); sr.add_argument('--size',type=int,default=20); sr.add_argument('--max-details',type=int,default=20); sr.add_argument('--no-details',action='store_true'); r=sub.add_parser('send-recipe'); r.add_argument('functional_id'); r.add_argument('variant_id')
    a=ap.parse_args(); a.command=a.command or 'test';
    global JSON_LINES; JSON_LINES=a.json_lines; cfg,creds=prepare(a);
    if a.device_uuid: c4m.set_device_uuid(a.device_uuid)
    if a.auth_only:print('READY                : KRUPS authentication available');return
    if a.command=='discover': dump({'appliances':c4m.discover_appliances(cfg,creds,c4m.load_json(TOKENS),a.country,a.language,a.app_version)}); return
    if a.command=='recipe-metadata': dump(c4m.recipe_metadata(cfg,c4m.load_json(TOKENS),a.recipe_id,a.variant_id,a.country,a.language,a.app_version)); return
    if a.command=='search-recipes': dump(proven_search.search_recipes(cfg,c4m.load_json(TOKENS),a.query,a.page,a.size,not a.no_details,a.max_details,a.country,a.language,a.app_version)); return
    if a.command=='test':
        print('AWS IoT MQTT         : connecting'); rc=c4m.mqtt_test(cfg,creds)
        if rc:raise SystemExit(rc)
        print('READY                : phone-free Cook4Me cloud connection works')
    elif a.command=='status':dump(c4m.cooking_status(cfg,creds))
    elif a.command=='shadow':dump(c4m.shadow_get(cfg,creds))
    elif a.command=='state':dump(c4m.appliance_state(cfg,creds))
    elif a.command=='send-recipe':dump(c4m.send_recipe(cfg,creds,a.functional_id,a.variant_id))
    elif a.command in ('watch','watch-all','watch-state'):
        print('Watching Cook4Me MQTT persistently; Ctrl-C stops.')
        failures=0
        try:
            while True:
                try:
                    if a.command=='watch':
                        for x in c4m.watch_cooking(cfg,creds): dump(x)
                    elif a.command=='watch-state':
                        for x in c4m.watch_state(cfg,creds): dump(x)
                    else:
                        for x in c4m.watch_topics(cfg,creds,include_shadow=True): dump(x)
                    raise ConnectionError('MQTT watcher ended unexpectedly')
                except KeyboardInterrupt:
                    raise
                except Exception as exc:
                    failures += 1
                    print(f'MQTT reconnect        : {exc.__class__.__name__}: {exc}', file=sys.stderr, flush=True)
                    time.sleep(min(30, 3*failures))
                    # Re-evaluate both KRUPS token and temporary AWS credentials.
                    # This keeps long-running watches alive across credential expiry.
                    cfg,creds=prepare(a)
                    failures=0
        except KeyboardInterrupt:
            print('Stopped with Ctrl+C.')
if __name__=='__main__':main()
