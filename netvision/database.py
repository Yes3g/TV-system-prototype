"""Versioned, transactional SQLite initialization and lossless seed import."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = Path(__file__).with_name('schema.sql')
SEED = ROOT / 'data' / 'db.json'
VERSION = 1


def database_path():
    configured = Path(os.environ.get('NETVISION_DB', 'var/netvision.sqlite3')).expanduser()
    return configured if configured.is_absolute() else ROOT / configured


def connect(path=None):
    db = sqlite3.connect(str(path or database_path()), timeout=5, isolation_level=None)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=5000')
    return db


@contextmanager
def transaction(db):
    db.execute('BEGIN IMMEDIATE')
    try:
        yield db
        db.commit()
    except BaseException:
        db.rollback()
        raise


def seed(db, data):
    def add(table, values):
        db.execute('INSERT INTO '+table+' VALUES ('+','.join('?' for _ in values)+')', values)
    regions = {c['region'] for c in data['channels']} | {r for u in data['users'] for r in u['allowedRegions']}
    for r in sorted(regions): add('regions', (r,))
    for i,u in enumerate(data['users']):
        add('users',(u['id'],u['name'],u['homeRegion'],i))
        s=u['settings']; add('settings',(u['id'],s['subtitles'],s['audio'],s['autoplay'],0))
    for i,g in enumerate(data['genres']): add('genres',(g['id'],g['name'],i))
    for i,c in enumerate(data['channels']): add('channels',(*[c[k] for k in ['id','name','shortName','region','accent','description']],i))
    for i,m in enumerate(data['mediaAssets']):
        add('media_assets',(*[m[k] for k in ['id','kind','src','poster','durationSeconds']],m.get('sourceNote'),i))
        for j,a in enumerate(m['audioOptions']): add('media_audio_options',(m['id'],a,j))
        for j,t in enumerate(m['subtitleTracks']): add('subtitle_tracks',(m['id'],j,t['label'],t['srclang'],t['src']))
    for i,p in enumerate(data['programs']):
        add('programs',(*[p.get(k) for k in ['id','channelId','title','format','description','availability']],i))
        for j,g in enumerate(p['genreIds']): add('program_genres',(p['id'],g,j))
    for i,e in enumerate(data['episodes']): add('episodes',(*[e[k] for k in ['id','programId','title','season','episode','mediaAssetId','durationMinutes','description']],i))
    for u in data['users']:
        for key,table in [('allowedRegions','allowed_regions'),('favoriteChannelIds','favorite_channels'),('favoriteProgramIds','favorite_programs')]:
            for j,v in enumerate(u[key]): add(table,(u['id'],v,j))
        for j,(g,w) in enumerate(u['genreWeights'].items()): add('genre_weights',(u['id'],g,w,j))
    for i,s in enumerate(data['scheduleItems']):
        add('schedule_items',(*[s[k] for k in ['id','channelId','episodeId','block','start','end','mode']],i))
        for j,day in enumerate(s['days']): add('schedule_days',(s['id'],day,j))
    for i,h in enumerate(data['watchHistory']): add('watch_history',(*[h[k] for k in ['userId','episodeId','watchedSeconds','completed','lastWatchedAt']],i))
    if not db.execute('SELECT 1 FROM users WHERE id=?',(data['currentUserId'],)).fetchone():
        raise ValueError('Invalid currentUserId in seed')
    add('metadata',('default_user',data['currentUserId']))


def initialize(path=None, seed_path=SEED):
    path = Path(path or database_path())
    path.parent.mkdir(parents=True,exist_ok=True)
    db=connect(path)
    try:
        with transaction(db):
            version=db.execute('PRAGMA user_version').fetchone()[0]
            tables=db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            if version==VERSION:
                if db.execute("SELECT value FROM metadata WHERE key='initialized'").fetchone() is None:
                    raise RuntimeError('Incomplete database; restore a backup. No data were overwritten.')
                return path
            if version or tables:
                raise RuntimeError('Unsupported or incomplete database schema; explicit migration is required. No data were overwritten.')
            # executescript implicitly commits: execute complete statements individually instead.
            statement=''
            for line in SCHEMA.read_text().splitlines(True):
                statement+=line
                if sqlite3.complete_statement(statement):
                    db.execute(statement); statement=''
            original=json.loads(Path(seed_path).read_text())
            seed(db,original)
            from .repository import catalog
            restored=catalog(db,include_meta=False)
            if restored!=original:
                raise ValueError('Seed round-trip mismatch: import rolled back')
            if db.execute('PRAGMA foreign_key_check').fetchall(): raise ValueError('Invalid seed relations')
            db.execute("INSERT INTO metadata VALUES ('initialized','1')")
            db.execute(f'PRAGMA user_version={VERSION}')
        return path
    finally:
        db.close()
