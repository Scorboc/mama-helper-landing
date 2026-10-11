"""Owner panel accessible only through an SSH loopback tunnel."""
import json
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import operations as ops
import ops_job
import ai_budget

HOSTS={'127.0.0.1:18791','localhost:18791','127.0.0.1:8791','localhost:8791'}


class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass

    def allowed(self,write=False):
        host=self.headers.get('Host','')
        if host not in HOSTS or self.headers.get('Sec-Fetch-Site')=='cross-site':return False
        return not write or (self.headers.get('Origin')=='http://'+host and self.headers.get('Content-Type')=='application/json')

    def send(self,status,body,kind='application/json'):
        data=(json.dumps(body,ensure_ascii=False) if kind=='application/json' else body).encode()
        self.send_response(status);self.send_header('Content-Type',kind+'; charset=utf-8')
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'")
        self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)

    def do_GET(self):
        if not self.allowed():return self.send(403,{'error':'Доступ только через локальный SSH-туннель'})
        try:
            if self.path=='/':return self.send(200,Path(__file__).with_name('ops.html').read_text(encoding='utf-8'),'text/html')
            if self.path=='/ops.js':return self.send(200,Path(__file__).with_name('ops.js').read_text(encoding='utf-8'),'text/javascript')
            if self.path=='/data':
                data=ops.summary();data['feedback']=ops_job.feedback_summary()
                data['aiBudget']=ai_budget.summary()
                data['content']=ops.documents('content');data['tasks']=ops.documents('task')
                path=ops_job.ROOT/'backup-status.json';data['backup']=json.loads(path.read_text()) if path.exists() else None
                reports=ops_job.ROOT/'reports';data['reports']=[p.name for p in sorted(reports.glob('week-*.json'))[-12:]]
                return self.send(200,data)
            return self.send(404,{'error':'Не найдено'})
        except Exception:return self.send(503,{'error':'Не удалось загрузить данные'})

    def do_POST(self):
        if not self.allowed(True):return self.send(403,{'error':'Запрос отклонён'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=16000:return self.send(400,{'error':'Слишком большой запрос'})
            body=json.loads(self.rfile.read(length))
            if self.path in ('/content','/task'):return self.send(200,ops.document(self.path[1:],body))
            if self.path=='/report':return self.send(200,ops_job.report())
            if self.path=='/ai-policy':return self.send(200,ai_budget.write_policy(body))
            return self.send(404,{'error':'Не найдено'})
        except ValueError as exc:return self.send(400,{'error':str(exc)[:160]})
        except Exception:return self.send(503,{'error':'Не удалось сохранить'})


if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',8791),Handler).serve_forever()
