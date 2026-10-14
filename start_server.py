#!/usr/bin/env python3
"""Start the local SQLite-backed NetVision application."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser
from netvision.database import ROOT, initialize
from netvision.server import APP_ID, INSTANCE_ID, make_server

HOSTS=('::1','127.0.0.1')
PORTS=(4173,4180,5173,8000,8080)
STATE=ROOT/'var'/'.netvision-url'


def url_for(host,port):return f'http://[{host}]:{port}/' if ':' in host else f'http://{host}:{port}/'


def responds(url):
    from urllib.parse import urlsplit
    try:
        u=urlsplit(url)
        if u.scheme!='http' or u.hostname not in ('localhost','127.0.0.1','::1') or u.port not in PORTS:return False
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url.rstrip('/')+'/api/health',timeout=0.7) as r:
            data=json.load(r)
            return r.status==200 and data.get('application')==APP_ID and data.get('instance')==INSTANCE_ID
    except Exception:return False


def open_browser(url):
    if not os.environ.get('NETVISION_NO_BROWSER'):webbrowser.open(url)


def serve(host,port):
    db_path=initialize()
    server=make_server(host,port,db_path)
    url=url_for(host,server.server_port)
    STATE.parent.mkdir(exist_ok=True);STATE.write_text(url)
    print(f'NetVision SQLite: {url}\nDatabase: {db_path}\nKeep this server running. Ctrl+C stops it.',flush=True)
    open_browser(url)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
    return 0


def background():
    if STATE.exists() and responds(STATE.read_text().strip()):
        open_browser(STATE.read_text().strip());return 0
    for host in HOSTS:
        for port in PORTS:
            url=url_for(host,port)
            if responds(url):open_browser(url);return 0
            # Bind probe only: SQLite initialization belongs to the child.
            try:make_server(host,port,Path('unused')).server_close()
            except OSError:continue
            STATE.parent.mkdir(exist_ok=True)
            with (STATE.parent/'server.log').open('ab') as log:
                child=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--serve',host,str(port)],cwd=ROOT,
                    stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
            for _ in range(40):
                if responds(url):return 0
                if child.poll() is not None:break
                time.sleep(.15)
    print('NetVision could not start. Read var/server.log. Python server is required; file mode is unsupported.',file=sys.stderr)
    return 1


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--background',action='store_true')
    parser.add_argument('--serve',nargs=2,metavar=('HOST','PORT'))
    args=parser.parse_args()
    try:
        if args.background:return background()
        if args.serve:
            host,port=args.serve
            if host not in HOSTS:parser.error('Only loopback hosts are supported')
            return serve(host,int(port))
        # Initialize before port selection: DB failures must not look like port conflicts.
        initialize()
        for host in HOSTS:
            for port in PORTS:
                try:return serve(host,port)
                except OSError:continue
        print('No local port available.',file=sys.stderr);return 1
    except Exception as e:
        print(f'NetVision startup failed: {e}\nDatabase was not reset. Check permissions or restore a backup.',file=sys.stderr)
        return 1

if __name__=='__main__':sys.exit(main())
