import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location("fal_video", Path(__file__).resolve().parents[1] / "tools" / "fal_video.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class TestFalVideo(unittest.TestCase):
    def test_valid_input(self):
        self.assertEqual(mod.prepare("https://example.com/img.png", " walk ")["prompt"], "walk")
    def test_no_insecure_url(self):
        with self.assertRaises(ValueError):
            mod.prepare("http://example.com/img.png", "walk")
    def test_empty_prompt(self):
        with self.assertRaises(ValueError):
            mod.prepare("https://example.com/img.png", " ")
    def test_model(self):
        self.assertEqual(mod.MODEL, "fal-ai/wan/v2.2-5b/image-to-video")

if __name__ == "__main__":
    unittest.main()
