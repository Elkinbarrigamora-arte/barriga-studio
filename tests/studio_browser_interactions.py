#!/usr/bin/env python3
"""Pruebas end-to-end con Chromium en una sesión aislada de almacenamiento local.

Requiere pip install playwright y Chrome/Chromium instalado.
No conecta Ollama, no publica nada y no lee los proyectos del usuario.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import shutil
import subprocess
import tempfile
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass


def run():
    browser_path = next((shutil.which(n) for n in (
        "google-chrome", "chromium", "chromium-browser", "microsoft-edge")
        if shutil.which(n)), None)
    if not browser_path:
        raise RuntimeError("No existe un navegador Chrome/Chromium para pruebas de interacción")

    handler = partial(QuietHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    total = 0

    def verify(label, condition):
        nonlocal total
        if not condition:
            raise AssertionError("Falló la prueba: " + label)
        total += 1
        print("OK", label, flush=True)

    try:
        with tempfile.TemporaryDirectory() as tmp, sync_playwright() as playwright:
            directory = Path(tmp)
            image = directory / "referencia.png"
            # PNG válido de un píxel: no invocar motores generativos.
            import base64
            image.write_bytes(base64.b64decode(
                "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9uY9oAAAAASUVORK5CYII="
            ))
            video = directory / "video-real-de-prueba.mp4"
            ffmpeg = shutil.which("ffmpeg")
            if ffmpeg:
                subprocess.run([
                    ffmpeg, "-y", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=blue:s=160x120:d=1",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", str(video)
                ], check=True, timeout=18)
            else:
                # Un MP4 de prueba debe contener video real: no usar bytes inventados.
                print("AVISO: FFmpeg ausente; se omitirá reproducción y descarga de MP4")
            browser = playwright.chromium.launch(executable_path=browser_path,
                                               headless=True, args=["--no-sandbox"])
            context = browser.new_context(
                viewport={"width": 1536, "height": 1024},
                accept_downloads=True, locale="es-CO")
            page = context.new_page()
            exceptions = []
            page.on("pageerror", lambda error: exceptions.append(str(error)))
            page.goto("http://127.0.0.1:{}/".format(server.server_address[1]),
                      wait_until="domcontentloaded", timeout=30000)
            page.locator("#studio-project-tools").wait_for(timeout=15000)

            verify("Editor de cuatro columnas", page.locator(".studio-workspace > section").count() == 4)
            verify("Tres plantillas seleccionables", page.locator(".studio-template-card").count() == 3)
            page.locator(".studio-template-card").nth(1).get_by_role(
                "button", name="Usar plantilla").click()
            page.wait_for_timeout(150)
            verify("Seleccionar plantilla existente",
                   page.locator("#style").input_value() == "Fotorrealismo cinematográfico")

            page.locator("#voice").select_option("Español masculino")
            verify("Selección del tipo de voz", page.locator("#voice").input_value() == "Español masculino")
            page.locator("#studio-music").select_option("cinematic")
            verify("Preferencias musicales se conservan", page.evaluate(
                "JSON.parse(localStorage.getItem('barriga-studio-ui-preferences-v1')).music"
            ) == "cinematic")

            page.locator("#name").fill("Proyecto de prueba auditada")
            idea = "La carta de ayer cuenta una verdad que cambió a dos hermanos."
            page.locator("#script").fill(idea)
            page.locator("#format").select_option("Horizontal 16:9")
            page.locator("#duration").select_option("60 segundos")
            verify("Contador de caracteres", str(len(idea)) in
                   page.locator("#studio-char-count").inner_text())
            page.locator("#reference").set_input_files(str(image))
            verify("Miniatura de imagen local",
                   page.locator(".studio-ref-thumbnail").count() == 1)

            page.get_by_role("button", name="Guardar en Mis proyectos").click()
            records = page.evaluate(
                "JSON.parse(localStorage.getItem('barriga-studio-projects-v1'))")
            verify("Guardar borrador real",
                   len(records) == 1 and records[0]["script"] == idea)
            verify("Guardar formato y duración",
                   records[0]["format"] == "Horizontal 16:9" and
                   records[0]["duration"] == "60 segundos")
            verify("Estado inicial es borrador",
                   "Borrador" in page.locator(".studio-project-meta").first.inner_text())

            page.locator(".studio-project-star").first.click()
            page.locator('[data-filter="favoritos"]').click()
            verify("Filtrar favoritos", page.locator(".project:not([hidden])").count() == 1)
            page.locator("#studio-project-search").fill("sin coincidencia")
            verify("Buscador sin coincidencias", page.locator(".project:not([hidden])").count() == 0)
            page.locator("#studio-project-search").fill("prueba")
            verify("Buscador con coincidencia", page.locator(".project:not([hidden])").count() == 1)
            page.locator('[data-filter="proceso"]').click()
            verify("No inventar procesos activos", page.locator(".project:not([hidden])").count() == 0)
            page.locator('[data-filter="completados"]').click()
            verify("No inventar videos completados", page.locator(".project:not([hidden])").count() == 0)
            page.locator('[data-filter="favoritos"]').click()
            page.get_by_role("button", name="Cuadrícula").click()
            verify("Alternancia a cuadrícula", "studio-project-grid" in
                   page.locator("#projectList").get_attribute("class"))
            page.get_by_role("button", name="Lista").click()
            page.locator(".studio-project-menu summary").first.click()
            page.locator(".studio-project-menu").first.get_by_role(
                "button", name="Duplicar").click()
            verify("Duplicar sin sobrescribir",
                   len(page.evaluate(
                       "JSON.parse(localStorage.getItem('barriga-studio-projects-v1'))")) == 2)

            if video.exists():
                page.locator("#studio-local-video").set_input_files(str(video))
                verify("Reproductor de MP4 local visible", page.locator("#studio-video").is_visible())
                verify("Descarga de MP4 habilitada con archivo",
                       not page.get_by_role("button", name="Descargar video").is_disabled())
                with page.expect_download(timeout=12000) as down:
                    page.get_by_role("button", name="Descargar video").click()
                verify("Archivo local descargable",
                       down.value.suggested_filename == "video-real-de-prueba.mp4")
                page.wait_for_function(
                    "document.querySelector('#studio-video').readyState >= 1",
                    timeout=9000)
                duration = page.locator("#studio-video").evaluate("(el) => el.duration")
                verify("Metadatos y duración de MP4 real", duration > 0)
                page.locator("#studio-video").evaluate(
                    "(el) => {el.muted = true; return el.play()}")
                page.wait_for_function(
                    "document.querySelector('#studio-video').currentTime > 0.05",
                    timeout=9000)
                verify("Reproducción efectiva de video local",
                       page.locator("#studio-video").evaluate("(el) => el.currentTime") > 0.05)


            # Importar respaldo sin perder metadatos de guion y sin reemplazar.
            respaldo = directory / "respaldo.json"
            respaldo.write_text(json.dumps({
                "formato": "barriga-studio-respaldo", "version": 1,
                "proyectos": [{
                    "id": "respaldo-prueba", "name": "Proyecto recuperado",
                    "script": "Guion aprobado en borrador",
                    "ideaOriginal": "Idea original completa y diferente",
                    "ultimoGuion": "Último guion generado y guardado",
                    "style": "Frutas dramáticas 3D",
                    "format": "Vertical 9:16", "duration": "30 segundos",
                    "voice": "Español femenino", "date": "Prueba de respaldo"
                }]
            }, ensure_ascii=False), encoding="utf-8")
            page.get_by_label("Archivo de respaldo JSON").set_input_files(str(respaldo))
            page.wait_for_function(
                "JSON.parse(localStorage.getItem('barriga-studio-projects-v1')).length===3")
            restored = page.evaluate(
                "JSON.parse(localStorage.getItem('barriga-studio-projects-v1'))"
                ".find(p => p.id === 'respaldo-prueba')")
            verify("Restauración conserva premisa original",
                   restored["ideaOriginal"] == "Idea original completa y diferente")
            verify("Restauración conserva último guion",
                   restored["ultimoGuion"] == "Último guion generado y guardado")
            verify("Video neuronal no simulado",
                   page.get_by_role("button", name="Generar video").is_disabled())
            page.on("dialog", lambda dialog: dialog.accept())
            page.get_by_role("button", name="Nuevo proyecto").click()
            page.locator("#name").fill("Segundo proyecto independiente")
            page.locator("#script").fill("Guion nuevo")
            page.get_by_role("button", name="Guardar en Mis proyectos").click()
            items = page.evaluate(
                "JSON.parse(localStorage.getItem('barriga-studio-projects-v1'))")
            verify("Nuevo proyecto no sobrescribe anterior",
                   len(items) == 4 and any(
                       x["name"] == "Proyecto de prueba auditada" for x in items))

            page.set_viewport_size({"width": 390, "height": 844})
            page.wait_for_timeout(300)
            sizes = page.evaluate(
                "({scroll:document.documentElement.scrollWidth,"
                "client:document.documentElement.clientWidth})")
            verify("Móvil sin desbordamiento horizontal global",
                   sizes["scroll"] <= sizes["client"] + 1)
            verify("Sin errores JS sin controlar", not exceptions)
            browser.close()
    finally:
        server.shutdown()
        thread.join(timeout=3)
        server.server_close()
    print("PRUEBAS INTERACTIVAS APROBADAS: {}".format(total), flush=True)


if __name__ == "__main__":
    run()
