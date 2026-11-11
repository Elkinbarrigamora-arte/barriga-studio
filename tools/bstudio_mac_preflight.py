#!/usr/bin/env python3
"""Read-only local Mac preflight for a single B STUDIO production release.

Does NOT read API keys, mutate projects, install software, open ports or upload data.
"""
import argparse
import json
import platform
import shutil
import socket
import subprocess
from pathlib import Path


def tool_check(name):
    path = shutil.which(name)
    return {"available": bool(path), "binary": path}


def git_info(root):
    if not (root / ".git").exists():
        return {"repository": False, "dirty": None, "tracked_modifications": None,
                "untracked": None, "branch": None}
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "status", "--porcelain=v1", "-uno"],
            capture_output=True, text=True, timeout=15, check=True
        )
        other = subprocess.run(
            ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, timeout=15, check=True
        )
        branch = subprocess.run(
            ["git", "-C", str(root), "branch", "--show-current"],
            capture_output=True, text=True, timeout=15, check=True
        )
        tracked = len(result.stdout.splitlines())
        extra = len(other.stdout.splitlines())
        return {"repository": True, "dirty": bool(tracked or extra),
                "tracked_modifications": tracked, "untracked": extra,
                "branch": branch.stdout.strip() or "(HEAD separado)"}
    except (subprocess.SubprocessError, OSError):
        return {"repository": True, "error": "No se pudo leer estado Git"}


def port_listening(host, port):
    try:
        with socket.create_connection((host, port), timeout=0.3):
            return True
    except OSError:
        return False


def inventory(root):
    # Count only — never print sensitive project names or media paths.
    output = {}
    paths = {
        "motor_video": root / "tools" / "bstudio_video",
        "elevenlabs": root / "tools" / "bstudio_elevenlabs",
        "drawthings": root / "tools" / "bstudio_drawthings",
        "puente_video_fal": root / "tools" / "fal_studio_server.py",
        "puente_central": root / "tools" / "puente_central.py",
        "generador_guiones": root / "tools" / "puente_local.py",
        "frontend": root / "index.html",
    }
    for name, path in paths.items():
        output[name] = {"exists": path.exists(), "kind": "dir" if path.is_dir() else "file"}
    return output


def inspect(root):
    checks = {name: tool_check(name) for name in
              ("python3", "git", "node", "npx", "ffmpeg", "ffprobe")}
    info = {
        "sistema": platform.system(),
        "arquitectura": platform.machine(),
        "mac_root_exists": root.is_dir(),
        "tools": checks,
        "repo": git_info(root),
        "components": inventory(root),
        "local_listeners": {
            str(port): port_listening("127.0.0.1", port)
            for port in (11434, 8766, 8771, 7871)
        },
    }
    blockers = []
    if not root.is_dir():
        blockers.append("La carpeta principal no existe.")
    if info["repo"].get("dirty"):
        blockers.append("Git tiene cambios locales sin publicar: conservar respaldo antes de integrar.")
    if not info["tools"]["ffmpeg"]["available"] or not info["tools"]["ffprobe"]["available"]:
        blockers.append("FFmpeg y FFprobe requieren instalación o ubicación válida en PATH.")
    if not info["tools"]["node"]["available"]:
        blockers.append("Node.js no disponible para pruebas y motores de integración.")
    if not info["components"]["frontend"]["exists"]:
        blockers.append("No se encontró la interfaz principal index.html.")
    if not info["components"]["motor_video"]["exists"]:
        blockers.append("No se observa la carpeta local del motor de video.")
    info["readiness"] = {
        "local_inventory_complete": len(blockers) == 0,
        "final_release_certified": False,
        "remaining_required": [
            "Auditar código y archivos locales sin perder contenido",
            "Verificar conectividad real del proveedor, voces y motor de video",
            "Probar escenas reales, MP4 de 35 segundos y controles de UI",
            "Hacer respaldo restaurable y ensayar rollback",
            "Ejecutar regresión y validar despliegue existente"
        ],
        "blockers": blockers,
    }
    return info


def main():
    parser = argparse.ArgumentParser(description="B STUDIO: diagnóstico local de solo lectura")
    parser.add_argument("--studio", type=Path, default=Path.home() / "barriga-studio")
    args = parser.parse_args()
    print(json.dumps(inspect(args.studio.expanduser().resolve()),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
