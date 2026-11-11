#!/usr/bin/env python3
"""B STUDIO ÉLITE: one-origin integration gateway for the ACTIVE Mac /studio.

Run the owner's existing tools/puente_central.py on a private upstream port,
then serve the SAME site at its original 127.0.0.1:8766 address. This module
does not edit the existing application, projects, files, or database. It
proxies ALL original routes and adds a strictly namespaced /_bstudio API.
New paid generation endpoints are never exposed.
"""
import argparse
import html
import http.client
import json
import re
import secrets
import socket
import sys
import webbrowser
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from bstudio_unified_bridge import (
    MODEL, make_handler, ollama_health, list_media, list_voices,
)

HOST = "127.0.0.1"
NAMESPACE = "/_bstudio"
PROTECTED_ROUTES = (
    "/api/engines", "/api/videos", "/api/voices", "/api/health",
    "/api/guion", "/api/recover", "/api/import-video",
    "/assets/bstudio-runtime.js",
)
BLOCKED_HEADERS = {
    "connection", "keep-alive", "proxy-authenticate", "proxy-authorization",
    "te", "trailers", "transfer-encoding", "upgrade",
}


class BoundedBody:
    """Pass exactly Content-Length bytes to the upstream without blocking for EOF."""

    def __init__(self, source, size):
        self.source = source
        self.remaining = size

    def read(self, amount=128 * 1024):
        if self.remaining <= 0:
            return b""
        chunk = self.source.read(min(self.remaining, max(1, amount)))
        if not chunk:
            raise OSError("El cliente interrumpió la carga antes de completarse.")
        self.remaining -= len(chunk)
        return chunk


def eligible_overlay(path, status, headers):
    """Never insert the overlay on APIs, text, JSON, or error pages."""
    if status != 200 or urlsplit(path).path not in ("/studio", "/studio/"):
        return False
    return "text/html" in str(headers.get("Content-Type", "")).lower()


def add_overlay(html_body, token, task_id):
    tag = ('<script defer src="/_bstudio/assets/bstudio-runtime.js" '
           'data-token="' + html.escape(token, quote=True) + '" '
           'data-api-base="/_bstudio" data-task-id="' +
           html.escape(task_id, quote=True) + '"></script>')
    if re.search(r"</body\s*>", html_body, re.IGNORECASE):
        return re.sub(r"</body\s*>", lambda m: tag + m.group(0),
                      html_body, count=1, flags=re.IGNORECASE)
    return html_body + tag


def make_gateway_handler(media_dir, runtime_path, token, listen_port,
                         upstream_port, model, voices_dir, task_id=""):
    """One namespace owns new capabilities; original Studio routes are forwarded."""
    base_handler = make_handler(
        Path.cwd(), media_dir, runtime_path, token, listen_port,
        model, voices_dir, initial_task_id=task_id,
    )

    class Gateway(base_handler):
        upstream_port = None

        def _namespace_route(self):
            original = self.path
            parts = urlsplit(original)
            if not parts.path.startswith(NAMESPACE + "/"):
                return None
            new_route = parts.path[len(NAMESPACE):]
            if not (new_route in PROTECTED_ROUTES or
                    new_route.startswith(("/media/", "/voices/"))):
                return None
            self.path = new_route + ("?" + parts.query if parts.query else "")
            return original

        def _delegate(self, method):
            original = self._namespace_route()
            if original is not None:
                try:
                    return getattr(super(), "do_" + method)()
                finally:
                    self.path = original
            if urlsplit(self.path).path.startswith(NAMESPACE + "/"):
                return self.send_json(404, {"error": "Ruta de integración inexistente."})
            return self.proxy_existing_application()

        def do_GET(self):
            return self._delegate("GET")

        def do_HEAD(self):
            return self._delegate("HEAD")

        def do_POST(self):
            return self._delegate("POST")

        def do_PUT(self):
            return self.proxy_existing_application()

        def do_PATCH(self):
            return self.proxy_existing_application()

        def do_DELETE(self):
            return self.proxy_existing_application()

        def do_OPTIONS(self):
            return self.proxy_existing_application()

        def proxy_existing_application(self):
            if not self.checked_host() or not self.checked_fetch_site():
                return self.send_json(403, {"error": "Acceso local no autorizado."})
            response_started = False
            try:
                conn = http.client.HTTPConnection(HOST, upstream_port, timeout=180)
                headers = {}
                for name, value in self.headers.items():
                    if name.lower() not in BLOCKED_HEADERS and name.lower() != "host":
                        headers[name] = value
                headers["Host"] = f"{HOST}:{upstream_port}"
                # Keep the externally-visible origin unchanged in Safari. The
                # private upstream sees its own address for CSRF origin checks.
                original_origin = f"http://{HOST}:{listen_port}"
                internal_origin = f"http://{HOST}:{upstream_port}"
                if headers.get("Origin") == original_origin:
                    headers["Origin"] = internal_origin
                if headers.get("Referer", "").startswith(original_origin + "/"):
                    headers["Referer"] = internal_origin + headers["Referer"][len(original_origin):]
                if urlsplit(self.path).path in ("/studio", "/studio/"):
                    headers["Accept-Encoding"] = "identity"
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 <= length <= 512 * 1024 * 1024:
                    return self.send_json(413, {"error": "Solicitud demasiado grande."})
                # Feed the inbound request body in bounded chunks through
                # http.client. Never buffer video uploads in RAM.
                body = BoundedBody(self.rfile, length) if length > 0 else None
                conn.request(self.command, self.path, body=body, headers=headers)
                upstream = conn.getresponse()
                response_headers = dict(upstream.getheaders())
                status = upstream.status
                overlay = eligible_overlay(self.path, status, response_headers)
                if overlay:
                    raw = upstream.read(8 * 1024 * 1024 + 1)
                    if len(raw) > 8 * 1024 * 1024:
                        return self.send_json(502, {
                            "error": "La página principal es demasiado grande para integrar sin riesgo."})
                    page = raw.decode("utf-8", errors="strict")
                    data = add_overlay(page, token, task_id).encode("utf-8")
                else:
                    data = None
                self.send_response(status)
                response_started = True
                for name, value in upstream.getheaders():
                    low = name.lower()
                    if low in BLOCKED_HEADERS or low in ("content-length", "content-encoding"):
                        if low == "content-encoding" and not overlay:
                            self.send_header(name, value)
                        continue
                    if low == "location" and value.startswith(internal_origin):
                        value = original_origin + value[len(internal_origin):]
                    self.send_header(name, value)
                if overlay:
                    self.send_header("Content-Length", str(len(data)))
                    self.send_header("Cache-Control", "no-store")
                else:
                    size = response_headers.get("Content-Length")
                    if size is not None:
                        self.send_header("Content-Length", size)
                    self.send_header("Connection", "close")
                self.end_headers()
                if self.command == "HEAD":
                    return
                if data is not None:
                    self.wfile.write(data)
                else:
                    while True:
                        # read1 returns available bytes immediately: a long-lived
                        # SSE stream must not wait for 128 KiB before flushing.
                        chunk = upstream.read1(128 * 1024)
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        self.wfile.flush()
            except (OSError, ValueError, UnicodeError,
                    http.client.HTTPException) as exc:
                # Never turn network failure into a successful-looking output.
                if not response_started:
                    try:
                        self.send_json(502, {
                            "error": "La aplicación original no respondió. "
                                     "Verifica el puente central antes de usar Élite.",
                            "tipo": type(exc).__name__,
                        })
                    except (OSError, ConnectionError):
                        pass
            finally:
                if "conn" in locals():
                    conn.close()

    return Gateway


def parse_options(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--port", type=int, default=8766, help="Puerto OFICIAL de la aplicación")
    p.add_argument("--upstream-port", type=int, default=8782, help="Puerto interno del puente central existente")
    p.add_argument("--media-dir", type=Path, default=Path.home()/"Movies"/"BarrigaStudio")
    p.add_argument("--voices-dir", type=Path)
    p.add_argument("--model", default="auto")
    p.add_argument("--task-id", default="")
    p.add_argument("--no-browser", action="store_true")
    args = p.parse_args(argv)
    if (not 1024 <= args.port <= 65535 or
            not 1024 <= args.upstream_port <= 65535 or
            args.port == args.upstream_port):
        p.error("Los puertos deben ser diferentes y válidos.")
    if args.task_id and not re.fullmatch(r"[A-Za-z0-9_-]{8,100}", args.task_id):
        p.error("Identificador PoYo inválido.")
    return args


def main(argv=None):
    args = parse_options(argv)
    runtime = Path(__file__).resolve().parents[1] / "assets" / "bstudio-runtime.js"
    if not runtime.is_file():
        raise SystemExit("Falta el módulo del panel integrado.")
    media = args.media_dir.expanduser().resolve()
    media.mkdir(parents=True, exist_ok=True)
    voices = args.voices_dir.expanduser().resolve() if args.voices_dir else None
    token = secrets.token_urlsafe(32)
    handler = make_gateway_handler(
        media, runtime, token, args.port, args.upstream_port,
        args.model, voices, args.task_id,
    )
    try:
        with ThreadingHTTPServer((HOST, args.port), handler) as server:
            url=f"http://{HOST}:{args.port}/studio"
            print("B STUDIOS ÉLITE — interfaz única: " + url, flush=True)
            print(f"Backend original privado: {HOST}:{args.upstream_port}",flush=True)
            print("Sin reemplazar archivos ni generar consumos PoYo.",flush=True)
            if not args.no_browser:
                webbrowser.open(url)
            server.serve_forever(poll_interval=0.2)
    except OSError:
        raise SystemExit(
            f"El puerto oficial {args.port} está ocupado: NO se detuvo ni "
            "modificó el servidor original. Detén el anterior conscientemente "
            "antes de activar este gateway."
        )


if __name__ == "__main__":
    main()
