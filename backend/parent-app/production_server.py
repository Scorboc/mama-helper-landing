"""Small same-origin HTTP adapter for a reverse proxy on a single VM."""
import importlib.util
import json
import ipaddress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

spec = importlib.util.spec_from_file_location('parent_api', Path(__file__).with_name('index.py'))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class AppServer(ThreadingHTTPServer):
    request_queue_size = 128
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    server_version = 'MamaHelper'

    def log_message(self, *_args):
        # Request paths and payloads can contain private user data.
        return

    def do_POST(self):
        if self.path == '/payment-notification':
            return self.payment_notification()
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

    def payment_notification(self):
        import billing
        from types import SimpleNamespace
        db = None
        status, body = 503, {'error':'Не удалось проверить уведомление.'}
        try:
            length = int(self.headers.get('Content-Length','0'))
            if not 0 < length <= 16000:
                raise app.AppError(400,'Неверный размер уведомления.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data,dict):
                raise app.AppError(400,'Неверное уведомление.')
            db = app.DB()
            # Unknown objects cannot trigger arbitrary provider queries.
            body = billing.webhook(SimpleNamespace(**vars(app)), db, data)
            db.conn.commit()
            status = 200
        except app.AppError as exc:
            if db: db.conn.rollback()
            status, body = exc.status, {'error':exc.message}
        except Exception:
            if db: db.conn.rollback()
        finally:
            if db: db.close()
        encoded = json.dumps(body).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

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


if __name__ == '__main__':
    app.cipher()
    app.initialize()
    import mail_delivery
    mail_delivery.start(app)
    AppServer(('127.0.0.1', 8787), Handler).serve_forever()
