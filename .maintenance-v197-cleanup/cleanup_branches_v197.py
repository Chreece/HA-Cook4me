"""Explicit one-shot Cook4Me branch cleanup; abort atomically on changed refs."""
import json, os, subprocess, urllib.request
from pathlib import Path

REPOSITORY = 'Chreece/HA-Cook4me'

def git(*args, input=None, check=True):
    return subprocess.run(['git', *args], input=input, text=True, capture_output=True, check=check)

def api(path):
    request = urllib.request.Request('https://api.github.com/repos/' + REPOSITORY + path,
        headers={'Authorization': 'Bearer ' + os.environ['GH_TOKEN'], 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=40) as response:
        return json.load(response)

def remote_heads():
    return {ref.removeprefix('refs/heads/'):sha for sha,ref in
        (line.split() for line in git('ls-remote','--heads','origin').stdout.splitlines())}

def ancestor(a,b):
    return git('merge-base','--is-ancestor',a,b,check=False).returncode == 0

def plan(remote, reviewed, stage, is_ancestor):
    if 'main' not in remote: raise ValueError('main missing')
    expected={k:v for k,v in reviewed.items() if k!='main'}
    expected.update(stage)
    if set(remote)-set(expected)-{'main'}: raise ValueError('unreviewed branches')
    selected=[]
    for name,sha in remote.items():
        if name=='main': continue
        if expected.get(name)!=sha: raise ValueError('branch moved: '+name)
        if not is_ancestor(sha,remote['main']): raise ValueError('unmerged history: '+name)
        selected.append((name,sha))
    return sorted(selected)

def main():
    assert os.environ['GITHUB_REPOSITORY'] == REPOSITORY
    assert os.environ['GITHUB_REF'] == 'refs/heads/main'
    repo=api('')
    assert repo['id']==1358990009 and repo['default_branch']=='main'
    assert not api('/pulls?state=open&per_page=100'), 'Open pull requests remain'
    before=remote_heads()
    main_sha=git('rev-parse','HEAD').stdout.strip()
    assert main_sha==os.environ['GITHUB_SHA']==before['main'], 'Main advanced since cleanup started'
    manifest=json.loads(Path('docs/BRANCH_CONSOLIDATION_V197.json').read_text())
    assert manifest['originalBranchCount']==287 and manifest['repository']==REPOSITORY
    reviewed={r['branch']:r['sha'] for r in manifest['branches']}
    assert len(reviewed)==287
    assert all(ancestor(sha,main_sha) for sha in reviewed.values()), 'An audited history was not retained'
    selected=plan(before,reviewed,{'chore/consolidate-v197':os.environ['REVIEWED_STAGING_SHA']},ancestor)
    tags=git('ls-remote','--tags','origin').stdout
    git('bundle','create','/tmp/cook4me-final-history.bundle','--all')
    report={'schemaVersion':1,'repository':REPOSITORY,'baseMain':main_sha,
            'originalAuditedBranches':287,'removedBranchCount':len(selected),
            'deletedRefs':[{'branch':n,'sha':s} for n,s in selected],
            'method':'atomic-push-with-per-ref-leases','allTipsReachableFromMain':True,
            'remainingBranches':['main'],'tagsUntouched':True,'liveDeployment':False}
    path=Path('docs/BRANCH_CLEANUP_V197.json')
    assert not path.exists(), 'Cleanup report already exists; review rather than running twice'
    path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    git('add',str(path))
    assert git('diff','--cached','--name-only').stdout.splitlines()==[str(path)]
    tree=git('write-tree').stdout.strip()
    git('config','user.name','Cook4Me maintenance')
    git('config','user.email','68458228+Chreece@users.noreply.github.com')
    commit=git('commit-tree',tree,'-p',main_sha,input='chore: complete audited branch cleanup; retain only main\n\nAll reviewed branch histories are reachable from main. Branch deletions and this report publish atomically with exact expected-ref checks. Tags and live Home Assistant untouched.\n').stdout.strip()
    assert ancestor(main_sha,commit)
    args=['push','--atomic','--force-with-lease=refs/heads/main:'+main_sha]
    args += ['--force-with-lease=refs/heads/'+n+':'+s for n,s in selected]
    args += ['origin',commit+':refs/heads/main']+[':refs/heads/'+n for n,s in selected]
    result=git(*args)
    print(result.stdout,result.stderr)
    assert remote_heads()=={'main':commit}, 'Unexpected remaining refs; investigate'
    assert git('ls-remote','--tags','origin').stdout==tags, 'Tag set changed concurrently'
    print('CLEANUP_COMPLETE',json.dumps({'main':commit,'removed':len(selected),'remaining':['main'],'allHistoriesPreserved':True,'tagsUnchanged':True}))
    with open(os.environ['GITHUB_STEP_SUMMARY'],'a') as summary:
        summary.write('# Cleanup verified\n\nOnly main remains. Removed '+str(len(selected))+' reviewed branch refs. All histories remain reachable; tags unchanged.\n')

if __name__=='__main__': main()
