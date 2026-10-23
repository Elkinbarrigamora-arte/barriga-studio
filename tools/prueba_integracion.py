#!/usr/bin/env python3
"""Prueba NO invasiva de Barriga IA + Barriga Studio: no activa trabajo nocturno."""
import argparse
import json
import os
from pathlib import Path
import plistlib
import shutil
import subprocess
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

OLLAMA = "http://127.0.0.1:11434"
MODEL = "qwen2.5-coder:14b"

def item(name, status, detail, evidence=None):
    return dict(componente=name, estado=status, detalle=detail, evidencia=evidence)

def studio_check(path):
    p = path.expanduser().resolve()
    if not (p / "index.html").is_file():
        return item("Studio", "FALLO", "No se encuentra index.html", str(p))
    try:
        g = subprocess.run(["git", "-C", str(p), "rev-parse", "--show-toplevel"],
                           capture_output=True, text=True, timeout=5)
        if g.returncode != 0:
            return item("Studio", "PARCIAL", "Interfaz presente pero repositorio Git no verificado", str(p))
    except (OSError, subprocess.TimeoutExpired):
        return item("Studio", "PARCIAL", "Interfaz presente pero Git no comprobado", str(p))
    return item("Studio", "OK", "Interfaz y repositorio presentes; conexion con IA no comprobada", str(p))

def supervisor_check():
    root = Path.home() / "Library/Application Support/BarrigaIA/Autodesarrollo"
    agent = Path.home() / "Library/LaunchAgents/com.barriga.ia.autodesarrollo.plist"
    if not (root / "barriga_autodesarrollo.py").is_file():
        return item("Supervisor", "FALLO", "No se encontro barriga_autodesarrollo.py")
    if not agent.is_file():
        return item("Supervisor", "PARCIAL", "Script presente, pero LaunchAgent no localizado")
    try:
        with agent.open("rb") as f:
            conf = plistlib.load(f)
        args = conf.get("ProgramArguments", [])
        if "revisar" in args:
            return item("Supervisor", "SOLO_DIAGNOSTICO", "Servicio ejecuta revisar, no desarrollo autonomo",
                        {"intervalo": conf.get("StartInterval")})
        return item("Supervisor", "PARCIAL", "Servicio localizado; funcion por verificar",
                    {"accion": str(args[-1]) if args else None})
    except (ValueError, TypeError, OSError) as e:
        return item("Supervisor", "FALLO", "No se pudo leer plist: " + type(e).__name__)

def ollama_check(model):
    try:
        with urlopen(OLLAMA + "/api/tags", timeout=5) as r:
            tags = json.load(r)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as e:
        return [item("Ollama", "FALLO", "Servidor no responde: " + type(e).__name__),
                item("Inferencia real", "NO_PROBADA", "Sin conexion al servidor")]
    names = [x.get("name", "") for x in tags.get("models", []) if isinstance(x, dict)]
    if model not in names:
        return [item("Ollama", "OK", "Servidor responde", names),
                item("Inferencia real", "FALLO", "Modelo requerido no encontrado", model)]
    data = {"model": model, "prompt": "Responde exactamente BARRIGA_OK", "stream": False,
            "options": {"temperature": 0, "num_predict": 32}}
    req = Request(OLLAMA + "/api/generate", method="POST",
                  data=json.dumps(data).encode("utf-8"),
                  headers={"Content-Type": "application/json"})
    start = time.monotonic()
    try:
        with urlopen(req, timeout=180) as response:
            answer = str(json.load(response).get("response", ""))
        status = "OK" if "BARRIGA_OK" in answer else "FALLO"
        return [item("Ollama", "OK", "Servidor y modelo presentes", model),
                item("Inferencia real", status, "Respuesta producida por el modelo",
                     {"respuesta": answer[:120], "segundos": round(time.monotonic() - start, 1)})]
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as e:
        return [item("Ollama", "OK", "Servidor y modelo presentes", model),
                item("Inferencia real", "FALLO", "Fallo de inferencia: " + type(e).__name__)]

def clip_check(path):
    if not path:
        return item("Video 5s", "NO_PROBADO", "No se proporciono MP4 real")
    if not path.expanduser().is_file():
        return item("Video 5s", "FALLO", "El archivo MP4 no existe")
    if not shutil.which("ffprobe"):
        return item("Video 5s", "NO_PROBADO", "ffprobe no disponible")
    try:
        c = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                            "format=duration,size", "-of", "json", str(path.expanduser())],
                           capture_output=True, text=True, timeout=15, check=True)
        info = json.loads(c.stdout)["format"]
        duration, size = float(info["duration"]), int(info["size"])
        if 3 <= duration <= 7 and size > 0:
            return item("Video 5s", "PARCIAL", "MP4 comprobado; movimiento corporal requiere inspeccion visual",
                        {"segundos": duration, "bytes": size})
        return item("Video 5s", "FALLO", "Duracion o contenido incorrecto",
                    {"segundos": duration, "bytes": size})
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError,
            subprocess.TimeoutExpired) as e:
        return item("Video 5s", "FALLO", "Error en ffprobe: " + type(e).__name__)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--studio", type=Path,
                   default=Path(os.environ.get("BARRIGA_STUDIO_DIR") or os.getcwd()))
    p.add_argument("--modelo", default=MODEL)
    p.add_argument("--clip", type=Path)
    p.add_argument("--salida", type=Path)
    args = p.parse_args()
    checks = [studio_check(args.studio), supervisor_check()] + ollama_check(args.modelo)
    checks += [item("FFmpeg", "OK" if shutil.which("ffmpeg") else "FALLO",
                    "Detectado" if shutil.which("ffmpeg") else "No detectado"),
               item("Draw Things API", "NO_PROBADA", "Requiere prueba real de la API, puerto no asumido"),
               item("Conexion IA-Studio", "NO_PROBADA", "No hay prueba de llamada autenticada extremo a extremo"),
               item("Agentes de investigacion", "NO_PROBADOS", "No hay evidencia de ciclos reales de investigacion"),
               clip_check(args.clip)]
    report = {"tipo": "prueba_previa_nocturna", "trabajo_nocturno_habilitado": False,
              "prueba_integral_superada": all(x["estado"] == "OK" for x in checks),
              "resultados": checks,
              "advertencia": "No instala, no genera videos, no entrena pesos, no modifica servicios."}
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    print(payload)
    if args.salida:
        target = args.salida.expanduser()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(payload + "\n", encoding="utf-8")
    return 0 if report["prueba_integral_superada"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
