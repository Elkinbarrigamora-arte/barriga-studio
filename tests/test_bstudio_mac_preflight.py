"""Offline preflight regression checks; never touch real Mac files."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SOURCE = Path(__file__).resolve().parents[1] / "tools" / "bstudio_mac_preflight.py"
SPEC = importlib.util.spec_from_file_location("bstudio_mac_preflight", SOURCE)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class MacPreflightTests(unittest.TestCase):
    def test_unknown_folder_is_reported(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(mod.inspect(Path(d) / "missing")["mac_root_exists"])

    def test_unknown_folder_is_not_github(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(mod.git_info(Path(d))["repository"])

    def test_inventory_detects_frontend(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"index.html").write_text("a",encoding="utf-8")
            self.assertTrue(mod.inventory(p)["frontend"]["exists"])

    def test_inventory_marks_missing_video_engine(self):
        with tempfile.TemporaryDirectory() as d:
            self.assertFalse(mod.inventory(Path(d))["motor_video"]["exists"])

    def test_inventory_detects_video_engine_folder(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"tools"/"bstudio_video").mkdir(parents=True)
            self.assertEqual(mod.inventory(p)["motor_video"]["kind"],"dir")
            self.assertTrue(mod.inventory(p)["motor_video"]["exists"])

    def test_no_port_zero_listener(self):
        self.assertFalse(mod.port_listening("127.0.0.1",0))

    def test_release_is_never_certified_by_inventory_alone(self):
        with tempfile.TemporaryDirectory() as d:
            report=mod.inspect(Path(d))
            self.assertIs(report["readiness"]["final_release_certified"],False)

    def test_report_only_contains_counts_not_project_names(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            (p/"index.html").write_text("Private project Aurora",encoding="utf-8")
            report=json.dumps(mod.inspect(p))
            self.assertNotIn("Private project Aurora",report)

    def test_missing_required_tools_block_release_readiness(self):
        with tempfile.TemporaryDirectory() as d:
            with mock.patch.object(mod.shutil,"which", return_value=None):
                report=mod.inspect(Path(d))
            self.assertFalse(report["readiness"]["local_inventory_complete"])

    def test_preflight_does_not_create_files(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            before=list(p.rglob("*"))
            mod.inspect(p)
            after=list(p.rglob("*"))
            self.assertEqual(before,after)


if __name__=="__main__":
    unittest.main()
