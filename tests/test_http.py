import json
from pathlib import Path
import tempfile
import threading
import unittest
import urllib.request
import urllib.error
from netvision.database import initialize,connect,ROOT
from netvision.server import make_server


class HttpTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.sqlite3';initialize(self.path)
        self.server=make_server('127.0.0.1',0,self.path)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.url=f'http://127.0.0.1:{self.server.server_port}'
    def tearDown(self):self.server.shutdown();self.server.server_close();self.thread.join();self.tmp.cleanup()
    def request(self,path,method='GET',data=None,headers=None):
        headers=headers or {}
        if data is not None:
            headers={'Content-Type':'application/json','X-NetVision-Token':self.server.csrf_token,**headers};data=json.dumps(data).encode()
        request=urllib.request.Request(self.url+path,data=data,method=method,headers=headers)
        try:response=urllib.request.urlopen(request)
        except urllib.error.HTTPError as e:response=e
        with response:return response.status,response.read(),response.headers
    def test_bootstrap_read_write_and_profile_isolation(self):
        status,raw,_=self.request('/api/bootstrap');data=json.loads(raw)
        self.assertEqual(status,200);self.assertEqual(len(data['mediaAssets']),20)
        self.assertEqual(self.request('/api/users/user-1/settings','PATCH',{'revision':0,'settings':{'autoplay':True}})[0],200)
        self.assertTrue(json.loads(self.request('/api/users/user-1/settings')[1])['settings']['autoplay'])
        self.assertFalse(json.loads(self.request('/api/users/user-2/settings')[1])['settings']['autoplay'])
        self.assertEqual(self.request('/api/users/user-1/settings','PATCH',{'revision':0,'settings':{'autoplay':False}})[0],409)
    def test_public_files_and_private_denial(self):
        self.assertEqual(self.request('/')[0],200)
        for path in ['/data/db.json','/data/db.js','/var/netvision.sqlite3','/netvision/schema.sql','/start_server.py','/media/../data/db.json','/media/test.sqlite3']:
            with self.subTest(path=path):self.assertIn(self.request(path)[0],[403,404])
    def test_security_validation_and_errors(self):
        self.assertEqual(self.request('/api/health',headers={'Host':'evil.example'})[0],403)
        self.assertEqual(self.request('/api/health',headers={'Origin':'https://evil.example'})[0],403)
        self.assertEqual(self.request('/api/users/user-1/settings','PATCH',{'revision':0,'settings':{'autoplay':True}},headers={'X-NetVision-Token':'bad'})[0],403)
        self.assertEqual(self.request('/api/users/missing/settings')[0],404)
        self.assertEqual(self.request('/api/unknown')[0],404)
        self.assertEqual(self.request('/api/users/user-1/settings','PATCH',{'revision':0,'settings':{'audio':'wrong'}})[0],400)
        self.assertEqual(self.request('/media/missing.mp4')[0],404)
        self.server.db_path=Path(self.tmp.name)/'absent'/'db.sqlite3'
        self.assertEqual(self.request('/api/bootstrap')[0],503)
    def test_history_api(self):
        status,raw,_=self.request('/api/playback-sessions','POST',{'userId':'user-2','episodeId':'episode-news-1'})
        self.assertEqual(status,201);token=json.loads(raw)['token']
        self.assertEqual(self.request('/api/playback-sessions/'+token,'PUT',{'sequence':1,'watchedSeconds':2,'completed':False})[0],200)
        self.assertEqual(len(json.loads(self.request('/api/users/user-2/history')[1])),1)
    def test_range_and_symlink(self):
        media=ROOT/'media'/'test-range.mp4';link=ROOT/'media'/'test-link.mp4'
        media.write_bytes(b'0123456789')
        try:
            status,raw,headers=self.request('/media/test-range.mp4',headers={'Range':'bytes=2-5'})
            self.assertEqual((status,raw),(206,b'2345'));self.assertEqual(headers['Content-Range'],'bytes 2-5/10')
            link.symlink_to(media)
            self.assertEqual(self.request('/media/test-link.mp4')[0],403)
        finally:
            if link.is_symlink():link.unlink()
            media.unlink()

if __name__=='__main__':unittest.main()
