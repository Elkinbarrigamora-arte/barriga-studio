#!/usr/bin/env python3
"""Recover an existing PoYo video using the authenticated CLI keyring.

READ-ONLY with respect to PoYo tasks: never submits or generates a new task.
Uses JSON CLI output instead of the truncated human-readable table.
"""
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

TASK_RE = re.compile(r"^[A-Za-z0-9_-]{8,100}$")
# Pin the known CLI version; credentials remain in the Mac keyring.
CLI_PACKAGE = "@poyoapi/cli@0.1.19"
MAX_DOWNLOAD = 250 * 1024 * 1024


def parse_task(raw):
    """Parse the CLI's machine-readable JSON, preserving the full file URL."""
    try:
        payload = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "La CLI no devolvió JSON. Comprueba que acepte --format json."
        ) from exc
    if isinstance(payload, list) and len(payload) == 1:
        payload = payload[0]
    if not isinstance(payload, dict):
        raise ValueError("Respuesta JSON de PoYo inesperada.")
    if "data" in payload and isinstance(payload["data"], dict):
        payload = payload["data"]
    return payload


def find_video_url(data):
    """Accept files in PoYo's documented arrays, never a guessed/truncated URL."""
    raw_files = data.get("files") or data.get("outputs") or data.get("output") or []
    if isinstance(raw_files, str):
        try:
            raw_files = json.loads(raw_files)
        except ValueError:
            raw_files = [raw_files]
    if isinstance(raw_files, dict):
        raw_files = [raw_files]
    if not isinstance(raw_files, list):
        raise ValueError("La estructura de archivos de PoYo es inesperada.")
    urls = []
    for item in raw_files:
        if isinstance(item, str):
            urls.append(item)
        elif isinstance(item, dict):
            for key in ("file_url", "url", "video_url"):
                if isinstance(item.get(key), str):
                    urls.append(item[key])
                    break
    for url in urls:
        if urlparse(url).path.lower().endswith(".mp4"):
            return url
    if urls:
        return urls[0]
    raise ValueError("La tarea no incluye una URL de video en files.")


def validate_download_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        raise ValueError("PoYo devolvió una URL de archivo no HTTPS.")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError("URL de archivo no permitida.")
    host = parsed.hostname.lower()
    if host in ("localhost",) or host.endswith(".localhost"):
        raise ValueError("No se permiten enlaces locales.")
    # Provider media hosts: extend after validating an actual provider response.
    allowed = ("cdn.doculator.org", "storage.poyo.ai", "cdn.poyo.ai")
    if host not in allowed:
        raise ValueError(
            "Host multimedia no reconocido: " + host +
            ". Revisa el dominio antes de autorizarlo en el código."
        )
    return url


def read_existing_task(task_id, runner=subprocess.run):
    if not TASK_RE.fullmatch(task_id):
        raise ValueError("ID de tarea inválido.")
    if not shutil.which("npx"):
        raise RuntimeError("No se encontró npx; instala Node.js 20 o posterior.")
    command = [
        "npx", "-y", CLI_PACKAGE, "task", "get", task_id,
        "--format", "json",
    ]
    result = runner(command, text=True, capture_output=True, timeout=120, check=False)
    if result.returncode != 0:
        # PoYo CLI's exitCodeFor(): 3 is HTTP 401 or 403, not a JSON format error.
        # Do not echo stderr because it can contain private account information.
        if result.returncode == 3:
            raise RuntimeError(
                "PoYo rechazó la autenticación o el acceso a esta tarea "
                "(HTTP 401/403). Comprueba con la misma CLI: "
                "'npx -y " + CLI_PACKAGE + " auth status' y "
                "'npx -y " + CLI_PACKAGE + " account'. "
                "No vuelvas a enviar la generación."
            )
        raise RuntimeError(
            "No se pudo consultar la tarea existente (salida CLI " +
            str(result.returncode) + "). No se generó ningún video nuevo."
        )
    data = parse_task(result.stdout)
    reported_id = data.get("task_id")
    if reported_id is not None and reported_id != task_id:
        raise RuntimeError("La respuesta de PoYo identifica otra tarea. No se descargó ningún archivo.")
    return data


class MediaRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # urllib resolves relative redirects before calling this method.
        validate_download_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def save_video(url, destination, opener=None, probe=None):
    validate_download_url(url)
    if opener is None:
        opener = build_opener(MediaRedirectHandler()).open
    if probe is None:
        probe = probe_video
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp_name = None
    try:
        req = Request(url, headers={"User-Agent": "BarrigaStudio/1.0"})
        with opener(req, timeout=90) as response:
            final_url = response.geturl() if hasattr(response, "geturl") else url
            validate_download_url(final_url)
            content_length = response.headers.get("Content-Length") if hasattr(response, "headers") else None
            if content_length and int(content_length) > MAX_DOWNLOAD:
                raise ValueError("Archivo supera 250 MB.")
            with tempfile.NamedTemporaryFile(
                prefix=".poyo-", suffix=".part",
                dir=destination.parent, delete=False
            ) as out:
                tmp_name = out.name
                total = 0
                while True:
                    chunk = response.read(128 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_DOWNLOAD:
                        raise ValueError("Descarga supera 250 MB.")
                    out.write(chunk)
            if content_length is not None and total != int(content_length):
                raise ValueError("La descarga no coincide con el tamaño anunciado.")
        with open(tmp_name, "rb") as video:
            header = video.read(12)
        if len(header) < 12 or header[4:8] != b"ftyp":
            raise ValueError("PoYo devolvió un archivo que no parece MP4.")
        details = probe(Path(tmp_name))
        # The staging file is in the same directory. A hard link publishes it
        # atomically without replacing another recovery or an existing file.
        os.link(tmp_name, destination)
        return total, details
    finally:
        if tmp_name and os.path.exists(tmp_name):
            os.unlink(tmp_name)


def probe_video(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("La ruta debe contener un archivo MP4 regular.")
    if not shutil.which("ffprobe"):
        raise RuntimeError("Se necesita FFprobe para verificar el MP4.")
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries",
         "format=format_name,duration:stream=codec_type,width,height",
         "-of", "json", str(path)],
        capture_output=True, text=True, timeout=45, check=False
    )
    if result.returncode != 0:
        raise RuntimeError("ffprobe no pudo validar el archivo MP4.")
    details = json.loads(result.stdout)
    info = details.get("format", {})
    if "mp4" not in info.get("format_name", "").split(","):
        raise RuntimeError("FFprobe no reconoció un contenedor MP4.")
    streams = details.get("streams", [])
    videos = [s for s in streams if s.get("codec_type") == "video"
              and s.get("width", 0) > 0 and s.get("height", 0) > 0]
    if not videos:
        raise RuntimeError("El archivo no contiene pista de video.")
    duration = float(info.get("duration", 0))
    if not math.isfinite(duration) or duration <= 0:
        raise RuntimeError("El archivo no tiene una duración de video válida.")
    digest = hashlib.sha256()
    with path.open("rb") as media:
        for chunk in iter(lambda: media.read(128 * 1024), b""):
            digest.update(chunk)
    return {
        "sha256": digest.hexdigest(),
        "duracion_segundos": duration,
        "tiene_audio": any(s.get("codec_type") == "audio" for s in streams),
        "video": videos,
    }


def main():
    parser = argparse.ArgumentParser(description="Recuperar MP4 existente de PoYo sin generar")
    parser.add_argument("task_id", help="ID de tarea PoYo ya creada")
    parser.add_argument("--output-dir", type=Path, default=Path.home() / "Movies" / "BarrigaStudio")
    parser.add_argument("--status-only", action="store_true", help="Consultar sin descargar")
    args = parser.parse_args()
    try:
        data = read_existing_task(args.task_id)
        status = str(data.get("status") or data.get("raw_status") or "").lower()
        print("Estado PoYo:", status or "desconocido")
        if status not in ("succeeded", "finished", "completed", "success"):
            print("La tarea todavía no está terminada. No se enviará otra generación.")
            return 2
        url = find_video_url(data)
        validate_download_url(url)
        if args.status_only:
            print("Video disponible. Usa el comando sin --status-only para recuperarlo.")
            return 0
        destination = args.output_dir.expanduser() / ("poyo-" + args.task_id + ".mp4")
        if destination.exists() or destination.is_symlink():
            details = probe_video(destination)
            details["vinculo_tarea"] = "archivo_preexistente_no_confirmado"
            print("Archivo ya existe; no se sobrescribe:", destination)
            print("Validación:", json.dumps(details, ensure_ascii=False))
            return 0
        size, details = save_video(url, destination)
        details["vinculo_tarea"] = (
            "id_confirmado_por_proveedor" if data.get("task_id") == args.task_id
            else "consulta_por_id_sin_confirmacion_en_respuesta"
        )
        print("Video descargado:", destination)
        print("Tamaño:", size, "bytes")
        print("Validación:", json.dumps(details, ensure_ascii=False))
        return 0
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        print("Error:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
