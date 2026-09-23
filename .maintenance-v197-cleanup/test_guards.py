from pathlib import Path
import subprocess,tempfile,unittest
from cleanup_branches_v197 import plan

class Guards(unittest.TestCase):
    def test_main_is_never_a_delete_target(self):
        self.assertEqual(plan({'main':'A','old':'B'},{'main':'Z','old':'B'},{},lambda a,b:True),[('old','B')])
    def test_changed_branch_blocks_everything(self):
        with self.assertRaisesRegex(ValueError,'moved'):plan({'main':'A','old':'C'},{'old':'B'},{},lambda a,b:True)
    def test_unknown_branch_blocks_everything(self):
        with self.assertRaisesRegex(ValueError,'unreviewed'):plan({'main':'A','new':'C'},{},{},lambda a,b:True)
    def test_unmerged_history_blocks_everything(self):
        with self.assertRaisesRegex(ValueError,'unmerged'):plan({'main':'A','old':'B'},{'old':'B'},{},lambda a,b:False)
    def test_already_removed_branches_are_not_recreated(self):
        self.assertEqual(plan({'main':'A'},{'old':'B'},{},lambda a,b:True),[])
    def test_stage_has_explicit_pinned_tip(self):
        self.assertEqual(plan({'main':'A','staging':'S'},{},{'staging':'S'},lambda a,b:True),[('staging','S')])
    def test_atomic_leased_deletion_rejects_race_without_changing_main(self):
        with tempfile.TemporaryDirectory() as d:
            origin=Path(d)/'origin';work=Path(d)/'work'
            def run(*args,ok=True,cwd=None):
                r=subprocess.run(['git',*args],cwd=cwd or work,text=True,capture_output=True)
                if ok and r.returncode:self.fail(r.stderr)
                return r
            run('init','--bare',str(origin),cwd=d);run('init',str(work),cwd=d)
            run('config','user.name','Guard test');run('config','user.email','test@example.invalid')
            run('remote','add','origin',str(origin));(work/'file').write_text('base')
            run('add','.');run('commit','-m','base');base=run('rev-parse','HEAD').stdout.strip()
            run('push','origin',base+':refs/heads/main',base+':refs/heads/old')
            (work/'file').write_text('next');run('add','.');run('commit','-m','next');nxt=run('rev-parse','HEAD').stdout.strip()
            run('push','origin',nxt+':refs/heads/old')
            r=run('push','--atomic','--force-with-lease=refs/heads/main:'+base,'--force-with-lease=refs/heads/old:'+base,'origin',nxt+':refs/heads/main',':refs/heads/old',ok=False)
            self.assertNotEqual(r.returncode,0)
            refs=dict(line.split()[::-1] for line in run('ls-remote','--heads','origin').stdout.splitlines())
            self.assertEqual(refs['refs/heads/main'],base);self.assertEqual(refs['refs/heads/old'],nxt)
            run('push','--atomic','--force-with-lease=refs/heads/main:'+base,'--force-with-lease=refs/heads/old:'+nxt,'origin',nxt+':refs/heads/main',':refs/heads/old')
            self.assertEqual(run('ls-remote','--heads','origin').stdout.strip(),nxt+'\trefs/heads/main')

if __name__=='__main__':unittest.main(verbosity=2)
