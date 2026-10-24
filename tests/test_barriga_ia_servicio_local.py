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
from barriga_ia_servicio_local import (
    abrir_generacion, ejecutar_motor, guardar_generacion,
    inicializar, listar_generaciones, validar_solicitud,
)
from puente_local import servidor


def borrador():
    return {
        "titulo": "El misterio de la carta",
        "nicho": "leyendas",
        "naturaleza": "ficcion",
        "gancho": "Daniel encontró una carta escrita ayer.",
        "historia": "Daniel siguió las pistas hasta el faro abandonado.",
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
        estructurar.assert_called_once_with(
            draft, duracion=35, modelo="modelo-local")
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

    def test_get_ruta_desconocida_y_header_antiframe(self):
        status, _ = self.pedir("/api/desconocido")
        self.assertEqual(status, 404)
        req = Request("http://127.0.0.1:{}/".format(self.port))
        with urlopen(req, timeout=5) as resp:
            self.assertEqual(resp.headers["X-Frame-Options"], "DENY")


if __name__ == "__main__":
    unittest.main()
