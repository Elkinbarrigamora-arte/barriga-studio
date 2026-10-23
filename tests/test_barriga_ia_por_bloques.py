"""Pruebas sin red del ensamblador de microguiones Barriga IA."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from barriga_ia_narrativa import ErrorNarrativa, contar_palabras
from barriga_ia_por_bloques import (
    ensamblar_por_bloques, generar_texto_local, limites_de_bloques,
    prompt_para_bloque, main,
)

GANCHO_CORTO = "¡Daniel encontró una carta escrita ayer!"
HISTORIA_CORTA = "Daniel " + " ".join(["descubrió"] * 64)
CIERRE_CORTO = (
    "Mateo estaba vivo bajo el faro y sostenía una segunda carta "
    "que Daniel jamás había enviado."
)


def original(nicho="leyendas", naturaleza="ficcion"):
    return {
        "titulo": "La carta del pasado",
        "nicho": nicho,
        "naturaleza": naturaleza,
        "gancho": "¡Daniel encontró una carta de su hermano desaparecido, pero estaba fechada ayer!",
        "historia": "Daniel " + " ".join(["investigaba"] * 180),
        "cierre": "Daniel creyó conocer la verdad, pero todavía había mucho que descubrir.",
        "personajes": [{"nombre": "Daniel"}, {"nombre": "Mateo"}],
        "continuidad": {"protagonista": "Daniel"},
        "fuentes": [],
        "duracion_objetivo_segundos": 35,
    }


class PruebasPorBloques(unittest.TestCase):
    def test_limites_35_segundos_y_gancho_breve(self):
        self.assertEqual(limites_de_bloques(35), {
            "gancho": (5, 8), "historia": (63, 70), "cierre": (13, 18)
        })
        self.assertEqual(contar_palabras(GANCHO_CORTO), 6)
        self.assertEqual(contar_palabras(HISTORIA_CORTA), 65)
        self.assertTrue(13 <= contar_palabras(CIERRE_CORTO) <= 18)

    def test_prompt_gancho_sin_dependencias_posteriores(self):
        req = prompt_para_bloque(
            "gancho", original(), {}, limites_de_bloques(35))
        self.assertIn("ENTRE 5 Y 8 PALABRAS", req)
        self.assertNotIn("desarrollo_definitivo", req)

    def test_ensamblaje_en_tres_bloques_y_revision_humana(self):
        textos = iter([GANCHO_CORTO, HISTORIA_CORTA, CIERRE_CORTO])
        llamadas = []
        def simular(prompt, modelo):
            llamadas.append(prompt)
            return next(textos)
        previo = original()
        salida = ensamblar_por_bloques(previo, generador=simular)
        self.assertEqual(len(llamadas), 3)
        self.assertEqual(salida["guion_original"], previo)
        self.assertEqual(salida["guion"]["gancho"], GANCHO_CORTO)
        self.assertEqual(salida["guion"]["historia"], HISTORIA_CORTA)
        self.assertEqual(salida["guion"]["cierre"], CIERRE_CORTO)
        self.assertTrue(salida["evaluacion"]["apto_para_revision_humana"])
        self.assertEqual(salida["estado"], "REVISION_HUMANA_PENDIENTE")
        self.assertFalse(salida["publicacion_automatica_autorizada"])
        self.assertEqual(len(salida["historial_bloques"]), 3)

    def test_reintenta_solamente_el_bloque_fuera_de_rango(self):
        respuestas = iter([
            "Daniel encontró ayer una carta que su hermano desaparecido había escrito hace mucho tiempo.",
            GANCHO_CORTO, HISTORIA_CORTA, CIERRE_CORTO,
        ])
        def simular(prompt, modelo):
            return next(respuestas)
        salida = ensamblar_por_bloques(original(), generador=simular)
        self.assertEqual(len(salida["historial_bloques"]), 4)
        self.assertFalse(salida["historial_bloques"][0]["longitud_valida"])
        self.assertTrue(salida["historial_bloques"][1]["longitud_valida"])
        self.assertTrue(salida["evaluacion"]["apto_para_revision_humana"])

    def test_rechaza_bloque_tras_dos_intentos(self):
        def verbose(prompt, modelo):
            return "Un guion demasiado largo " * 30
        anterior = original()
        copia = json.dumps(anterior, sort_keys=True)
        salida = ensamblar_por_bloques(anterior, generador=verbose)
        self.assertEqual(salida["estado"], "BLOQUE_RECHAZADO_GANCHO")
        self.assertIsNone(salida["guion"])
        self.assertIsNone(salida["evaluacion"])
        self.assertEqual(len(salida["historial_bloques"]), 2)
        self.assertFalse(salida["publicacion_automatica_autorizada"])
        self.assertEqual(json.dumps(anterior, sort_keys=True), copia)

    def test_no_se_reescriben_noticias(self):
        fuente = original("noticias", "factual")
        fuente["fuentes"] = ["https://example.com/informe"]
        with self.assertRaises(ErrorNarrativa):
            ensamblar_por_bloques(fuente, generador=lambda *x, **y: None)

    def test_duracion_invalida_y_limite_intentos(self):
        with self.assertRaises(ErrorNarrativa):
            limites_de_bloques(10)
        with self.assertRaises(ErrorNarrativa):
            ensamblar_por_bloques(original(), max_intentos=5)

    def test_no_sobrescribir_entrada_en_cli(self):
        with tempfile.TemporaryDirectory() as temp:
            origen = Path(temp) / "cuarta-prueba.json"
            datos = json.dumps({"guion": original()}, ensure_ascii=False)
            origen.write_text(datos, encoding="utf-8")
            args = ["narrativa.py", "--revisar-archivo", str(origen),
                    "--salida", str(origen)]
            with patch("sys.argv", args):
                with patch("sys.stderr", new_callable=io.StringIO):
                    with patch("barriga_ia_por_bloques.ensamblar_por_bloques") as brain:
                        code = main()
            self.assertEqual(code, 2)
            brain.assert_not_called()
            self.assertEqual(origen.read_text(encoding="utf-8"), datos)

    def test_no_sobrescribir_salida_preexistente(self):
        with tempfile.TemporaryDirectory() as temp:
            origen = Path(temp) / "cuarta-prueba.json"
            destino = Path(temp) / "quinta-prueba.json"
            origen.write_text(json.dumps({"guion": original()}), encoding="utf-8")
            destino.write_text("conservar este resultado", encoding="utf-8")
            args = ["narrativa.py", "--revisar-archivo", str(origen),
                    "--salida", str(destino)]
            with patch("sys.argv", args):
                with patch("sys.stderr", new_callable=io.StringIO):
                    with patch("barriga_ia_por_bloques.ensamblar_por_bloques") as brain:
                        code = main()
            self.assertEqual(code, 2)
            brain.assert_not_called()
            self.assertEqual(destino.read_text(encoding="utf-8"),
                             "conservar este resultado")

    def test_gancho_manual_permite_continuar_sin_modelo_para_gancho(self):
        respuestas = iter([HISTORIA_CORTA, CIERRE_CORTO])
        llamadas = []
        def simular(prompt, modelo):
            llamadas.append(prompt)
            return next(respuestas)
        res = ensamblar_por_bloques(original(), generador=simular,
                                    gancho_aprobado=GANCHO_CORTO)
        self.assertEqual(len(llamadas), 2)
        self.assertTrue(res["evaluacion"]["apto_para_revision_humana"])
        self.assertEqual(res["guion"]["gancho"], GANCHO_CORTO)
        self.assertEqual(res["historial_bloques"][0]["origen"],
                         "APROBADO_MANUALMENTE")
        self.assertEqual(len(res["historial_bloques"]), 3)

    def test_gancho_manual_invalido_no_dispara_generaciones(self):
        for gancho in ("Hola", " " * 4,
                       "Un gancho tan largo que definitivamente ya no cabe "
                       "dentro del tiempo previsto para el inicio de un reel"):
            with self.subTest(gancho=gancho):
                with self.assertRaises(ErrorNarrativa):
                    ensamblar_por_bloques(original(), gancho_aprobado=gancho)

    def test_gancho_usar_contexto_reducido_y_un_solo_campo(self):
        req = prompt_para_bloque(
            "gancho", original(), {}, limites_de_bloques(35))
        self.assertIn("ENTRE 5 Y 8 PALABRAS", req)
        self.assertIn('"texto"', req)
        self.assertNotIn("borrador_de_desarrollo", req)
        self.assertLess(len(req), 1100)

    def test_presupuesto_de_tokens_en_ollama_local(self):
        class Respuesta:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return json.dumps({
                    "response": json.dumps({"texto": GANCHO_CORTO})
                }).encode("utf-8")
        def resolver(request, timeout):
            self.assertEqual(request.full_url,
                             "http://127.0.0.1:11434/api/generate")
            datos = json.loads(request.data)
            self.assertEqual(datos["options"]["num_predict"], 75)
            self.assertEqual(datos["options"]["temperature"], 0.2)
            return Respuesta()
        with patch("barriga_ia_por_bloques.urlopen", side_effect=resolver):
            self.assertEqual(
                generar_texto_local("gancho corto", num_predict=75),
                GANCHO_CORTO)

    def test_error_de_ollama_no_se_convierte_en_exito(self):
        def fallar(prompt, modelo):
            raise ErrorNarrativa("Ollama detenido")
        salida = ensamblar_por_bloques(original(), generador=fallar)
        self.assertEqual(salida["estado"], "BLOQUE_RECHAZADO_GANCHO")
        self.assertIn("Ollama detenido", salida["historial_bloques"][0]["error"])
        self.assertEqual(len(salida["historial_bloques"]), 2)


if __name__ == "__main__":
    unittest.main()
