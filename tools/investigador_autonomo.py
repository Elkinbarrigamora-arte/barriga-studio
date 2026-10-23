#!/usr/bin/env python3
"""Investigador local y conservador de Barriga IA.

Lee canales de novedades publicos predefinidos, registra evidencia y sugiere
revisiones. No modifica Studio, no ejecuta contenido de internet, no publica
proyectos ni utiliza APIs de pago.
"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import plistlib
import re
import tempfile
from urllib.parse import urlparse
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

FEEDS = {
    "Ollama": "https://github.com/ollama/ollama/releases.atom",
    "ComfyUI": "https://github.com/Comfy-Org/ComfyUI/releases.atom",
    "llama.cpp": "https://github.com/ggml-org/llama.cpp/releases.atom",
}
TOPICS = {
    "video": ("video", "animation", "motion", "wan", "frame", "temporal", "render"),
    "voz": ("audio", "voice", "speech", "tts", "kokoro", "multispeaker"),
    "continuidad": ("consisten", "reference", "character", "identity", "scene"),
    "motor_local": ("inference", "memory", "metal", "quantiz", "model", "performance"),
}
SUGGESTIONS = {
    "video": "Revisar compatibilidad con generacion de clips reales; no activar hasta prueba local.",
    "voz": "Evaluar motor de voz expresiva y comprobar idioma y continuidad de voz.",
    "continuidad": "Probar referencias fijas de personajes y escenas antes de integrarlas.",
    "motor_local": "Medir consumo de memoria y rendimiento del equipo antes de cambiar motores.",
}
MAX_BYTES = 250_000
NS = {"a": "http://www.w3.org/2005/Atom"}
AGENT = "com.barriga.studio.investigacion"


def private_dir():
    path = Path.home() / "Library" / "Application Support" / "BarrigaStudio" / "Investigacion"
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path, 0o700)
    return path


def clean(text, limit=360):
    return re.sub(r"\\s+", " ", text or "").strip()[:limit]


def topics_for(text):
    lower = text.lower()
    return [topic for topic, words in TOPICS.items() if any(w in lower for w in words)]


def parse_atom(raw, source, expected_host="github.com"):
    root = ET.fromstring(raw)
    items = []
    for entry in root.findall("a:entry", NS)[:20]:
        title = clean(entry.findtext("a:title", "", NS), 180)
        updated = clean(entry.findtext("a:updated", "", NS), 50)
        url = ""
        for link in entry.findall("a:link", NS):
            if link.get("rel", "alternate") == "alternate":
                url = link.get("href", "")
                break
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != expected_host:
            continue
        summary = clean(entry.findtext("a:summary", "", NS), 300)
        topic = topics_for(title + " " + summary)
        if not topic:
            topic = ["motor_local"] if source in ("Ollama", "llama.cpp") else ["video"]
        items.append({"fuente": source, "titulo": title, "enlace": url,
                      "publicado": updated, "temas": topic,
                      "extracto": summary})
    return items


def fetch(name, url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "github.com" or url != FEEDS[name]:
        raise ValueError("Fuente no autorizada")
    request = Request(url, headers={"User-Agent": "BarrigaStudio-Investigador/1.0",
                                    "Accept": "application/atom+xml"})
    with urlopen(request, timeout=14) as response:
        final_url = urlparse(response.geturl())
        if final_url.scheme != "https" or final_url.hostname != "github.com":
            raise ValueError("Redireccion fuera de fuentes aprobadas")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Fuente supera limite")
    return parse_atom(raw, name)


def write_private(path, data):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".investigacion-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as out:
            json.dump(data, out, ensure_ascii=False, indent=2)
            out.write("\\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def research(directory, fetcher=fetch):
    previous = directory / "hallazgos.json"
    old = {"hallazgos": []}
    if previous.exists():
        try:
            old = json.loads(previous.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            # Nunca sobrescribir informacion previa ilegible.
            return {"estado": "DETENIDO", "motivo": "Respaldo anterior no legible"}
    seen = {entry.get("enlace") for entry in old.get("hallazgos", []) if isinstance(entry, dict)}
    collected = list(old.get("hallazgos", []))
    news = []
    errors = []
    for name, url in FEEDS.items():
        try:
            entries = fetcher(name, url)
            for entry in entries:
                if entry["enlace"] not in seen:
                    news.append(entry)
                    seen.add(entry["enlace"])
                    collected.append(entry)
        except Exception as exc:
            errors.append({"fuente": name, "tipo_error": type(exc).__name__})
    collected = collected[-150:]
    now = datetime.now(timezone.utc).isoformat()
    report = {"version": 1, "ultima_revision": now, "hallazgos": collected}
    suggestions = sorted({SUGGESTIONS[t] for item in news for t in item["temas"]})
    result = {"estado": "OK" if len(errors) < len(FEEDS) else "SIN_FUENTES",
              "fecha": now, "nuevos": len(news), "fuentes_consultadas": len(FEEDS),
              "errores": errors, "propuestas_para_revision": suggestions,
              "aviso": "Novedades externas sin prueba local; nada se ha implementado."}
    if result["estado"] != "SIN_FUENTES":
        write_private(previous, report)
    write_private(directory / "ultimo_reporte.json", result)
    return result


def install():
    directory = private_dir()
    agents = Path.home() / "Library" / "LaunchAgents"
    agents.mkdir(parents=True, exist_ok=True)
    path = agents / (AGENT + ".plist")
    content = {"Label": AGENT, "ProgramArguments": [os.sys.executable,
               str(Path(__file__).resolve()), "--una-vez"],
               "StartInterval": 43200, "RunAtLoad": True,
               "StandardOutPath": str(directory / "salida.log"),
               "StandardErrorPath": str(directory / "errores.log")}
    with path.open("wb") as fp:
        plistlib.dump(content, fp)
    os.chmod(path, 0o600)
    # Instalacion por usuario: no se inicia nada sin el comando explicito launchctl.
    return {"estado": "CONFIGURADO", "plist": str(path),
            "periodicidad_horas": 12, "activado": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--una-vez", action="store_true")
    action.add_argument("--preparar-programacion", action="store_true")
    args = parser.parse_args()
    result = install() if args.preparar_programacion else research(private_dir())
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
