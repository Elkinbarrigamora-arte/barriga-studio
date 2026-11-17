#!/usr/bin/env python3
"""End-to-end local FFmpeg smoke test using synthetic video+audio. No provider cost."""
import hashlib
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def check_recovery(source, root):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from bstudio_poyo_recover import save_video

    url = "https://cdn.doculator.org/synthetic.mp4"

    class Response(io.BytesIO):
        headers = {}

        def geturl(self):
            return url

    raw = source.read_bytes()
    final = root / "recovered.mp4"
    size, metadata = save_video(url, final, opener=lambda *a, **kw: Response(raw))
    if (size != len(raw) or final.read_bytes() != raw or not metadata["tiene_audio"]
            or metadata["sha256"] != hashlib.sha256(raw).hexdigest()):
        raise RuntimeError("Recovery did not preserve the verified audiovisual file.")
    invalid = root / "invalid.mp4"
    try:
        save_video(url, invalid, opener=lambda *a, **kw: Response(raw[:32]))
    except RuntimeError:
        pass
    else:
        raise RuntimeError("Truncated MP4 passed verification.")
    if invalid.exists() or list(root.glob(".poyo-*.part")):
        raise RuntimeError("Recovery left behind unverified output.")


def run(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError("Command failed: " + " ".join(args) + "\n" + result.stderr[-700:])


def main():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        scenes = []
        for i, (color, seconds) in enumerate((("red", 12), ("blue", 12), ("green", 11))):
            file = root / f"scene-{i}.mp4"
            run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", f"color=c={color}:s=160x284:r=30:d={seconds}",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(file))
            scenes.append({"file": str(file), "seconds": seconds})
        voice = root / "narration.wav"
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=35",
            "-c:a", "pcm_s16le", str(voice))
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({
            "target_seconds": 35, "scenes": scenes, "voice": str(voice)
        }), encoding="utf-8")
        outfile = root / "reel.mp4"
        assembler = Path(__file__).resolve().parents[1] / "tools" / "bstudio_reel_assemble.py"
        run(sys.executable, str(assembler), str(manifest), "--output", str(outfile))
        if not outfile.exists() or outfile.stat().st_size < 100:
            raise RuntimeError("Final MP4 missing or empty.")
        silent = root / "silent.wav"
        run("ffmpeg", "-hide_banner", "-loglevel", "error",
            "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "35",
            "-c:a", "pcm_s16le", str(silent))
        manifest.write_text(json.dumps({
            "target_seconds": 35, "scenes": scenes, "voice": str(silent)
        }), encoding="utf-8")
        rejected = root / "silent-reel.mp4"
        result = subprocess.run(
            [sys.executable, str(assembler), str(manifest), "--output", str(rejected)],
            capture_output=True, text=True, timeout=120, check=False,
        )
        if result.returncode != 1 or "silencio" not in result.stderr or rejected.exists():
            raise RuntimeError("A silent narration was not rejected before publishing.")
        check_recovery(outfile, root)
        print("FFmpeg smoke test passed: synthetic 35-second video and audio tracks.")
        print("Audio signal smoke passed: a silent 35-second narration was rejected.")
        print("Recovery smoke passed: valid MP4 preserved, truncated MP4 rejected.")


if __name__ == "__main__":
    main()
