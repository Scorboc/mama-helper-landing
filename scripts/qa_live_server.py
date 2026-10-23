"""Live isolated QA server (Claude, 22.10.2026): temp DB, AI ON via ProxyAPI (owner allowed payment), closed beta off,
serves app/dist + /api on 127.0.0.1:<port>. Seeds a synthetic account (child «Мия», 5 months).
Credentials -> outputs/qa-ai-20261022/live-account.local.json (local only, never printed). Never touches 8787/real DB.
Usage: python app/scripts/qa_live_server.py [--port 8799]   (runs until killed)
"""
import argparse
import datetime
import http.cookiejar
import importlib.util
import json
import mimetypes
import os
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import unquote, urlsplit

APP = Path(__file__).resolve().parents[1]
ROOT = APP.parent
OUT = ROOT / 'outputs' / 'qa-ai-20261022'
sys.path.insert(0, str(Path(__file__).resolve().parent))


def serve():
    backend = APP / 'backend' / 'parent-app'
    sys.path.insert(0, str(backend))
    spec = importlib.util.spec_from_file_location('qa_local_server', backend / 'local_server.py')
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    mod.app.cipher(); mod.app.initialize()
    from http.server import ThreadingHTTPServer
    web = Path(os.environ.get('QA_WEB_DIR') or (APP / 'dist')).resolve()

    class Handler(mod.Handler):
        def do_GET(self):
            if self.path.split('?')[0] == '/app-config.json':
                data = b'{"apiUrl":"/api"}'; mime = 'application/json'
            else:
                target = (web / unquote(urlsplit(self.path).path).lstrip('/')).resolve()
                if not target.is_relative_to(web):
                    self.send_error(403); return
                if not target.is_file():
                    target = web / 'index.html'
                data = target.read_bytes(); mime = mimetypes.guess_type(target.name)[0] or 'application/octet-stream'
            self.send_response(200); self.send_header('Content-Type', mime); self.send_header('Content-Length', str(len(data)))
            self.end_headers(); self.wfile.write(data)
    ThreadingHTTPServer(('127.0.0.1', int(os.environ['APP_PORT'])), Handler).serve_forever()


def seed(base, age=5, milestones=True):
    jar = http.cookiejar.CookieJar(); op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def api(action, **d):
        req = urllib.request.Request(base + '/api', data=json.dumps(dict(action=action, **d)).encode(), headers={'Content-Type': 'application/json', 'Origin': base})
        with op.open(req, timeout=30) as r:
            return json.load(r)
    email = f'qa-live-{datetime.datetime.now():%H%M%S}@example.test'; password = secrets.token_urlsafe(18)
    s = api('register', email=email, password=password, consent=True)
    t = datetime.date.today(); y, m = divmod(t.year * 12 + t.month - 1 - age, 12)
    # A few days past the monthly anniversary keeps the child safely inside the target month of life.
    birth = datetime.date(y, m + 1, min(t.day, 28)) - datetime.timedelta(days=3)
    st = s['state']; st['profile'] = dict(role='mom', stage='child', childName='Мия', childSex='female', birthDate=birth.isoformat(),
                                          week=20, weekDate=t.isoformat(), feeding='mixed', sleep='', health='', healthConfirmed=False, topics=['play'])

    def after(months, days):  # synthetic date inside the given month of life
        yy, mm = divmod(birth.year * 12 + birth.month - 1 + months, 12)
        return datetime.date(yy, mm + 1, min(birth.day, 28)) + datetime.timedelta(days=days)
    roll_day = after(3, 5)
    # Legacy «открытия» (old list in state.care) incl. one that duplicates the new roll mark — for the year-book adapter.
    st['care'] = {'tasks': [], 'diary': [], 'appointments': [], 'checked': [], 'followups': True, 'achievements': [
        {'id': secrets.token_hex(6), 'date': after(2, 3).isoformat(), 'kind': 'custom', 'note': 'Первый раз купались в большой ванне'},
        {'id': secrets.token_hex(6), 'date': roll_day.isoformat(), 'kind': 'roll', 'note': ''}] if milestones else []}
    api('save', state=st, revision=s['revision'])
    # Synthetic care history so «Последнее» has something to show: feeding (left) 2h10m ago, sleep ended 40 min ago.
    now = datetime.datetime.now(datetime.timezone.utc)
    iso = lambda d: (now - d).replace(microsecond=0).isoformat()
    day_at = lambda d: f'{d.isoformat()}T09:00:00+03:00'
    smile = after(1, 10)
    for rec in ({'id': secrets.token_hex(8), 'kind': 'feeding', 'at': iso(datetime.timedelta(hours=2, minutes=10)), 'side': 'left', 'value': ''},
                {'id': secrets.token_hex(8), 'kind': 'sleep', 'at': iso(datetime.timedelta(hours=2)), 'end': iso(datetime.timedelta(minutes=40)), 'sleepType': 'day'},
                {'id': secrets.token_hex(8), 'kind': 'achievement', 'at': day_at(smile), 'value': 'Первая улыбка', 'note': 'Улыбнулась папе утром'},
                {'id': secrets.token_hex(8), 'kind': 'achievement', 'at': day_at(smile), 'value': 'Первая улыбка', 'note': 'Улыбнулась папе утром'},
                {'id': secrets.token_hex(8), 'kind': 'achievement', 'at': day_at(roll_day), 'skill': 'roll', 'value': 'Переворачивается'}):
        if rec.get('skill') and not milestones:
            continue
        try:
            api('care-put', record=rec)
        except Exception as exc:  # seeding is best-effort; the page still works without history
            print('seed care-put failed:', type(exc).__name__, flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'live-account.local.json').write_text(json.dumps({'email': email, 'password': password, 'base': base}, indent=1), encoding='utf-8')


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--serve', action='store_true'); ap.add_argument('--port', type=int, default=8799)
    ap.add_argument('--web', default='', help='built site folder to serve instead of app/dist')
    ap.add_argument('--age', type=int, default=5, help='synthetic child age in full months')
    ap.add_argument('--no-milestones', action='store_true', help='seed without skill marks (roll)')
    a = ap.parse_args()
    if a.serve:
        return serve()
    if a.port == 8787:
        raise SystemExit('working port forbidden')
    import qa_ai_isolated as q
    with tempfile.TemporaryDirectory(prefix='mama-qa-live-') as tmp:
        env = q.isolated_env(tmp, a.port)
        env['APP_ORIGINS'] = f'http://127.0.0.1:{a.port},http://localhost:{a.port}'
        if a.web:
            env['QA_WEB_DIR'] = str(Path(a.web).resolve())
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', a.port))
        child = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '--serve', '--port', str(a.port)], env=env)
        try:
            base = f'http://127.0.0.1:{a.port}'
            for _ in range(100):
                try:
                    urllib.request.urlopen(base + '/app-config.json', timeout=0.5); break
                except OSError:
                    time.sleep(0.2)
            seed(base, a.age, not a.no_milestones)
            print('READY', base, flush=True)
            child.wait()
        finally:
            child.terminate()


if __name__ == '__main__':
    main()
