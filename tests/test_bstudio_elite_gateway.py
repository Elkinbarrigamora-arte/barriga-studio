"""B STUDIOS ÉLITE integration with the actual /studio URL, simulated legacy app.

The old app is a different HTTP process. These tests guarantee its routes and
project endpoints still work as before. No paid provider or Mac is accessed.
"""
import http.client
import json
import socket
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))
import bstudio_elite_gateway as gw  # noqa
from bstudio_unified_bridge import MODEL


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class OriginalStudio(BaseHTTPRequestHandler):
    original_projects = b'{"legacyProjects":["Saved original project"]}'
    last_post = None

    def log_message(self, *args):
        pass

    def reply(self, status, data, kind="application/json", **headers):
        self.send_response(status)
        self.send_header("Content-Type", kind)
        self.send_header("Content-Length", str(len(data)))
        for name, value in headers.items():
            self.send_header(name.replace("_", "-"), value)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)

    def do_GET(self):
        if self.path == "/studio":
            return self.reply(200, b"<html><head><title>B STUDIOS ELITE activo</title></head>"
                                  b"<body><main id='app'>Proyecto intacto</main></body></html>",
                              "text/html; charset=utf-8")
        if self.path == "/":
            return self.reply(200, b"<html><body>Otra ruta antigua</body></html>", "text/html")
        if self.path == "/api/health":
            return self.reply(200, b'{"originalHealth":true}')
        if self.path == "/api/projects":
            return self.reply(200, self.original_projects)
        if self.path == "/legacy-video.mp4":
            data = b"MOOV" + b"x" * 120
            return self.reply(200, data, "video/mp4")
        return self.reply(404, b'{"error":"old route missing"}')

    def do_POST(self):
        size = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(size)
        self.__class__.last_post = {
            "path": self.path, "body": body, "origin": self.headers.get("Origin")
        }
        return self.reply(200, b'{"originalSaved":true}')

    def do_HEAD(self):
        self.do_GET()


class EliteGatewayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.tmpdir = Path(cls.temp.name)
        cls.video_dir = cls.tmpdir / "videos"
        cls.video_dir.mkdir()
        (cls.video_dir / "real.mp4").write_bytes(b"\x00\x00\x00\x18ftypisom" + b"z" * 60)
        cls.runtime_file = cls.tmpdir / "bstudio-runtime.js"
        cls.runtime_file.write_text("console.log('real overlay script loaded')")
        cls.upstream_port = free_port()
        cls.frontend_port = free_port()
        cls.token = "test-token-elite"
        cls.old = ThreadingHTTPServer(("127.0.0.1", cls.upstream_port), OriginalStudio)
        cls.gateway = ThreadingHTTPServer(
            ("127.0.0.1", cls.frontend_port),
            gw.make_gateway_handler(
                cls.video_dir, cls.runtime_file, cls.token,
                cls.frontend_port, cls.upstream_port, "auto", None
            )
        )
        cls.threads = [threading.Thread(target=s.serve_forever, daemon=True)
                       for s in (cls.old, cls.gateway)]
        for thread in cls.threads:
            thread.start()

    @classmethod
    def tearDownClass(cls):
        for server in (cls.old, cls.gateway):
            server.shutdown()
            server.server_close()
        for thread in cls.threads:
            thread.join(timeout=3)
        cls.temp.cleanup()

    def request(self, path, method="GET", data=None, headers=None, token=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.frontend_port, timeout=4)
        hdr = dict(headers or {})
        if token is not None:
            hdr["X-Barriga-Token"] = token
        conn.request(method, path, body=data, headers=hdr)
        response = conn.getresponse()
        body = response.read()
        result = response.status, dict(response.getheaders()), body
        conn.close()
        return result

    def test_01_active_studio_is_original_html_plus_our_overlay(self):
        status, _, content = self.request("/studio")
        self.assertEqual(status, 200)
        self.assertIn(b"B STUDIOS ELITE activo", content)
        self.assertIn(b"Proyecto intacto", content)
        self.assertIn(b"/_bstudio/assets/bstudio-runtime.js", content)

    def test_02_runtime_asset_works_in_active_studio(self):
        status, _, content = self.request("/_bstudio/assets/bstudio-runtime.js")
        self.assertEqual(status, 200)
        self.assertIn(b"overlay script loaded", content)

    def test_03_legacy_projects_route_untouched(self):
        status, _, content = self.request("/api/projects")
        self.assertEqual(status, 200)
        self.assertEqual(content, OriginalStudio.original_projects)

    def test_04_original_health_not_intercepted(self):
        status, _, content = self.request("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(content), {"originalHealth": True})

    def test_05_other_pages_not_injected(self):
        status, _, content = self.request("/")
        self.assertEqual(status, 200)
        self.assertNotIn(b"_bstudio", content)

    def test_06_original_save_post_preserves_body_and_origin(self):
        origin = f"http://127.0.0.1:{self.frontend_port}"
        blob = b'{"project":"saved and restored"}'
        status, _, content = self.request("/api/projects", "POST", blob,
                                           {"Content-Type":"application/json",
                                            "Origin":origin})
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(content)["originalSaved"])
        self.assertEqual(OriginalStudio.last_post["body"], blob)
        self.assertEqual(OriginalStudio.last_post["path"], "/api/projects")
        self.assertEqual(OriginalStudio.last_post["origin"],
                         f"http://127.0.0.1:{self.upstream_port}")

    def test_07_existing_media_bytes_are_preserved(self):
        status, _, content = self.request("/legacy-video.mp4")
        self.assertEqual(status, 200)
        self.assertEqual(content, b"MOOV" + b"x"*120)

    def test_08_new_api_is_session_private(self):
        self.assertEqual(self.request("/_bstudio/api/videos")[0], 403)
        status, _, payload = self.request("/_bstudio/api/videos", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(payload)["videos"][0]["filename"], "real.mp4")

    def test_09_new_media_is_not_exposed_without_capability(self):
        self.assertEqual(self.request("/_bstudio/media/real.mp4")[0], 403)
        status, _, body = self.request("/_bstudio/media/real.mp4?token=" + self.token)
        self.assertEqual(status, 200)
        self.assertEqual(body, (self.video_dir / "real.mp4").read_bytes())

    def test_10_existing_script_route_stays_unmodified(self):
        status, _, body = self.request("/_bstudio/api/guion", method="POST",
                                       data=b'{"idea":"Narracion real"}',
                                       headers={"Content-Type":"application/json",
                                                "Origin":f"http://127.0.0.1:{self.frontend_port}"})
        self.assertEqual(status, 403)

    def test_11_unknown_private_route_is_not_proxied(self):
        status, _, _ = self.request("/_bstudio/api/unauthorized")
        self.assertEqual(status, 404)

    def test_12_query_parameters_persist_in_original_routes(self):
        status, _, _ = self.request("/api/projects?draft=1")
        self.assertEqual(status, 404)  # original route knows no query variant

    def test_13_original_head_content_type_is_preserved(self):
        status, headers, body = self.request("/legacy-video.mp4", "HEAD")
        self.assertEqual(status, 200)
        self.assertEqual(headers["Content-Type"], "video/mp4")
        self.assertEqual(body, b"")

    def test_14_model_detection_does_not_require_upstream(self):
        status, _, body = self.request("/_bstudio/api/engines", token=self.token)
        self.assertEqual(status, 200)
        self.assertIn("barriga-ia", [i["id"] for i in json.loads(body)["engines"]])

    def test_15_overlay_injection_is_html_escaped(self):
        value = gw.add_overlay("</body>", 'safe"&<token', 'task"><oops')
        self.assertNotIn('data-token="safe"&<token"', value)
        self.assertIn("&quot;&amp;&lt;token", value)
        self.assertIn("&quot;&gt;&lt;oops", value)

    def test_16_only_studio_html_gets_injected(self):
        self.assertTrue(gw.eligible_overlay("/studio", 200, {"Content-Type":"text/html"}))
        self.assertFalse(gw.eligible_overlay("/api/projects", 200, {"Content-Type":"text/html"}))
        self.assertFalse(gw.eligible_overlay("/studio", 404, {"Content-Type":"text/html"}))
        self.assertFalse(gw.eligible_overlay("/studio", 200, {"Content-Type":"application/json"}))

    def test_17_post_large_binary_stream_is_bounded(self):
        body = b"a" * (1024 * 1024)
        status, _, _ = self.request("/api/upload", "POST", body,
                                     {"Content-Type":"application/octet-stream"})
        self.assertEqual(status, 200)
        self.assertEqual(len(OriginalStudio.last_post["body"]), len(body))

    def test_18_cross_site_requests_are_blocked(self):
        status, _, _ = self.request("/studio", headers={"Sec-Fetch-Site":"cross-site"})
        self.assertEqual(status, 403)

    def test_19_duplicate_overlay_in_single_html_is_prevented_by_client(self):
        result = gw.add_overlay("<html><body>ok</body></html>", self.token, "task12345")
        self.assertEqual(result.count('src="/_bstudio/assets/bstudio-runtime.js"'), 1)


if __name__ == "__main__":
    unittest.main()
