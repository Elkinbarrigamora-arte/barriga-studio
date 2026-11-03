#!/usr/bin/env python3
"""Local-only Barriga Studio preview and fal.ai image-to-video button.

Serves the existing Studio files unchanged. Injects a small UI module and
handles chargeable generation behind explicit human confirmation in the browser.
No API key is ever sent to the frontend. Do not expose the port publicly.
"""
import argparse
import ipaddress
import json
import os
import secrets
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

HOST = "127.0.0.1"
MODEL = "fal-ai/wan/v2.2-5b/image-to-video"
MAX_BODY = 12000
ESTIMATED_USD = 0.15


def validate_request(data):
    if not isinstance(data, dict) or data.get("confirm_charge") is not True:
        raise ValueError("Confirma el costo antes de generar.")
    image = data.get("image_url")
    prompt = data.get("prompt")
    if not isinstance(image, str) or not isinstance(prompt, str):
        raise ValueError("Imagen y movimiento son obligatorios.")
    image = image.strip()
    prompt = prompt.strip()
    parsed = urlsplit(image)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("La imagen debe tener una URL HTTPS publica.")
    host = parsed.hostname.lower()
    if host == "localhost" or host.endswith(".localhost") or host.endswith(".local"):
        raise ValueError("No uses direcciones locales.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ValueError("Usa un dominio publico, no una direccion IP.")
    if len(image) > 3000 or not 8 <= len(prompt) <= 2000:
        raise ValueError("Revisa la longitud de URL o instrucciones.")
    return {"image_url": image, "prompt": prompt,
            "num_frames": 120, "frames_per_second": 24, "resolution": "720p",
            "aspect_ratio": "9:16"}


def handler_factory(studio, token, port, lock):
    origin = "http://%s:%s" % (HOST, port)

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(studio), **kwargs)

        def reply(self, status, obj):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            route = urlsplit(self.path).path
            if route in ("/", "/index.html"):
                html = (studio / "index.html").read_text(encoding="utf-8")
                injection = (
                    '<script>window.BSTUDIO_FAL_TOKEN=' + json.dumps(token) +
                    ';</script><script src="/assets/fal-video-button.js" defer></script>'
                )
                html = html.replace("</body>", injection + "</body>")
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            elif route == "/api/fal/health":
                self.reply(200, {"bridge": "OK", "key_configured": bool(os.getenv("FAL_KEY")),
                                 "model": MODEL, "cost_estimate_usd": ESTIMATED_USD})
            else:
                super().do_GET()

        def do_POST(self):
            if urlsplit(self.path).path != "/api/fal/generate":
                return self.reply(404, {"error": "Ruta desconocida"})
            if (self.headers.get("Origin") != origin or
                    self.headers.get("X-Barriga-Fal-Token") != token):
                return self.reply(403, {"error": "Solicitud no autorizada"})
            if self.headers.get("Content-Type", "").split(";")[0].strip() != "application/json":
                return self.reply(415, {"error": "Se requiere JSON"})
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 1 <= size <= MAX_BODY:
                    return self.reply(413, {"error": "Solicitud demasiado grande"})
                args = validate_request(json.loads(self.rfile.read(size)))
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                return self.reply(400, {"error": str(exc)})
            if not os.getenv("FAL_KEY"):
                return self.reply(503, {"error": "FAL_KEY no esta cargada en este servidor."})
            if not lock.acquire(blocking=False):
                return self.reply(409, {"error": "Ya hay una generacion en proceso."})
            try:
                import fal_client
                result = fal_client.subscribe(MODEL, arguments=args)
                video_url = (result.get("video") or {}).get("url")
                if not isinstance(video_url, str) or not video_url.startswith("https://"):
                    raise RuntimeError("El proveedor no devolvio una URL de video HTTPS.")
                self.reply(200, {"model": MODEL, "video_url": video_url,
                                 "estimated_usd": ESTIMATED_USD})
            except Exception as exc:
                # Never include traceback, headers or secret in client response.
                print("fal generation failed:", type(exc).__name__, flush=True)
                self.reply(502, {"error": "Fallo la generacion (" + type(exc).__name__ +
                                 "). Comprueba el estado en fal antes de reintentar; podrian existir cargos."})
            finally:
                lock.release()
    return Handler


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--studio", type=Path, default=Path.cwd())
    p.add_argument("--port", type=int, default=8877)
    p.add_argument("--no-browser", action="store_true")
    args = p.parse_args()
    studio = args.studio.expanduser().resolve()
    if not (studio / "index.html").is_file() or not (studio / "assets/fal-video-button.js").is_file():
        p.error("Faltan index.html o assets/fal-video-button.js; instala el archivo en la carpeta del proyecto.")
    if not 1024 <= args.port <= 65535:
        p.error("Puerto invalido")
    lock = threading.Lock()
    handler = handler_factory(studio, secrets.token_urlsafe(32), args.port, lock)
    with ThreadingHTTPServer((HOST, args.port), handler) as server:
        url = "http://%s:%s/" % (HOST, args.port)
        print("B STUDIO + fal.ai (local): " + url, flush=True)
        print("Generacion DE PAGO solo tras confirmacion individual en el boton.", flush=True)
        if not args.no_browser:
            import webbrowser
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Servidor detenido.", flush=True)


if __name__ == "__main__":
    main()
