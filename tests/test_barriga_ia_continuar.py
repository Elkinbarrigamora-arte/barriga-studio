"""Regresión: continuar prueba real sin perder el gancho ni inventar aprobación."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from barriga_ia_continuar import (
    recuperar_gancho, limites_escenas, armar_instruccion,
    continuar_en_escenas, main,
)
from barriga_ia_narrativa import ErrorNarrativa, contar_palabras


GANCHO = "¡La carta llegó treinta años después, ayer!"
PARTE_A = (
    "Daniel abrió la carta frente a la ventana y reconoció la letra de su "
    "hermano. El sobre olía a humo y llevaba un sello nuevo. Su teléfono "
    "vibró cuando leyó la fecha: ayer."
)
PARTE_B = (
    "Buscó entre fotografías antiguas y halló el mismo sello sobre la puerta "
    "del viejo faro. Corrió hasta allí mientras una luz temblaba detrás del "
    "cristal. Escuchó pasos adentro, aunque el faro llevaba décadas cerrado."
)
CIERRE = (
    "Al abrir la puerta, su hermano apareció envejecido. "
    "Había escrito la carta para guiarlo hasta allí."
)


def borrador():
    return {
        "titulo": "La carta del pasado",
        "nicho": "leyendas",
        "naturaleza": "ficcion",
        "gancho": "¡Daniel encontró la carta de su hermano desaparecido hace treinta años, fechada ayer!",
        "historia": "Daniel buscó respuestas en el viejo faro. " * 33,
        "cierre": "Su hermano estaba vivo y lo esperaba dentro.",
        "personajes": [{"nombre": "Daniel"}, {"nombre": "Mateo"}],
        "continuidad": {"protagonista": "Daniel"},
        "fuentes": [],
        "duracion_objetivo_segundos": 35,
    }


def sexta_prueba():
    return {
        "guion_original": borrador(),
        "historial_bloques": [
            {"bloque": "gancho", "intento": 1, "texto": GANCHO,
             "palabras": contar_palabras(GANCHO),
             "aceptable_para_ensamblaje": True},
            {"bloque": "historia", "intento": 1, "texto": "Demasiado " * 90,
             "aceptable_para_ensamblaje": False},
            {"bloque": "historia", "intento": 2, "texto": "Demasiado " * 100,
             "aceptable_para_ensamblaje": False},
        ],
        "guion": None,
        "estado": "BLOQUE_RECHAZADO_HISTORIA",
    }


class ContinuidadRegresion(unittest.TestCase):
    def test_presupuesto_dividir_35_segundos(self):
        self.assertEqual(limites_escenas(35),
                         {"historia_1": (31, 35),
                          "historia_2": (32, 35),
                          "cierre": (13, 18)})
        self.assertEqual(contar_palabras(GANCHO), 8)
        self.assertEqual(contar_palabras(PARTE_A), 33)
        self.assertEqual(contar_palabras(PARTE_B), 34)
        self.assertEqual(contar_palabras(CIERRE), 16)

    def test_recupera_gancho_aprobado_de_archivo_incompleto(self):
        with tempfile.TemporaryDirectory() as temp:
            archivo = Path(temp) / "sexta-prueba.json"
            archivo.write_text(json.dumps(sexta_prueba()), encoding="utf-8")
            original, gancho = recuperar_gancho(archivo)
        self.assertEqual(gancho, GANCHO)
        self.assertEqual(original["nicho"], "leyendas")

    def test_rechaza_engancho_sin_aprobacion(self):
        obj = sexta_prueba()
        obj["historial_bloques"][0]["aceptable_para_ensamblaje"] = False
        with tempfile.TemporaryDirectory() as temp:
            archivo = Path(temp) / "sexta-prueba.json"
            archivo.write_text(json.dumps(obj), encoding="utf-8")
            with self.assertRaises(ErrorNarrativa):
                recuperar_gancho(archivo)

    def test_ensambla_dos_microescenas_y_conserva_gancho(self):
        respuestas = iter([PARTE_A, PARTE_B, CIERRE])
        peticiones = []
        def simular(prompt, modelo):
            peticiones.append(prompt)
            return next(respuestas)
        original = borrador()
        salida = continuar_en_escenas(original, GANCHO, "Carta escrita ayer",
                                      generador=simular)
        self.assertEqual(salida["estado"], "REVISION_HUMANA_PENDIENTE")
        self.assertTrue(salida["evaluacion"]["apto_para_revision_humana"])
        self.assertEqual(salida["guion"]["gancho"], GANCHO)
        self.assertEqual(salida["guion"]["historia"], PARTE_A + " " + PARTE_B)
        self.assertEqual(len(salida["historial_intentos"]), 3)
        self.assertFalse(salida["publicacion_automatica_autorizada"])
        self.assertFalse(salida["revision_semantica_realizada"])
        self.assertNotIn("historia_2", peticiones[0])
        self.assertIn(PARTE_A, peticiones[1])

    def test_reintenta_solo_fragmento_largo(self):
        peticiones = []
        respuestas = iter(["Texto demasiado largo " * 70, PARTE_A,
                          PARTE_B, CIERRE])
        def simular(prompt, modelo):
            peticiones.append(prompt)
            return next(respuestas)
        salida = continuar_en_escenas(borrador(), GANCHO, "Carta escrita ayer",
                                      generador=simular)
        self.assertEqual(len(peticiones), 4)
        self.assertFalse(salida["historial_intentos"][0]["valido_en_estructura"])
        self.assertTrue(salida["historial_intentos"][1]["valido_en_estructura"])
        self.assertTrue(salida["evaluacion"]["apto_para_revision_humana"])

    def test_fallo_no_borra_fragmentos_anteriores(self):
        respuestas = iter([PARTE_A, "Historia muy extensa " * 60,
                           "Historia muy extensa " * 60])
        salida = continuar_en_escenas(borrador(), GANCHO, "Carta escrita ayer",
                                      generador=lambda prompt, modelo: next(respuestas))
        self.assertEqual(salida["estado"], "FRAGMENTO_RECHAZADO_HISTORIA_2")
        self.assertEqual(salida["bloques_conservados"]["historia_1"], PARTE_A)
        self.assertIsNone(salida["guion"])
        self.assertEqual(len(salida["historial_intentos"]), 3)

    def test_no_reescribir_hechos_factuales(self):
        obj = borrador()
        obj["naturaleza"] = "factual"
        with self.assertRaises(ErrorNarrativa):
            continuar_en_escenas(obj, GANCHO, "Historia factual",
                                generador=lambda prompt, modelo: PARTE_A)

    def test_cli_no_sobrescribe_origen_ni_salida_previa(self):
        with tempfile.TemporaryDirectory() as temp:
            origen = Path(temp) / "sexta-prueba.json"
            destino = Path(temp) / "septima-prueba.json"
            payload = json.dumps(sexta_prueba())
            origen.write_text(payload, encoding="utf-8")
            destino.write_text("reservado", encoding="utf-8")
            with patch("sys.argv", ["continuar.py", "--desde", str(origen),
                                    "--salida", str(destino)]):
                with patch("sys.stderr", new_callable=io.StringIO):
                    with patch("barriga_ia_continuar.generar_texto_local") as modelo:
                        codigo = main()
            self.assertEqual(codigo, 2)
            modelo.assert_not_called()
            self.assertEqual(origen.read_text(encoding="utf-8"), payload)
            self.assertEqual(destino.read_text(encoding="utf-8"), "reservado")

    def test_cli_guarda_resultado_sin_alterar_archivo_rechazado(self):
        with tempfile.TemporaryDirectory() as temp:
            origen = Path(temp) / "sexta-prueba.json"
            destino = Path(temp) / "septima-prueba.json"
            payload = json.dumps(sexta_prueba())
            origen.write_text(payload, encoding="utf-8")
            respuestas = iter([PARTE_A, PARTE_B, CIERRE])
            with patch("sys.argv", ["continuar.py", "--desde", str(origen),
                                    "--salida", str(destino)]):
                with patch("barriga_ia_continuar.generar_texto_local",
                           side_effect=lambda prompt, **kwargs: next(respuestas)):
                    with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                        codigo = main()
            self.assertEqual(codigo, 0)
            corto = json.loads(stdout.getvalue())
            self.assertTrue(corto["apto_para_revision_humana"])
            self.assertEqual(corto["llamadas_ollama"], 3)
            self.assertEqual(origen.read_text(encoding="utf-8"), payload)
            self.assertEqual(json.loads(destino.read_text(encoding="utf-8"))["guion"]["gancho"],
                             GANCHO)


if __name__ == "__main__":
    unittest.main()
