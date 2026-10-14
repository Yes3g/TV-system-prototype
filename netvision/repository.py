"""Relational reads and revision-protected writes. JSON is transport only."""
import math
import secrets
from datetime import datetime, timezone
from .database import transaction


class ApiError(Exception):
    def __init__(self,status,message):
        self.status=status
        super().__init__(message)


def rows(db,table):
    return db.execute('SELECT * FROM '+table+' ORDER BY position').fetchall()


def catalog(db,include_meta=True):
    result={'currentUserId':db.execute("SELECT value FROM metadata WHERE key='default_user'").fetchone()[0]}
    mappings={
        'users':('users',{'id':'id','name':'name','homeRegion':'home_region'}),
        'genres':('genres',{'id':'id','name':'name'}),
        'mediaAssets':('media_assets',{'id':'id','kind':'kind','src':'src','poster':'poster','durationSeconds':'duration_seconds'}),
        'channels':('channels',{'id':'id','name':'name','shortName':'short_name','region':'region','accent':'accent','description':'description'}),
        'programs':('programs',{'id':'id','channelId':'channel_id','title':'title','format':'format','description':'description','availability':'availability'}),
        'episodes':('episodes',{'id':'id','programId':'program_id','title':'title','season':'season','episode':'episode','mediaAssetId':'media_asset_id','durationMinutes':'duration_minutes','description':'description'}),
        'scheduleItems':('schedule_items',{'id':'id','channelId':'channel_id','episodeId':'episode_id','block':'block','start':'start','end':'end','mode':'mode'}),
        'watchHistory':('watch_history',{'userId':'user_id','episodeId':'episode_id','watchedSeconds':'watched_seconds','completed':'completed','lastWatchedAt':'last_watched_at'})
    }
    for name,(table,mapping) in mappings.items():
        result[name]=[{key:r[col] for key,col in mapping.items()} for r in rows(db,table)]
    def values(table,column,parent,value):
        return [r[0] for r in db.execute(f'SELECT {column} FROM {table} WHERE {parent}=? ORDER BY position',(value,))]
    for u in result['users']:
        for key,table,col in [('allowedRegions','allowed_regions','region_id'),('favoriteChannelIds','favorite_channels','channel_id'),('favoriteProgramIds','favorite_programs','program_id')]:
            u[key]=values(table,col,'user_id',u['id'])
        s=settings(db,u['id']);u['settings']=s['settings']
        if include_meta:u['settingsRevision']=s['revision']
        u['genreWeights']={r[0]:r[1] for r in db.execute('SELECT genre_id,weight FROM genre_weights WHERE user_id=? ORDER BY position',(u['id'],))}
    for m,r in zip(result['mediaAssets'],rows(db,'media_assets')):
        if r['source_note'] is not None:m['sourceNote']=r['source_note']
        m['audioOptions']=values('media_audio_options','option','media_id',m['id'])
        m['subtitleTracks']=[dict(t) for t in db.execute('SELECT label,srclang,src FROM subtitle_tracks WHERE media_id=? ORDER BY position',(m['id'],))]
    for p in result['programs']:
        p['genreIds']=values('program_genres','genre_id','program_id',p['id'])
        if p['availability'] is None: del p['availability']
    for s in result['scheduleItems']:s['days']=values('schedule_days','day','schedule_id',s['id'])
    for h in result['watchHistory']:h['completed']=bool(h['completed'])
    if include_meta:result['legacyImportDone']=bool(db.execute("SELECT 1 FROM metadata WHERE key='legacy_import'").fetchone())
    return result


def settings(db,user):
    r=db.execute('SELECT * FROM settings WHERE user_id=?',(user,)).fetchone()
    if not r:raise ApiError(404,'Unknown profile')
    return {'settings':{'subtitles':r['subtitles'],'audio':r['audio'],'autoplay':bool(r['autoplay'])},'revision':r['revision']}


def validate_settings(changes):
    if not isinstance(changes,dict) or not changes or set(changes)-{'subtitles','audio','autoplay'}:raise ApiError(400,'Invalid settings fields')
    for k,v in changes.items():
        if k=='autoplay':valid=type(v) is bool
        elif k=='subtitles':valid=v in ('off','en','cs')
        else:valid=v in ('original','cz-dub')
        if not valid:raise ApiError(400,'Invalid '+k)


def update_settings(db,user,body):
    if set(body)!={'revision','settings'} or type(body['revision']) is not int or body['revision']<0:raise ApiError(400,'revision and settings required')
    validate_settings(body['settings'])
    with transaction(db):
        current=settings(db,user)
        if current['revision']!=body['revision']:raise ApiError(409,'Settings changed in another window. Reloaded current values; please retry.')
        changes=body['settings']
        db.execute('UPDATE settings SET '+','.join(k+'=?' for k in changes)+',revision=revision+1 WHERE user_id=?',(*changes.values(),user))
        return settings(db,user)


def import_legacy(db,body):
    if set(body)!={'users'} or not isinstance(body['users'],dict):raise ApiError(400,'Expected users object')
    # Validate all entries before changing anything.
    for uid,entry in body['users'].items():
        if not isinstance(entry,dict) or set(entry)!={'settings'}:raise ApiError(400,'Invalid legacy profile')
        validate_settings(entry['settings'])
    with transaction(db):
        if db.execute("SELECT 1 FROM metadata WHERE key='legacy_import'").fetchone():raise ApiError(409,'Legacy settings were already imported')
        applied=[];skipped=[]
        for uid,entry in body['users'].items():
            r=db.execute('SELECT revision FROM settings WHERE user_id=?',(uid,)).fetchone()
            if not r or r[0]!=0:skipped.append(uid);continue
            changes=entry['settings']
            db.execute('UPDATE settings SET '+','.join(k+'=?' for k in changes)+',revision=revision+1 WHERE user_id=?',(*changes.values(),uid))
            applied.append(uid)
        db.execute("INSERT INTO metadata VALUES ('legacy_import',?)",(datetime.now(timezone.utc).isoformat(),))
        return {'applied':applied,'skipped':skipped}


def start_playback(db,user,episode):
    with transaction(db):
        settings(db,user)
        if not db.execute('SELECT 1 FROM episodes WHERE id=?',(episode,)).fetchone():raise ApiError(404,'Unknown episode')
        token=secrets.token_urlsafe(24)
        # Keep only the newest session for each pair. Old tokens yield 409.
        db.execute('DELETE FROM playback_sessions WHERE user_id=? AND episode_id=?',(user,episode))
        db.execute('INSERT INTO playback_sessions(token,user_id,episode_id) VALUES (?,?,?)',(token,user,episode))
        return {'token':token}


def update_history(db,token,body):
    if set(body)!={'sequence','watchedSeconds','completed'}:raise ApiError(400,'Invalid history fields')
    seq=body['sequence'];pos=body['watchedSeconds'];done=body['completed']
    if type(seq) is not int or seq<1 or type(pos) not in (int,float) or not math.isfinite(pos) or pos<0 or type(done) is not bool:raise ApiError(400,'Invalid playback progress')
    with transaction(db):
        session=db.execute('SELECT * FROM playback_sessions WHERE token=?',(token,)).fetchone()
        if not session or seq<=session['last_seq']:raise ApiError(409,'Stale playback session or sequence')
        db.execute('UPDATE playback_sessions SET last_seq=? WHERE token=?',(seq,token))
        now=datetime.now(timezone.utc).isoformat()
        db.execute('''INSERT INTO watch_history VALUES (?,?,?,?,?,(SELECT COALESCE(MAX(position),-1)+1 FROM watch_history))
            ON CONFLICT(user_id,episode_id) DO UPDATE SET watched_seconds=excluded.watched_seconds,
            completed=excluded.completed,last_watched_at=excluded.last_watched_at''',
            (session['user_id'],session['episode_id'],pos,done,now))
        return {'saved':True,'lastWatchedAt':now}


def history(db,user):
    settings(db,user)
    return [{'episodeId':r['episode_id'],'watchedSeconds':r['watched_seconds'],'completed':bool(r['completed']),'lastWatchedAt':r['last_watched_at']} for r in db.execute('SELECT * FROM watch_history WHERE user_id=? ORDER BY last_watched_at DESC',(user,))]
