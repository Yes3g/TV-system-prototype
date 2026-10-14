import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from netvision.database import initialize,connect,SEED
from netvision import repository as r


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'test.sqlite3'
        initialize(self.path);self.db=connect(self.path)
    def tearDown(self):self.db.close();self.tmp.cleanup()
    def test_lossless_import_and_order(self):
        self.assertEqual(r.catalog(self.db,False),json.loads(SEED.read_text()))
        self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(),[])
    def test_persistence_and_repeat_initialization(self):
        r.update_settings(self.db,'user-1',{'revision':0,'settings':{'subtitles':'cs','autoplay':True}})
        initialize(self.path)
        other=connect(self.path)
        try:
            self.assertEqual(r.settings(other,'user-1')['settings']['subtitles'],'cs')
            self.assertEqual(r.settings(other,'user-1')['revision'],1)
            self.assertEqual(len(r.catalog(other)['episodes']),23)
            self.assertFalse(r.settings(other,'user-2')['settings']['autoplay'])
        finally:other.close()
    def test_integrity(self):
        for sql in ["INSERT INTO genres(id,name,position) VALUES (NULL,'Invalid',99)", "UPDATE episodes SET program_id='missing'", "UPDATE schedule_items SET channel_id='nova' WHERE id='schedule-ct-news'", "UPDATE programs SET channel_id='nova' WHERE id='program-newsroom'", "UPDATE episodes SET program_id='program-fun-live' WHERE id='episode-news-1'", "UPDATE settings SET autoplay=2", "UPDATE genre_weights SET weight=2"]:
            with self.subTest(sql=sql),self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql)
    def test_invalid_seed_rolls_back_and_can_retry(self):
        path=Path(self.tmp.name)/'bad.sqlite3';seed=Path(self.tmp.name)/'bad.json'
        data=json.loads(SEED.read_text());data['episodes'][0]['programId']='missing';seed.write_text(json.dumps(data))
        with self.assertRaises(sqlite3.IntegrityError):initialize(path,seed)
        c=connect(path)
        try:self.assertEqual(c.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(),[])
        finally:c.close()
        initialize(path)
    def test_unknown_seed_attribute_not_silently_lost(self):
        path=Path(self.tmp.name)/'extra.sqlite3';seed=Path(self.tmp.name)/'extra.json'
        data=json.loads(SEED.read_text());data['users'][0]['newField']='test';seed.write_text(json.dumps(data))
        with self.assertRaises(ValueError):initialize(path,seed)
    def test_unsupported_version_preserved(self):
        self.db.execute('PRAGMA user_version=99')
        with self.assertRaises(RuntimeError):initialize(self.path)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM users').fetchone()[0],2)
    def test_concurrent_settings_conflict(self):
        def change(value):
            c=connect(self.path)
            try:
                r.update_settings(c,'user-1',{'revision':0,'settings':{'subtitles':value}});return 200
            except r.ApiError as e:return e.status
            finally:c.close()
        with ThreadPoolExecutor(2) as pool:self.assertEqual(sorted(pool.map(change,['cs','en'])),[200,409])
    def test_import_once_skip_modified_and_atomic_validation(self):
        r.update_settings(self.db,'user-1',{'revision':0,'settings':{'audio':'cz-dub'}})
        result=r.import_legacy(self.db,{'users':{'user-1':{'settings':{'subtitles':'cs'}},'user-2':{'settings':{'subtitles':'en'}}}})
        self.assertEqual(result,{'applied':['user-2'],'skipped':['user-1']})
        with self.assertRaises(r.ApiError):r.import_legacy(self.db,{'users':{}})
        self.assertEqual(r.settings(self.db,'user-1')['settings']['subtitles'],'off')
    def test_history_pair_and_stale_sequence(self):
        token=r.start_playback(self.db,'user-1','episode-news-1')['token']
        self.assertEqual(len(r.history(self.db,'user-1')),2) # session alone is not history
        r.update_history(self.db,token,{'sequence':2,'watchedSeconds':9,'completed':False})
        with self.assertRaises(r.ApiError):r.update_history(self.db,token,{'sequence':1,'watchedSeconds':1,'completed':False})
        token2=r.start_playback(self.db,'user-1','episode-news-1')['token']
        with self.assertRaises(r.ApiError):r.update_history(self.db,token,{'sequence':3,'watchedSeconds':12,'completed':False})
        r.update_history(self.db,token2,{'sequence':1,'watchedSeconds':15,'completed':True})
        self.assertEqual(r.history(self.db,'user-2'),[])
        rows=[h for h in r.history(self.db,'user-1') if h['episodeId']=='episode-news-1']
        self.assertEqual(len(rows),1);self.assertEqual(rows[0]['watchedSeconds'],15)
    def test_bad_values(self):
        for changes in [{'autoplay':1},{'subtitles':'xx'},{'audio':{}},{'oops':1}]:
            with self.assertRaises(r.ApiError):r.update_settings(self.db,'user-1',{'revision':0,'settings':changes})
        with self.assertRaises(r.ApiError):r.settings(self.db,'missing')
        token=r.start_playback(self.db,'user-1','episode-news-1')['token']
        for value in [float('nan'),-1,True]:
            with self.assertRaises(r.ApiError):r.update_history(self.db,token,{'sequence':1,'watchedSeconds':value,'completed':False})

if __name__=='__main__':unittest.main()
