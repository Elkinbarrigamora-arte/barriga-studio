"""Checks for guarded launch of the owner's single real /studio app."""
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"tools"))
import bstudio_elite_start as start


class EliteLauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.studio = Path(self.tmp.name)
        (self.studio / "tools").mkdir()
        (self.studio / "tools" / "puente_central.py").write_text("print('original')")
        self.argv = ["--studio", str(self.studio),
                     "--port", "18766", "--internal-port", "18782", "--no-browser"]

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_central_bridge_blocks_without_any_erase(self):
        (self.studio / "tools" / "puente_central.py").unlink()
        with mock.patch.object(start, "subprocess") as proc:
            with self.assertRaises(SystemExit) as err:
                start.main(self.argv)
        proc.Popen.assert_not_called()
        self.assertIn("BLOQUEADO", str(err.exception))

    def test_in_use_official_port_refuses_to_kill_existing_app(self):
        with mock.patch.object(start, "port_is_in_use", return_value=True):
            with mock.patch.object(start, "subprocess") as proc:
                with self.assertRaises(SystemExit) as err:
                    start.main(self.argv)
                proc.Popen.assert_not_called()
        self.assertIn("no será detenida", str(err.exception))

    def test_in_use_private_port_refuses_to_duplicate_backend(self):
        with mock.patch.object(start, "port_is_in_use", side_effect=[False, True]):
            with mock.patch.object(start, "subprocess") as proc:
                with self.assertRaises(SystemExit) as err:
                    start.main(self.argv)
                proc.Popen.assert_not_called()
        self.assertIn("puerto interno", str(err.exception))

    def test_different_ports_are_mandatory(self):
        with self.assertRaises(SystemExit):
            start.main(self.argv + ["--internal-port", "18766"])

    def test_vendored_runtime_module_required_before_start(self):
        with mock.patch.object(start, "port_is_in_use", return_value=False):
            with mock.patch.object(start.Path, "is_file", autospec=True,
                                   side_effect=lambda p: "bstudio-runtime.js" not in str(p)):
                with self.assertRaises(SystemExit) as err:
                    start.main(self.argv)
        self.assertIn("Falta", str(err.exception)) if "Falta" in str(err.exception) else self.assertIn("falta", str(err.exception))

    def test_launch_uses_the_original_bridge_in_original_cwd(self):
        studio_before=(self.studio / "tools" / "puente_central.py").read_text()
        child=mock.Mock()
        child.poll.return_value=None
        child.wait.return_value=0
        with mock.patch.object(start, "port_is_in_use", return_value=False), \
             mock.patch.object(start, "is_http_studio_ready", return_value=True), \
             mock.patch.object(start.subprocess, "Popen", return_value=child) as popen, \
             mock.patch.object(start, "gateway_main", return_value=None) as gw:
            start.main(self.argv)
        command=popen.call_args.args[0]
        self.assertEqual(command[1], str(self.studio / "tools" / "puente_central.py"))
        self.assertEqual(command[2:], ["--puerto", "18782"])
        self.assertEqual(popen.call_args.kwargs["cwd"], str(self.studio))
        self.assertEqual((self.studio / "tools" / "puente_central.py").read_text(), studio_before)
        args=gw.call_args.args[0]
        self.assertIn("18766", args)
        self.assertIn("18782", args)
        child.terminate.assert_called_once()

    def test_backend_exits_before_ready_no_integration_is_exposed(self):
        child=mock.Mock()
        child.poll.return_value=2
        with mock.patch.object(start, "port_is_in_use", return_value=False), \
             mock.patch.object(start.subprocess, "Popen", return_value=child), \
             mock.patch.object(start, "gateway_main") as gw:
            with self.assertRaises(SystemExit) as err:
                start.main(self.argv)
        gw.assert_not_called()
        self.assertIn("terminó", str(err.exception))

    def test_startup_failure_classifies_missing_module_without_leaking_secret(self):
        log = io.BytesIO(
            b"secret sk-test-DO-NOT-SHARE\\n"
            b"ModuleNotFoundError: No module named 'internal_private'\\n")
        reason = start.startup_failure_reason(log)
        self.assertIn("ModuleNotFoundError", reason)
        self.assertNotIn("sk-test", reason)
        self.assertNotIn("internal_private", reason)

    def test_startup_failure_classifies_busy_internal_port(self):
        log = io.BytesIO(b"OSError: [Errno 48] Address already in use\\n")
        self.assertIn("ocupado", start.startup_failure_reason(log))

    def test_startup_failure_does_not_echo_unrecognised_tracebacks(self):
        log = io.BytesIO(b"SECRETO=12345\\nError secreto\\n")
        self.assertNotIn("SECRETO", start.startup_failure_reason(log))

    def test_http_readiness_never_claims_port_open_as_studio_ready(self):
        class Response:
            status=200
            headers={"Content-Type":"application/json"}
            def __enter__(self): return self
            def __exit__(self,*args): pass
        with mock.patch.object(start.urllib.request, "urlopen", return_value=Response()):
            self.assertFalse(start.is_http_studio_ready(18782))

    def test_find_interpreter_prefers_original_app_virtualenv(self):
        path=self.studio / ".venv"/"bin"/"python"
        path.parent.mkdir(parents=True)
        path.write_text("# python")
        self.assertEqual(start.find_interpreter(self.studio),str(path))


if __name__ == "__main__":
    unittest.main()
