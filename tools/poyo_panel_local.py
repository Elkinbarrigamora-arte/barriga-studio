#!/usr/bin/env python3
"""Local, read-only PoYo planning/status panel. No paid submissions here."""
import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from poyo_wan_fast import PRICE_USD, LIMIT_USD, read_ledger
from bstudio_poyo_recover import (
    read_existing_task, find_video_url, validate_download_url, save_video,
    probe_video, TASK_RE,
)

HOST = "127.0.0.1"
PORT = 8771
HTML = r"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Barriga Studio | PoYo 480p</title>
<style>
:root{font-family:system-ui;color-scheme:dark}body{background:#0d1021;color:#fff;margin:0;padding:22px}
main{max-width:740px;margin:auto}h1{color:#ffd64a}section{background:#1b203a;padding:20px;border-radius:15px;margin:18px 0}
label{display:block;margin:12px 0 5px}textarea,input{width:100%;box-sizing:border-box;background:#10152b;color:#fff;border:1px solid #666;padding:12px;border-radius:9px}
textarea{min-height:125px}button{background:#ffd64a;color:#161620;border:0;border-radius:20px;padding:12px 18px;font-weight:800;cursor:pointer}
pre{white-space:pre-wrap;overflow-wrap:anywhere}small{color:#bfbfd0}#out{min-height:50px}
</style></head><body><main><h1>🎬 Barriga Studio · PoYo</h1>
<p>Preparación segura · 9:16 · 480p · límite objetivo de US$5</p>
<section><h2>1. Preparar escena</h2><label for="prompt">Descripción del movimiento</label>
<textarea id="prompt" maxlength="800" placeholder="Un vaquero cabalga por el desierto al atardecer..."></textarea>
<p><small>Estimado publicado: US$0,03 por generación. No se garantiza duración del clip.</small></p>
<button id="preview">Preparar sin gastar</button></section>
<section><h2>2. Consultar video existente</h2>
<label for="task">ID de tarea</label><input id="task" maxlength="160" placeholder="task_id">
<p><button id="check">Consultar estado</button> <button id="recover">Recuperar MP4 existente</button></p>
<small>Usa la cuenta ya autenticada en el llavero de macOS. Recuperar una tarea completada no genera otra escena ni consume nuevos créditos.</small></section>
<section><h2>Resultado</h2><pre id="out" role="status" aria-live="polite">Sin solicitudes todavía.</pre></section>
<p><small>Esta pantalla no tiene botón de generación pagada. Los proyectos del Studio principal permanecen intactos.</small></p>
</main><script>
const out=document.querySelector('#out');
async function call(path,options){
 out.textContent='Procesando solicitud local...';
 try{const res=await fetch(path,options);
 const obj=await res.json();out.textContent=JSON.stringify(obj,null,2);
 if(!res.ok)out.textContent='Error: '+out.textContent;
 }catch(err){out.textContent='No se pudo consultar el servidor local: '+err.message;}
}
document.querySelector('#preview').onclick=()=>{
 const prompt=document.querySelector('#prompt').value.trim();
 if(!prompt){out.textContent='Escribe una descripción.';return}
 call('/api/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt})});
};
document.querySelector('#check').onclick=()=>{
 const id=document.querySelector('#task').value.trim();
 if(!/^[a-zA-Z0-9_-]{1,160}$/.test(id)){out.textContent='ID de tarea inválido.';return}
 call('/api/status/'+encodeURIComponent(id));
};
document.querySelector('#recover').onclick=()=>{
 const id=document.querySelector('#task').value.trim();
 if(!/^[a-zA-Z0-9_-]{8,100}$/.test(id)){out.textContent='ID de tarea inválido.';return}
 call('/api/recover',{method:'POST',headers:{'Content-Type':'application/json'},
 body:JSON.stringify({task_id:id})});
};
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def send(self, status, payload, html=False):
        data = (payload if html else json.dumps(payload, ensure_ascii=False)).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8" if html else "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def same_origin(self):
        return self.headers.get("Origin") == f"http://{HOST}:{PORT}"

    def do_GET(self):
        route = urlsplit(self.path).path
        if route == "/":
            return self.send(200, HTML, html=True)
        match = re.fullmatch(r"/api/status/([A-Za-z0-9_-]{1,160})", route)
        if match:
            try:
                result = read_existing_task(match.group(1))
                return self.send(200, {
                    "task_id": result.get("task_id", match.group(1)),
                    "status": result.get("status") or result.get("raw_status"),
                    "completed_files_available": bool(result.get("files")),
                    "note": "Consulta por CLI con autenticación existente; sin nuevos cargos.",
                })
            except (RuntimeError, ValueError, OSError) as exc:
                return self.send(502, {"error": str(exc)})
        return self.send(404, {"error": "Ruta no encontrada"})

    def do_POST(self):
        route = urlsplit(self.path).path
        if route not in ("/api/preview", "/api/recover"):
            return self.send(404, {"error": "Ruta no encontrada"})
        if not self.same_origin():
            return self.send(403, {"error": "Origen no autorizado"})
        if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
            return self.send(415, {"error": "Se requiere JSON"})
        try:
            size = int(self.headers.get("Content-Length", "0"))
            if not 1 <= size <= 4000:
                return self.send(413, {"error": "Solicitud muy grande"})
            payload = json.loads(self.rfile.read(size))
            if route == "/api/recover":
                task_id = payload.get("task_id", "") if isinstance(payload, dict) else ""
                if not isinstance(task_id, str) or not TASK_RE.fullmatch(task_id):
                    return self.send(400, {"error": "ID de tarea inválido"})
                result = read_existing_task(task_id)
                status = str(result.get("status") or result.get("raw_status") or "").lower()
                if status not in ("succeeded", "finished", "completed", "success"):
                    return self.send(409, {"error": "La tarea no está terminada; no se creará otra"})
                url = find_video_url(result)
                validate_download_url(url)
                dest = Path.home() / "Movies" / "BarrigaStudio" / ("poyo-" + task_id + ".mp4")
                if dest.exists():
                    return self.send(200, {
                        "estado": "archivo_ya_existente", "ruta": str(dest),
                        "nota": "No se sobreescribió. Confirma la integridad del archivo existente.",
                    })
                size = save_video(url, dest)
                return self.send(200, {
                    "estado": "mp4_descargado", "ruta": str(dest),
                    "bytes": size, "validacion": probe_video(dest),
                    "credito_generacion_adicional": 0,
                })
            prompt = payload.get("prompt", "")
            if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 800:
                return self.send(400, {"error": "Descripción inválida"})
            ledger = read_ledger()
            return self.send(200, {
                "mode": "DRY_RUN_NO_CHARGE", "resolution": "480p", "aspect_ratio": "9:16",
                "model": "wan2.2-text-to-video-fast", "prompt": prompt.strip(),
                "estimated_usd": PRICE_USD["480p"], "budget_limit_usd": LIMIT_USD,
                "local_reserved_usd": ledger["reserved_usd"],
                "charged_usd": 0, "video_generated": False,
            })
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as exc:
            return self.send(400, {"error": str(exc)})


if __name__ == "__main__":
    from webbrowser import open as open_browser
    print(f"Barriga Studio PoYo panel: http://{HOST}:{PORT}")
    with ThreadingHTTPServer((HOST, PORT), Handler) as server:
        open_browser(f"http://{HOST}:{PORT}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Panel detenido")
