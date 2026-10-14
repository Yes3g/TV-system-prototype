import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from netvision.database import ROOT,connect
from netvision.repository import update_settings,settings


class MaintenanceTests(unittest.TestCase):
    def test_lifecycle_from_different_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);dbpath=root/'test.sqlite3';env={**os.environ,'NETVISION_DB':str(dbpath)}
            def run(*args,ok=True):
                result=subprocess.run([sys.executable,str(ROOT/'manage.py'),*args],cwd=root,env=env,capture_output=True,text=True)
                self.assertEqual(result.returncode==0,ok,result.stdout+result.stderr)
                return result
            run('init');run('check')
            db=connect(dbpath)
            update_settings(db,'user-1',{'revision':0,'settings':{'subtitles':'en'}});db.close()
            run('backup',str(root/'saved.sqlite3'))
            run('reset',ok=False)
            db=connect(dbpath);self.assertEqual(settings(db,'user-1')['settings']['subtitles'],'en');db.close()
            run('reset','--yes')
            db=connect(dbpath);self.assertEqual(settings(db,'user-1')['settings']['subtitles'],'off');db.close()
            run('restore',str(root/'saved.sqlite3'),'--yes')
            db=connect(dbpath);self.assertEqual(settings(db,'user-1')['settings']['subtitles'],'en');db.close()
            self.assertEqual(len(list(root.glob('*.backup-*'))),2)
            run('restore',str(root/'missing.sqlite3'),'--yes',ok=False)
            self.assertFalse((root/'missing.sqlite3').exists())
