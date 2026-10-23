"""Pruebas del puente local sin conexión a Ollama real."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "puente_narrativo_local", ROOT / "tools/puente_narrativo_local.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class PruebasPuenteNarrativo(unittest.TestCase):
    def test_no_sobrescribe_destino(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "local-data/narrativa"
            folder.mkdir(parents=True)
            (folder / "entrada.json").write_text("{}")
            (folder / "salida.json").write_text("guardado")
            with patch.object(mod.subprocess, "run") as runner:
                with self.assertRaisesRegex(ValueError, "salida ya existe"):
                    mod.continuar(folder / "entrada.json", folder / "salida.json", root=root)
                runner.assert_not_called()

    def test_no_permite_entradas_fuera_del_repositorio(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            outside = root / "externo.json"
            outside.write_text("{}")
            with patch.object(mod.subprocess, "run") as runner:
                with self.assertRaisesRegex(ValueError, "Solo se permiten"):
                    mod.continuar(outside, root / "local-data/narrativa/salida.json", root=root)
                runner.assert_not_called()

    def test_no_inicia_generacion_al_consultar_estado(self):
        with tempfile.TemporaryDirectory() as td:
            with patch.object(mod.subprocess, "run") as runner:
                result = mod.estado(Path(td))
                self.assertFalse(result["publicacion_automatica"])
                self.assertEqual(result["modo"], "LOCAL_MANUAL")
                runner.assert_not_called()

    def test_continuar_llama_solo_motor_autorizado(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "local-data/narrativa"
            folder.mkdir(parents=True)
            entry = folder / "entrada.json"
            entry.write_text("{}")
            dest = folder / "salida.json"
            with patch.object(mod.subprocess, "run") as runner:
                runner.return_value.returncode = 2
                ret = mod.continuar(entry, dest, root=root)
                self.assertEqual(ret, 2)
                args = runner.call_args.args[0]
                self.assertTrue(args[1].endswith("tools/barriga_ia_continuar.py"))
                self.assertNotIn("shell", str(runner.call_args))


if __name__ == "__main__":
    unittest.main()
