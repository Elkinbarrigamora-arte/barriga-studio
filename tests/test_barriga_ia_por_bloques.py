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
    prompt_para_bloque, proponer_gancho_seguro, main,
    leer_sesion_por_bloques, detectar_problemas_editoriales,
)

GANCHO_CORTO = "¡Daniel encontró una carta escrita ayer!"
HISTORIA_CORTA = (
    "Daniel siguió el rastro de la carta hasta el faro abandonado. "
    "Allí encontró una fotografía de Mateo frente a la puerta, tomada aquella misma mañana. "
    "Un pescador aseguró haber visto su antigua chaqueta cerca del muelle. "
    "Daniel revisó el sobre y descubrió una dirección escrita a mano. "
    "Al llegar al lugar, escuchó pasos detrás de una pared y reconoció la voz de su hermano desaparecido."
)
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

    def test_regresion_quinta_prueba_dos_ganchos_identicos_y_pepe(self):
        # Fallo observado en la Mac: Ollama repitió el mismo texto de 11 palabras.
        texto = "Daniel encontró una carta antigua en el viejo cajón de Pepe."
        self.assertEqual(contar_palabras(texto), 11)
        prompts = []
        def simular(prompt, modelo):
            prompts.append(prompt)
            return texto
        salida = ensamblar_por_bloques(original(), generador=simular)
        self.assertEqual(salida["estado"], "BLOQUE_RECHAZADO_GANCHO")
        self.assertEqual(len(salida["historial_bloques"]), 2)
        primeros = salida["historial_bloques"][0]["motivos_rechazo"]
        segundos = salida["historial_bloques"][1]["motivos_rechazo"]
        self.assertTrue(any("Extensión" in x for x in primeros))
        self.assertTrue(any("Pepe" in x for x in primeros))
        self.assertTrue(any("ayer" in x for x in primeros))
        self.assertTrue(any("repetida" in x for x in segundos))
        self.assertNotEqual(prompts[0], prompts[1])
        self.assertIn("Pepe", prompts[1])
        self.assertIn("REEMPLAZA", prompts[1])
        self.assertIsNone(salida["guion"])

    def test_gancho_corto_con_personaje_nuevo_no_es_aceptado(self):
        falso = "La carta de Pepe apareció ayer."
        self.assertEqual(contar_palabras(falso), 6)
        respuestas = iter([falso, GANCHO_CORTO, HISTORIA_CORTA, CIERRE_CORTO])
        def simular(prompt, modelo):
            return next(respuestas)
        salida = ensamblar_por_bloques(original(), generador=simular)
        self.assertEqual(len(salida["historial_bloques"]), 4)
        primer = salida["historial_bloques"][0]
        self.assertTrue(primer["longitud_valida"])
        self.assertFalse(primer["aceptable_para_ensamblaje"])
        self.assertTrue(any("Pepe" in x for x in primer["motivos_rechazo"]))
        self.assertEqual(salida["guion"]["gancho"], GANCHO_CORTO)

    def test_segundo_intento_cambia_temperatura_y_conserva_limites(self):
        texto = "Daniel encontró una carta antigua en el viejo cajón de Pepe."
        cuerpos = []
        class Respuesta:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
            def read(self):
                return json.dumps({
                    "response": json.dumps({"texto": texto})
                }).encode("utf-8")
        def resolver(request, timeout):
            cuerpos.append(json.loads(request.data))
            return Respuesta()
        with patch("barriga_ia_por_bloques.urlopen", side_effect=resolver):
            salida = ensamblar_por_bloques(original())
        self.assertEqual(salida["estado"], "BLOQUE_RECHAZADO_GANCHO")
        self.assertEqual(len(cuerpos), 2)
        self.assertEqual(
            [d["options"]["temperature"] for d in cuerpos], [0.2, 0.65])
        self.assertEqual(
            [d["options"]["num_predict"] for d in cuerpos], [75, 75])
        self.assertNotEqual(cuerpos[0]["prompt"], cuerpos[1]["prompt"])

    def test_terminal_informa_gancho_rechazado_y_motivos(self):
        texto = "Daniel encontró una carta antigua en el viejo cajón de Pepe."
        with tempfile.TemporaryDirectory() as temp:
            origen = Path(temp) / "cuarta-prueba.json"
            destino = Path(temp) / "sexta-prueba.json"
            origen.write_text(json.dumps({"guion": original()},
                                         ensure_ascii=False), encoding="utf-8")
            argv = ["por_bloques.py", "--revisar-archivo", str(origen),
                    "--salida", str(destino)]
            with patch("sys.argv", argv):
                with patch("barriga_ia_por_bloques.generar_texto_local",
                           return_value=texto):
                    with patch("sys.stdout", new_callable=io.StringIO) as stdout:
                        code = main()
            self.assertEqual(code, 2)
            detalle = json.loads(stdout.getvalue())
            self.assertEqual(detalle["ultimo_texto_rechazado"], texto)
            self.assertTrue(any("repetida" in motivo
                                for motivo in detalle["motivos_ultimo_rechazo"]))
            self.assertTrue(destino.exists())
            self.assertFalse(detalle["publicacion_automatica_autorizada"])

    def test_regla_de_premisa_es_fiel_y_no_inventa_autor(self):
        premisa = (
            "Un hombre encuentra una carta de su hermano desaparecido hace "
            "treinta años, pero descubre que alguien la escribió ayer"
        )
        propuesta = proponer_gancho_seguro(
            original(), limites_de_bloques(35), premisa=premisa)
        self.assertEqual(propuesta["texto"],
                         "¡La carta de su hermano fue escrita ayer!")
        self.assertEqual(contar_palabras(propuesta["texto"]), 8)
        self.assertEqual(propuesta["origen"], "REGLA_FIEL_A_PREMISA")
        self.assertNotIn("Pepe", propuesta["texto"])
        self.assertNotIn("hermano escribió", propuesta["texto"])

    def test_alternativa_evitar_llamada_de_ollama_para_gancho(self):
        premisa = (
            "Un hombre encuentra una carta de su hermano desaparecido hace "
            "treinta años, pero descubre que alguien la escribió ayer"
        )
        llamadas = []
        respuestas = iter([HISTORIA_CORTA, CIERRE_CORTO])
        def modelo(prompt, modelo):
            llamadas.append(prompt)
            return next(respuestas)
        antes = original()
        snapshot = json.dumps(antes, sort_keys=True)
        resultado = ensamblar_por_bloques(
            antes, duracion=35, generador=modelo,
            estrategia_gancho="reglas-primero", premisa=premisa)
        self.assertEqual(len(llamadas), 2)
        self.assertEqual(resultado["historial_bloques"][0]["intento"], 0)
        self.assertEqual(resultado["historial_bloques"][0]["origen"],
                         "REGLA_FIEL_A_PREMISA")
        self.assertEqual(resultado["guion"]["gancho"],
                         "¡La carta de su hermano fue escrita ayer!")
        self.assertEqual(resultado["estado"], "REVISION_HUMANA_PENDIENTE")
        self.assertEqual(snapshot, json.dumps(antes, sort_keys=True))
        self.assertFalse(resultado["publicacion_automatica_autorizada"])

    def test_sin_hechos_suficientes_no_inventa_gancho(self):
        guion = original()
        guion["gancho"] = "En el camino sin salida."
        guion["historia"] = "Un viajero observó unas luces en el cielo."
        self.assertIsNone(proponer_gancho_seguro(
            guion, limites_de_bloques(35), premisa="Un viajero encontró luces"))
        # Se conserva la ruta normal a Ollama cuando no puede deducirlo.
        consultas = iter([GANCHO_CORTO, HISTORIA_CORTA, CIERRE_CORTO])
        salida = ensamblar_por_bloques(
            guion, estrategia_gancho="reglas-primero",
            premisa="Un viajero encontró luces",
            generador=lambda prompt, modelo: next(consultas))
        self.assertEqual(salida["historial_bloques"][0]["intento"], 1)
        self.assertEqual(salida["guion"]["gancho"], GANCHO_CORTO)

    def test_conservar_salida_anterior_y_reportar_metodo_gancho(self):
        premisa = (
            "Un hombre encuentra una carta de su hermano desaparecido hace "
            "treinta años, pero descubre que alguien la escribió ayer"
        )
        with tempfile.TemporaryDirectory() as temp:
            entrada = Path(temp) / "cuarta-prueba.json"
            salida = Path(temp) / "septima-prueba.json"
            datos = json.dumps({"guion": original()}, ensure_ascii=False)
            entrada.write_text(datos, encoding="utf-8")
            argv = ["por_bloques.py", "--revisar-archivo", str(entrada),
                    "--salida", str(salida), "--estrategia-gancho",
                    "reglas-primero", "--premisa", premisa]
            with patch("sys.argv", argv):
                with patch("barriga_ia_por_bloques.generar_texto_local",
                           side_effect=[HISTORIA_CORTA, CIERRE_CORTO]) as modelo:
                    with patch("sys.stdout", new_callable=io.StringIO) as out:
                        code = main()
            self.assertEqual(code, 0)
            self.assertEqual(modelo.call_count, 2)
            informe = json.loads(out.getvalue())
            self.assertEqual(informe["numero_llamadas_ollama"], 2)
            self.assertEqual(informe["metodo_gancho"], "REGLA_FIEL_A_PREMISA")
            self.assertEqual(entrada.read_text(encoding="utf-8"), datos)
            guardado = json.loads(salida.read_text(encoding="utf-8"))
            self.assertEqual(guardado["historial_bloques"][0]["origen"],
                             "REGLA_FIEL_A_PREMISA")
            self.assertFalse(guardado["publicacion_automatica_autorizada"])

    def test_premisa_invalida_se_rechaza_sin_usar_ollama(self):
        with self.assertRaises(ErrorNarrativa):
            proponer_gancho_seguro(
                original(), limites_de_bloques(35), premisa="ayer")
        with self.assertRaises(ErrorNarrativa):
            ensamblar_por_bloques(
                original(), estrategia_gancho="reglas-primero",
                premisa="x", generador=lambda prompt, modelo: "nunca")

    def test_error_de_ollama_no_se_convierte_en_exito(self):
        def fallar(prompt, modelo):
            raise ErrorNarrativa("Ollama detenido")
        salida = ensamblar_por_bloques(original(), generador=fallar)
        self.assertEqual(salida["estado"], "BLOQUE_RECHAZADO_GANCHO")
        self.assertIn("Ollama detenido", salida["historial_bloques"][0]["error"])
        self.assertEqual(len(salida["historial_bloques"]), 2)


class PruebasRecuperacionSexta(unittest.TestCase):
    def crear_informe_sexta(self):
        borrador = original()
        return {
            "guion_original": borrador,
            "estado": "BLOQUE_RECHAZADO_HISTORIA",
            "historial_bloques": [
                {"bloque": "gancho", "intento": 1,
                 "texto": GANCHO_CORTO, "palabras": 6,
                 "longitud_valida": True, "aceptable_para_ensamblaje": True,
                 "motivos_rechazo": []},
                {"bloque": "historia", "intento": 1,
                 "texto": "Daniel " + "descubrió " * 121,
                 "palabras": 122, "aceptable_para_ensamblaje": False,
                 "motivos_rechazo": ["Extensión 122 palabras fuera de 63 a 70"]},
                {"bloque": "historia", "intento": 2,
                 "texto": "Daniel leyó la carta y encontró que había cometido ",
                 "palabras": 10, "aceptable_para_ensamblaje": False,
                 "motivos_rechazo": ["Oración incompleta"]},
            ],
            "guion": None,
            "publicacion_automatica_autorizada": False,
        }

    def test_reanudar_conserva_gancho_y_solo_regenera_historia_y_cierre(self):
        informe = self.crear_informe_sexta()
        respuestas = iter([
            "Daniel " + " ".join(["pensó"] * 64),  # truncado aunque mida 65
            HISTORIA_CORTA,
            CIERRE_CORTO,
        ])
        prompts = []
        def simular(prompt, modelo):
            prompts.append(prompt)
            return next(respuestas)
        salida = ensamblar_por_bloques(
            original(), sesion_previa=informe, generador=simular)
        self.assertEqual(len(prompts), 3)
        self.assertEqual(salida["guion"]["gancho"], GANCHO_CORTO)
        self.assertEqual(salida["guion"]["historia"], HISTORIA_CORTA)
        self.assertEqual(salida["estado"], "REVISION_HUMANA_PENDIENTE")
        self.assertEqual(salida["registros_recuperados"], 3)
        self.assertEqual(salida["historial_bloques"][:3], informe["historial_bloques"])
        self.assertTrue(any("Oración incompleta" in x
                            for x in salida["historial_bloques"][3]["motivos_rechazo"]))
        self.assertIn("PLAN ALTERNATIVO", prompts[0])
        self.assertIn("PLAN ALTERNATIVO", prompts[1])
        self.assertEqual(salida["evaluacion"]["palabras"], 87)
        self.assertFalse(salida["publicacion_automatica_autorizada"])

    def test_no_aceptar_respuesta_repetida_historicamente(self):
        informe = self.crear_informe_sexta()
        repetido = "Daniel " + " ".join(["descubrió"] * 121)
        guion = ensamblar_por_bloques(
            original(), sesion_previa=informe,
            generador=lambda prompt, modelo: repetido)
        self.assertEqual(guion["estado"], "BLOQUE_RECHAZADO_HISTORIA")
        self.assertTrue(any("repetida" in x for x in
                            guion["historial_bloques"][-1]["motivos_rechazo"]))
        self.assertEqual(guion["bloques_aprobados_en_longitud"]["gancho"], 6)

    def test_leer_archivo_sexta_sin_editar_ni_sobrescribir(self):
        informe = self.crear_informe_sexta()
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = Path(carpeta) / "sexta-prueba.json"
            contenido = json.dumps(informe, ensure_ascii=False)
            ruta.write_text(contenido, encoding="utf-8")
            guion, recuperado = leer_sesion_por_bloques(ruta)
            self.assertEqual(guion, informe["guion_original"])
            self.assertEqual(recuperado, informe)
            self.assertEqual(ruta.read_text(encoding="utf-8"), contenido)

    def test_oracion_truncada_se_rechaza_incluso_con_65_palabras(self):
        texto = HISTORIA_CORTA.rstrip(".") + " y"
        self.assertIn("Oración incompleta",
                      " ".join(detectar_problemas_editoriales(
                          texto, original(), "historia")))

    def test_velocidad_configurable_cambia_estimacion(self):
        from barriga_ia_narrativa import evaluar_guion
        guion = original()
        a = evaluar_guion(guion, 35, 150)
        b = evaluar_guion(guion, 35, 120)
        self.assertGreater(b["segundos_estimados"], a["segundos_estimados"])
        self.assertEqual(limites_de_bloques(35), {
            "gancho": (5, 8), "historia": (63, 70), "cierre": (13, 18)})
        self.assertNotEqual(limites_de_bloques(35, 120)["historia"], (63, 70))
        with self.assertRaises(ErrorNarrativa):
            evaluar_guion(guion, 35, 20)


if __name__ == "__main__":
    unittest.main()
