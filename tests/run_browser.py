"""Isolated real-browser test. Requires Node, Playwright and Chromium; see README."""
import os
from pathlib import Path
import subprocess
import tempfile
import threading
from netvision.database import ROOT,initialize,connect,transaction
from netvision.server import make_server

artifacts=Path(os.environ.get('NETVISION_TEST_ARTIFACTS',ROOT/'test-results')).resolve()
artifacts.mkdir(parents=True,exist_ok=True)
media=ROOT/'media'/'netvision-test-pattern.webm'
if media.exists():raise SystemExit('Test media path already exists; refusing to overwrite')
try:
    with tempfile.TemporaryDirectory() as tmp:
        path=Path(tmp)/'browser.sqlite3';initialize(path)
        db=connect(path)
        with transaction(db):db.execute("UPDATE media_assets SET src='media/netvision-test-pattern.webm',poster=''")
        db.close()
        for phase in ['main','restart']:
            server=make_server('127.0.0.1',0,path)
            thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
            try:
                subprocess.run([os.environ.get('NODE','node'),str(ROOT/'tests'/'browser.cjs'),f'http://127.0.0.1:{server.server_port}/',str(media),str(artifacts),phase],check=True)
            finally:server.shutdown();server.server_close();thread.join()
finally:
    if media.exists():media.unlink()
