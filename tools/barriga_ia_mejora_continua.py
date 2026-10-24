#!/usr/bin/env python3
"""Evaluación local de Barriga IA y preparación CONSENTIDA de ejemplos.

Este módulo no usa Ollama, no entrena pesos, no publica datos y no instala
tareas persistentes. Python 3.9+. Lee el SQLite existente en modo SOLO LECTURA.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sqlite3
import statistics
import sys

from barriga_ia_fidelidad import auditar_fidelidad

DEFAULT_DB = Path(__file__).resolve().parents[1] / "local-data" / "guiones-locales.sqlite3"
INSTRUCCION = (
    "Escribe un microguion original en español conservando los hechos "
    "obligatorios de la premisa. Devuelve JSON con gancho, historia y cierre. "
    "Mantén consistencia temporal, causalidad y un desenlace concreto."
)


def leer_registros(db, limite=1000):
    """Consultar datos existentes sin crear tablas ni modificar archivos."""
    if type(limite) is not int or not 1 <= limite <= 10000:
        raise ValueError("El límite de lectura debe estar entre 1 y 10000")
    db = Path(db).expanduser().resolve()
    if not db.is_file():
        raise FileNotFoundError("Base de datos de Barriga IA no encontrada: " + str(db))
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True, timeout=8) as con:
        rows = con.execute(
            "SELECT id, datos FROM generaciones ORDER BY fecha DESC,id DESC LIMIT ?",
            (limite,)
        ).fetchall()
    records = []
    for ident, raw in rows:
        try:
            item = json.loads(raw)
            if isinstance(item, dict):
                records.append((ident, item))
        except (ValueError, TypeError):
            # El reporte nunca modifica registros dañados.
            continue
    return records


def elegible_para_entrenamiento(item):
    """Solo ejemplos positivos aprobados expresamente por humanos.

    La revisión del motor no equivale a aprobación humana, y la aprobación
    no equivale al consentimiento para reutilizar contenido en entrenamiento.
    """
    if not isinstance(item, dict):
        return False
    if item.get("aprobacion_humana") is not True:
        return False
    if item.get("consentimiento_entrenamiento") is not True:
        return False
    if item.get("apto_para_revision_humana") is not True:
        return False
    if item.get("estado") != "REVISION_HUMANA_PENDIENTE":
        return False
    idea, guion = item.get("idea"), item.get("guion")
    if not isinstance(idea, str) or not 5 <= len(idea.strip()) <= 500:
        return False
    if not isinstance(guion, dict):
        return False
    if any(not isinstance(guion.get(k), str) or not guion[k].strip()
           for k in ("gancho", "historia", "cierre")):
        return False
    if auditar_fidelidad(idea, guion):
        return False
    return True


def resumen_registros(registros):
    estados = Counter(str(item.get("estado", "SIN_ESTADO")) for _, item in registros)
    duraciones = Counter(str(item.get("duracion_objetivo", "NO_REGISTRADA"))
                         for _, item in registros)
    latencias = [
        item["segundos_inferencia"] for _, item in registros
        if type(item.get("segundos_inferencia")) in (int, float)
        and item["segundos_inferencia"] >= 0
    ]
    llamadas = [
        item.get("rendimiento", {}).get("llamadas_ollama")
        for _, item in registros if isinstance(item.get("rendimiento"), dict)
    ]
    llamadas = [v for v in llamadas if type(v) is int and v >= 0]
    fidelidad = {"sin_guion_valorable": 0, "con_rechazos_heuristicos": 0,
                 "sin_rechazos_heuristicos": 0}
    for _, item in registros:
        idea, guion = item.get("idea"), item.get("guion")
        if not isinstance(idea, str) or not isinstance(guion, dict):
            fidelidad["sin_guion_valorable"] += 1
            continue
        motivos = auditar_fidelidad(idea, guion)
        if motivos:
            fidelidad["con_rechazos_heuristicos"] += 1
        else:
            fidelidad["sin_rechazos_heuristicos"] += 1
    return {
        "metodo": "auditoria_offline_sqlite_sin_inferencia",
        "generaciones_leidas": len(registros),
        "estados": dict(sorted(estados.items())),
        "duracion_solicitada": dict(sorted(duraciones.items())),
        "segundos_mediana": round(statistics.median(latencias), 2) if latencias else None,
        "latencias_disponibles": len(latencias),
        "llamadas_ollama_mediana": statistics.median(llamadas) if llamadas else None,
        "telemetria_llamadas_disponible": len(llamadas),
        "fidelidad_heuristica": fidelidad,
        "ejemplos_con_aprobacion_y_permiso_para_entrenamiento": sum(
            elegible_para_entrenamiento(item) for _, item in registros),
        "advertencia": (
            "Una validacion heuristica no demuestra calidad semantica; "
            "estos valores NO son una evaluacion con Ollama ni entrenamiento."
        ),
    }


def crear_ejemplos(registros):
    for ident, item in registros:
        if not elegible_para_entrenamiento(item):
            continue
        guion = item["guion"]
        duracion = item.get("duracion_objetivo", 35)
        if type(duracion) is not int or not 20 <= duracion <= 60:
            continue
        salida = {k: guion[k].strip() for k in ("gancho", "historia", "cierre")}
        yield {
            "messages": [
                {"role": "system", "content": INSTRUCCION},
                {"role": "user", "content": item["idea"].strip() +
                 "\nDuración objetivo: {} segundos.".format(duracion)},
                {"role": "assistant", "content": json.dumps(
                    salida, ensure_ascii=False)},
            ],
            "metadata": {"id_origen": ident, "duracion_objetivo": duracion,
                         "modelo_original": item.get("modelo", "no_registrado")},
        }


def exportar_jsonl(registros, destino):
    """Crear archivo nuevo 0600; jamás sobreescribir un dataset existente."""
    destino = Path(destino).expanduser().resolve()
    if destino.suffix.lower() != ".jsonl":
        raise ValueError("El dataset de salida debe usar extensión .jsonl")
    ejemplos = list(crear_ejemplos(registros))
    if not ejemplos:
        return 0
    # Evitar guardar datos privados accidentalmente en una carpeta versionada.
    raiz = Path(__file__).resolve().parents[1]
    carpeta_local = raiz / "local-data"
    if raiz in destino.parents and carpeta_local not in destino.parents:
        raise ValueError("Guarda datasets privados fuera del repositorio "
                         "o dentro de local-data (carpeta excluida de Git)")
    destino.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(str(destino), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            for ejemplo in ejemplos:
                handle.write(json.dumps(ejemplo, ensure_ascii=False) + "\n")
    except Exception:
        try:
            destino.unlink()
        except OSError:
            pass
        raise
    return len(ejemplos)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB,
                        help="SQLite existente; siempre lectura solamente")
    parser.add_argument("--limite", type=int, default=1000)
    parser.add_argument("--exportar-jsonl", type=Path, default=None,
                        help="Opcional: solo registros con aprobación y permiso explícitos")
    args = parser.parse_args(argv)
    registros = leer_registros(args.db, args.limite)
    resultado = resumen_registros(registros)
    if args.exportar_jsonl is not None:
        resultado["ejemplos_exportados"] = exportar_jsonl(
            registros, args.exportar_jsonl)
        resultado["ruta_dataset"] = (
            str(args.exportar_jsonl) if resultado["ejemplos_exportados"] else None)
    print(json.dumps(resultado, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (FileNotFoundError, sqlite3.Error, ValueError, OSError) as exc:
        print("No se pudo completar la auditoría local: " + str(exc),
              file=sys.stderr)
        sys.exit(1)
