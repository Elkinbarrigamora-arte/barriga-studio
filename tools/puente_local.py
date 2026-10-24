#!/usr/bin/env python3
"""Puente privado de prueba entre el Studio local y Ollama. No edita archivos existentes."""
import argparse
import json
import sqlite3
import secrets
import threading
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
    abrir_generacion, inicializar, reanudar_cierre,
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
 let sePuedeReparar=false;
 let ultimoResultado=null;
 function iniciar(){
   const field=document.getElementById('script');
   if(!field)return;
   const box=document.createElement('div');
   box.style.cssText='padding:14px;margin:12px 0;border:1px solid #ab90ff;border-radius:12px;background:#14122c';
   const title=document.createElement('strong');
   title.textContent='🧠 BARRIGA IA · Guionista local verificado';
   // Solo un editor visible; preservamos la idea cuando se presenta el guion.
   field.addEventListener('input',()=>{
      if(field.value.trim()!==(field.dataset.ultimoGuion||'').trim()){
         field.dataset.ideaOriginal=field.value.trim();
         field.dataset.ultimoGuion='';
      }
   });
   const restaurar=document.createElement('button');
   restaurar.type='button';restaurar.className='button ghost';
   restaurar.style.margin='8px';
   restaurar.textContent='Restaurar idea original';
   restaurar.onclick=()=>{
      const original=(field.dataset.ideaOriginal||'').trim();
      if(!original){msg.textContent='No hay una idea original guardada.';return}
      if(field.value.trim()!==original &&
         !confirm('¿Mostrar la idea original en el editor? Guarda los cambios antes.'))return;
      field.value=original;
      field.dataset.ultimoGuion='';
      field.dispatchEvent(new Event('input',{bubbles:true}));
      msg.textContent='Idea original restaurada en Guion. Puedes editarla o volver a generar.';
   };
   const btn=document.createElement('button');
   btn.type='button';btn.className='button';btn.style.margin='10px';
   btn.textContent='Generar y validar guion';
   const reparar=document.createElement('button');
   reparar.type='button';reparar.className='button ghost';
   reparar.style.margin='8px';
   reparar.textContent='Reparar solo cierre';
   reparar.style.display='none';
   const msg=document.createElement('p');msg.className='muted';msg.setAttribute('role','status');
   msg.textContent='Escribe tu idea en Guion (arriba) y pulsa Generar. Requiere Ollama encendido.';
   const vista=document.createElement('pre');
   vista.setAttribute('aria-label','Vista previa del resultado, no sustituye el guion original');
   vista.style.cssText='display:none;white-space:pre-wrap;overflow-wrap:anywhere;padding:12px;border:1px solid #555;border-radius:10px;max-height:350px;overflow:auto';
   const usar=document.createElement('button');
   usar.type='button';usar.className='button ghost';usar.style.margin='8px';
   usar.textContent='Usar este resultado en el editor';
   usar.style.display='none';
   const historial=document.createElement('select');
   historial.setAttribute('aria-label','Generaciones locales guardadas');
   const recuperar=document.createElement('button');
   recuperar.type='button';recuperar.className='button ghost';recuperar.style.margin='8px';
   recuperar.textContent='Recuperar guion';
   function cargarGuion(data){
      const guion=data.guion||{};
      const partes=['GANCHO',guion.gancho||'','', 'HISTORIA',guion.historia||'',
                    '', 'CIERRE',guion.cierre||''];
      const generado=partes.join('\n');
      // No reemplazar el texto del usuario con un borrador rechazado.
      // Todos los resultados se muestran primero en una vista de solo lectura.
      ultimoResultado=data;
      vista.textContent=generado;
      vista.style.display='block';
      usar.style.display='inline-block';
      ultima=data.id;
      sePuedeReparar=data.estado==='BLOQUE_RECHAZADO_CIERRE';
      reparar.style.display=sePuedeReparar?'inline-block':'none';
      const msgEstado=data.apto_para_revision_humana ?
        'APTO PARA REVISION HUMANA (no publicado).' :
        'BORRADOR RECHAZADO O INCOMPLETO; revisar antes de utilizar.';
      const motivos=Array.isArray(data.motivos_fidelidad)?
        data.motivos_fidelidad.join('; '):'';
      const rechazos=Array.isArray(data.motivos_bloque)?
        data.motivos_bloque.filter(x=>typeof x==='string').join('; '):'';
      const perf=data.rendimiento||{};
      const detalle=(typeof perf.llamadas_ollama==='number')?
        (' · Ollama: '+perf.llamadas_ollama+' llamadas'
         +(data.segundos?' · '+data.segundos+' s':'')
         +(typeof perf.tokens_por_segundo==='number'?
           ' · '+perf.tokens_por_segundo+' tokens/s':''))
        :'';
      msg.textContent=msgEstado+' ID: '+data.id+'. Estado: '+data.estado+
        (motivos?'. Motivos: '+motivos:'')+
        (rechazos?'. Rechazo del bloque: '+rechazos:'')+'.'+detalle;
   }
   usar.onclick=()=>{
      if(!ultimoResultado)return;
      const g=ultimoResultado.guion||{};
      const partes=['GANCHO',g.gancho||'','', 'HISTORIA',g.historia||'',
                    '', 'CIERRE',g.cierre||''];
      const generado=partes.join('\n');
      if(![g.gancho,g.historia,g.cierre].some(x=>typeof x==='string'&&x.trim())){
         msg.textContent='El resultado no contiene texto aprovechable.';
         return;
      }
      const aviso=ultimoResultado.apto_para_revision_humana?
        '¿Reemplazar el editor con esta versión? Se conservará la idea original.':
        'ATENCIÓN: esta versión fue rechazada o está incompleta. ¿Quieres usarla igualmente para editarla? Se conservará la idea original.';
      if(!confirm(aviso))return;
      const idea=String(ultimoResultado.idea||field.dataset.ideaOriginal||field.value).trim();
      field.dataset.ideaOriginal=idea;
      field.dataset.ultimoGuion=generado;
      field.value=generado;
      field.dispatchEvent(new Event('input',{bubbles:true}));
      msg.textContent='Versión cargada para editar; la idea original se conserva en Restaurar idea original. Guarda tu proyecto si quieres conservar la edición.';
   };
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
      const texto=field.value.trim();
      const generado=(field.dataset.ultimoGuion||'').trim();
      const idea=(generado&&texto===generado)?
        (field.dataset.ideaOriginal||'').trim():texto;
      if(!idea){msg.textContent='Primero escribe la idea en el campo Guion.';return}
      if(idea.length>2400){
        msg.textContent='La idea no puede superar 2400 caracteres. Acórtala antes de generar.';
        return;
      }
      if(generado&&texto===generado&&
         !confirm('¿Generar otra versión desde la idea original? Se reemplazará el guion visible.'))return;
      field.dataset.ideaOriginal=idea;
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
   reparar.onclick=async()=>{
      if(!sePuedeReparar||!ultima)return;
      if(!confirm('¿Reintentar solo el cierre guardando una nueva versión? No se cambiarán el gancho ni la historia anteriores.'))return;
      reparar.disabled=true;btn.disabled=true;
      msg.textContent='Reanudando el cierre desde el historial, sin regenerar los otros bloques...';
      try{
         const resp=await fetch('/api/guion/reparar-cierre',{
            method:'POST',headers:{...cabeceras,'Content-Type':'application/json'},
            body:JSON.stringify({id:ultima})
         });
         const data=await resp.json();
         if(!resp.ok)throw Error(data.error||('Error HTTP '+resp.status));
         cargarGuion(data);
         await refrescar();
      }catch(e){msg.textContent='Reparación no completada: '+e.message}
      finally{reparar.disabled=false;btn.disabled=false}
   };
   recuperar.onclick=async()=>{
      const id=historial.value;
      if(!id)return;
      // Recuperar muestra una vista previa sin modificar el editor.
      try{
        const resp=await fetch('/api/guion/'+encodeURIComponent(id),{headers:cabeceras});
        const data=await resp.json();
        if(!resp.ok)throw Error(data.error||'No encontrada');
        cargarGuion(data);
      }catch(e){msg.textContent='No se pudo recuperar: '+e.message}
   };
   box.append(title,btn,reparar,restaurar,msg,vista,usar,historial,recuperar);
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
    informe = resultado.get("informe") or {}
    estado = str(resultado.get("estado", "INCOMPLETO"))
    motivos_bloque = []
    if estado.startswith("BLOQUE_RECHAZADO_"):
        nombre = estado[len("BLOQUE_RECHAZADO_"):].lower()
        historial = informe.get("historial_bloques", [])
        if isinstance(historial, list):
            for paso in reversed(historial):
                if isinstance(paso, dict) and paso.get("bloque") == nombre:
                    motivos_bloque = paso.get("motivos_rechazo", [])
                    break
    if not isinstance(motivos_bloque, list):
        motivos_bloque = []
    motivos_bloque = [m[:220] for m in motivos_bloque
                     if isinstance(m, str)][:4]
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
        "idea": resultado.get("idea", ""),
        "motivos_fidelidad": resultado.get("motivos_fidelidad", []),
        "motivos_bloque": motivos_bloque,
        "apto_para_revision_humana": resultado.get(
            "apto_para_revision_humana", False),
        "aprobacion_humana": False,
        "publicacion_automatica_autorizada": False,
        "modelo": resultado.get("modelo", ""),
        "segundos": resultado.get("segundos_inferencia", 0),
        "rendimiento": resultado.get("rendimiento", {}),
        "reanudado_desde": resultado.get("reanudado_desde"),
    }


def guion(idea, modelo, db):
    """Una única ruta de narrativa por bloques + informe persistente."""
    resultado = ejecutar_motor(idea, modelo=modelo)
    ident = guardar_generacion(resultado, db=db)
    return presentar_generacion(resultado, ident)


def servidor(studio, token, puerto, modelo, db):
    origin = f"http://{HOST}:{puerto}"
    generacion_libre = threading.BoundedSemaphore(value=1)
    class Handler(BaseHTTPRequestHandler):
        def send(self, status, body, content_type="application/json; charset=utf-8"):
            data = (body if isinstance(body, str) else
                    json.dumps(body, ensure_ascii=False)).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Content-Security-Policy", "frame-ancestors 'none'")
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
            route = urlsplit(self.path).path
            if route not in ("/api/guion", "/api/guion/reparar-cierre"):
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
                if not isinstance(args, dict):
                    return self.send(400, {"error": "La solicitud debe ser un objeto JSON"})
                if route == "/api/guion":
                    idea = args.get("idea", "")
                    if not isinstance(idea, str) or not 2 <= len(idea.strip()) <= 2400:
                        return self.send(400, {"error": "Escribe una idea entre 2 y 2400 caracteres"})
                else:
                    ident = args.get("id", "")
                    if not isinstance(ident, str) or len(ident) != 23:
                        return self.send(400, {"error": "Identificador de generación inválido"})
                # Un único trabajo de inferencia evita saturar la GPU y
                # ejecutar generaciones duplicadas simultáneamente.
                if not generacion_libre.acquire(blocking=False):
                    return self.send(429, {
                        "error": "Barriga IA ya está generando otro guion. "
                                 "Espera a que termine antes de iniciar uno nuevo."
                    })
                try:
                    if route == "/api/guion/reparar-cierre":
                        reparado, nuevo_id = reanudar_cierre(ident, modelo, db)
                        resultado = presentar_generacion(reparado, nuevo_id)
                    else:
                        resultado = guion(idea.strip(), modelo, db)
                finally:
                    generacion_libre.release()
                self.send(200, resultado)
            except ErrorNarrativa as exc:
                # Si Ollama local falla, no confundirlo con un error del editor.
                if any(x in str(exc).casefold() for x in (
                        "ollama", "respuesta", "timeout", "inferir")):
                    return self.send(502, {"error": "Motor Ollama local: " + str(exc)[:150]})
                return self.send(400, {"error": str(exc)[:180]})
            except (ValueError, TypeError) as exc:
                return self.send(400, {"error": "Solicitud inválida: " + str(exc)[:120]})
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
