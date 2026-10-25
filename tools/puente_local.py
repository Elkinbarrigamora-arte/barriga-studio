#!/usr/bin/env python3
"""Puente privado de prueba entre el Studio local y Ollama. No edita archivos existentes."""
import argparse
import json
import secrets
import time
import webbrowser
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from drawthings_client import PRESETS, DrawThingsError, build_payload, check_connection, generate_image

HOST = "127.0.0.1"
OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5-coder:14b"
PANEL = r'''
<script>
(()=>{
 const token=__TOKEN__;
 function iniciar(){
   const field=document.getElementById('script');
   if(!field)return;
   const box=document.createElement('div');
   box.style.cssText='padding:14px;margin:12px 0;border:1px solid #ab90ff;border-radius:12px;background:#14122c';
   const title=document.createElement('strong');
   title.textContent='🧠 BARRIGA IA · Guionista local';
   const btn=document.createElement('button');
   btn.type='button';btn.className='button';btn.style.margin='10px';
   btn.textContent='Completar guion con Barriga IA';
   const msg=document.createElement('p');msg.className='muted';msg.setAttribute('role','status');
   msg.textContent='Usa Ollama en tu Mac. No requiere servicios de pago.';
   btn.onclick=async()=>{
     const idea=field.value.trim()||(document.getElementById('name')?.value.trim()||'');
     if(!idea){msg.textContent='Primero escribe una idea o un nombre para tu historia.';return}
     if(field.value.trim()&&!confirm('¿Reemplazar el guion actual? Guarda una copia si necesitas conservarlo.'))return;
     btn.disabled=true;msg.textContent='Barriga IA está creando un guion real...';
     try{
       const resp=await fetch('/api/guion',{method:'POST',headers:{
         'Content-Type':'application/json','X-Barriga-Token':token},
         body:JSON.stringify({idea})});
       const data=await resp.json();
       if(!resp.ok)throw Error(data.error||('Error HTTP '+resp.status));
       field.value='GANCHO\n'+data.gancho+'\n\nHISTORIA\n'+data.historia+
                   '\n\nOFERTA O CIERRE\n'+data.oferta_cierre;
       field.dispatchEvent(new Event('input', { bubbles:true }));
       msg.textContent='Guion generado por '+data.modelo+' en '+data.segundos+
         ' segundos. Revísalo antes de guardarlo.';
     }catch(error){msg.textContent='No se pudo generar: '+error.message}
     finally{btn.disabled=false}
   };
   box.append(title,document.createElement('br'),btn,msg);
   field.parentElement.appendChild(box);
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',iniciar);
 else iniciar();
})();
</script>
'''
IMAGE_PANEL = (
    '<script>window.__BARRIGA_LOCAL_TOKEN__=__TOKEN__;</script>'
    '<script defer src="/assets/drawthings-bridge.js"></script>'
)
def guion(idea, modelo):
    prompt = (
        "Eres guionista cinematográfico de Barriga Studio. Devuelve SOLAMENTE "
        "un objeto JSON válido con tres campos de texto: gancho, historia y oferta_cierre. "
        "Escribe un guion original para video de 30 a 40 segundos, total aproximado "
        "de 75 a 95 palabras. Gancho de 0 a 4 segundos, historia de 4 a 32, "
        "oferta o cierre narrativo de 32 a 40. "
        "No interrumpas la historia para dirigirte al espectador. "
        "Respeta continuidad de personajes y causas. No presentes ficción como hechos. "
        "Idea del usuario: " + idea)
    payload = json.dumps({"model": modelo, "prompt": prompt, "stream": False,
                          "format": "json", "options": {"temperature": 0.7,
                          "num_predict": 550}}).encode("utf-8")
    request = Request(OLLAMA, data=payload, method="POST",
                      headers={"Content-Type": "application/json"})
    started = time.monotonic()
    try:
        with urlopen(request, timeout=180) as response:
            answer = json.loads(json.load(response).get("response", ""))
    except (HTTPError, URLError, TimeoutError, OSError, ValueError, TypeError) as exc:
        raise RuntimeError("Ollama local no respondió con un guion JSON válido: " +
                           type(exc).__name__) from exc
    keys = ("gancho", "historia", "oferta_cierre")
    if not isinstance(answer, dict) or any(not isinstance(answer.get(k), str) or
                                           not answer[k].strip() for k in keys):
        raise RuntimeError("El modelo no generó las tres partes del guion")
    return {k: answer[k].strip() for k in keys} | {
        "modelo": modelo, "segundos": round(time.monotonic()-started, 1)}

def servidor(studio, token, puerto, modelo):
    origin = f"http://{HOST}:{puerto}"
    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, content_type="application/json; charset=utf-8"):
            data = (body if isinstance(body, str) else
                    json.dumps(body, ensure_ascii=False)).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def send_binary(self, data, content_type):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Disposition", "inline")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        def authorized(self):
            return (self.headers.get("Host") == f"{HOST}:{puerto}"
                    and self.headers.get("X-Barriga-Token") == token
                    and self.headers.get("Origin", origin) == origin)
        def do_GET(self):
            if self.headers.get("Host") != f"{HOST}:{puerto}":
                return self.send(403, {"error": "Host no autorizado"})
            route = urlsplit(self.path).path
            if route in ("/", "/index.html"):
                html = (studio/"index.html").read_text(encoding="utf-8")
                injected = (PANEL + IMAGE_PANEL).replace("__TOKEN__", json.dumps(token))
                html = html.replace("</body>", injected + "</body>")
                self.send(200, html, "text/html; charset=utf-8")
            elif route == "/assets/studio-mejoras.js":
                asset = studio / "assets" / "studio-mejoras.js"
                if not asset.is_file():
                    self.send(404, {"error": "Módulo de mejoras no encontrado"})
                else:
                    self.send(200, asset.read_text(encoding="utf-8"),
                              "text/javascript; charset=utf-8")
            elif route.startswith("/assets/"):
                relative = route[len("/assets/"): ]
                if (not relative or "/" in relative or "\\" in relative or
                    relative.startswith(".") or not relative.endswith((".js", ".css"))):
                    return self.send(404, {"error": "Ruta desconocida"})
                asset = studio / "assets" / relative
                if not asset.is_file():
                    return self.send(404, {"error": "Recurso no encontrado"})
                content_type = ("text/javascript; charset=utf-8" if relative.endswith(".js")
                                else "text/css; charset=utf-8")
                self.send(200, asset.read_text(encoding="utf-8"), content_type)
            elif route == "/api/health":
                self.send(200, {"servidor": "OK", "modelo_solicitado": modelo,
                                "inferencia_real_comprobada": False,
                                "video_neuronal_comprobado": False})
            elif route == "/api/drawthings/perfiles":
                if not self.authorized():
                    return self.send(403, {"error": "No autorizado"})
                self.send(200, {"perfiles": PRESETS})
            elif route == "/api/drawthings/estado":
                if not self.authorized():
                    return self.send(403, {"error": "No autorizado"})
                try:
                    self.send(200, check_connection())
                except DrawThingsError as exc:
                    self.send(502, {"error": str(exc)})
            else:
                self.send(404, {"error": "Ruta desconocida"})
        def do_POST(self):
            if self.path not in ("/api/guion", "/api/drawthings/generar"):
                return self.send(404, {"error": "Ruta desconocida"})
            if self.headers.get("Origin") != origin or not self.authorized():
                return self.send(403, {"error": "Origen o token no autorizado"})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.send(415, {"error": "Se requiere JSON"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 1 <= size <= 8000:
                    return self.send(413, {"error": "Solicitud demasiado grande"})
                args = json.loads(self.rfile.read(size))
                if self.path == "/api/drawthings/generar":
                    payload = build_payload(args)
                    image, content_type = generate_image(payload)
                    return self.send_binary(image, content_type)
                idea = args.get("idea", "")
                if not isinstance(idea, str) or not 2 <= len(idea.strip()) <= 2400:
                    return self.send(400, {"error": "Escribe una idea entre 2 y 2400 caracteres"})
                self.send(200, guion(idea.strip(), modelo))
            except (ValueError, TypeError) as exc:
                self.send(400, {"error": str(exc)[:200]})
            except DrawThingsError as exc:
                self.send(502, {"error": str(exc)})
            except RuntimeError as exc:
                self.send(502, {"error": str(exc)})
    return Handler

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--studio",type=Path,default=Path.cwd())
    parser.add_argument("--puerto",type=int,default=8766)
    parser.add_argument("--modelo",default=MODEL)
    parser.add_argument("--sin-navegador",action="store_true")
    args=parser.parse_args()
    carpeta=args.studio.expanduser().resolve()
    if not (carpeta/"index.html").is_file():
        parser.error("No se encontró index.html en "+str(carpeta))
    if not 1024 <= args.puerto <= 65535:
        parser.error("Puerto inválido")
    with ThreadingHTTPServer((HOST,args.puerto),servidor(carpeta,
             secrets.token_urlsafe(32),args.puerto,args.modelo)) as http:
        url=f"http://{HOST}:{args.puerto}/"
        print("Barriga Studio + IA: "+url,flush=True)
        print("Solo se escucha en 127.0.0.1; la versión original no se modifica.",flush=True)
        print("Ctrl+C detiene la prueba. No activa tareas nocturnas.",flush=True)
        if not args.sin_navegador:
            webbrowser.open(url)
        try: http.serve_forever()
        except KeyboardInterrupt: print("Prueba detenida.")

if __name__=="__main__":
    main()
