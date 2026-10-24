"""Pruebas sin Ollama de recuperación de la sexta prueba narrativa."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from barriga_ia_recuperar import (
    cargar_sexta, reanudar, validar_bloque, oraciones_completas,
    texto_canonico, prompt_historia, main,
)
from barriga_ia_narrativa import contar_palabras


def fixture():
    original = {
        "titulo": "Carta inesperada", "nicho": "leyendas",
        "naturaleza": "ficcion",
        "gancho": "¡La carta de su hermano apareció ayer!",
        "historia": "Daniel investigaba " + "el misterio. " * 91,
        "cierre": "El hermano miró la carta y reveló lo que había sucedido.",
        "personajes": [{"nombre": "Daniel"}, {"nombre": "Mateo"}],
        "continuidad": {"protagonista": "Daniel"},
        "fuentes": [], "duracion_objetivo_segundos": 35,
    }
    historia = (
        "Daniel abrió la carta frente a su madre. La tinta todavía olía a "
        "pintura reciente. Buscó en el sótano de la casa y encontró una "
        "fotografía con el rostro de Mateo, su hermano. En el reverso "
        "alguien había escrito la misma fecha. Daniel escuchó pasos "
        "detrás de la puerta. Se volvió y vio una llave oxidada bajo "
        "la sombra del antiguo reloj."
    )
    # Debe estar dentro de 63–70: construimos datos cortos fiables.
    n = contar_palabras(historia)
    if n < 63:
        historia = historia[:-1] + " en aquella tarde inesperada."
    cierre = ("Daniel abrió la puerta: Mateo estaba allí, envejecido, y le mostró "
              "una fotografía donde ambos aparecían juntos.")
    registro = {
        "guion_original": original,
        "historial_bloques": [
            {"bloque": "gancho", "intento": 1,
             "texto": original["gancho"],
             "aceptable_para_ensamblaje": True, "palabras": 7},
            {"bloque": "historia", "intento": 1,
             "texto": "Daniel investigó." * 40,
             "aceptable_para_ensamblaje": False},
            {"bloque": "historia", "intento": 2,
             "texto": "Daniel investigó." * 40,
             "aceptable_para_ensamblaje": False},
        ],
        "bloques_aprobados_en_longitud": {"gancho": 7},
        "estado": "BLOQUE_RECHAZADO_HISTORIA",
    }
    return registro, historia, cierre


class TestRecuperacion(unittest.TestCase):
    def test_contador_historia_fixture(self):
        _, historia, cierre = fixture()
        self.assertTrue(63 <= contar_palabras(historia) <= 70,
                        contar_palabras(historia))
        self.assertTrue(13 <= contar_palabras(cierre) <= 18,
                        contar_palabras(cierre))

    def test_rechazo_oraciones_incompletas(self):
        for value in ("Daniel vio que", "Daniel entró,", "Daniel encontró una",
                      "«La carta seguía abierta.", "Daniel encontró un"):
            self.assertFalse(oraciones_completas(value), value)
        self.assertTrue(oraciones_completas("Daniel abrió la carta."))

    def test_duplicate_case_spacing_and_punctuation(self):
        self.assertEqual(texto_canonico(" Daniel   MIRÓ."),
                         texto_canonico("daniel miró!"))

    def test_cargar_y_preservar_gancho_sin_reintentos(self):
        registro, historia, cierre = fixture()
        with tempfile.TemporaryDirectory() as directory:
            fuente = Path(directory) / "sexta-prueba.json"
            fuente.write_text(json.dumps(registro, ensure_ascii=False), encoding="utf-8")
            reg, original, historico, aprobados, limites = cargar_sexta(fuente, 35)
            self.assertEqual(aprobados["gancho"], registro["guion_original"]["gancho"])
            self.assertEqual(len(historico), 3)
            self.assertEqual(limites["historia"], (63, 70))
            entradas = iter([historia, cierre])
            llamadas = []
            def simular(prompt, modelo):
                llamadas.append(prompt)
                return next(entradas)
            nuevo = reanudar(reg, original, historico, aprobados, limites,
                            generador=simular)
            self.assertEqual(len(llamadas), 2)
            self.assertEqual(nuevo["guion"]["gancho"], aprobados["gancho"])
            self.assertEqual(nuevo["historial_bloques"][:3], historico)
            self.assertEqual(nuevo["bloques_preservados"], ["gancho"])
            self.assertFalse(nuevo["publicacion_automatica_autorizada"])

    def test_reintento_alternativo_y_no_repetir_rechazados(self):
        registro, historia, cierre = fixture()
        with tempfile.TemporaryDirectory() as directory:
            fuente = Path(directory) / "sexta.json"
            fuente.write_text(json.dumps(registro), encoding="utf-8")
            reg, original, historial, aprobados, limites = cargar_sexta(fuente, 35)
            respuestas = iter([
                registro["historial_bloques"][1]["texto"],
                historia,
                cierre,
            ])
            prompts = []
            def simular(prompt, modelo):
                prompts.append(prompt)
                return next(respuestas)
            out = reanudar(reg, original, historial, aprobados, limites,
                          generador=simular)
            nuevos = out["historial_bloques"][3:]
            self.assertIn("Repetición literal", " ".join(nuevos[0]["motivos_rechazo"]))
            self.assertIn("ESTRATEGIA ALTERNATIVA", prompts[1])
            self.assertEqual(nuevos[1]["bloque"], "historia")

    def test_bloqueo_por_historia_truncada_y_no_exito_falso(self):
        registro, historia, cierre = fixture()
        with tempfile.TemporaryDirectory() as directory:
            fuente = Path(directory) / "sexta.json"
            fuente.write_text(json.dumps(registro), encoding="utf-8")
            reg, original, historial, aprobados, limites = cargar_sexta(fuente, 35)
            incompleta = historia.rstrip(".") + " y"
            with patch("barriga_ia_recuperar.generar_texto_local") as fake:
                fake.return_value = incompleta
                result = reanudar(reg, original, historial, aprobados, limites,
                                 max_intentos=2, generador=fake)
            self.assertEqual(result["estado"], "BLOQUE_RECHAZADO_HISTORIA")
            self.assertIsNone(result["guion"])
            self.assertEqual(result["historial_bloques"][:3], historial)

    def test_error_no_sobrescribe_archivo(self):
        registro, historia, cierre = fixture()
        with tempfile.TemporaryDirectory() as directory:
            fuente = Path(directory) / "sexta.json"
            fuente.write_text(json.dumps(registro), encoding="utf-8")
            with patch("sys.argv", ["recuperar.py", "--recuperar", str(fuente),
                                    "--salida", str(fuente)]):
                with patch("sys.stderr"):
                    self.assertEqual(main(), 2)
            self.assertEqual(json.loads(fuente.read_text()), registro)

    def test_velocidad_configurable_y_diagnostico(self):
        registro, historia, cierre = fixture()
        with tempfile.TemporaryDirectory() as directory:
            fuente = Path(directory) / "sexta.json"
            fuente.write_text(json.dumps(registro), encoding="utf-8")
            reg, orig, hist, ap, lim = cargar_sexta(fuente, 35)
            respuestas = iter([historia, cierre])
            result = reanudar(reg, orig, hist, ap, lim, velocidad_ppm=160,
                              generador=lambda prompt, modelo: next(respuestas))
            if result["evaluacion"]:
                self.assertEqual(result["evaluacion"]["velocidad_narracion_ppm"], 160)
                self.assertFalse(result["publicacion_automatica_autorizada"])

    def test_prompt_incluye_motivos_especificos_del_rechazo(self):
        registro, historia, cierre = fixture()
        registro["historial_bloques"][-1]["motivos_rechazo"] = [
            "Extensión 123 palabras fuera de 63 a 70",
            "Respuesta repetida literalmente tras un rechazo",
        ]
        with tempfile.TemporaryDirectory() as directory:
            fuente = Path(directory) / "sexta.json"
            fuente.write_text(json.dumps(registro), encoding="utf-8")
            reg, orig, hist, aprobados, limites = cargar_sexta(fuente, 35)
            prompts = []
            def simular(prompt, modelo):
                prompts.append(prompt)
                return historia if len(prompts) == 1 else cierre
            reanudar(reg, orig, hist, aprobados, limites, generador=simular)
            self.assertIn("Extensión 123 palabras", prompts[0])
            self.assertIn("Respuesta repetida literalmente", prompts[0])

    def test_no_reinventar_personajes_en_control_heuristico(self):
        reg, historia, _ = fixture()
        razones = validar_bloque("Daniel habló con Camilo.", "historia",
                                 reg["guion_original"],
                                 {"historia": (3, 6)}, set())
        self.assertTrue(any("nombre nuevo" in x for x in razones))


if __name__ == "__main__":
    unittest.main()
