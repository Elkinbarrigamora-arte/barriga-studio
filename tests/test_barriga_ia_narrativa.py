"""Pruebas del motor Narrativa Inteligente: sin redes, sin pagos y sin publicar."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from barriga_ia_narrativa import (ErrorNarrativa, NICHOS, evaluar_guion,
                                  generar_local, preparar_solicitud)


GANCHO = "¡La última carta de su hermano llegó treinta años después del naufragio!"
HISTORIA = (
    "Daniel encontró una caja oxidada enterrada junto al viejo muelle. "
    "Dentro había una carta con la letra de Mateo, su hermano desaparecido. "
    "Decía que la tormenta no había sido un accidente. "
    "Daniel cruzó el pueblo buscando a la única persona que conocía la verdad. "
    "La anciana del faro le entregó una fotografía donde aparecían los dos hermanos. "
    "Sin embargo, alguien había escrito una fecha imposible detrás de la imagen. "
    "Cuando Daniel llegó al faro, la luz se encendió aunque llevaba décadas apagada."
)
CIERRE = (
    "Entonces comprendió que Mateo nunca abandonó el puerto. "
    "La verdadera despedida apenas estaba comenzando."
)


def ejemplo(nicho="leyendas", naturaleza="ficcion", fuentes=None):
    return {
        "titulo": "La carta bajo el faro",
        "nicho": nicho,
        "naturaleza": naturaleza,
        "gancho": GANCHO,
        "historia": HISTORIA,
        "cierre": CIERRE,
        "personajes": [{"nombre": "Daniel"}, {"nombre": "Mateo"}],
        "continuidad": {"escenario": "Faro antiguo", "protagonista": "Daniel"},
        "fuentes": fuentes if fuentes is not None else [],
        "duracion_objetivo_segundos": 35,
    }


class PruebasNarrativa(unittest.TestCase):
    def test_perfiles_editoriales_presentes(self):
        for nicho in ("historia", "mitos", "leyendas", "animales", "terror",
                      "terror_cartoon", "planeta", "maravillas", "amor",
                      "noticias", "miniseries"):
            self.assertIn(nicho, NICHOS)

    def test_prompt_gancho_historia_cierre(self):
        prompt = preparar_solicitud("El secreto del viejo faro", "leyendas")
        for palabra in ("GANCHO", "HISTORIA", "CIERRE", "No inventes fuentes"):
            self.assertIn(palabra, prompt)
        self.assertIn("continuidad", prompt.lower())

    def test_evaluacion_ficcion_no_publica(self):
        resultado = evaluar_guion(ejemplo())
        self.assertGreaterEqual(resultado["puntuacion_heuristica"], 65)
        self.assertTrue(resultado["apto_para_revision_humana"])
        self.assertFalse(resultado["publicacion_automatica_autorizada"])
        self.assertFalse(resultado["verificacion_externa_realizada"])
        self.assertIn("gancho", resultado["desglose"])

    def test_factual_requiere_fuentes_y_no_afirma_verificacion(self):
        with self.assertRaises(ErrorNarrativa):
            preparar_solicitud("Una noticia sorprendente", "noticias",
                               naturaleza="factual")
        reporte = evaluar_guion(ejemplo("noticias", "factual"))
        self.assertFalse(reporte["apto_para_revision_humana"])
        self.assertTrue(reporte["bloqueos"])
        con_fuente = evaluar_guion(
            ejemplo("noticias", "factual", ["https://example.org/informe"]))
        self.assertFalse(con_fuente["verificacion_externa_realizada"])
        self.assertTrue(con_fuente["advertencias"])

    def test_miniseries_requiere_continuidad(self):
        with self.assertRaises(ErrorNarrativa):
            preparar_solicitud("La aventura de Mateo y Daniel", "miniseries")
        prompt = preparar_solicitud(
            "La aventura de Mateo y Daniel", "miniseries",
            biblia={"Daniel": {"voz": "es-CO", "vestuario": "azul"}})
        self.assertIn("vestuario", prompt)
        clip = ejemplo("miniseries")
        clip["continuidad"] = {}
        self.assertTrue(evaluar_guion(clip)["bloqueos"])

    def test_rechaza_respuestas_incompletas(self):
        for bad in (None, [], {"gancho": "Hola"}, dict(ejemplo(), historia="")):
            with self.assertRaises(ErrorNarrativa):
                evaluar_guion(bad)

    def test_tres_ejemplos_narrativos(self):
        for nicho in ("leyendas", "animales", "amor"):
            with self.subTest(nicho=nicho):
                rep = evaluar_guion(ejemplo(nicho=nicho))
                self.assertTrue(rep["apto_para_revision_humana"])
                self.assertEqual(rep["duracion_objetivo"], 35)

    def test_ollama_solo_solicitud_local_y_json(self):
        salida = {"response": json.dumps(ejemplo(), ensure_ascii=False)}
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self):
                return json.dumps(salida).encode("utf-8")
        def simular(request, timeout):
            self.assertEqual(request.full_url, "http://127.0.0.1:11434/api/generate")
            datos = json.loads(request.data)
            self.assertEqual(datos["options"]["temperature"], 0.7)
            self.assertFalse(datos["stream"])
            return FakeResponse()
        with patch("barriga_ia_narrativa.urlopen", side_effect=simular):
            self.assertEqual(generar_local("prueba")["titulo"],
                             "La carta bajo el faro")


if __name__ == "__main__":
    unittest.main()
