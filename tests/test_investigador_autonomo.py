import importlib.util
from pathlib import Path
import tempfile
import unittest

LOCATION = Path(__file__).resolve().parents[1] / "tools" / "investigador_autonomo.py"
spec = importlib.util.spec_from_file_location("investigador_autonomo", LOCATION)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

ATOM = b'''<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>New voice and video model</title><updated>2026-10-23T10:00:00Z</updated>
<link href="https://github.com/ollama/ollama/releases/tag/v1" rel="alternate"/>
<summary>Speech motion improvements</summary></entry>
<entry><title>bad</title><link href="https://unsafe.example/video" rel="alternate"/></entry>
</feed>'''


class InvestigadorTests(unittest.TestCase):
    def test_recognizes_topics_and_filters_host(self):
        found = module.parse_atom(ATOM, "Ollama")
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["temas"], ["video", "voz"])

    def test_keeps_old_and_avoids_duplicates(self):
        with tempfile.TemporaryDirectory() as d:
            where = Path(d)
            def fake(name, url):
                return module.parse_atom(ATOM, name)
            one = module.research(where, fake)
            self.assertEqual(one["nuevos"], 1)
            two = module.research(where, fake)
            self.assertEqual(two["nuevos"], 0)
            self.assertEqual(len(module.json.loads((where / "hallazgos.json").read_text())["hallazgos"]), 1)

    def test_does_not_replace_corrupt_history(self):
        with tempfile.TemporaryDirectory() as d:
            where = Path(d)
            source = where / "hallazgos.json"
            source.write_text("not json")
            result = module.research(where, lambda n,u: [])
            self.assertEqual(result["estado"], "DETENIDO")
            self.assertEqual(source.read_text(), "not json")

    def test_does_not_follow_untrusted_links(self):
        data = module.parse_atom(ATOM, "Ollama")
        self.assertTrue(all("github.com" in x["enlace"] for x in data))


if __name__ == "__main__":
    unittest.main()
