#!/usr/bin/env python3
"""Explicit offline maintenance. Stop the server before restore/reset."""
import argparse
from contextlib import closing
from datetime import datetime,timezone
from pathlib import Path
import sqlite3
from netvision.database import initialize,connect,database_path,transaction,VERSION


def backup(source,destination):
    if not source.is_file():raise ValueError('Source database does not exist')
    if destination.exists():raise ValueError('Backup destination already exists')
    destination.parent.mkdir(parents=True,exist_ok=True)
    with closing(connect(source)) as src,closing(sqlite3.connect(destination)) as dst:src.backup(dst)


def check(path):
    if not path.is_file():raise ValueError('Database does not exist')
    with closing(connect(path)) as db:
        if db.execute('PRAGMA user_version').fetchone()[0]!=VERSION:raise ValueError('Unsupported schema')
        if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Invalid database')
        if not db.execute("SELECT 1 FROM metadata WHERE key='initialized'").fetchone():raise ValueError('Incomplete database')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('init');sub.add_parser('check')
    b=sub.add_parser('backup');b.add_argument('destination',type=Path)
    r=sub.add_parser('restore');r.add_argument('source',type=Path);r.add_argument('--yes',action='store_true')
    r=sub.add_parser('reset');r.add_argument('--yes',action='store_true')
    m=sub.add_parser('set-media');m.add_argument('media_id');m.add_argument('relative_path',help='Path within project media/, e.g. media/film.mp4')
    args=parser.parse_args();path=database_path()
    if args.command=='init':print(initialize());return
    if args.command=='check':check(path);print('Integrity and foreign keys OK');return
    if args.command=='backup':backup(path,args.destination);print(args.destination);return
    if args.command=='set-media':
        from netvision.database import ROOT
        value=Path(args.relative_path)
        target=(ROOT/value).resolve()
        if value.is_absolute() or not target.is_relative_to((ROOT/'media').resolve()) or not target.is_file() or target.suffix.lower() not in ('.mp4','.webm','.ogg','.ogv'):raise ValueError('Use an existing supported video within media/')
        from urllib.parse import quote
        with closing(connect(path)) as db,transaction(db):
            cur=db.execute('UPDATE media_assets SET src=? WHERE id=?',(quote(target.relative_to(ROOT).as_posix(),safe='/'),args.media_id))
            if not cur.rowcount:raise ValueError('Unknown media ID')
        print('Media URL updated; reload the application.');return
    if not args.yes:raise ValueError('Stop server first. This replaces data; pass --yes explicitly. A backup is always created.')
    if args.command=='restore':check(args.source)
    if path.exists():
        destination=path.with_name(path.name+'.backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ'))
        backup(path,destination);print('Backup:',destination)
    temp=path.with_name(path.name+'.replacement')
    if temp.exists():raise ValueError('Replacement file already exists; inspect it before retrying')
    if args.command=='restore':backup(args.source,temp)
    else:initialize(temp)
    check(temp)
    # Stop the server before this operation; no active connections or WAL files allowed.
    for suffix in ('-wal','-shm','-journal'):
        if Path(str(path)+suffix).exists():raise ValueError('Database sidecar present. Stop server and resolve it before replacing the database.')
    temp.replace(path);print('Database replaced.')

if __name__=='__main__':
    try:main()
    except Exception as e:raise SystemExit(str(e))
