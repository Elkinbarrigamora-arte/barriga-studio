#!/usr/bin/env python3
"""Barriga IA: calendario local y almacén de vídeos aprobados.

No se conecta a redes sociales ni publica. Es independiente de Barriga Studio.
Los datos privados se guardan en local-data/ (ignorado por git).
"""
import argparse
import csv
from datetime import date, datetime, timedelta
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from zoneinfo import ZoneInfo

TIMEZONE = "America/Bogota"
HORARIOS = ("03:30", "17:30")
MAX_VIDEOS = 30
DEFAULT_DB = Path(__file__).resolve().parents[1] / "local-data" / "barriga-ia.sqlite3"
HASHTAG = re.compile(r"^#[\w\u00c0-\u024f]{2,40}$", re.UNICODE)


class ErrorCalendario(ValueError):
    """La operación fue rechazada sin modificar el estado."""


class CalendarioIA:
    def __init__(self, db=DEFAULT_DB):
        self.db = Path(db)
        self.db.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db)
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY,
                archivo TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                titulo TEXT NOT NULL,
                hashtags TEXT NOT NULL,
                estado TEXT NOT NULL DEFAULT 'APROBADO_MANUAL',
                creado TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS turnos (
                fecha TEXT NOT NULL,
                hora TEXT NOT NULL,
                video_id TEXT UNIQUE REFERENCES videos(id),
                PRIMARY KEY(fecha, hora)
            );
        """)
        self.conn.commit()

    def close(self):
        self.conn.close()

    def planificar(self, desde, dias=30):
        inicio = date.fromisoformat(desde) if isinstance(desde, str) else desde
        if not 1 <= dias <= 30:
            raise ErrorCalendario("El horizonte debe ser de 1 a 30 días")
        with self.conn:
            for delta in range(dias):
                fecha = (inicio + timedelta(days=delta)).isoformat()
                for hora in HORARIOS:
                    self.conn.execute(
                        "INSERT OR IGNORE INTO turnos(fecha, hora) VALUES (?, ?)",
                        (fecha, hora))
        return dias * len(HORARIOS)

    @staticmethod
    def validar_manifiesto(m):
        if not isinstance(m, dict):
            raise ErrorCalendario("Se necesita un manifiesto JSON")
        ident = m.get("id")
        titulo = m.get("titulo")
        tags = m.get("hashtags")
        if not isinstance(ident, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,70}", ident):
            raise ErrorCalendario("Identificador inválido")
        if not isinstance(titulo, str) or not 1 <= len(titulo.strip()) <= 180:
            raise ErrorCalendario("Título inválido")
        if not isinstance(tags, list) or len(tags) != 5 or any(
                not isinstance(t, str) or not HASHTAG.fullmatch(t) for t in tags):
            raise ErrorCalendario("Se requieren exactamente cinco hashtags válidos")
        if len({t.casefold() for t in tags}) != 5:
            raise ErrorCalendario("Los hashtags no deben repetirse")
        if m.get("aprobacion_manual") is not True:
            raise ErrorCalendario("Falta aprobación manual: no hay ocho filtros automáticos operativos")
        archivo = m.get("archivo")
        if not isinstance(archivo, str) or not archivo or not Path(archivo).is_file():
            raise ErrorCalendario("No existe un archivo de vídeo local")
        ruta = Path(archivo).expanduser().resolve()
        if ruta.suffix.lower() != ".mp4" or ruta.stat().st_size < 12:
            raise ErrorCalendario("Se requiere un MP4 real, no un guion o imagen")
        with ruta.open("rb") as f:
            header = f.read(12)
        if header[4:8] != b"ftyp":
            raise ErrorCalendario("La cabecera no corresponde a un contenedor MP4")
        # La cabecera MP4 no garantiza decodificación: la reproducción se revisa aparte.
        return ident, titulo.strip(), tags, ruta

    def ingresar(self, manifiesto):
        ident, titulo, tags, ruta = self.validar_manifiesto(manifiesto)
        if self.conn.execute(
                "SELECT COUNT(*) FROM videos WHERE estado != 'ARCHIVADO'"
                ).fetchone()[0] >= MAX_VIDEOS:
            raise ErrorCalendario("Almacén lleno (30). Archiva manualmente antes de añadir")
        digest_state = hashlib.sha256()
        with ruta.open("rb") as source:
            for fragmento in iter(lambda: source.read(1024 * 1024), b""):
                digest_state.update(fragmento)
        digest = digest_state.hexdigest()
        try:
            with self.conn:
                self.conn.execute("""
                    INSERT INTO videos(id, archivo, sha256, titulo, hashtags, creado)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                    (ident, str(ruta), digest, titulo,
                     json.dumps(tags, ensure_ascii=False),
                     datetime.now(ZoneInfo(TIMEZONE)).isoformat()))
        except sqlite3.IntegrityError as exc:
            raise ErrorCalendario("Ya existe un vídeo con ese identificador") from exc

    def asignar(self, ident, fecha, hora):
        if hora not in HORARIOS:
            raise ErrorCalendario("Horario no permitido")
        date.fromisoformat(fecha)
        with self.conn:
            video = self.conn.execute("SELECT estado FROM videos WHERE id=?", (ident,)).fetchone()
            if not video or video[0] != "APROBADO_MANUAL":
                raise ErrorCalendario("El vídeo no está disponible para programar")
            exists = self.conn.execute("SELECT video_id FROM turnos WHERE fecha=? AND hora=?",
                                       (fecha, hora)).fetchone()
            if exists is None or exists[0] is not None:
                raise ErrorCalendario("Turno inexistente u ocupado")
            self.conn.execute("UPDATE turnos SET video_id=? WHERE fecha=? AND hora=?",
                              (ident, fecha, hora))
            self.conn.execute("UPDATE videos SET estado='PLANIFICADO_LOCAL' WHERE id=?", (ident,))

    def archivar(self, ident):
        """Liberar capacidad solo manualmente, cuando ya no está asignado."""
        with self.conn:
            exists = self.conn.execute("SELECT 1 FROM turnos WHERE video_id=?", (ident,)).fetchone()
            if exists:
                raise ErrorCalendario("No se puede archivar un vídeo con turno asignado")
            cur = self.conn.execute(
                "UPDATE videos SET estado='ARCHIVADO' WHERE id=? AND estado='APROBADO_MANUAL'",
                (ident,))
            if cur.rowcount != 1:
                raise ErrorCalendario("Solo se pueden archivar vídeos sin programación")

    def exportar_csv(self, destino):
        """Solo genera un borrador para carga manual en las herramientas oficiales."""
        target = Path(destino)
        target.parent.mkdir(parents=True, exist_ok=True)
        rows = self.conn.execute("""
            SELECT t.fecha, t.hora, COALESCE(t.video_id, ''),
                   COALESCE(v.archivo, ''), COALESCE(v.titulo, ''),
                   COALESCE(v.hashtags, '[]')
            FROM turnos t LEFT JOIN videos v ON t.video_id=v.id
            ORDER BY t.fecha, t.hora
        """).fetchall()
        with target.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(("fecha", "hora", "zona_horaria", "id_video",
                             "archivo_local", "titulo", "hashtags", "estado"))
            for fecha, hora, ident, archivo, titulo, tags in rows:
                writer.writerow((fecha, hora, TIMEZONE, ident, archivo, titulo,
                                 " ".join(json.loads(tags)),
                                 "PENDIENTE_CARGA_EXTERNA" if ident else "SIN_VIDEO"))
        return len(rows)

    def resumen(self):
        slots = self.conn.execute("SELECT COUNT(*) FROM turnos").fetchone()[0]
        occupied = self.conn.execute(
            "SELECT COUNT(*) FROM turnos WHERE video_id IS NOT NULL").fetchone()[0]
        stored = self.conn.execute(
            "SELECT COUNT(*) FROM videos WHERE estado != 'ARCHIVADO'").fetchone()[0]
        return {"turnos": slots, "turnos_con_video": occupied, "videos_en_almacen": stored,
                "limite_almacen": MAX_VIDEOS, "zona_horaria": TIMEZONE,
                "publicacion_automatica": False, "conectores_sociales": False}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--db", type=Path, default=DEFAULT_DB)
    subs = p.add_subparsers(dest="comando", required=True)
    sub_plan = subs.add_parser("planificar")
    sub_plan.add_argument("--desde", default=(datetime.now(ZoneInfo(TIMEZONE)).date()
                                               + timedelta(days=1)).isoformat())
    sub_add = subs.add_parser("ingresar")
    sub_add.add_argument("--manifiesto", type=Path, required=True)
    sub_assign = subs.add_parser("asignar")
    sub_assign.add_argument("--id", required=True)
    sub_assign.add_argument("--fecha", required=True)
    sub_assign.add_argument("--hora", choices=HORARIOS, required=True)
    sub_export = subs.add_parser("exportar")
    sub_export.add_argument("--salida", type=Path, required=True)
    sub_archive = subs.add_parser("archivar")
    sub_archive.add_argument("--id", required=True)
    subs.add_parser("estado")
    args = p.parse_args()
    core = CalendarioIA(args.db)
    try:
        if args.comando == "planificar":
            print(json.dumps({"turnos_solicitados": core.planificar(args.desde)}))
        elif args.comando == "ingresar":
            core.ingresar(json.loads(args.manifiesto.read_text(encoding="utf-8")))
            print("Aprobación manual registrada; publicación desactivada")
        elif args.comando == "asignar":
            core.asignar(args.id, args.fecha, args.hora)
            print("Asignado localmente; falta programarlo en cada red social")
        elif args.comando == "exportar":
            print(json.dumps({"turnos_exportados": core.exportar_csv(args.salida)}))
        elif args.comando == "archivar":
            core.archivar(args.id)
            print("Vídeo archivado sin borrar el archivo original")
        else:
            print(json.dumps(core.resumen(), ensure_ascii=False, indent=2))
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        p.exit(2, "Error: " + str(exc) + "\n")
    finally:
        core.close()


if __name__ == "__main__":
    main()
