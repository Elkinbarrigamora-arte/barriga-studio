#!/usr/bin/env python3
"""Assemble already-rendered video scenes and an existing Spanish narration into MP4.

Local-only; no API calls, no new model generations, no paid provider requests.
Requires FFmpeg and FFprobe available on PATH.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

WIDTH = 480
HEIGHT = 854
FPS = 30


def require_media_tools():
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise RuntimeError(tool + " no está disponible en PATH.")
        

def probe(path, runner=subprocess.run):
    command = ["ffprobe", "-v", "error", "-show_entries",
               "format=duration:stream=codec_type,width,height",
               "-of", "json", str(path)]
    result = runner(command, text=True, capture_output=True, timeout=60, check=False)
    if result.returncode != 0:
        raise RuntimeError("FFprobe no pudo inspeccionar " + str(path))
    try:
        obj = json.loads(result.stdout)
        duration = float(obj["format"]["duration"])
    except (KeyError, ValueError, TypeError) as exc:
        raise RuntimeError("Duración multimedia inválida: " + str(path)) from exc
    if not math.isfinite(duration) or duration <= 0:
        raise RuntimeError("Archivo multimedia vacío o inválido.")
    return duration, obj.get("streams", [])


def read_manifest(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("El manifiesto debe ser un objeto JSON.")
    scenes = payload.get("scenes")
    if not isinstance(scenes, list) or not 1 <= len(scenes) <= 20:
        raise ValueError("Se requieren entre 1 y 20 escenas.")
    target = float(payload.get("target_seconds", 35))
    if not math.isfinite(target) or not 1 <= target <= 300:
        raise ValueError("Duración objetivo fuera de rango.")
    parsed = []
    for i, scene in enumerate(scenes):
        if not isinstance(scene, dict) or not isinstance(scene.get("file"), str):
            raise ValueError("Escena inválida: " + str(i + 1))
        f = Path(scene["file"]).expanduser().resolve()
        seconds = float(scene.get("seconds", 0))
        if not f.is_file() or not math.isfinite(seconds) or not 0.1 <= seconds <= 60:
            raise ValueError("Archivo o duración inválidos en escena " + str(i + 1))
        parsed.append((f, seconds))
    if abs(sum(s for _, s in parsed) - target) > 0.01:
        raise ValueError("La suma de las escenas debe coincidir con target_seconds.")
    voice = payload.get("voice")
    if not isinstance(voice, str) or not Path(voice).expanduser().is_file():
        raise ValueError("Falta el archivo de narración final en español.")
    return target, parsed, Path(voice).expanduser().resolve()


def build_command(scenes, voice, target, outfile):
    files = []
    for file, _ in scenes:
        files += ["-i", str(file)]
    files += ["-i", str(voice)]
    filters = []
    for i, (_, seconds) in enumerate(scenes):
        filters.append(
            f"[{i}:v:0]trim=duration={seconds:.4f},setpts=PTS-STARTPTS,"
            f"fps={FPS},scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
            f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}]"
        )
    joins = "".join(f"[v{i}]" for i in range(len(scenes)))
    filters.append(f"{joins}concat=n={len(scenes)}:v=1:a=0[v]")
    filters.append(
        f"[{len(scenes)}:a:0]atrim=duration={target:.4f},"
        "asetpts=PTS-STARTPTS[a]"
    )
    return (["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y"]
            + files + ["-filter_complex", ";".join(filters),
            "-map", "[v]", "-map", "[a]", "-c:v", "libx264",
            "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
            "-r", str(FPS), "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart", "-t", f"{target:.4f}",
            str(outfile)])


def validate_sources(target, scenes, voice):
    for file, seconds in scenes:
        duration, streams = probe(file)
        if not any(s.get("codec_type") == "video" for s in streams):
            raise ValueError("Escena sin pista de video: " + str(file))
        if duration + 0.05 < seconds:
            raise ValueError(
                "Escena demasiado corta; evitar congelar imágenes: " + str(file)
            )
    duration, streams = probe(voice)
    if not any(s.get("codec_type") == "audio" for s in streams):
        raise ValueError("Narración sin pista de audio.")
    if abs(duration - target) > 0.5:
        raise ValueError(
            f"Duración de narración ({duration:.2f}s) no coincide con "
            f"el montaje ({target:.2f}s). Ajustar audio antes de exportar."
        )


def validate_output(outfile, target):
    duration, streams = probe(outfile)
    videos = [s for s in streams if s.get("codec_type") == "video"]
    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    if abs(duration - target) > 0.5 or not videos or not has_audio:
        raise RuntimeError("El MP4 final no cumple duración y pistas de audio/video.")
    if int(videos[0].get("width", 0)) != WIDTH or int(videos[0].get("height", 0)) != HEIGHT:
        raise RuntimeError("La resolución del MP4 no corresponde al perfil 9:16.")
    return duration


def main():
    parser = argparse.ArgumentParser(description="B STUDIO: montaje local con voz, sin costo API")
    parser.add_argument("manifest", type=Path, help="JSON con escenas y archivo de voz")
    parser.add_argument("--output", type=Path, default=Path.home() / "Movies" / "BarrigaStudio" / "reel-35s.mp4")
    parser.add_argument("--dry-run", action="store_true", help="Validar y mostrar comando sin renderizar")
    args = parser.parse_args()
    tmp = None
    try:
        target, scenes, voice = read_manifest(args.manifest)
        require_media_tools()
        validate_sources(target, scenes, voice)
        outfile = args.output.expanduser().resolve()
        if outfile.exists():
            raise ValueError("El destino ya existe; no se sobrescribe: " + str(outfile))
        if args.dry_run:
            print(json.dumps({
                "ready": True, "target_seconds": target,
                "scene_count": len(scenes), "audio_verified": True,
                "charge_usd": 0
            }, ensure_ascii=False))
            return 0
        outfile.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            prefix=".bstudio-", suffix=".mp4",
            dir=outfile.parent, delete=False
        ) as temp:
            tmp = Path(temp.name)
        result = subprocess.run(
            build_command(scenes, voice, target, tmp), capture_output=True,
            text=True, timeout=1800, check=False
        )
        if result.returncode != 0:
            raise RuntimeError("FFmpeg no completó el montaje: " + result.stderr[-1500:])
        checked_duration = validate_output(tmp, target)
        os.replace(tmp, outfile)
        tmp = None
        print(json.dumps({
            "status": "verified", "mp4": str(outfile),
            "duration_seconds": round(checked_duration, 2),
            "resolution": f"{WIDTH}x{HEIGHT}", "audio": True,
            "charge_usd": 0
        }, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, RuntimeError, OSError, subprocess.TimeoutExpired) as exc:
        print("Error:", exc, file=sys.stderr)
        return 1
    finally:
        if tmp and tmp.is_file():
            tmp.unlink()


if __name__ == "__main__":
    sys.exit(main())
