import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request
from unittest.mock import patch
from netvision.database import ROOT
from netvision.server import APP_ID,INSTANCE_ID
from start_server import responds


class StartupTests(unittest.TestCase):
    def test_real_launcher_from_another_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            with socket.socket() as probe:
                probe.bind(('127.0.0.1',0));port=probe.getsockname()[1]
            env={**os.environ,'NETVISION_DB':str(Path(tmp)/'db.sqlite3'),'NETVISION_NO_BROWSER':'1'}
            process=subprocess.Popen([sys.executable,str(ROOT/'start_server.py'),'--serve','127.0.0.1',str(port)],cwd=tmp,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
            try:
                data=None
                for _ in range(80):
                    if process.poll() is not None:break
                    try:
                        with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health',timeout=.2) as response:data=json.load(response)
                        break
                    except OSError:time.sleep(.05)
                self.assertIsNotNone(data)
                self.assertEqual(data['application'],APP_ID)
                self.assertEqual(data['instance'],INSTANCE_ID)
                self.assertTrue((Path(tmp)/'db.sqlite3').exists())
            finally:
                if process.poll() is None:process.send_signal(signal.SIGINT)
                output=process.communicate(timeout=5)[0]
            self.assertEqual(process.returncode,0,output)
    def test_identity_check_rejects_unrelated_and_other_copy(self):
        import io
        class Response(io.BytesIO):status=200
        for payload,expected in [({'application':'other'},False),({'application':APP_ID,'instance':'other'},False),({'application':APP_ID,'instance':INSTANCE_ID},True)]:
            with patch('urllib.request.build_opener') as build:
                build.return_value.open.return_value=Response(json.dumps(payload).encode())
                self.assertEqual(responds('http://127.0.0.1:4173/'),expected)
        self.assertFalse(responds('https://example.com/'))
