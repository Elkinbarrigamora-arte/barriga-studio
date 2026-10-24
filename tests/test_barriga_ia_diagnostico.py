"""Diagnóstico local: nunca instala modelos ni cambia parámetros."""
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import barriga_ia_diagnostico as diag


class DiagnosticoPruebas(unittest.TestCase):
    def test_memoria_gpu_y_cuantizacion_se_reportan_sin_activar_motor(self):
        def respuesta(ruta, datos=None):
            if ruta == "/api/ps":
                return {"models": [{
                    "name": "qwen2.5-coder:14b",
                    "size": 9000000000, "size_vram": 7000000000}]}
            if ruta == "/api/show":
                return {"details": {"quantization_level": "Q4_K_M"}}
            self.fail("No debe consultar rutas adicionales")
        with patch.object(diag, "_ollama", side_effect=respuesta) as llamar:
            with patch.object(diag, "_memoria_mac", return_value=17179869184):
                resultado = diag.diagnosticar()
        self.assertEqual(resultado["cuantizacion_reportada"], "Q4_K_M")
        self.assertEqual(resultado["ram_total_bytes"], 17179869184)
        self.assertEqual(resultado["modelos_cargados"][0][
            "memoria_gpu_bytes"], 7000000000)
        self.assertEqual(llamar.call_count, 2)

    def test_sin_ollama_no_inventa_gpu_ni_cuantizacion(self):
        with patch.object(diag, "_ollama", return_value=None):
            with patch.object(diag, "_memoria_mac", return_value=None):
                resultado = diag.diagnosticar()
        self.assertFalse(resultado["ollama_responde"])
        self.assertIsNone(resultado["cuantizacion_reportada"])
        self.assertEqual(resultado["modelos_cargados"], [])


if __name__ == "__main__":
    unittest.main()
