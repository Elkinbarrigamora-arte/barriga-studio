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

    def test_redirect_rejects_untrusted_host_before_request(self):
        handler = module.MediaRedirectHandler()
        original = module.Request("https://cdn.doculator.org/start")
        with self.assertRaises(ValueError):
            handler.redirect_request(original, None, 302, "", {}, "https://elsewhere.example/a.mp4")
        allowed = "https://cdn.poyo.ai/video.mp4"
        redirected = handler.redirect_request(original, None, 302, "", {}, allowed)
        self.assertEqual(redirected.full_url, allowed)

    def test_valid_mp4_is_atomic_and_preserved(self):
        video = b"\x00\x00\x00\x18ftypisom" + b"x" * 200
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "video.mp4"
            def probe(staged):
                self.assertFalse(destination.exists())
                self.assertEqual(staged.read_bytes(), video)
                return {"duracion_segundos": 5}

            size, details = module.save_video(
                "https://cdn.doculator.org/videos/t.mp4", destination,
                opener=lambda *a, **k: FakeResponse(video), probe=probe
            )
            self.assertEqual(size, len(video))
            self.assertEqual(details["duracion_segundos"], 5)
            self.assertEqual(destination.read_bytes(), video)

    def test_failed_probe_keeps_no_final_or_staging_file(self):
        video = b"\x00\x00\x00\x18ftypisom" + b"x" * 200
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "video.mp4"
            with self.assertRaisesRegex(RuntimeError, "invalid stream"):
                module.save_video(
                    "https://cdn.doculator.org/videos/t.mp4", destination,
                    opener=lambda *a, **k: FakeResponse(video),
                    probe=mock.Mock(side_effect=RuntimeError("invalid stream"))
                )
            self.assertEqual(list(Path(folder).iterdir()), [])

    def test_concurrent_recovery_preserves_existing_file(self):
        video = b"\x00\x00\x00\x18ftypisom" + b"x" * 200
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "video.mp4"
            def competing_recovery(_):
                destination.write_bytes(b"previous download")
                return {}
            with self.assertRaises(FileExistsError):
                module.save_video(
                    "https://cdn.doculator.org/videos/t.mp4", destination,
                    opener=lambda *a, **k: FakeResponse(video), probe=competing_recovery
                )
            self.assertEqual(destination.read_bytes(), b"previous download")
            self.assertEqual(list(Path(folder).iterdir()), [destination])

    def test_probe_rejects_symlink_before_running_ffprobe(self):
        with tempfile.TemporaryDirectory() as folder:
            link = Path(folder) / "video.mp4"
            link.symlink_to("other.mp4")
            with mock.patch.object(module.subprocess, "run") as run:
                with self.assertRaises(ValueError):
                    module.probe_video(link)
            run.assert_not_called()

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

    def test_403_reports_auth_without_exposing_credentials(self):
        def rejected(command, **kwargs):
            return mock.Mock(returncode=3, stdout="", stderr="secret-personal-token")
        with mock.patch.object(module.shutil, "which", return_value="/usr/bin/npx"):
            with self.assertRaises(RuntimeError) as ctx:
                module.read_existing_task("0AHQMX2G2T4ZZE6O", runner=rejected)
        self.assertIn("401/403", str(ctx.exception))
        self.assertNotIn("secret-personal-token", str(ctx.exception))

    def test_provider_response_for_another_task_is_rejected(self):
        def mismatched(command, **kwargs):
            return mock.Mock(returncode=0, stdout=json.dumps({
                "data": {"task_id": "other-task-id", "status": "succeeded",
                         "files": ["https://cdn.doculator.org/other.mp4"]}
            }))
        with mock.patch.object(module.shutil, "which", return_value="/usr/bin/npx"):
            with self.assertRaisesRegex(RuntimeError, "identifica otra tarea"):
                module.read_existing_task("0AHQMX2G2T4ZZE6O", runner=mismatched)

    def test_invalid_task_id(self):
        with self.assertRaises(ValueError):
            module.read_existing_task("../bad")


if __name__ == "__main__":
    unittest.main()
