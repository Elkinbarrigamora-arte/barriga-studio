"""Regression tests for the 35-second audiovisual assembler, without FFmpeg calls."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / "tools" / "bstudio_reel_assemble.py"
SPEC = importlib.util.spec_from_file_location("bstudio_reel_assemble", SOURCE)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class ReelAssemblyTests(unittest.TestCase):
    def make_manifest(self, root, voice=True):
        path = Path(root)
        scenes = []
        for i in range(7):
            f = path / ("scene-" + str(i) + ".mp4")
            f.write_bytes(b"dummy")
            scenes.append({"file": str(f), "seconds": 5})
        voice_path = path / "voz-es.wav"
        if voice:
            voice_path.write_bytes(b"dummy")
        manifest = path / "manifest.json"
        manifest.write_text(json.dumps({
            "target_seconds": 35,
            "scenes": scenes, "voice": str(voice_path)
        }))
        return manifest

    def test_manifest_35_seconds(self):
        with tempfile.TemporaryDirectory() as folder:
            target, scenes, voice = module.read_manifest(self.make_manifest(folder))
            self.assertEqual(target, 35)
            self.assertEqual(len(scenes), 7)
            self.assertTrue(voice.is_file())

    def test_rejects_mismatch(self):
        with tempfile.TemporaryDirectory() as folder:
            manifest = self.make_manifest(folder)
            obj = json.loads(manifest.read_text())
            obj["scenes"][0]["seconds"] = 4
            manifest.write_text(json.dumps(obj))
            with self.assertRaises(ValueError):
                module.read_manifest(manifest)

    def test_rejects_missing_voice(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                module.read_manifest(self.make_manifest(folder, voice=False))

    def test_ffmpeg_command_has_video_and_audio_no_network(self):
        scenes = [(Path("/tmp/a.mp4"), 5), (Path("/tmp/b.mp4"), 5)]
        command = module.build_command(scenes, Path("/tmp/voz.wav"), 10, Path("/tmp/out.mp4"))
        text = " ".join(command)
        self.assertIn("concat=n=2:v=1:a=0", text)
        self.assertIn("-map [a]", text)
        self.assertIn("480:854", text)
        self.assertNotIn("submit", command)
        self.assertNotIn("http", text)

    def test_rejects_silent_voice(self):
        with mock.patch.object(module, "probe", side_effect=[
            (5.0, [{"codec_type": "video"}]),
            (35.0, [{"codec_type": "video"}])
        ]):
            with self.assertRaises(ValueError):
                module.validate_sources(35, [(Path("/tmp/a.mp4"), 5)], Path("/tmp/voice.wav"))

    def test_rejects_undersized_video_scene(self):
        with mock.patch.object(module, "probe", return_value=(3.0, [{"codec_type": "video"}])):
            with self.assertRaises(ValueError):
                module.validate_sources(35, [(Path("/tmp/a.mp4"), 5)], Path("/tmp/voice.wav"))

    def test_validate_final_video_audio_and_duration(self):
        with mock.patch.object(module, "probe", return_value=(
            35.1, [{"codec_type": "video", "width": 480, "height": 854},
                   {"codec_type": "audio"}]
        )):
            self.assertAlmostEqual(module.validate_output(Path("/tmp/out.mp4"), 35), 35.1)

    def test_validate_final_rejects_missing_audio(self):
        with mock.patch.object(module, "probe", return_value=(
            35.0, [{"codec_type": "video", "width": 480, "height": 854}]
        )):
            with self.assertRaises(RuntimeError):
                module.validate_output(Path("/tmp/out.mp4"), 35)


if __name__ == "__main__":
    unittest.main()
