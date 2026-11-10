"""Offline regression tests for the PoYo existing-task recovery path."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_FILE = Path(__file__).resolve().parents[1] / "tools" / "bstudio_poyo_recover.py"
SPEC = importlib.util.spec_from_file_location("bstudio_poyo_recover", MODULE_FILE)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class FakeResponse:
    def __init__(self, data, url="https://cdn.doculator.org/videos/t.mp4"):
        self.data = data
        self.url = url
        self.pos = 0
        self.headers = {"Content-Length": str(len(data))}

    def read(self, n):
        chunk = self.data[self.pos:self.pos + n]
        self.pos += len(chunk)
        return chunk

    def geturl(self):
        return self.url

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None


class RecoveryTests(unittest.TestCase):
    def test_json_preserves_full_url(self):
        url = "https://cdn.doculator.org/videos/0AHQMX2G2T4ZZE6O.mp4?token=abcdef"
        task = module.parse_task(json.dumps({"status": "succeeded", "files": [{"file_url": url}]}))
        self.assertEqual(module.find_video_url(task), url)

    def test_nested_data(self):
        task = module.parse_task(json.dumps({"code": 200, "data": {
            "status": "finished", "files": ["https://cdn.doculator.org/x.mp4"]
        }}))
        self.assertEqual(task["status"], "finished")

    def test_wrong_host_rejected(self):
        for url in ("http://cdn.doculator.org/a.mp4", "https://localhost/a.mp4",
                    "https://not-poyo.example/a.mp4", "file:///tmp/a.mp4"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                module.validate_download_url(url)

    def test_valid_mp4_is_atomic_and_preserved(self):
        video = b"\x00\x00\x00\x18ftypisom" + b"x" * 200
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "video.mp4"
            size = module.save_video(
                "https://cdn.doculator.org/videos/t.mp4", destination,
                opener=lambda *a, **k: FakeResponse(video)
            )
            self.assertEqual(size, len(video))
            self.assertEqual(destination.read_bytes(), video)

    def test_non_video_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "video.mp4"
            with self.assertRaises(ValueError):
                module.save_video(
                    "https://cdn.doculator.org/videos/t.mp4", destination,
                    opener=lambda *a, **k: FakeResponse(b"<html>not a video</html>")
                )
            self.assertFalse(destination.exists())

    def test_cli_invocation_is_read_only_and_machine_json(self):
        captured = []
        def fake_run(command, **kwargs):
            captured.extend(command)
            return mock.Mock(returncode=0, stdout=json.dumps({
                "status": "succeeded",
                "files": [{"file_url": "https://cdn.doculator.org/t.mp4"}]
            }))
        with mock.patch.object(module.shutil, "which", return_value="/usr/bin/npx"):
            data = module.read_existing_task("0AHQMX2G2T4ZZE6O", runner=fake_run)
        self.assertEqual(data["status"], "succeeded")
        self.assertEqual(captured[-2:], ["--format", "json"])
        self.assertIn("get", captured)
        self.assertNotIn("submit", captured)

    def test_invalid_task_id(self):
        with self.assertRaises(ValueError):
            module.read_existing_task("../bad")


if __name__ == "__main__":
    unittest.main()
