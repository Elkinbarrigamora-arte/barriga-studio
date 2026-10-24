#!/usr/bin/env python3
"""Capturas auditables de la web estática real (sin Ollama ni APIs de pago).

Opcional: requiere Chrome/Chromium presente. Si falta, informa el bloqueo.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import threading

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "evidencia-ui")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    browser = next((shutil.which(x) for x in (
        "google-chrome", "chromium", "chromium-browser", "microsoft-edge")
        if shutil.which(x)), None)
    report = {
        "escenario": "Studio estático, proyectos del navegador de pruebas vacío",
        "ollama_probado": False,
        "video_generado": False,
        "referencia_comparada": False,
        "navegador": browser or "no disponible",
        "capturas": {},
    }
    if not browser:
        report["bloqueo"] = "Chrome/Chromium no instalado: sin capturas reales"
        (args.output / "estado.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(report["bloqueo"])
        return

    handler = partial(QuietHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = "http://127.0.0.1:{}/".format(server.server_address[1])
        base = [
            browser, "--headless", "--no-sandbox", "--disable-gpu",
            "--disable-dev-shm-usage", "--disable-background-networking",
            "--hide-scrollbars", "--virtual-time-budget=2500",
        ]
        # Comprobar que no se omitió el JS dinámico.
        dom = subprocess.run(base + ["--dump-dom", url], text=True,
                             capture_output=True, timeout=40)
        if dom.returncode:
            raise RuntimeError("El navegador no pudo iniciar: " + dom.stderr[-600:])
        for marker in ('id="studio-project-tools"', 'class="studio-scene"',
                       'id="studio-video"', 'id="studio-music"',
                       'id="studio-completar-ia"'):
            if marker not in dom.stdout:
                raise RuntimeError("La interfaz no montó el elemento " + marker)
        for name, size in (("escritorio-1536x1024.png", "1536,1024"),
                           ("movil-390x844.png", "390,844")):
            filename = args.output / name
            command = base + [
                "--window-size=" + size,
                "--screenshot=" + str(filename),
                url
            ]
            run = subprocess.run(command, text=True, capture_output=True, timeout=40)
            if run.returncode or not filename.is_file() or filename.stat().st_size < 1000:
                raise RuntimeError("Captura no disponible: " + name + " " + run.stderr[-450:])
            report["capturas"][name] = filename.stat().st_size
            print("Captura comprobada:", filename, filename.stat().st_size, "bytes")
        report["estado"] = "Capturas creadas; comparación con referencia aún pendiente"
    finally:
        server.shutdown()
        thread.join(timeout=4)
        server.server_close()
        (args.output / "estado.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
