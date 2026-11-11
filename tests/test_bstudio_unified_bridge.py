"""Integration coverage for one Studio bridge; fully offline and no paid requests."""
import http.client
import io
import importlib.util
import json
import socket
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock
from http.server import ThreadingHTTPServer

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
spec = importlib.util.spec_from_file_location("bstudio_unified_bridge", TOOLS / "bstudio_unified_bridge.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class UnifiedBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.studio = root / "studio"
        self.media = root / "video"
        self.studio.mkdir()
        self.media.mkdir()
        (self.studio / "index.html").write_text(
            '<!doctype html><title>Mi estudio</title><main id="crear"></main></body>',
            encoding="utf-8")
        (self.studio / "assets").mkdir()
        (self.studio / "assets" / "studio-mejoras.js").write_text("window.OK=true")
        self.runtime = root / "runtime.js"
        self.runtime.write_text("window.BRIDGE=true")
        self.movie = self.media / "video-real.mp4"
        self.movie.write_bytes(b"\x00\x00\x00\x18ftypisom" + b"a" * 120)
        self.token = "secret-test-token"
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        self.port = port
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", port),
            bridge.make_handler(self.studio, self.media, self.runtime,
                                self.token, port, "qwen2.5-coder:14b", None))
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=3)
        self.temp.cleanup()

    def send(self, path="/", method="GET", payload=None, token=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        options = dict(headers or {})
        if token is not None:
            options["X-Barriga-Token"] = token
        if payload is not None:
            options["Origin"] = "http://127.0.0.1:" + str(self.port)
            options["Content-Type"] = "application/json"
            payload = json.dumps(payload).encode("utf-8")
        conn.request(method, path, body=payload, headers=options)
        res = conn.getresponse()
        data = res.read()
        out = res.status, dict(res.getheaders()), data
        conn.close()
        return out

    def test_home_embeds_same_version_without_modifying_it(self):
        original = (self.studio / "index.html").read_text()
        status, _, body = self.send()
        self.assertEqual(status, 200)
        self.assertIn(b"bstudio-runtime.js", body)
        self.assertIn(b"Mi estudio", body)
        self.assertEqual((self.studio / "index.html").read_text(), original)

    def test_runtime_asset_is_served(self):
        status, _, body = self.send("/assets/bstudio-runtime.js")
        self.assertEqual(status, 200)
        self.assertIn(b"window.BRIDGE=true", body)

    def test_original_asset_is_preserved(self):
        status, _, body = self.send("/assets/studio-mejoras.js")
        self.assertEqual(status, 200)
        self.assertIn(b"window.OK=true", body)

    def test_json_private_without_token(self):
        status, _, _ = self.send("/api/videos")
        self.assertEqual(status, 403)

    def test_video_list_is_real_file_inventory(self):
        status, _, body = self.send("/api/videos", token=self.token)
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["videos"][0]["filename"], "video-real.mp4")

    def test_media_requires_session_capability(self):
        status, _, _ = self.send("/media/video-real.mp4")
        self.assertEqual(status, 403)

    def test_media_range_supports_safari(self):
        status, headers, body = self.send(
            "/media/video-real.mp4?token=" + self.token,
            headers={"Range": "bytes=4-11"})
        self.assertEqual(status, 206)
        self.assertEqual(body, b"ftypisom")
        self.assertEqual(headers.get("Accept-Ranges"), "bytes")

    def test_full_media_has_correct_bytes(self):
        status, _, body = self.send("/media/video-real.mp4?token=" + self.token)
        self.assertEqual(status, 200)
        self.assertEqual(body, self.movie.read_bytes())

    def test_media_traversal_cannot_read_private_files(self):
        status, _, _ = self.send("/media/%2E%2E%2Findex.html?token=" + self.token)
        self.assertEqual(status, 404)

    def test_invalid_range_rejected(self):
        status, _, _ = self.send("/media/video-real.mp4?token=" + self.token,
                                 headers={"Range": "bytes=500-700"})
        self.assertEqual(status, 416)

    def test_post_without_token_denied(self):
        status, _, _ = self.send("/api/guion", "POST", {"idea": "Una historia"})
        self.assertEqual(status, 403)

    def test_script_offline_explains_model(self):
        with mock.patch.object(bridge, "ollama_health", return_value={"state": "offline"}):
            status, _, body = self.send("/api/guion", "POST",
                                        {"idea": "Una historia"}, token=self.token)
        self.assertEqual(status, 503)
        self.assertIn("Ollama", body.decode("utf-8"))

    def test_script_ready_calls_real_adapter_only_on_request(self):
        payload = {"gancho": "Inicio", "historia": "Suceso", "oferta_cierre": "Final",
                   "modelo": "qwen2.5-coder:14b", "segundos": 1}
        with mock.patch.object(bridge, "ollama_health", return_value={"state": "ready"}), \
             mock.patch.object(bridge, "generate_ollama_script", return_value=payload) as fn:
            status, _, body = self.send("/api/guion", "POST",
                                        {"idea": "Una historia"}, token=self.token)
        self.assertEqual(status, 200)
        fn.assert_called_once_with("Una historia", "qwen2.5-coder:14b")
        self.assertEqual(json.loads(body)["historia"], "Suceso")

    def test_video_recovery_invalid_task_rejected(self):
        status, _, _ = self.send("/api/recover", "POST",
                                 {"task_id": "../other"}, token=self.token)
        self.assertEqual(status, 400)

    def test_provider_403_no_duplicate_and_clear_error(self):
        with mock.patch.object(bridge, "read_existing_task",
                               side_effect=RuntimeError("PoYo 401/403")):
            status, _, body = self.send("/api/recover", "POST",
                                        {"task_id": "0AHQMX2G2T4ZZE6O"}, token=self.token)
        self.assertEqual(status, 502)
        self.assertIn("No se reenvió", body.decode("utf-8"))
        self.assertEqual(len(list(self.media.iterdir())), 1)

    def test_existing_local_video_does_not_requery_provider(self):
        (self.media / "poyo-0AHQMX2G2T4ZZE6O.mp4").write_bytes(self.movie.read_bytes())
        with mock.patch.object(bridge, "read_existing_task") as called:
            status, _, body = self.send("/api/recover", "POST",
                                        {"task_id": "0AHQMX2G2T4ZZE6O"}, token=self.token)
        self.assertEqual(status, 200)
        self.assertIn(b"already_downloaded", body)
        called.assert_not_called()

    def test_media_symlinks_are_not_exposed(self):
        (self.media / "linked.mp4").symlink_to(self.movie)
        self.assertEqual(len(bridge.list_media(self.media)), 1)

    def test_engines_do_not_misrepresent_unverified_video(self):
        with mock.patch.object(bridge, "ollama_health", return_value={"state": "ready"}):
            items = bridge.engine_inventory("qwen2.5-coder:14b", None)
        self.assertEqual(next(e for e in items if e["id"] == "poyo")["paid_generation_enabled"], False)
        self.assertEqual(next(e for e in items if e["id"] == "fal")["state"], "not_connected")

    def test_media_response_rejects_cross_origin_fetch(self):
        status, _, _ = self.send("/media/video-real.mp4?token=" + self.token,
                                 headers={"Sec-Fetch-Site": "cross-site"})
        self.assertEqual(status, 403)

    def test_import_selected_mp4_without_deleting_source(self):
        original = b"\x00\x00\x00\x18ftypisom" + b"z" * 80
        result = bridge.import_existing_mp4(io.BytesIO(original), self.media,
                                             "nuevo-video.mp4", len(original))
        self.assertEqual(result["filename"], "nuevo-video.mp4")
        self.assertEqual((self.media / "nuevo-video.mp4").read_bytes(), original)
        self.assertEqual(self.movie.read_bytes()[:12], b"\x00\x00\x00\x18ftypisom")

    def test_import_duplicate_name_does_not_overwrite(self):
        original = b"\x00\x00\x00\x18ftypisom" + b"k" * 40
        self.media.joinpath("nuevo-video.mp4").write_bytes(b"ORIGINAL")
        result = bridge.import_existing_mp4(io.BytesIO(original), self.media,
                                             "nuevo-video.mp4", len(original))
        self.assertEqual(result["filename"], "nuevo-video-1.mp4")
        self.assertEqual(self.media.joinpath("nuevo-video.mp4").read_bytes(), b"ORIGINAL")

    def test_import_rejects_non_mp4_bytes(self):
        with self.assertRaises(ValueError):
            bridge.import_existing_mp4(io.BytesIO(b"not-a-video!" + b"x" * 100),
                                         self.media, "fake.mp4", 112)
        self.assertFalse((self.media / "fake.mp4").exists())
        self.assertFalse(list(self.media.glob(".bstudio-import-*")))

    def test_import_rejects_path_traversal(self):
        with self.assertRaises(ValueError):
            bridge.import_existing_mp4(io.BytesIO(b"x"*40), self.media,
                                         "../private.mp4", 40)

    def test_import_rejects_too_large(self):
        with self.assertRaises(ValueError):
            bridge.import_existing_mp4(io.BytesIO(b"x"*40), self.media,
                                         "large.mp4", bridge.MAX_IMPORT_BYTES + 1)

    def test_import_rejects_incomplete_stream_and_cleans_temp(self):
        with self.assertRaises(ValueError):
            bridge.import_existing_mp4(io.BytesIO(b"\x00\x00\x00\x18ftypisom"),
                                         self.media, "incomplete.mp4", 200)
        self.assertFalse((self.media / "incomplete.mp4").exists())
        self.assertFalse(list(self.media.glob(".bstudio-import-*")))

    def test_import_api_denies_requests_without_session(self):
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/api/import-video", body=b"\x00\x00\x00\x18ftypisom",
                     headers={"Content-Type": "video/mp4",
                              "X-Barriga-Filename": "new.mp4",
                              "Origin": "http://127.0.0.1:" + str(self.port)})
        reply = conn.getresponse()
        self.assertEqual(reply.status, 403)
        reply.read()
        conn.close()

    def test_import_api_uses_existing_session_and_lists_video(self):
        contents = b"\x00\x00\x00\x18ftypisom" + b"a" * 64
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        conn.request("POST", "/api/import-video", body=contents,
                     headers={"Content-Type": "video/mp4",
                              "X-Barriga-Filename": "otro-video.mp4",
                              "X-Barriga-Token": self.token,
                              "Origin": "http://127.0.0.1:" + str(self.port)})
        reply = conn.getresponse()
        self.assertEqual(reply.status, 201)
        message = json.loads(reply.read())
        conn.close()
        self.assertEqual(message["paid_credits"], 0)
        self.assertIn("otro-video.mp4", [entry["filename"] for entry in bridge.list_media(self.media)])

    def test_head_response_for_video(self):
        status, headers, body = self.send("/media/video-real.mp4?token=" + self.token, "HEAD")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertEqual(headers.get("Accept-Ranges"), "bytes")


if __name__ == "__main__":
    unittest.main()
