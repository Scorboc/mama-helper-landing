"""Explicit loopback-only test server. Not a production web server."""
import importlib.util
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

os.environ['APP_LOCAL']='1'
spec=importlib.util.spec_from_file_location('parent_api',Path(__file__).with_name('index.py'))
app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)

class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def do_POST(self):
        length=int(self.headers.get('Content-Length','0'))
        if length>150000:self.send_error(413);return
        response=app.handler({'httpMethod':'POST','headers':dict(self.headers),'body':self.rfile.read(length).decode(),'requestContext':{'identity':{'sourceIp':self.client_address[0]}}})
        self.send_response(response['statusCode'])
        for k,v in response['headers'].items():self.send_header(k,v)
        self.end_headers();self.wfile.write(response['body'].encode())
    def do_OPTIONS(self):
        response=app.handler({'httpMethod':'OPTIONS','headers':dict(self.headers)})
        self.send_response(response['statusCode'])
        for k,v in response['headers'].items():self.send_header(k,v)
        self.end_headers()

if __name__=='__main__':
    app.cipher();app.initialize();print('Local account server: 127.0.0.1:8787')
    ThreadingHTTPServer(('127.0.0.1',8787),Handler).serve_forever()
