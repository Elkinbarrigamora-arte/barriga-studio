"""Controles de telemetría que no requieren Ollama ni conexión externa."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from barriga_ia_acelerador import (
    medir_solicitud, iniciar_llamada, finalizar_llamada, resumen,
)


class TelemetriaPruebas(unittest.TestCase):
    def test_sin_contexto_no_retiene_datos(self):
        self.assertIsNone(iniciar_llamada("ollama-prueba", "borrador"))
        self.assertEqual(resumen([])["llamadas_ollama"], 0)

    def test_mide_tokens_ignorando_datos_del_guion(self):
        with medir_solicitud() as llamadas:
            uno = iniciar_llamada("modelo-local", "borrador_completo")
            finalizar_llamada(uno, {
                "eval_count": 150, "prompt_eval_count": 70,
                "eval_duration": 5000000000, "response": "texto privado",
            })
            dos = iniciar_llamada("modelo-local", "ajuste_de_bloque")
            finalizar_llamada(dos, {"eval_count": 50, "eval_duration": 2000000000})
            stats = resumen(llamadas)
            self.assertEqual(stats["llamadas_ollama"], 2)
            self.assertEqual(stats["tokens_generados"], 200)
            self.assertEqual(stats["tokens_por_segundo"], 28.57)
            self.assertEqual(stats["detalle"][0]["tokens_entrada"], 70)
            self.assertNotIn("texto privado", str(stats))
        self.assertEqual(stats["errores_ollama"], 0)

    def test_registra_error_sin_marcarlo_como_exitoso(self):
        with medir_solicitud() as llamadas:
            e = iniciar_llamada("modelo-local", "borrador_completo")
            finalizar_llamada(e, error=True)
            stats = resumen(llamadas)
        self.assertEqual(stats["errores_ollama"], 1)
        self.assertIsNone(stats["tokens_por_segundo"])


if __name__ == "__main__":
    unittest.main()
