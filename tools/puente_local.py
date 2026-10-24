#!/usr/bin/env python3
"""Puente privado de prueba entre el Studio local y Ollama. No edita archivos existentes."""
import argparse
import json
import sqlite3
import secrets
import time
import webbrowser
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from barriga_ia_narrativa import ErrorNarrativa
from barriga_ia_servicio_local import (
    ejecutar_motor, guardar_generacion, listar_generaciones,
    abrir_generacion, inicializar,
)

HOST = "127.0.0.1"
OLLAMA = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen2.5-coder:14b"
PANEL = r'''
<script>
(()=>{
 const token=__TOKEN__;
 const cabeceras={'X-Barriga-Token':token};
 let ultima=null;
 function iniciar(){
   const field=document.getElementById('script');
   if(!field)return;
   const box=document.createElement('div');
   box.style.cssText='padding:14px;margin:12px 0;border:1px solid #ab90ff;border-radius:12px;background:#14122c';
   const title=document.createElement('strong');
   title.textContent='🧠 BARRIGA IA · Guionista local verificado';
   const btn=document.createElement('button');
   btn.type='button';btn.className='button';btn.style.margin='10px';
   btn.textContent='Generar y validar guion';
   const msg=document.createElement('p');msg.className='muted';msg.setAttribute('role','status');
   msg.textContent='Motor narrativo local por bloques. Requiere Ollama encendido.';
   const historial=document.createElement('select');
   historial.setAttribute('aria-label','Generaciones locales guardadas');
   const recuperar=document.createElement('button');
   recuperar.type='button';recuperar.className='button ghost';recuperar.style.margin='8px';
   recuperar.textContent='Recuperar guion';
   function cargarGuion(data){
      const guion=data.guion||{};
      const partes=['GANCHO',guion.gancho||'','', 'HISTORIA',guion.historia||'',
                    '', 'CIERRE',guion.cierre||''];
      field.value=partes.join('\n');
      field.dispatchEvent(new Event('input',{bubbles:true}));
      ultima=data.id;
      const msgEstado=data.apto_para_revision_humana ?
        'APTO PARA REVISION HUMANA (no publicado).' :
        'BORRADOR RECHAZADO O INCOMPLETO; revisar antes de utilizar.';
      msg.textContent=msgEstado+' ID: '+data.id+'. Estado: '+data.estado+'.';
   }
   async function refrescar(){
      const resp=await fetch('/api/historial',{headers:cabeceras});
      if(!resp.ok)throw Error('No se pudo consultar el historial');
      const data=await resp.json();
      historial.replaceChildren();
      for(const row of data.generaciones){
         const op=document.createElement('option');
         op.value=row.id;
         op.textContent=row.titulo+' · '+row.estado+' · '+row.fecha;
         historial.append(op);
      }
      if(ultima)historial.value=ultima;
   }
   btn.onclick=async()=>{
      const idea=field.value.trim()||(document.getElementById('name')?.value.trim()||'');
      if(!idea){msg.textContent='Primero escribe una idea o un nombre.';return}
      if(field.value.trim()&&!confirm('¿Reemplazar lo que hay en el editor? Guarda el proyecto antes.'))return;
      btn.disabled=true;msg.textContent='Ollama está generando y revisando los tres bloques...';
      try{
         const resp=await fetch('/api/guion',{method:'POST',headers:{
              ...cabeceras,'Content-Type':'application/json'},
              body:JSON.stringify({idea})});
         const data=await resp.json();
         if(!resp.ok)throw Error(data.error||('Error HTTP '+resp.status));
         cargarGuion(data);
         await refrescar();
      }catch(e){msg.textContent='Error: '+e.message}
      finally{btn.disabled=false}
   };
   recuperar.onclick=async()=>{
      const id=historial.value;
      if(!id)return;
      if(field.value.trim()&&!confirm('¿Cargar esta versión guardada? El texto sin guardar será reemplazado.'))return;
      try{
        const resp=await fetch('/api/guion/'+encodeURIComponent(id),{headers:cabeceras});
        const data=await resp.json();
        if(!resp.ok)throw Error(data.error||'No encontrada');
        cargarGuion(data);
      }catch(e){msg.textContent='No se pudo recuperar: '+e.message}
   };
   box.append(title,document.createElement('br'),btn,msg,historial,recuperar);
   field.parentElement.appendChild(box);
   refrescar().catch(e=>{msg.textContent='Historial no disponible: '+e.message});
 }
 if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',iniciar);
 else iniciar();
})();
</script>
'''


def presentar_generacion(resultado, ident):
    guion = resultado.get("guion") or {}
    return {
        "id": ident,
        "gancho": guion.get("gancho", ""),
        "historia": guion.get("historia", ""),
        "oferta_cierre": guion.get("cierre", ""),
        "guion": {
            "titulo": guion.get("titulo", ""),
            "gancho": guion.get("gancho", ""),
            "historia": guion.get("historia", ""),
            "cierre": guion.get("cierre", ""),
        },
        "estado": resultado.get("estado", "INCOMPLETO"),
        "apto_para_revision_humana": resultado.get(
            "apto_para_revision_humana", False),
        "aprobacion_humana": False,
        "publicacion_automatica_autorizada": False,
        "modelo": resultado.get("modelo", ""),
        "segundos": resultado.get("segundos_inferencia", 0),
    }


def guion(idea, modelo, db):
    """Una única ruta de narrativa por bloques + informe persistente."""
    resultado = ejecutar_motor(idea, modelo=modelo)
    ident = guardar_generacion(resultado, db=db)
    return presentar_generacion(resultado, ident)


def servidor(studio, token, puerto, modelo, db):
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
        def do_GET(self):
            route = urlsplit(self.path).path
            if route in ("/", "/index.html"):
                html = (studio/"index.html").read_text(encoding="utf-8")
                html = html.replace("</body>", PANEL.replace("__TOKEN__",
                                      json.dumps(token))+"</body>")
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
                                "motor_narrativo_por_bloques": True,
                                "almacenamiento_local": True,
                                "video_neuronal_comprobado": False})
            elif route == "/api/historial" or route.startswith("/api/guion/"):
                if self.headers.get("X-Barriga-Token") != token:
                    return self.send(403, {"error": "Token no autorizado"})
                if route == "/api/historial":
                    return self.send(200, {"generaciones": listar_generaciones(db)})
                ident = route[len("/api/guion/"):]
                item = abrir_generacion(ident, db)
                if item is None:
                    return self.send(404, {"error": "Generación no encontrada"})
                return self.send(200, presentar_generacion(item, ident))
            else:
                self.send(404, {"error": "Ruta desconocida"})
        def do_POST(self):
            if self.path != "/api/guion":
                return self.send(404, {"error": "Ruta desconocida"})
            if self.headers.get("Origin") != origin or \
               self.headers.get("X-Barriga-Token") != token:
                return self.send(403, {"error": "Origen o token no autorizado"})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.send(415, {"error": "Se requiere JSON"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 1 <= size <= 8000:
                    return self.send(413, {"error": "Solicitud demasiado grande"})
                args = json.loads(self.rfile.read(size))
                idea = args.get("idea", "")
                if not isinstance(idea, str) or not 2 <= len(idea.strip()) <= 2400:
                    return self.send(400, {"error": "Escribe una idea entre 2 y 2400 caracteres"})
                self.send(200, guion(idea.strip(), modelo, db))
            except (ValueError, TypeError, ErrorNarrativa) as exc:
                return self.send(400, {"error": str(exc)[:180]})
            except (sqlite3.Error, OSError):
                return self.send(500, {"error": "Error guardando la generación local"})
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
    db = inicializar(carpeta / "local-data" / "guiones-locales.sqlite3")
    with ThreadingHTTPServer((HOST,args.puerto),servidor(carpeta,
             secrets.token_urlsafe(32),args.puerto,args.modelo,db)) as http:
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
