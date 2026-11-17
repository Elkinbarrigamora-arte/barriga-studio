"""Guard public B STUDIO evidence docs against project UUID disclosure."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DOCS = (
    ROOT / "docs" / "BSTUDIO_DIAGNOSTICO_CONECTORES_2026-11-17.md",
    ROOT / "docs" / "BSTUDIO_REVALIDACION_2026-11-17_0555UTC.md",
    ROOT / "docs" / "BSTUDIO_REVALIDACION_2026-11-17_0801UTC.md",
    ROOT / "docs" / "BSTUDIO_RELEASE_UNICA.md",
    ROOT / "docs" / "BSTUDIO_ELITE_ORDEN_INGENIERIA.md",
    ROOT / "docs" / "BSTUDIO_PUENTE_UNIFICADO.md",
    ROOT / "docs" / "POYO_WAN_FAST.md",
    ROOT / "docs" / "REEL_35S_QA.md",
)
UUID_PATTERN = re.compile(
    r"\\b[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}\\b",
    re.IGNORECASE,
)


class PublicEvidencePrivacyTests(unittest.TestCase):
    def test_public_docs_exist(self):
        for path in PUBLIC_DOCS:
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file(), f"Missing public evidence doc: {path.name}")

    def test_public_docs_do_not_publish_uuid_identifiers(self):
        for path in PUBLIC_DOCS:
            with self.subTest(path=path.name):
                content = path.read_text(encoding="utf-8")
                self.assertIsNone(
                    UUID_PATTERN.search(content),
                    f"UUID-like private identifier found in {path.name}",
                )


if __name__ == "__main__":
    unittest.main()
