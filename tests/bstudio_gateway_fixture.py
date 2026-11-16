#!/usr/bin/env python3
"""Offline fixture for B STUDIOS ÉLITE's actual /studio one-origin overlay QA.

This is only a CI fixture. It NEVER deploys, starts Ollama or contacts PoYo.
"""
import json
import secrets
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
from bstudio_elite_gateway import make_gateway_handler

UPSTREAM_PORT=18882
FRONT_PORT=18866

class ExistingCentral(BaseHTTPRequestHandler):
    projects=[]
    def log_message(self,*args):pass
    def reply(self,status,body,content_type="application/json"):
        self.send_response(status)
        self.send_header("Content-Type",content_type)
        self.send_header("Content-Length",str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def do_GET(self):
        if self.path=="/studio":
            page='''<!doctype html><html lang="es"><head>
<title>B STUDIOS ÉLITE — Producción activa</title></head><body>
<main><header><h1>B STUDIOS ÉLITE</h1></header>
<section id="crear"><h2>Estudio central original</h2>
<label for="script">Guion original</label>
<textarea id="script"></textarea>
<button id="old-save" onclick="document.querySelector('#old-status').textContent='Proyecto original conservado';localStorage.setItem('original-demo','OK')">
Guardar proyecto original</button>
<p id="old-status"></p></section>
<a href="/api/legacy-health" id="old-api">Ver API original</a>
</main></body></html>'''
            return self.reply(200,page.encode("utf-8"),"text/html; charset=utf-8")
        if self.path=="/api/legacy-health":
            return self.reply(200,b'{"legacy":true}')
        if self.path=="/api/projects":
            return self.reply(200,json.dumps({"projects":self.projects}).encode("utf-8"))
        return self.reply(404,b'{"error":"old route not found"}')
    def do_POST(self):
        n=int(self.headers.get("Content-Length","0"))
        if self.path=="/api/projects":
            data=self.rfile.read(n)
            self.projects.append(json.loads(data))
            return self.reply(200,b'{"saved":true}')
        return self.reply(404,b'{"error":"old route not found"}')

def main():
    with tempfile.TemporaryDirectory(prefix="bstudio-elite-ci-") as temp:
        media=Path(temp)/"media"
        media.mkdir()
        runtime=ROOT/"assets"/"bstudio-runtime.js"
        token=secrets.token_urlsafe(32)
        with ThreadingHTTPServer(("127.0.0.1",UPSTREAM_PORT),ExistingCentral) as old, \
             ThreadingHTTPServer(
                 ("127.0.0.1",FRONT_PORT),
                 make_gateway_handler(media,runtime,token,FRONT_PORT,
                                      UPSTREAM_PORT,"auto",None)
             ) as gateway:
            work=threading.Thread(target=old.serve_forever,daemon=True)
            work.start()
            print("CI fixture for sole /studio ready",flush=True)
            try:
                gateway.serve_forever()
            except KeyboardInterrupt:
                pass
            finally:
                old.shutdown()
                work.join(2)

if __name__=="__main__":main()
