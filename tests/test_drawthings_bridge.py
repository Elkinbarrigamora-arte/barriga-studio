"""Pruebas sin acceso a Draw Things, a internet ni a los proyectos del usuario."""
import base64
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import drawthings_client as client
import puente_local


class FakeResponse:
    status = 200

    def __init__(self, data):
        self.stream = io.BytesIO(data)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self, length=-1):
        return self.stream.read(length)


class DrawThingsTests(unittest.TestCase):
    def setUp(self):
        self.args = {
            "preset": "planeta", "prompt": client.PRESETS["planeta"]["prompt"],
            "steps": 35, "guidance_scale": 6, "seed": -1,
        }

    def test_build_payload_fixes_single_image_size_and_guidance_name(self):
        payload = client.build_payload(self.args)
        self.assertEqual((payload["width"], payload["height"]), (1024, 1024))
        self.assertEqual((payload["batch_size"], payload["batch_count"]), (1, 1))
        self.assertEqual(payload["guidance_scale"], 6)
        self.assertNotIn("cfg_scale", payload)

    def test_rejects_bad_profiles_and_resource_heavy_options(self):
        for key, value in (("preset", "anything"), ("steps", 150),
                           ("guidance_scale", 99), ("seed", 2**32),
                           ("prompt", "x"), ("steps", True)):
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    client.build_payload(self.args | {key: value})

    def test_connection_reports_actual_selected_model(self):
        data = json.dumps({"model": "sd_xl_base_1.0_q6p_q8p.ckpt"}).encode()
        with patch.object(client, "urlopen", return_value=FakeResponse(data)) as mock:
            status = client.check_connection()
        self.assertTrue(status["activo"])
        self.assertEqual(status["modelo"], "sd_xl_base_1.0_q6p_q8p.ckpt")
        self.assertEqual(mock.call_args.args[0], "http://127.0.0.1:7860/")

    def test_generation_returns_one_real_png_in_memory(self):
        png = b"\x89PNG\r\n\x1a\n" + b"test-binary"
        reply = json.dumps({"images": [base64.b64encode(png).decode()]}).encode()
        with patch.object(client, "urlopen", return_value=FakeResponse(reply)) as mock:
            image, mime = client.generate_image(client.build_payload(self.args))
        self.assertEqual((image, mime), (png, "image/png"))
        request = mock.call_args.args[0]
        self.assertEqual(request.full_url, "http://127.0.0.1:7860/sdapi/v1/txt2img")
        self.assertEqual(request.get_method(), "POST")

    def test_rejects_multiple_or_missing_images(self):
        for images in ([], ["one", "two"]):
            with self.subTest(images=images):
                with patch.object(client, "urlopen", return_value=FakeResponse(
                        json.dumps({"images": images}).encode())):
                    with self.assertRaises(client.DrawThingsError):
                        client.generate_image(client.build_payload(self.args))

    def test_rejects_non_image_bytes_and_oversized_responses(self):
        reply = json.dumps({"images": [base64.b64encode(b"not-a-png").decode()]}).encode()
        with patch.object(client, "urlopen", return_value=FakeResponse(reply)):
            with self.assertRaises(client.DrawThingsError):
                client.generate_image(client.build_payload(self.args))
        with patch.object(client, "MAX_REPLY", 10), patch.object(
                client, "urlopen", return_value=FakeResponse(b"{" + b"x" * 20)):
            with self.assertRaises(client.DrawThingsError):
                client.generate_image(client.build_payload(self.args))

    def test_bridge_uses_local_token_and_does_not_edit_original_studio(self):
        self.assertIn("__TOKEN__", puente_local.IMAGE_PANEL)
        self.assertIn("drawthings-bridge.js", puente_local.IMAGE_PANEL)
        self.assertIn("127.0.0.1", puente_local.HOST)
        js = (Path(__file__).resolve().parents[1] / "assets" / "drawthings-bridge.js").read_text()
        self.assertIn("/api/drawthings/generar", js)
        self.assertIn("URL.createObjectURL", js)
        self.assertNotIn("localStorage.setItem", js)


if __name__ == "__main__":
    unittest.main()
