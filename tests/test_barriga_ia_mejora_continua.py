"""Regresiones de auditoría offline y elegibilidad estricta para datasets."""
import json
from pathlib import Path
import os
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from barriga_ia_mejora_continua import (
    crear_ejemplos, elegible_para_entrenamiento, exportar_jsonl,
    leer_registros, resumen_registros,
)
from barriga_ia_servicio_local import guardar_generacion


def ejemplo_aprobado():
    return {
        "idea": ("Un hombre recibe una carta escrita ayer por su hermano "
                 "desaparecido hace veinte años."),
        "guion": {
            "titulo": "La carta", "gancho": "¡La carta de su hermano fue escrita ayer!",
            "historia": ("Daniel recibió una carta de Mateo, su hermano "
                        "desaparecido hace veinte años, escrita ayer. "
                        "Siguió las pistas hasta el archivo del hospital."),
            "cierre": ("Mateo reveló la prueba: el director falsificó los registros "
                       "para mantenerlo encerrado."),
        },
        "estado": "REVISION_HUMANA_PENDIENTE",
        "apto_para_revision_humana": True,
        "aprobacion_humana": True,
        "consentimiento_entrenamiento": True,
        "duracion_objetivo": 35,
        "modelo": "modelo-local",
        "segundos_inferencia": 12.5,
        "rendimiento": {"llamadas_ollama": 2},
    }


class AuditoriaOfflineTest(unittest.TestCase):
    def test_aprobacion_y_permiso_explicitos_son_ambos_obligatorios(self):
        base = ejemplo_aprobado()
        self.assertTrue(elegible_para_entrenamiento(base))
        for attr in ("aprobacion_humana", "consentimiento_entrenamiento",
                     "apto_para_revision_humana"):
            with self.subTest(attr=attr):
                copy = dict(base)
                copy[attr] = False
                self.assertFalse(elegible_para_entrenamiento(copy))
                del copy[attr]
                self.assertFalse(elegible_para_entrenamiento(copy))
        rechazado = dict(base, estado="PREMISA_DESVIADA")
        self.assertFalse(elegible_para_entrenamiento(rechazado))
        guion_invalido = dict(base, guion=dict(base["guion"], historia="Un río mágico"))
        self.assertFalse(elegible_para_entrenamiento(guion_invalido))

    def test_sqlite_lectura_solamente_y_reporte_sin_textos_privados(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / "local-data" / "guiones.sqlite3"
            base = ejemplo_aprobado()
            guardar_generacion(base, db)
            rechazado = dict(base, estado="PREMISA_DESVIADA",
                             aprobacion_humana=False,
                             consentimiento_entrenamiento=False)
            guardar_generacion(rechazado, db)
            before = db.read_bytes()
            registros = leer_registros(db)
            report = resumen_registros(registros)
            self.assertEqual(len(registros), 2)
            self.assertEqual(report["generaciones_leidas"], 2)
            self.assertEqual(
                report["ejemplos_con_aprobacion_y_permiso_para_entrenamiento"], 1)
            self.assertEqual(report["segundos_mediana"], 12.5)
            self.assertEqual(report["llamadas_ollama_mediana"], 2)
            self.assertNotIn("Daniel recibió", json.dumps(report))
            self.assertNotIn(base["idea"], json.dumps(report, ensure_ascii=False))
            self.assertEqual(before, db.read_bytes())

    def test_exportar_solo_un_dataset_consentido_sin_sobrescribir(self):
        base = ejemplo_aprobado()
        rechazado = dict(base, consentimiento_entrenamiento=False)
        registros = [("BI-" + "a" * 20, base), ("BI-" + "b" * 20, rechazado)]
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "datos-privados.jsonl"
            self.assertEqual(exportar_jsonl(registros, destino), 1)
            records = [json.loads(line) for line in destino.read_text().splitlines()]
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["metadata"]["id_origen"], "BI-" + "a" * 20)
            self.assertEqual(len(records[0]["messages"]), 3)
            if os.name == "posix":
                self.assertEqual(destino.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                exportar_jsonl(registros, destino)

    def test_sin_datos_aptos_no_generar_archivos(self):
        with tempfile.TemporaryDirectory() as tmp:
            ruta = Path(tmp) / "dataset.jsonl"
            self.assertEqual(exportar_jsonl(
                [("BI-" + "c" * 20, dict(ejemplo_aprobado(),
                                          aprobacion_humana=False))], ruta), 0)
            self.assertFalse(ruta.exists())
            with self.assertRaises(FileNotFoundError):
                leer_registros(Path(tmp) / "inexistente.db")
            self.assertFalse((Path(tmp) / "inexistente.db").exists())

    def test_preparacion_no_modifica_pesos_ni_lanza_ollama(self):
        codigo = (ROOT / "tools" / "barriga_ia_mejora_continua.py").read_text()
        self.assertNotIn("subprocess.run(", codigo)
        self.assertNotIn("urllib.request", codigo)
        self.assertNotIn("requests.", codigo)
        self.assertIn("mode=ro", codigo)
        self.assertIn("consentimiento_entrenamiento", codigo)


if __name__ == "__main__":
    unittest.main()
