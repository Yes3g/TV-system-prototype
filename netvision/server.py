"""Loopback HTTP API and allowlisted public files; no database downloads."""
import json
import hashlib
import mimetypes
import secrets
import socket
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, unquote
from .database import ROOT, connect
from . import repository as repo

APP_ID='netvision-sqlite-v1'
INSTANCE_ID=hashlib.sha256(str(ROOT.resolve()).encode()).hexdigest()[:20]
PUBLIC={'/':'index.html','/index.html':'index.html','/app.js':'app.js','/persistence.js':'persistence.js','/styles.css':'styles.css'}


class Handler(BaseHTTPRequestHandler):
    protocol_version='HTTP/1.1'

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def log_message(self,format,*args):
        print('%s - %s'%(self.address_string(),format%args))

    def reply(self,status,payload):
        raw=json.dumps(payload,ensure_ascii=False,allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        if self.command!='HEAD':self.wfile.write(raw)

    def authority(self):
        host=self.headers.get('Host','')
        allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}',f'[::1]:{self.server.server_port}'}
        if host not in allowed:raise repo.ApiError(403,'Invalid Host')
        origin=self.headers.get('Origin')
        if origin and origin!='http://'+host:raise repo.ApiError(403,'Cross-origin request rejected')

    def body(self):
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise repo.ApiError(415,'Use application/json')
        if self.headers.get('Transfer-Encoding'):raise repo.ApiError(400,'Chunked requests are unsupported')
        try:n=int(self.headers.get('Content-Length','0'))
        except ValueError:raise repo.ApiError(400,'Invalid content length')
        if not 0<n<=65536:raise repo.ApiError(413,'Request body must be 1–65536 bytes')
        try:
            data=json.loads(self.rfile.read(n),parse_constant=lambda v: (_ for _ in ()).throw(ValueError(v)))
        except (ValueError,UnicodeError):raise repo.ApiError(400,'Invalid JSON')
        if not isinstance(data,dict):raise repo.ApiError(400,'Expected JSON object')
        return data

    def dispatch(self):
        # Close request connections deliberately; avoids unread malformed-body reuse.
        self.close_connection=True
        try:
            self.authority()
            path=unquote(urlsplit(self.path).path)
            if not path.startswith('/api/'):
                if self.command not in ('GET','HEAD'):raise repo.ApiError(405,'Method not allowed')
                return self.static(path)
            if self.command in ('POST','PATCH','PUT','DELETE'):
                if not secrets.compare_digest(self.headers.get('X-NetVision-Token',''),self.server.csrf_token):raise repo.ApiError(403,'Missing or invalid application token')
                body=self.body()
            else:body=None
            if path=='/api/health' and self.command=='GET':return self.reply(200,{'application':APP_ID,'instance':INSTANCE_ID})
            db=connect(self.server.db_path)
            try:
                parts=path.strip('/').split('/')
                if path=='/api/bootstrap' and self.command=='GET':
                    # One consistent snapshot across all relation queries.
                    db.execute('BEGIN')
                    data=repo.catalog(db);db.commit()
                    data['apiToken']=self.server.csrf_token
                    return self.reply(200,data)
                if path=='/api/legacy-settings' and self.command=='POST':return self.reply(200,repo.import_legacy(db,body))
                if len(parts)==4 and parts[1]=='users' and parts[3]=='settings':
                    if self.command=='GET':return self.reply(200,repo.settings(db,parts[2]))
                    if self.command=='PATCH':return self.reply(200,repo.update_settings(db,parts[2],body))
                    raise repo.ApiError(405,'Method not allowed')
                if len(parts)==4 and parts[1]=='users' and parts[3]=='history' and self.command=='GET':return self.reply(200,repo.history(db,parts[2]))
                if path=='/api/playback-sessions' and self.command=='POST':
                    if set(body)!={'userId','episodeId'} or not all(isinstance(v,str) for v in body.values()):raise repo.ApiError(400,'userId and episodeId required')
                    return self.reply(201,repo.start_playback(db,body['userId'],body['episodeId']))
                if len(parts)==3 and parts[1]=='playback-sessions' and self.command=='PUT':return self.reply(200,repo.update_history(db,parts[2],body))
                raise repo.ApiError(404,'Unknown API route')
            finally:db.close()
        except (BrokenPipeError,ConnectionResetError):return
        except repo.ApiError as e:self.reply(e.status,{'error':str(e)})
        except sqlite3.IntegrityError:self.reply(400,{'error':'Database constraint rejected these values'})
        except sqlite3.Error as e:
            self.log_error('Database error: %s',e)
            self.reply(503,{'error':'Database unavailable. No save was confirmed. Check the server log and retry.'})
        except (OSError,ValueError,TypeError) as e:
            self.log_error('Request error: %s',e)
            self.reply(400,{'error':'Invalid request or unavailable file'})

    def static(self,path):
        root=ROOT.resolve()
        if path in PUBLIC:
            relative=Path(PUBLIC[path])
        elif path.startswith('/captions/') or path.startswith('/media/'):
            relative=Path(path.lstrip('/'))
            if relative.suffix.lower() not in {'.mp4','.webm','.ogg','.ogv','.vtt','.jpg','.jpeg','.png','.webp'}:
                raise repo.ApiError(404,'File type not public')
        else:raise repo.ApiError(404,'File not public')
        if '..' in relative.parts:raise repo.ApiError(403,'Invalid file path')
        current=root
        for part in relative.parts:
            current=current/part
            if current.is_symlink():raise repo.ApiError(403,'Symlinks are not public')
        target=(root/relative).resolve()
        if not target.is_relative_to(root):raise repo.ApiError(403,'File outside public directory')
        if not target.is_file():raise repo.ApiError(404,'Media or file not found')
        size=target.stat().st_size;start=0;end=size-1;status=200
        byte_range=self.headers.get('Range')
        if byte_range:
            import re
            match=re.fullmatch(r'bytes=(\d*)-(\d*)',byte_range)
            if not match or not any(match.groups()):raise repo.ApiError(416,'Unsupported byte range')
            a,b=match.groups()
            if a:start=int(a);end=min(int(b),end) if b else end
            else:start=max(0,size-int(b))
            if start>end or start>=size:
                self.send_response(416);self.send_header('Content-Range',f'bytes */{size}');self.send_header('Content-Length','0');self.end_headers();return
            status=206
        length=max(0,end-start+1)
        self.send_response(status)
        self.send_header('Content-Type',mimetypes.guess_type(target.name)[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(length));self.send_header('Accept-Ranges','bytes')
        self.send_header('X-Content-Type-Options','nosniff')
        if status==206:self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.end_headers()
        if self.command!='HEAD':
            with target.open('rb') as f:
                f.seek(start)
                while length:
                    data=f.read(min(length,65536))
                    if not data:break
                    self.wfile.write(data);length-=len(data)

    do_GET=do_HEAD=do_POST=do_PATCH=do_PUT=do_DELETE=dispatch


class LocalServer(ThreadingHTTPServer):
    daemon_threads=True


def make_server(host,port,path):
    cls=LocalServer
    if ':' in host:
        class IPv6Server(LocalServer):address_family=socket.AF_INET6
        cls=IPv6Server
    server=cls((host,port),Handler)
    server.db_path=Path(path)
    server.csrf_token=secrets.token_urlsafe(32)
    return server
