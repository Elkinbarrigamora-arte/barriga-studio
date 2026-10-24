"""Pruebas sin red ni servicios de publicación para Barriga IA."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from barriga_ia_calendario import CalendarioIA, ErrorCalendario, HORARIOS, MAX_VIDEOS


class CalendarioIATest(unittest.TestCase):
    def setUp(self):
        self.work = tempfile.TemporaryDirectory()
        self.root = Path(self.work.name)
        self.ia = CalendarioIA(self.root / "estado.sqlite3")
        # Contenedor MP4 sintético mínimo: solo útil para prueba de admisión,
        # no representa un archivo multimedia realmente decodificable.
        self.clip = self.root / "clip.mp4"
        self.clip.write_bytes(b"\x00\x00\x00\x18ftypisom0000")

    def tearDown(self):
        self.ia.close()
        self.work.cleanup()

    def manifiesto(self, n):
        return {
            "id": f"clip_{n}",
            "archivo": str(self.clip),
            "titulo": f"Historia original {n}",
            "hashtags": ["#Relatos", "#Historias", "#Ciencia", "#Vida", "#Naturaleza"],
            "aprobacion_manual": True,
        }

    def test_sesenta_turnos_exactos_y_repeticion_idempotente(self):
        self.assertEqual(self.ia.planificar("2026-10-24"), 60)
        self.assertEqual(self.ia.planificar("2026-10-24"), 60)
        self.assertEqual(self.ia.resumen()["turnos"], 60)
        rows = self.ia.conn.execute(
            "SELECT fecha, hora FROM turnos ORDER BY fecha, hora").fetchall()
        self.assertEqual(rows[0], ("2026-10-24", "03:30"))
        self.assertEqual(rows[1], ("2026-10-24", "17:30"))
        self.assertEqual(rows[-1], ("2026-11-22", "17:30"))

    def test_ingreso_solo_ante_aprobacion_explicita(self):
        m = self.manifiesto(1)
        m["aprobacion_manual"] = False
        with self.assertRaises(ErrorCalendario):
            self.ia.ingresar(m)
        m["aprobacion_manual"] = True
        self.ia.ingresar(m)
        self.assertEqual(self.ia.resumen()["videos_en_almacen"], 1)

    def test_rechaza_hashtags_duplicados(self):
        m = self.manifiesto(1)
        m["hashtags"] = ["#reels", "#Reels", "#cine", "#Arte", "#Mundo"]
        with self.assertRaises(ErrorCalendario):
            self.ia.ingresar(m)

    def test_limite_treinta_y_no_elimina_archivos(self):
        for i in range(MAX_VIDEOS):
            self.ia.ingresar(self.manifiesto(i))
        with self.assertRaises(ErrorCalendario):
            self.ia.ingresar(self.manifiesto(30))
        self.assertTrue(self.clip.exists())
        self.ia.archivar("clip_0")
        self.ia.ingresar(self.manifiesto(30))
        self.assertEqual(self.ia.resumen()["videos_en_almacen"], MAX_VIDEOS)

    def test_no_asigna_dos_veces_mismo_video(self):
        self.ia.planificar("2026-10-24")
        self.ia.ingresar(self.manifiesto(1))
        self.ia.asignar("clip_1", "2026-10-24", "03:30")
        with self.assertRaises(ErrorCalendario):
            self.ia.asignar("clip_1", "2026-10-24", "17:30")
        with self.assertRaises(ErrorCalendario):
            self.ia.archivar("clip_1")

    def test_exportacion_sin_envio_a_redes(self):
        self.ia.planificar("2026-10-24")
        path = self.root / "plan.csv"
        self.assertEqual(self.ia.exportar_csv(path), 60)
        rows = path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(rows), 61)
        self.assertIn("SIN_VIDEO", path.read_text(encoding="utf-8"))
        self.ia.ingresar(self.manifiesto(1))
        self.ia.asignar("clip_1", "2026-10-24", "17:30")
        self.ia.exportar_csv(path)
        self.assertIn("PENDIENTE_CARGA_EXTERNA", path.read_text(encoding="utf-8"))
        self.assertFalse(self.ia.resumen()["publicacion_automatica"])
        self.assertFalse(self.ia.resumen()["conectores_sociales"])


if __name__ == "__main__":
    unittest.main()
