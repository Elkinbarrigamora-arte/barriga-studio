"""Pruebas del motor Narrativa Inteligente: sin redes, sin pagos y sin publicar."""
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from barriga_ia_narrativa import (ErrorNarrativa, NICHOS, evaluar_guion,
                                  generar_local, preparar_solicitud, normalizar_formato,
                                  contar_palabras, revisar_borrador_local,
                                  preparar_revision, main)


GANCHO = "¡La última carta de su hermano apareció treinta años después del naufragio!"
HISTORIA = (
    "Daniel halló una caja oxidada junto al muelle. "
    "Dentro estaba la letra de Mateo, desaparecido aquella noche. "
    "La carta decía: «No fue una tormenta». "
    "Daniel recorrió el pueblo hasta encontrar a la antigua guardiana del faro. "
    "Ella le mostró una fotografía de los dos hermanos y señaló una fecha imposible: ayer. "
    "En ese instante, la luz del faro volvió a encenderse."
)
CIERRE = (
    "Daniel subió corriendo. Detrás de la puerta esperaba Mateo, envejecido y vivo. "
    "El secreto apenas comenzaba."
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
        self.assertIn('"objetivo": 88', prompt)
        self.assertIn('"maximo": 97', prompt)

    def test_evaluacion_ficcion_no_publica(self):
        resultado = evaluar_guion(ejemplo())
        self.assertGreaterEqual(resultado["puntuacion_heuristica"], 65)
        self.assertTrue(resultado["apto_para_revision_humana"])
        self.assertFalse(resultado["publicacion_automatica_autorizada"])
        self.assertFalse(resultado["verificacion_externa_realizada"])
        self.assertIn("gancho", resultado["desglose"])
        self.assertEqual(resultado["estado_revision"], "REVISION_HUMANA_PENDIENTE")

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

    def test_regresion_35_segundos_con_175_palabras_no_es_apto(self):
        # Reproduce el fallo editorial visto con Ollama en la Mac.
        guion = ejemplo()
        guion["historia"] += " Investigó durante días sin encontrar respuestas." * 18
        reporte = evaluar_guion(guion, 35)
        self.assertGreater(reporte["segundos_estimados"], 42)
        self.assertFalse(reporte["apto_para_revision_humana"])
        self.assertEqual(reporte["estado_revision"], "DEVOLVER_PARA_CORRECCION")
        self.assertTrue(any("Duración incompatible" in x for x in reporte["bloqueos"]))
        self.assertFalse(reporte["publicacion_automatica_autorizada"])

    def test_regresion_segunda_prueba_103_palabras_41_segundos(self):
        # Simula la longitud de la segunda generación REAL sin exponer el relato.
        guion = ejemplo()
        while sum(contar_palabras(guion[k]) for k in ("gancho", "historia", "cierre")) < 103:
            guion["historia"] += " secreto"
        rep = evaluar_guion(guion, 35)
        self.assertEqual(rep["palabras"], 103)
        self.assertEqual(rep["segundos_estimados"], 41.2)
        self.assertFalse(rep["apto_para_revision_humana"])
        self.assertEqual(rep["estado_revision"], "DEVOLVER_PARA_CORRECCION")
        self.assertTrue(any("Duración incompatible" in x for x in rep["bloqueos"]))

    def test_alertas_por_ortografia_y_cierre_de_relleno(self):
        guion = ejemplo()
        guion["historia"] += " El forgero volvió al muelle."
        guion["cierre"] = "Daniel llamó a sus conocidos, resuelven el caso y todos quedaron felices."
        guion["continuidad"] = {}
        reporte = evaluar_guion(guion, 35)
        self.assertTrue(any("forgero" in x for x in reporte["advertencias"]))
        self.assertTrue(any("genérico" in x for x in reporte["advertencias"]))
        self.assertTrue(any("ficha de continuidad" in x for x in reporte["advertencias"]))

    def test_continuidad_sospechosa_generar_advertencias(self):
        guion = ejemplo()
        guion["continuidad"]["escenario"] = "Puerto"
        guion["personajes"].append({
            "nombre": "Tío Juan",
            "descripcion": "hermano menor de Daniel desaparecido"
        })
        reporte = evaluar_guion(guion, 35)
        self.assertTrue(any("Escenario" in x for x in reporte["advertencias"]))
        self.assertTrue(any("parentesco" in x for x in reporte["advertencias"]))

    def test_script_guardado_con_guion_anidado_se_puede_releer(self):
        # Contrato de normalización después de extraer el campo guion del informe.
        datos = {"guion": ejemplo(), "evaluacion": {"puntuacion_heuristica": 20}}
        narracion, ajustes = normalizar_formato(datos["guion"])
        self.assertFalse(ajustes)
        self.assertTrue(evaluar_guion(narracion)["apto_para_revision_humana"])

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

    def test_regresion_personajes_devuelto_como_objeto(self):
        # Error real de la Mac: Ollama entregó personajes distinto de lista.
        guion = ejemplo()
        guion["personajes"] = {"Daniel": {"rol": "protagonista"},
                               "Mateo": "hermano"}
        reparado, cambios = normalizar_formato(guion)
        self.assertEqual([p["nombre"] for p in reparado["personajes"]],
                         ["Daniel", "Mateo"])
        self.assertTrue(cambios)
        self.assertTrue(evaluar_guion(reparado)["apto_para_revision_humana"])

    def test_reparacion_conservadora_de_texto_y_continuidad(self):
        guion = ejemplo()
        guion["personajes"] = "Daniel y su hermano Mateo"
        guion["continuidad"] = "El faro y el mismo vestuario"
        guion["fuentes"] = ""
        reparado, cambios = normalizar_formato(guion)
        self.assertEqual(reparado["personajes"],
                         [{"descripcion": "Daniel y su hermano Mateo"}])
        self.assertEqual(reparado["continuidad"],
                         {"notas": "El faro y el mismo vestuario"})
        self.assertEqual(reparado["fuentes"], [])
        self.assertGreaterEqual(len(cambios), 2)
        self.assertFalse(evaluar_guion(reparado)["publicacion_automatica_autorizada"])

    def test_lista_de_nombres_y_duracion_numerica(self):
        guion = ejemplo()
        guion["personajes"] = ["Daniel", "Mateo"]
        guion["duracion_objetivo_segundos"] = "35"
        reparado, ajustes = normalizar_formato(guion)
        self.assertEqual(reparado["personajes"], [{"nombre": "Daniel"}, {"nombre": "Mateo"}])
        self.assertEqual(reparado["duracion_objetivo_segundos"], 35)
        self.assertTrue(ajustes)

    def test_esquema_json_solicita_array_personajes(self):
        salida = {"response": json.dumps(ejemplo(), ensure_ascii=False)}
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self):
                return json.dumps(salida).encode("utf-8")
        def simular(request, timeout):
            datos = json.loads(request.data)
            self.assertEqual(datos["format"]["properties"]["personajes"]["type"], "array")
            self.assertEqual(datos["format"]["properties"]["continuidad"]["type"], "object")
            self.assertEqual(datos["format"]["properties"]["fuentes"]["type"], "array")
            return FakeResponse()
        with patch("barriga_ia_narrativa.urlopen", side_effect=simular):
            self.assertEqual(generar_local("prueba")["titulo"], "La carta bajo el faro")

    def test_generar_local_corrige_personajes_antes_de_evaluar(self):
        guion = ejemplo()
        guion["personajes"] = {"nombre": "Daniel"}
        salida = {"response": json.dumps(guion, ensure_ascii=False)}
        class FakeResponse:
            def __enter__(self):
                return self
            def __exit__(self, *_):
                return False
            def read(self):
                return json.dumps(salida).encode("utf-8")
        with patch("barriga_ia_narrativa.urlopen", return_value=FakeResponse()):
            producido = generar_local("prueba")
            self.assertEqual(producido["personajes"], [{"nombre": "Daniel"}])
            self.assertTrue(evaluar_guion(producido)["apto_para_revision_humana"])

    def test_revisiones_corrigen_longitud_sin_truncar_palabras(self):
        largo = ejemplo()
        largo["historia"] += " Otra descripción innecesaria del puerto." * 20
        self.assertGreater(evaluar_guion(largo)["segundos_estimados"], 39.2)
        corto = ejemplo()
        llamadas = []
        def corregir(prompt, **kwargs):
            llamadas.append((prompt, kwargs))
            return corto, []
        with patch("barriga_ia_narrativa.generar_local", side_effect=corregir):
            salida = revisar_borrador_local(largo, duracion=35)
        self.assertEqual(salida["intentos_realizados"], 2)
        self.assertTrue(salida["evaluacion"]["apto_para_revision_humana"])
        self.assertFalse(salida["publicacion_automatica_autorizada"])
        self.assertEqual(salida["historial_intentos"][0]["guion"], largo)
        self.assertEqual(salida["historial_intentos"][-1]["guion"], corto)
        self.assertIn("intervalo_obligatorio_palabras", llamadas[0][0])
        self.assertEqual(llamadas[0][1]["temperatura"], 0.25)

    def test_dos_revisiones_maximas_aunque_ollama_siga_fallando(self):
        largo = ejemplo()
        largo["historia"] += " No hubo una revelación concreta." * 20
        with patch("barriga_ia_narrativa.generar_local",
                   return_value=(largo, [])) as model:
            salida = revisar_borrador_local(largo, max_revisiones=2)
        self.assertEqual(salida["intentos_realizados"], 3)
        self.assertEqual(model.call_count, 2)
        self.assertFalse(salida["evaluacion"]["apto_para_revision_humana"])
        self.assertEqual(salida["evaluacion"]["estado_revision"],
                         "DEVOLVER_PARA_CORRECCION")
        self.assertIn("agotó", salida["incidencia_reescritura"])

    def test_una_respuesta_de_nicho_diferente_no_se_adopta(self):
        largo = ejemplo()
        largo["historia"] += " No hubo una revelación concreta." * 20
        desviado = ejemplo("noticias", "factual", ["https://example.com"])
        with patch("barriga_ia_narrativa.generar_local",
                   return_value=(desviado, [])) as model:
            salida = revisar_borrador_local(largo)
        self.assertEqual(model.call_count, 1)
        self.assertEqual(salida["guion"]["nicho"], "leyendas")
        self.assertEqual(salida["intentos_realizados"], 1)
        self.assertIn("cambió", salida["incidencia_reescritura"])

    def test_no_reescribe_noticias_sin_revision_de_fuentes(self):
        largo = ejemplo("noticias", "factual", ["https://example.com"])
        largo["historia"] += " Información sin contexto temporal." * 20
        with patch("barriga_ia_narrativa.generar_local") as model:
            salida = revisar_borrador_local(largo)
        model.assert_not_called()
        self.assertEqual(salida["intentos_realizados"], 1)
        self.assertFalse(salida["evaluacion"]["apto_para_revision_humana"])
        self.assertIn("hechos reales", salida["incidencia_reescritura"])

    def test_revisar_archivo_guarda_nuevo_sin_borrar_tercera_prueba(self):
        largo = ejemplo()
        largo["historia"] += " Otra descripción innecesaria del puerto." * 20
        with tempfile.TemporaryDirectory() as temp:
            anterior = Path(temp) / "tercera-prueba.json"
            posterior = Path(temp) / "cuarta-prueba.json"
            original = json.dumps({"guion": largo}, ensure_ascii=False)
            anterior.write_text(original, encoding="utf-8")
            with patch("sys.argv", ["narrativa.py", "--revisar-archivo",
                                    str(anterior), "--salida", str(posterior)]):
                with patch("barriga_ia_narrativa.generar_local",
                           return_value=(ejemplo(), [])):
                    with patch("sys.stdout", new_callable=io.StringIO):
                        resultado = main()
            self.assertEqual(resultado, 0)
            self.assertEqual(anterior.read_text(encoding="utf-8"), original)
            self.assertTrue(posterior.exists())
            saved = json.loads(posterior.read_text(encoding="utf-8"))
            self.assertEqual(saved["intentos_realizados"], 2)
            self.assertTrue(saved["evaluacion"]["apto_para_revision_humana"])

    def test_resumen_compacto_y_archivo_completo(self):
        largo = ejemplo()
        largo["historia"] += " Otra descripción innecesaria del puerto." * 20
        with tempfile.TemporaryDirectory() as temp:
            anterior = Path(temp) / "tercera-prueba.json"
            posterior = Path(temp) / "cuarta-prueba.json"
            anterior.write_text(json.dumps({"guion": largo}), encoding="utf-8")
            with patch("sys.argv", ["narrativa.py", "--revisar-archivo",
                                    str(anterior), "--resumen", "--salida",
                                    str(posterior)]):
                with patch("barriga_ia_narrativa.generar_local",
                           return_value=(ejemplo(), [])):
                    with patch("sys.stdout", new_callable=io.StringIO) as salida:
                        codigo = main()
            self.assertEqual(codigo, 0)
            corto = json.loads(salida.getvalue())
            self.assertEqual(corto["intentos"], 2)
            self.assertEqual(corto["estado"], "REVISION_HUMANA_PENDIENTE")
            self.assertFalse(corto["publicacion_automatica_autorizada"])
            self.assertNotIn("historial_intentos", corto)
            completo = json.loads(posterior.read_text(encoding="utf-8"))
            self.assertEqual(len(completo["historial_intentos"]), 2)

    def test_rechazar_sobrescribir_fuente_antes_de_llamar_ollama(self):
        with tempfile.TemporaryDirectory() as temp:
            anterior = Path(temp) / "tercera-prueba.json"
            original = json.dumps({"guion": ejemplo()}, ensure_ascii=False)
            anterior.write_text(original, encoding="utf-8")
            with patch("sys.argv", ["narrativa.py", "--revisar-archivo",
                                    str(anterior), "--salida", str(anterior)]):
                with patch("barriga_ia_narrativa.generar_local") as model:
                    with patch("sys.stderr", new_callable=io.StringIO):
                        codigo = main()
            self.assertEqual(codigo, 2)
            model.assert_not_called()
            self.assertEqual(anterior.read_text(encoding="utf-8"), original)

    def test_revision_con_error_local_guarda_mejor_ultimo_borrador(self):
        largo = ejemplo()
        largo["historia"] += " Otra descripción innecesaria del puerto." * 20
        with patch("barriga_ia_narrativa.generar_local",
                   side_effect=ErrorNarrativa("Ollama no responde")) as model:
            salida = revisar_borrador_local(largo)
        self.assertEqual(model.call_count, 1)
        self.assertEqual(salida["guion"], largo)
        self.assertIn("Ollama no responde", salida["incidencia_reescritura"])

    def test_limite_revisiones_se_valida(self):
        with self.assertRaises(ErrorNarrativa):
            revisar_borrador_local(ejemplo(), max_revisiones=99)

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
