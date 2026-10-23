"""Regresiones del agente colaborativo: no requieren Ollama."""
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("agente_colaborativo_local",
    BASE / "tools/agente_colaborativo_local.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class AgenteColaborativoTests(unittest.TestCase):
    def test_rechaza_acciones_libres(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mod.connect(Path(tmp) / "cola.sqlite3") as conn:
                with self.assertRaises(ValueError):
                    mod.enqueue(conn, "shell", "rm -rf /")

    def test_tarea_unica_y_resultado_persistente(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mod.connect(Path(tmp) / "cola.sqlite3") as conn:
                ident = mod.enqueue(conn, "diagnostico")
                with patch.object(mod, "run_action", return_value={"ok": True}) as run:
                    result = mod.run_next(conn)
                    self.assertEqual(result["id"], ident)
                    self.assertEqual(result["estado"], "TERMINADA")
                    self.assertEqual(mod.run_next(conn)["estado"], "SIN_TAREAS")
                    run.assert_called_once()
                stored = conn.execute("SELECT estado FROM tareas WHERE id=?", (ident,)).fetchone()
                self.assertEqual(stored[0], "TERMINADA")

    def test_falla_sin_repetir(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mod.connect(Path(tmp) / "cola.sqlite3") as conn:
                mod.enqueue(conn, "evaluar_ollama", "Revisar motor")
                with patch.object(mod, "run_action", side_effect=TimeoutError("sin respuesta")):
                    self.assertEqual(mod.run_next(conn)["estado"], "FALLIDA")
                    self.assertEqual(mod.run_next(conn)["estado"], "SIN_TAREAS")

    def test_tarea_local_no_publica(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mod.connect(Path(tmp) / "cola.sqlite3") as conn:
                mod.enqueue(conn, "pruebas")
                self.assertEqual(conn.execute("SELECT COUNT(*) FROM tareas").fetchone()[0], 1)


if __name__ == "__main__":
    unittest.main()
