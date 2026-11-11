#!/usr/bin/env python3
"""Start the existing B STUDIOS ÉLITE Mac app under ONE public local URL.

Does not modify or overwrite the original application. Starts its central
bridge on a private loopback upstream and exposes only the original /studio URL,
enriched with the verified private AI/audio/media integration overlay.
Refuses to interrupt an occupied official port or duplicate running jobs.
"""
import argparse
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

from bstudio_elite_gateway import main as gateway_main

HOST = "127.0.0.1"


def port_is_in_use(port):
    with socket.socket() as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((HOST, port)) == 0


def is_http_studio_ready(port):
    try:
        request = urllib.request.Request(
            f"http://{HOST}:{port}/studio", headers={"Accept": "text/html"})
        with urllib.request.urlopen(request, timeout=2) as res:
            return (res.status == 200
                    and "text/html" in res.headers.get("Content-Type", "").lower())
    except (OSError, urllib.error.HTTPError):
        return False


def find_interpreter(studio):
    local_python = studio / ".venv" / "bin" / "python"
    return str(local_python) if local_python.is_file() else sys.executable


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--studio", type=Path, default=Path.home()/"barriga-studio")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--internal-port", type=int, default=8782)
    parser.add_argument("--media-dir", type=Path,
                        default=Path.home()/"Movies"/"BarrigaStudio")
    parser.add_argument("--voices-dir", type=Path)
    parser.add_argument("--task-id", default="")
    parser.add_argument("--model", default="auto")
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    if args.port == args.internal_port or not (1024 <= args.port <= 65535
                                               and 1024 <= args.internal_port <= 65535):
        raise SystemExit("ERROR: puertos incompatibles.")
    studio = args.studio.expanduser().resolve()
    central = studio / "tools" / "puente_central.py"
    if not central.is_file():
        raise SystemExit(
            "BLOQUEADO: no existe tools/puente_central.py en la carpeta indicada. "
            "No se reemplazó ni creó ninguna plataforma."
        )
    if port_is_in_use(args.port):
        raise SystemExit(
            f"BLOQUEADO: el puerto oficial {args.port} está ocupado. "
            "La versión actual sigue abierta y no será detenida automáticamente. "
            "Detén su servidor con Ctrl+C cuando no haya trabajos en curso y repite."
        )
    if port_is_in_use(args.internal_port):
        raise SystemExit(
            f"BLOQUEADO: el puerto interno {args.internal_port} está ocupado. "
            "No se reinició ni interrumpió ningún servicio."
        )
    runtime = Path(__file__).resolve().parents[1]/"assets"/"bstudio-runtime.js"
    if not runtime.is_file():
        raise SystemExit("BLOQUEADO: falta el módulo del panel integrado.")
    python = find_interpreter(studio)
    # The existing application is not modified, copied into GitHub or deleted.
    # It owns all its original data and project paths, and still runs from its cwd.
    command = [python, str(central), "--puerto", str(args.internal_port)]
    child = subprocess.Popen(
        command, cwd=str(studio), stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        healthy = False
        for _ in range(100):
            if child.poll() is not None:
                raise RuntimeError(
                    "El puente central existente se detuvo al iniciar. "
                    "Revisa sus dependencias o inícialo manualmente para diagnosticarlo."
                )
            if is_http_studio_ready(args.internal_port):
                healthy = True
                break
            time.sleep(0.3)
        if not healthy:
            raise RuntimeError(
                "El puente original no pudo servir /studio en 30 segundos. "
                "No se publicó una pantalla de reemplazo."
            )
        gateway_args = [
            "--port", str(args.port), "--upstream-port", str(args.internal_port),
            "--media-dir", str(args.media_dir), "--model", args.model,
        ]
        if args.voices_dir:
            gateway_args += ["--voices-dir", str(args.voices_dir)]
        if args.task_id:
            gateway_args += ["--task-id", args.task_id]
        if args.no_browser:
            gateway_args.append("--no-browser")
        print("Se confirmó el /studio EXISTENTE en el puente central.",flush=True)
        print("Integrando interfaz oficial con los motores que estén realmente listos.", flush=True)
        return gateway_main(gateway_args)
    except KeyboardInterrupt:
        print("Deteniendo solo los procesos de esta ejecución.", flush=True)
    except (OSError, RuntimeError) as exc:
        raise SystemExit("B STUDIO ÉLITE no pudo activar la integración: " + str(exc))
    finally:
        # Only terminate the child this launcher created; never kill a prior
        # Studio session or other local processes.
        if child.poll() is None:
            child.terminate()
            try:
                child.wait(timeout=6)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3)


if __name__=="__main__":
    main()
