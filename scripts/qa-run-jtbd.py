"""Windows-safe local QA lifecycle; stops only its own process trees."""
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time

app = Path(__file__).resolve().parents[1]
out = app.parent / 'outputs' / 'qa-v3'
out.mkdir(parents=True, exist_ok=True)
node = os.environ.get('MAMA_QA_NODE') or shutil.which('node') or str(Path.home() / '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
servers = [([sys.executable, '-X', 'utf8', str(app/'scripts/qa-isolated-api.py')], 8787),
           ([node, str(app/'node_modules/vite/bin/vite.js'), '--host', '127.0.0.1', '--port', '5173', '--strictPort'], 5173)]
children = []
logs = []


def listening(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=.2):
            return True
    except OSError:
        return False


try:
    for _, port in servers:
        if listening(port):
            raise RuntimeError('QA port already in use: ' + str(port) + '. Existing service was not changed.')
    for command, port in servers:
        log = (out/('server-'+str(port)+'.log')).open('w', encoding='utf-8')
        logs.append(log)
        process = subprocess.Popen(command,cwd=app,stdout=log,stderr=subprocess.STDOUT)
        children.append(process)
        start = time.monotonic()
        while not listening(port):
            if process.poll() is not None or time.monotonic()-start > 30:
                raise RuntimeError('QA server failed to start: ' + str(port) + '. See local log.')
            time.sleep(.1)
    result = subprocess.run([sys.executable, '-X', 'utf8', str(app/'scripts/qa-jtbd-browser.py')],cwd=app)
    sys.exit(result.returncode)
finally:
    for process in reversed(children):
        if process.poll() is None:
            if os.name == 'nt':
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            else:
                process.terminate()
            process.wait(timeout=10)
    for log in logs:
        log.close()
