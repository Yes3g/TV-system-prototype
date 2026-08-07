#!/usr/bin/env python3
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import subprocess
import sys
import time
import urllib.request


APP_DIR = Path(__file__).resolve().parent
HOST = "::1"
FALLBACK_HOST = "127.0.0.1"
PORTS = [4173, 4180, 5173, 8000, 8080]
STATE_FILE = APP_DIR / ".netvision-url"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args))


class DualStackServer(ThreadingHTTPServer):
    address_family = socket.AF_INET6


def try_server(host, port):
    handler = partial(QuietHandler, directory=str(APP_DIR))
    server_class = DualStackServer if ":" in host else ThreadingHTTPServer
    return server_class((host, port), handler)


def open_browser(url):
    try:
        subprocess.run(["open", url], check=False)
    except Exception:
        pass


def url_for(host, port):
    url_host = f"[{host}]" if ":" in host else host
    return f"http://{url_host}:{port}/"


def responds(url):
    try:
        with urllib.request.urlopen(url, timeout=0.7) as response:
            return response.status < 500
    except Exception:
        return False


def run_server(host, port, announce=True):
    server = try_server(host, port)
    url = url_for(host, port)
    STATE_FILE.write_text(url)
    if announce:
        print("")
        print("NetVision prototype is running.")
        print(f"Open: {url}")
        print("")
        print("Keep this window open while using the prototype.")
        print("Press Ctrl+C to stop the server.")
        print("")
    open_browser(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    return 0


def foreground():
    for host in (HOST, FALLBACK_HOST):
        for port in PORTS:
            try:
                return run_server(host, port)
            except OSError:
                continue

    print("Could not start NetVision: no local preview port was available.")
    print("Try closing other local servers and run this file again.")
    return 1


def start_background():
    if STATE_FILE.exists():
        previous_url = STATE_FILE.read_text().strip()
        if previous_url and responds(previous_url):
            open_browser(previous_url)
            return 0

    for host in (HOST, FALLBACK_HOST):
        for port in PORTS:
            url = url_for(host, port)
            if responds(url):
                STATE_FILE.write_text(url)
                open_browser(url)
                return 0
            try:
                try_server(host, port).server_close()
            except OSError:
                continue

            subprocess.Popen(
                [sys.executable, str(Path(__file__).resolve()), "--serve", host, str(port)],
                cwd=str(APP_DIR),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            for _ in range(20):
                if responds(url):
                    STATE_FILE.write_text(url)
                    open_browser(url)
                    return 0
                time.sleep(0.15)

    open_browser(str((APP_DIR / "index.html").resolve()))
    return 1


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "--serve":
        return run_server(sys.argv[2], int(sys.argv[3]), announce=False)
    if len(sys.argv) == 2 and sys.argv[1] == "--background":
        return start_background()
    return foreground()


if __name__ == "__main__":
    sys.exit(main())
