"""Real Git race tests: no network; unrelated work survives and data conflicts stop."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class CollectorPushTests(unittest.TestCase):
    def git(self,where,*args):
        return subprocess.check_output(['git',*args],cwd=where,stderr=subprocess.DEVNULL,text=True).strip()

    def write_commit(self,where,files):
        for name,text in files.items():
            path=where/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text(text)
        self.git(where,'add','.')
        self.git(where,'commit','-m','fixture')

    def setup_repo(self,root):
        remote=root/'remote.git';remote.mkdir();self.git(remote,'init','--bare','--initial-branch=main')
        local=root/'local';self.git(root,'clone',str(remote),str(local))
        for where in (local,):
            self.git(where,'config','user.name','Test');self.git(where,'config','user.email','test@example.invalid')
        self.write_commit(local,{'data/gclri/latest.json':'old','data/gclri/history.json':'old',
                                 'scripts/collect_gclri_market.py':'old-code'})
        self.git(local,'push','origin','main');base=self.git(local,'rev-parse','HEAD')
        other=root/'other';self.git(root,'clone',str(remote),str(other))
        self.git(other,'config','user.name','Test');self.git(other,'config','user.email','test@example.invalid')
        self.write_commit(local,{'data/gclri/latest.json':'new','data/gclri/history.json':'new'})
        return remote,local,other,base

    def test_unrelated_concurrent_publication_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            remote,local,other,base=self.setup_repo(Path(tmp))
            self.write_commit(other,{'intelligence/report.html':'concurrent report'})
            self.git(other,'push','origin','main')
            result=subprocess.run(['bash',str(ROOT/'scripts/push_gclri_commit.sh'),base],cwd=local,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(self.git(remote,'show','main:intelligence/report.html'),'concurrent report')
            self.assertEqual(self.git(remote,'show','main:data/gclri/latest.json'),'new')

    def test_concurrent_source_change_blocks_without_overwriting(self):
        for path in ('data/gclri/latest.json','scripts/collect_gclri_market.py'):
            with self.subTest(path=path),tempfile.TemporaryDirectory() as tmp:
                remote,local,other,base=self.setup_repo(Path(tmp))
                self.write_commit(other,{path:'newer upstream'})
                self.git(other,'push','origin','main');head=self.git(remote,'rev-parse','main')
                result=subprocess.run(['bash',str(ROOT/'scripts/push_gclri_commit.sh'),base],cwd=local,capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0)
                self.assertEqual(self.git(remote,'rev-parse','main'),head)
                self.assertEqual(self.git(remote,'show','main:'+path),'newer upstream')

    def test_timestamp_only_collection_is_allowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            remote,local,other,base=self.setup_repo(Path(tmp))
            (local/'data/gclri/history.json').write_text('old')
            self.git(local,'add','data/gclri/history.json')
            self.git(local,'commit','--amend','--no-edit')
            result=subprocess.run(['bash',str(ROOT/'scripts/push_gclri_commit.sh'),base],cwd=local,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(self.git(remote,'show','main:data/gclri/latest.json'),'new')
            self.assertEqual(self.git(remote,'show','main:data/gclri/history.json'),'old')
