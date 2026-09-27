"""Small same-origin HTTP adapter for a reverse proxy on a single VM."""
import importlib.util
import json
import ipaddress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

spec = importlib.util.spec_from_file_location('parent_api', Path(__file__).with_name('index.py'))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class Handler(BaseHTTPRequestHandler):
    server_version = 'MamaHelper'

    def log_message(self, *_args):
        # Request paths and payloads can contain private user data.
        return

    def do_POST(self):
        if self.path != '/api':
            self.send_error(404)
            return
        length = int(self.headers.get('Content-Length', '0'))
        if length < 0 or length > 8_000_000:
            self.send_error(413)
            return
        response = app.handler({
            'httpMethod': 'POST',
            'headers': dict(self.headers),
            'body': self.rfile.read(length).decode('utf-8'),
            'requestContext': {'identity': {'sourceIp': self.visitor_ip()}},
        })
        self.send_response(response['statusCode'])
        for key, value in response['headers'].items():
            self.send_header(key, value)
        self.end_headers()
        self.wfile.write(response['body'].encode('utf-8'))

    def visitor_ip(self):
        # Only the local reverse proxy is trusted, and nginx overwrites X-Real-IP.
        peer = self.client_address[0]
        if peer in ('127.0.0.1', '::1'):
            try:
                return str(ipaddress.ip_address(self.headers.get('X-Real-IP', peer)))
            except ValueError:
                pass
        return peer

    def do_OPTIONS(self):
        if self.path != '/api':
            self.send_error(404)
            return
        response = app.handler({'httpMethod': 'OPTIONS', 'headers': dict(self.headers)})
        self.send_response(response['statusCode'])
        for key, value in response['headers'].items():
            self.send_header(key, value)
        self.end_headers()

    def do_GET(self):
        if self.path != '/healthz':
            self.send_error(404)
            return
        try:
            app.cipher()
            db = app.DB()
            db.query('SELECT 1').fetchone()
            db.close()
            status, body = 200, b'{"ok":true}'
        except Exception:
            status, body = 503, b'{"ok":false}'
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class AppServer(ThreadingHTTPServer):
    request_queue_size = 128
    daemon_threads = True


if __name__ == '__main__':
    app.cipher()
    app.initialize()
    AppServer(('127.0.0.1', 8787), Handler).serve_forever()
