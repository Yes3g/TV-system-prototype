"""Finder launcher: keep LAN server alive until the user closes its dialog."""
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser
from netvision.server import APP_ID, INSTANCE_ID

ROOT = Path(__file__).resolve().parent

def dialog(message, button='OK'):
    script = 'on run argv\n display dialog (item 1 of argv) buttons {item 2 of argv} default button 1\nend run'
    subprocess.run(['/usr/bin/osascript', '-e', script, message, button], check=True)

def address():
    for interface in ('en0', 'en1', 'en2'):
        result = subprocess.run(['/usr/sbin/ipconfig', 'getifaddr', interface], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    raise RuntimeError('Připojte Mac k Wi-Fi. Nepodařilo se zjistit adresu místní sítě.')

def healthy(url):
    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        with opener.open(url+'api/health', timeout=.4) as response:
            data = json.load(response)
            return data.get('application') == APP_ID and data.get('instance') == INSTANCE_ID
    except (OSError, ValueError):
        return False

def main():
    child = None
    try:
        host = address()
        url = 'http://'+host+':4174/'
        if healthy(url):
            webbrowser.open(url)
            dialog('NetVision již běží. Na telefonu ve stejné Wi-Fi otevřete v Safari:\n'+url+'\n\nServer spravuje původní spouštěč.')
            return
        (ROOT/'var').mkdir(exist_ok=True)
        with (ROOT/'var'/'lan-server.log').open('ab') as log:
            child = subprocess.Popen([sys.executable, str(ROOT/'start_server.py'), '--lan', host],
                cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=log,
                env={**os.environ, 'NETVISION_NO_BROWSER':'1'})
        for _ in range(80):
            if child.poll() is not None:
                raise RuntimeError('Server se nespustil. Podrobnosti: var/lan-server.log. Port 4174 může používat jiná aplikace.')
            if healthy(url):break
            time.sleep(.1)
        else:raise RuntimeError('Server včas neodpověděl. Podrobnosti: var/lan-server.log.')
        webbrowser.open(url)
        dialog('NetVision běží. Na iPhonu/iPadu ve stejné Wi-Fi otevřete v Safari:\n\n'+url+'\n\nToto okno ponechte otevřené. Tlačítkem server vypnete.', 'Zastavit server')
    except Exception as error:
        dialog(str(error))
    finally:
        if child is not None and child.poll() is None:
            child.terminate()
            try:child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                child.kill();child.wait()

if __name__ == '__main__':main()
