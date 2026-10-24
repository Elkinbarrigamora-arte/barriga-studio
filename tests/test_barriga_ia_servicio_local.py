"""Pruebas sin Ollama para motor local y puente HTTP privado."""
import json
from pathlib import Path
import socket
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from barriga_ia_narrativa import ErrorNarrativa
from barriga_ia_fidelidad import auditar_fidelidad
from barriga_ia_servicio_local import (
    abrir_generacion, ejecutar_motor, guardar_generacion,
    inicializar, listar_generaciones, validar_solicitud, reanudar_cierre,
)
from puente_local import servidor, presentar_generacion


def borrador():
    return {
        "titulo": "El misterio de la carta",
        "nicho": "leyendas",
        "naturaleza": "ficcion",
        "gancho": "Daniel encontró una carta escrita ayer.",
        "historia": ("La carta decía que su hermano Mateo, desaparecido "
                    "hace veinte años, seguía vivo. Daniel siguió "
                    "las pistas hasta el faro abandonado."),
        "cierre": "Allí reconoció la voz de su hermano.",
        "personajes": [{"nombre": "Daniel"}, {"nombre": "Mateo"}],
        "continuidad": {},
        "fuentes": [],
        "duracion_objetivo_segundos": 35,
    }


def resultado_mock(estado="REVISION_HUMANA_PENDIENTE"):
    return {
        "version": 1, "idea": "Una carta escrita ayer", "modelo": "modelo-local",
        "estado": estado, "segundos_inferencia": 1.2,
        "apto_para_revision_humana": estado == "REVISION_HUMANA_PENDIENTE",
        "publicacion_automatica_autorizada": False,
        "aprobacion_humana": False, "guion": borrador(),
        "informe": {"historial_bloques": []},
    }


class MotorUnificadoTest(unittest.TestCase):
    def test_valida_longitud_idea_y_duracion(self):
        for idea, duracion in [("", 35), ("abc", 35), ("normal", 5),
                               ("normal", True), ("x" * 501, 35)]:
            with self.subTest(idea=idea[:20], duracion=duracion):
                with self.assertRaises(ErrorNarrativa):
                    validar_solicitud(idea, duracion)
        validar_solicitud("Una carta aparece ayer", 35)

    def test_una_sola_ruta_usa_motor_narrativo_por_bloques(self):
        draft = borrador()
        evaluation = {"apto_para_revision_humana": True}
        with patch("barriga_ia_servicio_local.generar_local",
                   return_value=draft) as crear:
            with patch("barriga_ia_servicio_local.ensamblar_por_bloques",
                       return_value={
                           "guion": draft, "evaluacion": evaluation,
                           "estado": "REVISION_HUMANA_PENDIENTE"
                       }) as estructurar:
                salida = ejecutar_motor(
                    "Una carta escrita ayer", "modelo-local", duracion=35)
        crear.assert_called_once()
        self.assertIn('"nicho": "ficcion"', crear.call_args[0][0])
        self.assertIn("PREMISA INMUTABLE", crear.call_args[0][0])
        estructurar.assert_called_once_with(
            draft, duracion=35, modelo="modelo-local",
            premisa="Una carta escrita ayer",
            estrategia_gancho="reglas-primero", reutilizar_borrador=True)
        self.assertEqual(salida["rendimiento"]["llamadas_ollama"], 0)
        self.assertTrue(salida["apto_para_revision_humana"])
        self.assertFalse(salida["aprobacion_humana"])
        self.assertFalse(salida["publicacion_automatica_autorizada"])

    def test_rechazo_se_conserva_y_no_se_finge_aprobacion(self):
        draft = borrador()
        with patch("barriga_ia_servicio_local.generar_local", return_value=draft):
            with patch("barriga_ia_servicio_local.ensamblar_por_bloques",
                       return_value={
                           "guion": None, "evaluacion": None,
                           "estado": "BLOQUE_RECHAZADO_HISTORIA",
                       }):
                salida = ejecutar_motor("Una carta escrita ayer", "modelo-local")
        self.assertEqual(salida["estado"], "BLOQUE_RECHAZADO_HISTORIA")
        self.assertEqual(salida["guion"], draft)
        self.assertFalse(salida["guion_estructurado_completo"])
        self.assertFalse(salida["apto_para_revision_humana"])

    def test_historia_del_rio_y_coco_se_rechaza_por_desvio(self):
        idea = ("Un hombre recibe una carta escrita ayer por su hermano "
                "desaparecido hace veinte años.")
        cambiado = {
            "gancho": ("En una pequeña aldea, un hermano desapareció después "
                       "de ver un río misterioso. ¿Qué sucedió realmente?"),
            "historia": (
                "Daniel, el hermano mayor, había prometido a su hermano "
                "menor, Miguel, que nunca cruzaría el río que corría a "
                "través del bosque. Un día, Miguel ignoró la advertencia. "
                "Años después, Daniel descubre una leyenda sobre un coco "
                "en el río maldito."),
            "cierre": (
                "Al tocar el coco, Daniel ve a Miguel salir del río. "
                "El amor de sus padres había roto la maldición."),
        }
        motivos = auditar_fidelidad(idea, cambiado)
        self.assertTrue(any("ayer" in x for x in motivos))
        self.assertTrue(any("carta" in x for x in motivos))
        self.assertTrue(any("20 anos" in x for x in motivos))
        self.assertTrue(any("Gancho interrogativo" in x for x in motivos))

    def test_fidelidad_acepta_relato_que_conserva_hechos_de_premisa(self):
        idea = ("Un hombre recibe una carta escrita ayer por su hermano "
                "desaparecido hace veinte años.")
        guion = borrador()
        self.assertEqual(auditar_fidelidad(idea, guion), [])

    def test_fidelidad_acepta_20_anos_y_formas_equivalentes(self):
        idea = ("Un hombre recibe una carta escrita ayer por su hermano "
                "desaparecido hace veinte años. Al seguir las pistas, "
                "descubre una verdad inesperada.")
        relato = {
            "gancho": "¡La carta de su hermano fue escrita ayer!",
            "historia": (
                "Juan encontró la carta que Mateo, su hermano desaparecido "
                "hace 20 años, escribió ayer. Investigó el sello y recorrió "
                "la ciudad hasta descubrir la habitación donde Mateo "
                "había permanecido escondido. El hombre dejó una pista "
                "grabada en la pared antes de abrir la puerta."),
            "cierre": (
                "Mateo le mostró las pruebas y explicó que su desaparición "
                "había sido forzada para proteger a Juan."),
        }
        self.assertEqual(auditar_fidelidad(idea, relato), [])

    def test_fidelidad_no_exige_20_si_se_escribio_veinte(self):
        idea = ("Un hombre recibe una carta escrita ayer por su hermano "
                "desaparecido hace 20 años.")
        relato = {
            "gancho": "¡La carta de su hermano fue escrita ayer!",
            "historia": (
                "Juan encontró una carta escrita ayer por Mateo, "
                "su hermano desaparecido hace veinte años. "
                "Al abrirla descubrió dónde podía encontrarlo."),
            "cierre": (
                "Juan encontró a Mateo tras la puerta y ambos "
                "comprendieron cómo se había entregado la carta."),
        }
        self.assertEqual(auditar_fidelidad(idea, relato), [])

    def test_fidelidad_sigue_rechazando_duracion_y_familiar_cambiados(self):
        idea = ("Un hombre recibe una carta escrita ayer por su hermano "
                "desaparecido hace veinte años.")
        relato = {
            "gancho": "¡La carta escrita ayer ocultaba un secreto!",
            "historia": (
                "Juan abrió la carta enviada por su hermano Mateo. "
                "Su esposa Ana había desaparecido hace diez años "
                "y Juan siguió las pistas hasta un edificio abandonado."),
            "cierre": "Juan encontró a Ana esperando en la entrada.",
        }
        problemas = auditar_fidelidad(idea, relato)
        self.assertTrue(any("20 anos" in x for x in problemas), problemas)
        self.assertTrue(any("su hermano" in x for x in problemas), problemas)

    def test_regresion_intercambio_hermano_por_esposa(self):
        """La nueva carta se conserva, pero no se puede cambiar al desaparecido."""
        idea = ("Un hombre recibe una carta escrita ayer por su hermano "
                "desaparecido hace veinte años. Al seguir las pistas, "
                "descubre una verdad inesperada.")
        guion = {
            "gancho": "La carta de ayer contiene un misterio antiguo.",
            "historia": (
                "Juan, al leer la carta de su hermano Carlos escrita ayer, "
                "se da cuenta de que su esposa Ana desapareció hace veinte "
                "años. Visita el pueblo donde vivían y descubre que Carlos "
                "fue acusado y encarcelado. Con la ayuda de Pedro, investiga "
                "y encuentra pruebas de su inocencia. La verdadera culpable "
                "es María, una vieja rival. Juan logra liberar a Carlos y "
                "revelar la verdad a la comunidad."),
            "cierre": (
                "Juan revela la verdad a la comunidad, liberando a Carlos "
                "y restableciendo la paz."),
        }
        motivos = auditar_fidelidad(idea, guion)
        self.assertTrue(any("su hermano" in m for m in motivos), motivos)
        self.assertTrue(any("repite acciones" in m for m in motivos), motivos)

    def test_valida_un_hermano_desaparecido_sin_cambiar_personajes(self):
        idea = ("Un hombre recibe una carta escrita ayer por su hermano "
                "desaparecido hace veinte años.")
        historia = {
            "gancho": "La carta escrita ayer contenía la voz del pasado.",
            "historia": (
                "Daniel abrió la carta escrita ayer por su hermano Mateo, "
                "desaparecido hace veinte años. El papel tenía una "
                "fotografía de una estación abandonada. Daniel siguió "
                "esa pista y reconoció una marca que ambos dibujaban "
                "cuando eran niños."),
            "cierre": (
                "En la estación encontró a Mateo. La carta le había "
                "permitido reencontrarlo."),
        }
        self.assertEqual(auditar_fidelidad(idea, historia), [])

    def test_regresion_final_heroe_sin_resolver_carta(self):
        idea = ("Un hombre recibe una carta escrita ayer por su hermano "
                "desaparecido hace veinte años. Al seguir las pistas, "
                "descubre una verdad inesperada.")
        guion = {
            "gancho": "Juan encuentra una carta antigua de su hermano desaparecido.",
            "historia": (
                "Después de años de búsqueda, Juan recibe una carta escrita "
                "ayer por su hermano desaparecido hace veinte años. La carta "
                "lo lleva a un antiguo pueblo donde su padre trabajaba. "
                "Allí, descubre que su hermano está vivo, pero en una "
                "situación peligrosa. Juan debe actuar rápido para salvarlo "
                "de una organización criminal que lo está utilizando en "
                "una trama oscura."),
            "cierre": (
                "Juan rescata a su hermano y descubre que él era el "
                "verdadero héroe que siempre soñó ser."),
        }
        motivos = auditar_fidelidad(idea, guion)
        self.assertTrue(any("Cierre genérico" in x for x in motivos), motivos)

    def test_rechaza_conspiracion_como_revelacion_sin_detalle(self):
        idea = ("Un hombre recibe una carta escrita ayer por su hermano "
                "desaparecido hace veinte años.")
        guion = {
            "gancho": "Una carta escrita ayer desafió veinte años de silencio.",
            "historia": (
                "Juan leyó la carta de su hermano desaparecido hace veinte "
                "años. Siguió las pistas de la carta hasta el pueblo."),
            "cierre": "La familia era parte de una antigua conspiración.",
        }
        motivos = auditar_fidelidad(idea, guion)
        self.assertTrue(any("Cierre genérico" in x for x in motivos), motivos)

    def test_no_confundir_una_esposa_desaparecida_con_el_hermano(self):
        idea = ("Un hombre recibe una carta escrita ayer por su hermano "
                "desaparecido hace veinte años.")
        historia = {
            "gancho": "La carta de ayer reveló una pista estremecedora.",
            "historia": (
                "Su hermano Carlos escribió desde la prisión que "
                "su esposa Ana había desaparecido hace veinte años. "
                "La carta llevaba una fotografía de Ana."),
            "cierre": "Al abrir la foto, vio a Ana junto al juez.",
        }
        motivos = auditar_fidelidad(idea, historia)
        self.assertTrue(any("su hermano" in m for m in motivos), motivos)

    def test_reintento_de_premisa_no_llama_ensamblador_si_ambos_fallan(self):
        idea = ("Un hombre recibe una carta escrita ayer por su hermano "
                "desaparecido hace veinte años.")
        desviado = {
            "titulo": "El río maldito", "nicho": "leyendas",
            "naturaleza": "ficcion",
            "gancho": "¡El coco cambió la vida de Daniel!",
            "historia": "Daniel encontró un río encantado y quiso cruzarlo.",
            "cierre": "Al final todo fue una maldición.",
            "personajes": [], "continuidad": {}, "fuentes": [],
            "duracion_objetivo_segundos": 35,
        }
        with patch("barriga_ia_servicio_local.generar_local",
                   return_value=desviado) as crear:
            with patch("barriga_ia_servicio_local.ensamblar_por_bloques") as ensamblar:
                resultado = ejecutar_motor(idea, modelo="modelo-local")
        self.assertEqual(crear.call_count, 2)
        ensamblar.assert_not_called()
        self.assertEqual(resultado["estado"], "PREMISA_DESVIADA")
        self.assertFalse(resultado["apto_para_revision_humana"])
        self.assertEqual(len(resultado["informe"]["intentos_borrador"]), 2)

    def test_borrador_apto_no_rescata_desvio_en_ensamblaje(self):
        idea = ("Un hombre recibe una carta escrita ayer por su hermano "
                "desaparecido hace veinte años.")
        desviado = dict(borrador(), gancho="El río se tragó a Miguel.",
                        historia="Miguel entró al agua y encontró un coco.",
                        cierre="El coco devolvió a Miguel sano y salvo.")
        with patch("barriga_ia_servicio_local.generar_local",
                   return_value=borrador()):
            with patch("barriga_ia_servicio_local.ensamblar_por_bloques",
                       return_value={
                           "guion": desviado,
                           "evaluacion": {"apto_para_revision_humana": True},
                           "estado": "REVISION_HUMANA_PENDIENTE",
                       }):
                resultado = ejecutar_motor(idea, "modelo-local")
        self.assertEqual(resultado["estado"], "PREMISA_DESVIADA")
        self.assertFalse(resultado["apto_para_revision_humana"])
        self.assertTrue(resultado["motivos_fidelidad"])

    def test_rechazo_de_premisa_se_puede_guardar_y_recuperar(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "local-data" / "generaciones.sqlite3"
            data = resultado_mock("PREMISA_DESVIADA")
            data["motivos_fidelidad"] = ["Objeto omitido: carta"]
            data["apto_para_revision_humana"] = False
            ident = guardar_generacion(data, db)
            result = abrir_generacion(ident, db)
            self.assertEqual(result["estado"], "PREMISA_DESVIADA")
            self.assertFalse(result["apto_para_revision_humana"])
            self.assertTrue(result["motivos_fidelidad"])

    def test_error_cierre_exhibe_motivo_de_rechazo(self):
        resultado = resultado_mock("BLOQUE_RECHAZADO_CIERRE")
        resultado["informe"] = {"historial_bloques": [
            {"bloque": "cierre", "intento": 1,
             "motivos_rechazo": ["Extensión 29 palabras fuera de 13 a 18"]},
            {"bloque": "cierre", "intento": 2,
             "motivos_rechazo": ["Cierre genérico: sin revelación concreta"]},
        ]}
        vista = presentar_generacion(resultado, "BI-" + "0" * 20)
        self.assertEqual(vista["motivos_bloque"],
                         ["Cierre genérico: sin revelación concreta"])
        self.assertFalse(vista["apto_para_revision_humana"])

    def test_reanudar_unicamente_el_cierre_conservando_original(self):
        idea = ("Un hombre recibe una carta escrita ayer por su hermano "
                "desaparecido hace veinte años.")
        historia = (
            "Daniel siguió el rastro de la carta hasta el faro abandonado. "
            "Allí encontró una fotografía de Mateo frente a la puerta, "
            "tomada aquella misma mañana. Un pescador aseguró haber visto "
            "su antigua chaqueta cerca del muelle. Daniel revisó el sobre "
            "y descubrió una dirección escrita a mano. Al llegar al lugar, "
            "escuchó pasos detrás de una pared y reconoció la voz de su "
            "hermano desaparecido hace veinte años."
        )
        gancho = "¡Daniel encontró una carta escrita ayer!"
        cierre = (
            "Mateo estaba vivo bajo el faro y sostenía una segunda carta "
            "que Daniel jamás había enviado."
        )
        borr = dict(borrador(), gancho=gancho, historia=historia)
        def fila(bloque, texto, aprobada, intento=1):
            return {
                "bloque": bloque, "texto": texto, "intento": intento,
                "palabras": len(texto.split()),
                "longitud_valida": aprobada,
                "aceptable_para_ensamblaje": aprobada,
                "motivos_rechazo": [] if aprobada else
                    ["Extensión 20 palabras fuera de 13 a 18"],
            }
        informe = {
            "guion_original": borr,
            "historial_bloques": [
                fila("gancho", gancho, True),
                fila("historia", historia, True),
                fila("cierre", "Mateo revela algo que solo el sabia.", False),
            ]
        }
        data = resultado_mock("BLOQUE_RECHAZADO_CIERRE")
        data.update(idea=idea, duracion_objetivo=35,
                    guion=borr, informe=informe)
        with tempfile.TemporaryDirectory() as temp:
            db = inicializar(Path(temp) / "local" / "guiones.sqlite3")
            viejo = guardar_generacion(data, db)
            with patch("barriga_ia_servicio_local.generar_local") as completo:
                with patch("barriga_ia_por_bloques.generar_texto_local",
                           return_value=cierre) as bloque:
                    reparado, nuevo = reanudar_cierre(viejo, "modelo-local", db)
            completo.assert_not_called()
            bloque.assert_called_once()
            self.assertNotEqual(nuevo, viejo)
            self.assertEqual(reparado["reanudado_desde"], viejo)
            self.assertEqual(reparado["guion"]["gancho"], gancho)
            self.assertEqual(reparado["guion"]["historia"], historia)
            self.assertEqual(reparado["guion"]["cierre"], cierre)
            self.assertEqual(reparado["estado"], "REVISION_HUMANA_PENDIENTE")
            self.assertFalse(reparado["publicacion_automatica_autorizada"])
            self.assertEqual(
                abrir_generacion(viejo, db)["estado"],
                "BLOQUE_RECHAZADO_CIERRE")
            self.assertEqual(abrir_generacion(nuevo, db)["guion"]["cierre"],
                             cierre)

    def test_reanudar_no_acepta_registros_sin_bloques_aprobados(self):
        data = resultado_mock("BLOQUE_RECHAZADO_CIERRE")
        data["informe"] = {"guion_original": borrador(),
                           "historial_bloques": []}
        with tempfile.TemporaryDirectory() as temp:
            db = inicializar(Path(temp) / "local" / "guiones.sqlite3")
            viejo = guardar_generacion(data, db)
            with patch("barriga_ia_servicio_local.ensamblar_por_bloques") as g:
                with self.assertRaisesRegex(ErrorNarrativa,
                                            "no son recuperables"):
                    reanudar_cierre(viejo, "modelo-local", db)
            g.assert_not_called()
            self.assertEqual(len(listar_generaciones(db)), 1)

    def test_persistencia_real_y_lectura_con_diferentes_conexiones(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "local-data" / "generaciones.sqlite3"
            inicializar(db)
            a = guardar_generacion(resultado_mock(), db)
            b = guardar_generacion(resultado_mock("BLOQUE_RECHAZADO_CIERRE"), db)
            self.assertNotEqual(a, b)
            listado = listar_generaciones(db)
            self.assertEqual(len(listado), 2)
            self.assertEqual(abrir_generacion(a, db)["guion"], borrador())
            self.assertEqual(
                abrir_generacion(b, db)["estado"], "BLOQUE_RECHAZADO_CIERRE")
            self.assertIsNone(abrir_generacion("BI-../../.env", db))
            self.assertIsNone(abrir_generacion("BI-" + "0"*20, db))


class PuenteHTTPTest(unittest.TestCase):
    def setUp(self):
        from http.server import ThreadingHTTPServer
        self.tmp = tempfile.TemporaryDirectory()
        self.studio = Path(self.tmp.name)
        (self.studio / "index.html").write_text(
            "<html><body>Studio</body></html>", encoding="utf-8")
        self.db = self.studio / "local-data" / "local.sqlite3"
        inicializar(self.db)
        guardar_generacion(resultado_mock(), self.db)
        # Reservar un puerto al construir la ruta de origin esperada.
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.server = ThreadingHTTPServer(
            ("127.0.0.1", self.port),
            servidor(self.studio, "clave-prueba", self.port,
                     "modelo-local", self.db))
        self.thread = threading.Thread(target=self.server.serve_forever,
                                       daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()
        self.tmp.cleanup()

    def pedir(self, route, method="GET", data=None, token=None, origin=None):
        headers = {}
        if token:
            headers["X-Barriga-Token"] = token
        if origin:
            headers["Origin"] = origin
        if data is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(data).encode("utf-8")
        req = Request("http://127.0.0.1:{}{}".format(self.port, route),
                      data=data, headers=headers, method=method)
        try:
            with urlopen(req, timeout=5) as resp:
                return resp.status, resp.read().decode("utf-8")
        except HTTPError as exc:
            return exc.code, exc.read().decode("utf-8")

    def test_get_index_incluye_panel_sin_modificar_archivo(self):
        status, pagina = self.pedir("/")
        self.assertEqual(status, 200)
        self.assertIn("Generar y validar guion", pagina)
        # Hay un único editor: la idea viene de Guion y no de otro textarea.
        self.assertNotIn("ideaInput", pagina)
        self.assertNotIn("Idea original (se conserva sin cambios)", pagina)
        self.assertIn("const texto=field.value.trim()", pagina)
        self.assertIn("field.dataset.ideaOriginal", pagina)
        self.assertIn("const idea=(generado&&texto===generado)?", pagina)
        self.assertIn("Restaurar idea original", pagina)
        self.assertIn("clave-prueba", pagina)
        self.assertEqual((self.studio / "index.html").read_text(),
                         "<html><body>Studio</body></html>")

    def test_historial_privado_por_token(self):
        status, _ = self.pedir("/api/historial")
        self.assertEqual(status, 403)
        status, body = self.pedir("/api/historial", token="clave-prueba")
        self.assertEqual(status, 200)
        items = json.loads(body)["generaciones"]
        self.assertEqual(len(items), 1)
        ident = items[0]["id"]
        status, body = self.pedir("/api/guion/" + ident, token="clave-prueba")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["guion"]["titulo"],
                         "El misterio de la carta")
        status, _ = self.pedir("/api/guion/" + ident, token="otro")
        self.assertEqual(status, 403)

    def test_historial_puede_mostrar_motivo_de_premisa_desviada(self):
        data = resultado_mock("PREMISA_DESVIADA")
        data["motivos_fidelidad"] = ["Pista temporal omitida: ayer"]
        data["apto_para_revision_humana"] = False
        ident = guardar_generacion(data, self.db)
        status, body = self.pedir("/api/guion/" + ident, token="clave-prueba")
        self.assertEqual(status, 200)
        recibido = json.loads(body)
        self.assertEqual(recibido["estado"], "PREMISA_DESVIADA")
        self.assertEqual(recibido["motivos_fidelidad"],
                         ["Pista temporal omitida: ayer"])
        self.assertFalse(recibido["apto_para_revision_humana"])

    def test_post_rechaza_peticion_sin_origen_y_clave(self):
        status, _ = self.pedir("/api/guion", "POST",
                               {"idea": "Una carta misteriosa"})
        self.assertEqual(status, 403)
        status, _ = self.pedir("/api/guion", "POST",
                               {"idea": "Una carta misteriosa"},
                               token="clave-prueba",
                               origin="https://sitio-no-autorizado.example")
        self.assertEqual(status, 403)

    def test_post_valida_tipo_y_no_llama_ollama(self):
        with patch("puente_local.ejecutar_motor") as generar:
            status, _ = self.pedir(
                "/api/guion", "POST", ["no es un objeto"],
                token="clave-prueba",
                origin="http://127.0.0.1:{}".format(self.port))
        self.assertEqual(status, 400)
        generar.assert_not_called()

    def test_post_guarda_y_nunca_autopublica(self):
        with patch("puente_local.ejecutar_motor",
                   return_value=resultado_mock()) as generar:
            status, body = self.pedir(
                "/api/guion", "POST", {"idea": "Una carta misteriosa"},
                token="clave-prueba",
                origin="http://127.0.0.1:{}".format(self.port))
        self.assertEqual(status, 200)
        salida = json.loads(body)
        self.assertFalse(salida["publicacion_automatica_autorizada"])
        self.assertFalse(salida["aprobacion_humana"])
        self.assertEqual(
            abrir_generacion(salida["id"], self.db)["estado"],
            "REVISION_HUMANA_PENDIENTE")
        generar.assert_called_once()

    def test_no_permite_dos_generaciones_simultaneas(self):
        primera_inicio = threading.Event()
        primera_fin = threading.Event()
        resultados = []
        origin = "http://127.0.0.1:{}".format(self.port)

        def lenta(idea, modelo):
            primera_inicio.set()
            primera_fin.wait(timeout=3)
            return resultado_mock()

        def primera():
            resultados.append(self.pedir(
                "/api/guion", "POST", {"idea": "Una carta misteriosa"},
                token="clave-prueba", origin=origin))
        with patch("puente_local.ejecutar_motor", side_effect=lenta):
            hilo = threading.Thread(target=primera)
            hilo.start()
            try:
                self.assertTrue(primera_inicio.wait(timeout=2))
                estado, cuerpo = self.pedir(
                    "/api/guion", "POST", {"idea": "Otra historia diferente"},
                    token="clave-prueba", origin=origin)
                self.assertEqual(estado, 429)
                self.assertIn("otro guion", cuerpo)
            finally:
                primera_fin.set()
                hilo.join(timeout=4)
        self.assertEqual(resultados[0][0], 200)

    def test_post_reparar_cierre_es_privado_y_no_publica(self):
        identificador = "BI-" + "a" * 20
        endpoint = "/api/guion/reparar-cierre"
        origen = "http://127.0.0.1:{}".format(self.port)
        estado, _ = self.pedir(endpoint, "POST", {"id": identificador})
        self.assertEqual(estado, 403)
        estado, _ = self.pedir(
            endpoint, "POST", {"id": "invalido"},
            token="clave-prueba", origin=origen)
        self.assertEqual(estado, 400)
        reparado = resultado_mock()
        reparado["reanudado_desde"] = identificador
        with patch("puente_local.reanudar_cierre",
                   return_value=(reparado, "BI-" + "b" * 20)) as reanudar:
            estado, body = self.pedir(
                endpoint, "POST", {"id": identificador},
                token="clave-prueba", origin=origen)
        self.assertEqual(estado, 200)
        salida = json.loads(body)
        self.assertEqual(salida["reanudado_desde"], identificador)
        self.assertFalse(salida["publicacion_automatica_autorizada"])
        reanudar.assert_called_once_with(identificador, "modelo-local", self.db)

    def test_get_ruta_desconocida_y_header_antiframe(self):
        status, _ = self.pedir("/api/desconocido")
        self.assertEqual(status, 404)
        req = Request("http://127.0.0.1:{}/".format(self.port))
        with urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.headers["X-Frame-Options"], "DENY")


if __name__ == "__main__":
    unittest.main()
