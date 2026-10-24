"""Contrato de series y plan audiovisual, sin Ollama ni motor de video."""
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from barriga_ia_narrativa import ErrorNarrativa
from barriga_ia_contexto import (
    normalizar_contexto, instrucciones_editoriales, crear_plan_video,
)
from barriga_ia_servicio_local import (
    guardar_biblia_serie, leer_biblia_serie, ejecutar_motor,
)
from puente_local import presentar_generacion


SERIE = {"modo": "serie", "serie_id": "pepito-pepita",
         "biblia": {"descripcion": "Pepito lleva sombrero rojo; Pepita viste azul."}}


class MemoriaNarrativaTest(unittest.TestCase):
    def test_independiente_predeterminado_sin_serie(self):
        contexto = normalizar_contexto()
        self.assertEqual(contexto["modo"], "independiente")
        self.assertIsNone(contexto["serie_id"])
        self.assertIsNone(contexto["biblia"])
        self.assertIn("no continúes historias", instrucciones_editoriales(contexto))

    def test_no_arrastrar_memoria_a_reel_independiente(self):
        for datos in (
            {"modo": "independiente", "serie_id": "pepito-pepita"},
            {"modo": "independiente", "biblia": {"personaje": "Pepito"}},
        ):
            with self.subTest(datos=datos):
                with self.assertRaises(ErrorNarrativa):
                    normalizar_contexto(datos)

    def test_serie_exige_orden_y_biblia_validos(self):
        for datos in (
            {"modo": "serie", "serie_id": "pepito-pepita"},
            {"modo": "serie", "serie_id": "pepito pepita", "biblia": {"x": 1}},
            {"modo": "serie", "serie_id": "pepito-pepita", "biblia": {}},
            {"modo": "desconocido"},
            [],
        ):
            with self.subTest(datos=datos):
                with self.assertRaises(ErrorNarrativa):
                    normalizar_contexto(datos)

    def test_serie_solo_recibe_su_ficha_explicita(self):
        a = normalizar_contexto(SERIE)
        b = normalizar_contexto({"modo": "serie", "serie_id": "dinosaurios",
                                 "biblia": {"descripcion": "Triceratops azul"}})
        self.assertIn("sombrero rojo", instrucciones_editoriales(a))
        self.assertNotIn("Triceratops", instrucciones_editoriales(a))
        self.assertNotIn("Pepita", instrucciones_editoriales(b))

    def test_video_es_plan_no_archivo_generado(self):
        contexto = normalizar_contexto(SERIE)
        guion = {"gancho": "Aparece una puerta.",
                 "historia": "Pepita encuentra una llave.",
                 "cierre": "La llave abre el castillo."}
        plan = crear_plan_video(guion, 35, contexto)
        self.assertEqual([x["bloque"] for x in plan["escenas"]],
                         ["gancho", "historia", "cierre"])
        self.assertEqual(plan["escenas"][0]["inicio_segundos"], 0)
        self.assertEqual(plan["escenas"][-1]["fin_segundos"], 35)
        self.assertEqual(plan["modo"], "serie")
        self.assertEqual(plan["biblia_serie"], SERIE["biblia"])
        self.assertFalse(plan["video_generado"])
        self.assertFalse(plan["voz_generada"])
        self.assertEqual(plan["escenas"][1]["narracion"], guion["historia"])
        self.assertIsNone(crear_plan_video(None, 35, contexto))

    def test_video_responde_a_formato_visual_y_voz_del_studio(self):
        c = normalizar_contexto({"video": {
            "formato": "16:9", "estilo_visual": "Animación 3D",
            "voz": "Español femenino"}})
        p = crear_plan_video({"gancho": "Uno", "historia": "Dos",
                              "cierre": "Tres"}, 60, c)
        self.assertEqual((p["formato"], p["estilo_visual"], p["voz"]),
                         ("16:9", "Animación 3D", "Español femenino"))
        self.assertIsNone(p["serie_id"])
        with self.assertRaises(ErrorNarrativa):
            normalizar_contexto({"video": {"formato": "21:9"}})

    def test_series_almacenadas_por_id_sin_mezclarse(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "local-data" / "barriga.sqlite3"
            guardar_biblia_serie("pepito-pepita", {"texto": "Rojo"}, db)
            guardar_biblia_serie("dinosaurios", {"texto": "T-Rex"}, db)
            self.assertEqual(leer_biblia_serie("pepito-pepita", db),
                             {"texto": "Rojo"})
            self.assertEqual(leer_biblia_serie("dinosaurios", db),
                             {"texto": "T-Rex"})
            self.assertIsNone(leer_biblia_serie("joyas", db))
            self.assertIsNone(leer_biblia_serie("../peligro", db))
            guardar_biblia_serie("pepito-pepita", {"texto": "Azul"}, db)
            self.assertEqual(leer_biblia_serie("pepito-pepita", db),
                             {"texto": "Azul"})
            with sqlite3.connect(str(db)) as con:
                self.assertEqual(con.execute(
                    "SELECT COUNT(*) FROM versiones_memorias_series "
                    "WHERE serie_id='pepito-pepita'").fetchone()[0], 2)

    def test_prompt_de_dinosaurio_no_contiene_regresion_carta(self):
        guion = {"titulo": "Un dinosaurio", "gancho": "Gancho",
                 "historia": "Historia", "cierre": "Cierre",
                 "personajes": [], "continuidad": {},
                 "fuentes": [], "nicho": "ficcion", "naturaleza": "ficcion"}
        with patch("barriga_ia_servicio_local.generar_local",
                   return_value=guion) as gen:
            with patch("barriga_ia_servicio_local.ensamblar_por_bloques",
                       return_value={"guion": guion, "evaluacion": {
                           "apto_para_revision_humana": True},
                           "estado": "REVISION_HUMANA_PENDIENTE"}):
                r = ejecutar_motor("El dinosaurio entra en un bosque.",
                                   "modelo-prueba", duracion=30)
        prompt = gen.call_args.args[0]
        self.assertNotIn("DURACIÓN EXACTA de la desaparición", prompt)
        self.assertNotIn("No sustituyas cartas por ríos", prompt)
        self.assertIn("MODO REEL INDEPENDIENTE", prompt)
        self.assertEqual(r["plan_video"]["duracion_objetivo_segundos"], 30)
        self.assertEqual(r["contexto_editorial"]["modo"], "independiente")

    def test_serie_solicitada_cambia_prompt_y_guarda_identidad(self):
        guion = {"titulo": "Pepita", "gancho": "Gancho", "historia": "Historia",
                 "cierre": "Cierre", "personajes": [], "continuidad": {},
                 "fuentes": [], "nicho": "miniseries", "naturaleza": "ficcion"}
        with patch("barriga_ia_servicio_local.generar_local",
                   return_value=guion) as gen:
            with patch("barriga_ia_servicio_local.ensamblar_por_bloques",
                       return_value={"guion": guion, "evaluacion": {
                           "apto_para_revision_humana": True},
                           "estado": "REVISION_HUMANA_PENDIENTE"}):
                r = ejecutar_motor("Pepita descubre una puerta secreta.",
                                   "modelo-prueba", contexto=SERIE)
        self.assertIn('"nicho": "miniseries"', gen.call_args.args[0])
        self.assertIn("sombrero rojo", gen.call_args.args[0])
        self.assertEqual(r["contexto_editorial"]["serie_id"], "pepito-pepita")
        vista = presentar_generacion(r, "BI-" + "0" * 20)
        self.assertEqual(vista["plan_video"]["serie_id"], "pepito-pepita")
        self.assertFalse(vista["publicacion_automatica_autorizada"])


if __name__ == "__main__":
    unittest.main()
