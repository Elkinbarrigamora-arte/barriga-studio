#!/usr/bin/env python3
"""B STUDIO: one local, private bridge for real scripts and existing video files.

- Serves the owner's existing index.html unchanged (including unpublished edits).
- Calls the installed Ollama model only when the user requests a script.
- Lists/plays/downloads actual MP4 files from the selected local directory.
- Recovers an EXISTING PoYo task only; NEVER creates a paid generation.
- Shows engine readiness honestly. Does not expose Mac ports to the internet.
"""
import argparse
import json
import mimetypes
import os
import re
import secrets
import socket
import sys
import tempfile
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit, parse_qs
from urllib.request import urlopen

from puente_local import guion as generate_ollama_script
from bstudio_poyo_recover import (
    TASK_RE, read_existing_task, find_video_url, validate_download_url,
    save_video, probe_video,
)

HOST = "127.0.0.1"
MODEL = "qwen2.5-coder:14b"
ALLOWED_MEDIA = {".mp4", ".mov", ".m4v"}
NAME_RE = re.compile(r"^[^/\\\x00-\x1f]{1,200}\.(mp4|mov|m4v)$", re.IGNORECASE)
MAX_IMPORT_BYTES = 250 * 1024 * 1024
VOICE_RE = re.compile(r"^[^/\\\x00-\x1f]{1,200}\.(wav|mp3|m4a|aac)$", re.IGNORECASE)


def list_voices(voices_dir):
    """List existing local audio only, without reading or changing source files."""
    if voices_dir is None or not voices_dir.is_dir():
        return []
    results = []
    for path in voices_dir.iterdir():
        try:
            if (path.is_symlink() or not path.is_file()
                    or not VOICE_RE.fullmatch(path.name)):
                continue
            stat = path.stat()
            if stat.st_size < 12:
                continue
            results.append({"filename": path.name, "bytes": stat.st_size,
                            "modified": int(stat.st_mtime), "type": "audio"})
        except OSError:
            continue
    results.sort(key=lambda item: item["modified"], reverse=True)
    return results[:150]



def import_existing_mp4(stream, media_dir, filename, size):
    """Copy an owner-selected MP4 into the local gallery without overwriting files.

    Never contacts video providers, never sends jobs, and never deletes source media.
    An exclusive hard link commits the temporary copy only if the destination is free.
    """
    if (not isinstance(filename, str) or not NAME_RE.fullmatch(filename)
            or not filename.lower().endswith(".mp4")
            or filename.startswith(".") or Path(filename).name != filename):
        raise ValueError("Selecciona un archivo MP4 con un nombre válido.")
    if not isinstance(size, int) or not 12 <= size <= MAX_IMPORT_BYTES:
        raise ValueError("El MP4 debe medir entre 12 bytes y 250 MB.")
    media_dir.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=media_dir, prefix=".bstudio-import-",
            suffix=".part", delete=False
        ) as out:
            temporary = Path(out.name)
            remaining = size
            while remaining:
                chunk = stream.read(min(128 * 1024, remaining))
                if not chunk:
                    raise ValueError("La carga llegó incompleta. No se guardó ningún video.")
                out.write(chunk)
                remaining -= len(chunk)
        with temporary.open("rb") as uploaded:
            header = uploaded.read(12)
        if header[4:8] != b"ftyp":
            raise ValueError("El archivo no tiene encabezado MP4 válido.")
        stem = Path(filename).stem
        for number in range(1001):
            output_name = filename if number == 0 else f"{stem}-{number}.mp4"
            candidate = media_dir / output_name
            try:
                os.link(temporary, candidate)
                return {"filename": output_name, "bytes": size}
            except FileExistsError:
                continue
        raise RuntimeError("Demasiadas copias con el mismo nombre.")
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)



def select_script_model(installed_names, requested):
    """Select an installed text-capable Ollama model, never download one silently."""
    available = [n for n in installed_names if isinstance(n, str) and n]
    if requested != "auto":
        return next((n for n in available if n == requested or
                     (":" not in requested and n == requested + ":latest")), None)
    preferred = ("qwen2.5-coder:14b", "qwen2.5:14b", "qwen3:14b",
                 "qwen2.5:7b", "llama3.2:3b", "llama3.1:8b")
    for candidate in preferred:
        if candidate in available:
            return candidate
    # Avoid choosing an embedding model as a scriptwriter.
    return next((n for n in available if not any(
        marker in n.lower() for marker in ("embed", "nomic", "bge-", "rerank")
    )), None)


def ollama_health(model=MODEL, opener=urlopen):
    """Check real installed models; auto mode selects only models already installed."""
    try:
        with opener("http://127.0.0.1:11434/api/tags", timeout=3) as response:
            obj = json.load(response)
        names = [entry.get("name", "") for entry in obj.get("models", [])
                 if isinstance(entry, dict)]
        selected = select_script_model(names, model)
        if selected:
            return {"state": "ready",
                    "detail": "Modelo local disponible: " + selected,
                    "model": selected}
        return {"state": "missing_model",
                "detail": "Ollama responde, pero no hay un modelo de texto compatible instalado."
                if model == "auto" else
                "El modelo solicitado no está instalado: " + model,
                "model": model}
    except (OSError, ValueError, TypeError, KeyError):
        return {"state": "offline", "detail":
                "No se pudo consultar Ollama en 127.0.0.1:11434.", "model": model}


def list_media(media_dir):
    if not media_dir.is_dir():
        return []
    results = []
    for path in media_dir.iterdir():
        try:
            if (path.is_symlink() or not path.is_file()
                    or path.suffix.lower() not in ALLOWED_MEDIA
                    or not NAME_RE.fullmatch(path.name)):
                continue
            st = path.stat()
            if st.st_size < 12:
                continue
            results.append({"filename": path.name, "bytes": st.st_size,
                            "modified": int(st.st_mtime), "type": "video"})
        except OSError:
            continue
    results.sort(key=lambda item: item["modified"], reverse=True)
    return results[:150]


def engine_inventory(model, voices_dir):
    ollama = ollama_health(model)
    voices = list_voices(voices_dir)
    return [
        {"id": "barriga-ia", "name": "Barriga IA · Ollama", **ollama,
         "operation": "script"},
        {"id": "poyo", "name": "PoYo · Wan 2.2", "state": "requires_verification",
         "detail": "Solo recuperar tareas existentes. Acceso y permisos del proveedor sin confirmar.",
         "operation": "existing_video_recovery", "paid_generation_enabled": False},
        {"id": "voices", "name": "Voces existentes", "state": "files_found" if voices else "not_verified",
         "detail": (str(len(voices)) + " archivo(s) de audio detectados; falta comprobar su calidad."
                    if voices else "Las voces no están localizadas en la carpeta configurada; no se recrean."),
         "operation": "external_audio", "count": len(voices)},
        {"id": "fal", "name": "fal.ai · video", "state": "not_connected",
         "detail": "Sin adaptador de video autenticado y probado en este puente.",
         "operation": "video"},
        {"id": "drawthings", "name": "Draw Things / Kling", "state": "not_verified",
         "detail": "No hay endpoint de video real comprobado. No se afirma generación.",
         "operation": "video"},
    ]


def make_handler(studio, media_dir, runtime_asset, token, port, model, voices_dir, initial_task_id=""):
    origin = "http://127.0.0.1:" + str(port)

    class Handler(BaseHTTPRequestHandler):
        # Do not log query strings (the local video playback capability is secret).
        def log_message(self, fmt, *args):
            pass

        def headers_for(self, status, length, content_type, more=None):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            if more:
                for name, value in more.items():
                    self.send_header(name, value)
            self.end_headers()

        def send_bytes(self, status, data, kind):
            self.headers_for(status, len(data), kind)
            self.wfile.write(data)

        def send_json(self, status, payload):
            encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_bytes(status, encoded, "application/json; charset=utf-8")

        def checked_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{port}"

        def checked_token(self):
            return secrets.compare_digest(
                self.headers.get("X-Barriga-Token", ""), token)

        def checked_origin(self):
            return self.headers.get("Origin") == origin

        def checked_fetch_site(self):
            return self.headers.get("Sec-Fetch-Site", "same-origin") in ("same-origin", "none")

        def do_GET(self):
            if not self.checked_host() or not self.checked_fetch_site():
                return self.send_json(403, {"error": "Acceso local no autorizado."})
            url = urlsplit(self.path)
            route = url.path
            if route in ("/", "/index.html"):
                try:
                    html = (studio / "index.html").read_text(encoding="utf-8")
                    config = json.dumps({"token": token, "taskId": initial_task_id}, ensure_ascii=False)
                    injected = ('<script>window.__BSTUDIO_BRIDGE__=' + config +
                                ';</script><script defer src="/assets/bstudio-runtime.js"></script>')
                    html = html.replace("</body>", injected + "</body>") if \
                        "</body>" in html else html + injected
                    return self.send_bytes(200, html.encode("utf-8"),
                                           "text/html; charset=utf-8")
                except (OSError, UnicodeError):
                    return self.send_json(500, {"error": "No se pudo abrir el estudio."})
            if route == "/assets/bstudio-runtime.js":
                try:
                    return self.send_bytes(200, runtime_asset.read_bytes(),
                                           "text/javascript; charset=utf-8")
                except OSError:
                    return self.send_json(500, {"error": "Módulo de interfaz ausente."})
            if route.startswith("/assets/"):
                basename = route.removeprefix("/assets/")
                if not re.fullmatch(r"[A-Za-z0-9_.-]{1,150}\.(?:css|js)", basename):
                    return self.send_json(404, {"error": "Recurso no disponible."})
                asset = studio / "assets" / basename
                if not asset.is_file() or asset.is_symlink():
                    return self.send_json(404, {"error": "Recurso no disponible."})
                return self.send_bytes(200, asset.read_bytes(),
                                       "text/css; charset=utf-8" if basename.endswith(".css")
                                       else "text/javascript; charset=utf-8")
            if route in ("/api/engines", "/api/videos", "/api/voices", "/api/health"):
                if not self.checked_token():
                    return self.send_json(403, {"error": "Sesión local no autorizada."})
                if route == "/api/engines":
                    return self.send_json(200, {"engines": engine_inventory(model, voices_dir)})
                if route == "/api/videos":
                    return self.send_json(200, {"videos": list_media(media_dir)})
                if route == "/api/voices":
                    return self.send_json(200, {
                        "voices": list_voices(voices_dir),
                        "configured": bool(voices_dir and voices_dir.is_dir()),
                    })
                return self.send_json(200, {
                    "studio": "running", "local_only": True, "paid_submissions": False,
                    "script_engine": ollama_health(model), "media_files": len(list_media(media_dir))})
            if route.startswith("/media/"):
                # HTML5 video elements cannot attach custom headers. Authenticate a
                # session-specific capability in the query; prevent cross-site loads.
                supplied = parse_qs(url.query).get("token", [""])[0]
                if not secrets.compare_digest(supplied, token):
                    return self.send_json(403, {"error": "Vista previa no autorizada."})
                return self.serve_file(unquote(route[len("/media/"):]), media_dir, NAME_RE)
            if route.startswith("/voices/"):
                supplied = parse_qs(url.query).get("token", [""])[0]
                if not secrets.compare_digest(supplied, token):
                    return self.send_json(403, {"error": "Vista previa no autorizada."})
                if voices_dir is None:
                    return self.send_json(404, {"error": "Carpeta de voces no configurada."})
                return self.serve_file(unquote(route[len("/voices/"):]), voices_dir, VOICE_RE)
            return self.send_json(404, {"error": "Ruta inexistente."})

        def do_HEAD(self):
            if not self.checked_host() or not self.checked_fetch_site():
                return self.headers_for(403, 0, "text/plain")
            url = urlsplit(self.path)
            if url.path.startswith("/media/"):
                supplied = parse_qs(url.query).get("token", [""])[0]
                if secrets.compare_digest(supplied, token):
                    return self.serve_file(
                        unquote(url.path[len("/media/"):]), media_dir, NAME_RE, head_only=True)
            if url.path.startswith("/voices/") and voices_dir is not None:
                supplied = parse_qs(url.query).get("token", [""])[0]
                if secrets.compare_digest(supplied, token):
                    return self.serve_file(
                        unquote(url.path[len("/voices/"):]), voices_dir, VOICE_RE, head_only=True)
            return self.headers_for(404, 0, "text/plain")

        def serve_file(self, name, folder, name_pattern, head_only=False):
            if not name_pattern.fullmatch(name):
                return self.headers_for(404, 0, "text/plain")
            file = folder / name
            if file.is_symlink() or not file.is_file():
                return self.headers_for(404, 0, "text/plain")
            try:
                size = file.stat().st_size
                if size < 12:
                    return self.headers_for(404, 0, "text/plain")
                byte_range = self.headers.get("Range")
                start, end = 0, size - 1
                if byte_range:
                    matched = re.fullmatch(r"bytes=(\d+)-(\d*)", byte_range)
                    if not matched:
                        return self.headers_for(416, 0, "text/plain",
                                                {"Content-Range": f"bytes */{size}"})
                    start = int(matched.group(1))
                    end = min(int(matched.group(2)), size - 1) if matched.group(2) else end
                    if start > end or start >= size:
                        return self.headers_for(416, 0, "text/plain",
                                                {"Content-Range": f"bytes */{size}"})
                status = 206 if byte_range else 200
                headers = {"Accept-Ranges": "bytes",
                           "Content-Disposition": "inline",
                           "Content-Range": f"bytes {start}-{end}/{size}"} if byte_range else \
                          {"Accept-Ranges": "bytes", "Content-Disposition": "inline"}
                kind = mimetypes.guess_type(name)[0] or "video/mp4"
                self.headers_for(status, end - start + 1, kind, headers)
                if head_only:
                    return
                with file.open("rb") as inp:
                    inp.seek(start)
                    remaining = end - start + 1
                    while remaining:
                        chunk = inp.read(min(128 * 1024, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)
            except (OSError, BrokenPipeError, ConnectionResetError):
                pass

        def do_POST(self):
            if not self.checked_host() or not self.checked_origin() or \
                    not self.checked_fetch_site() or not self.checked_token():
                return self.send_json(403, {"error": "Origen o sesión no autorizados."})
            route = urlsplit(self.path).path
            if route not in ("/api/guion", "/api/recover", "/api/import-video"):
                return self.send_json(404, {"error": "Ruta inexistente."})
            if route == "/api/import-video":
                if self.headers.get("Content-Type", "").split(";")[0] != "video/mp4":
                    return self.send_json(415, {"error": "Solo se aceptan archivos MP4."})
                try:
                    length = int(self.headers.get("Content-Length", "0"))
                    filename = unquote(self.headers.get("X-Barriga-Filename", ""))
                    result = import_existing_mp4(self.rfile, media_dir, filename, length)
                    return self.send_json(201, {
                        "status": "imported", "video": result["filename"],
                        "bytes": result["bytes"], "paid_credits": 0,
                        "message": "Copia local creada; el archivo original no se modificó."
                    })
                except (ValueError, OSError, RuntimeError) as exc:
                    return self.send_json(400, {"error": str(exc)})
            if self.headers.get("Content-Type", "").split(";")[0] != "application/json":
                return self.send_json(415, {"error": "Solo JSON."})
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 1 <= length <= 8000:
                    return self.send_json(413, {"error": "Solicitud demasiado grande."})
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict):
                    return self.send_json(400, {"error": "JSON inválido."})
                if route == "/api/guion":
                    idea = body.get("idea", "")
                    if not isinstance(idea, str) or not 2 <= len(idea.strip()) <= 2400:
                        return self.send_json(400, {"error": "Idea entre 2 y 2400 caracteres."})
                    health = ollama_health(model)
                    if health["state"] != "ready":
                        return self.send_json(503, {
                            "error": "Barriga IA no está listo: " + (health.get("detail") or
                                     "Ollama no responde o no tiene un modelo compatible.")})
                    selected_model = health.get("model") or model
                    result = generate_ollama_script(idea.strip(), selected_model)
                    return self.send_json(200, result)
                task_id = body.get("task_id", "")
                if not isinstance(task_id, str) or not TASK_RE.fullmatch(task_id):
                    return self.send_json(400, {"error": "Identificador de tarea inválido."})
                destination = media_dir / ("poyo-" + task_id + ".mp4")
                if destination.exists():
                    return self.send_json(200, {
                        "status": "already_downloaded",
                        "video": destination.name, "message": "Archivo local encontrado; sin duplicarlo."})
                task = read_existing_task(task_id)
                status = str(task.get("status") or task.get("raw_status") or "").lower()
                if status not in ("succeeded", "finished", "completed", "success"):
                    return self.send_json(409, {
                        "error": "El proveedor no confirmó la finalización. No se envía otra generación.",
                        "provider_status": status})
                url = find_video_url(task)
                validate_download_url(url)
                num_bytes = save_video(url, destination)
                details = probe_video(destination)
                return self.send_json(200, {
                    "status": "downloaded", "video": destination.name, "bytes": num_bytes,
                    "media_probe": details, "new_generation_credits": 0})
            except (ValueError, TypeError):
                return self.send_json(400, {"error": "Solicitud JSON inválida."})
            except (RuntimeError, OSError) as exc:
                return self.send_json(502, {
                    "error": str(exc), "note": "No se reenvió ninguna generación de pago."})

    return Handler


def main():
    parser = argparse.ArgumentParser(description="B STUDIO: puente local unificado de IA y videos")
    parser.add_argument("--studio", type=Path, default=Path.home() / "barriga-studio")
    parser.add_argument("--media-dir", type=Path,
                        default=Path.home() / "Movies" / "BarrigaStudio")
    parser.add_argument("--voices-dir", type=Path)
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--model", default="auto", help="Modelo Ollama instalado; auto detecta uno compatible")
    parser.add_argument("--task-id", default="", help="Tarea PoYo existente para mostrar en el estudio")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if args.task_id and not TASK_RE.fullmatch(args.task_id):
        parser.error("ID de PoYo inválido.")
    if not 1024 <= args.port <= 65535:
        parser.error("Puerto inválido.")
    studio = args.studio.expanduser().resolve()
    media_dir = args.media_dir.expanduser().resolve()
    voices_dir = args.voices_dir.expanduser().resolve() if args.voices_dir else None
    runtime = Path(__file__).resolve().parent.parent / "assets" / "bstudio-runtime.js"
    if not (studio / "index.html").is_file():
        parser.error("No se encontró index.html en la versión local del estudio.")
    if not runtime.is_file():
        parser.error("Falta el módulo de interfaz assets/bstudio-runtime.js.")
    media_dir.mkdir(parents=True, exist_ok=True)
    token = secrets.token_urlsafe(32)
    try:
        with ThreadingHTTPServer(
            (HOST, args.port),
            make_handler(studio, media_dir, runtime, token, args.port, args.model, voices_dir, args.task_id)
        ) as server:
            url = f"http://127.0.0.1:{args.port}/"
            print("B STUDIO · puente unificado local: " + url, flush=True)
            print("Ollama + videos existentes + recuperación PoYo (SIN envíos de pago).", flush=True)
            print("La carpeta original se sirve sin modificar archivos.", flush=True)
            if not args.no_browser:
                webbrowser.open(url)
            try:
                server.serve_forever(poll_interval=0.2)
            except KeyboardInterrupt:
                print("Puente unificado detenido.", flush=True)
    except OSError as exc:
        parser.error("No se pudo abrir el puerto local; cierra el servidor previo o usa --port 8781. " +
                     type(exc).__name__)


if __name__ == "__main__":
    main()
