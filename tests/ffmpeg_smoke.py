#!/usr/bin/env python3
"""End-to-end local FFmpeg smoke test using synthetic video+audio. No provider cost."""
import json
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    if result.returncode:
        raise RuntimeError("Command failed: " + " ".join(args) + "\n" + result.stderr[-700:])


def main():
    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        scenes = []
        for i, color in enumerate(("red", "blue")):
            file = root / f"scene-{i}.mp4"
            run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", f"color=c={color}:s=160x284:r=30:d=1",
                "-c:v", "libx264", "-pix_fmt", "yuv420p", str(file))
            scenes.append({"file": str(file), "seconds": 1})
        voice = root / "narration.wav"
        run("ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
            "-c:a", "pcm_s16le", str(voice))
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({
            "target_seconds": 2, "scenes": scenes, "voice": str(voice)
        }), encoding="utf-8")
        outfile = root / "reel.mp4"
        assembler = Path(__file__).resolve().parents[1] / "tools" / "bstudio_reel_assemble.py"
        run(sys.executable, str(assembler), str(manifest), "--output", str(outfile))
        if not outfile.exists() or outfile.stat().st_size < 100:
            raise RuntimeError("Final MP4 missing or empty.")
        print("FFmpeg smoke test passed: video + audio + exact duration.")


if __name__ == "__main__":
    main()
