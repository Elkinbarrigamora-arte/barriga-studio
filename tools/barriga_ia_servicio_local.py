#!/usr/bin/env python3
"""Servicio narrativo local: un solo motor, persistencia y revisión humana.

No publica, no genera voz/video, no sincroniza dispositivos, no abre puertos.
Su consumidor HTTP debe ejecutarse exclusivamente en 127.0.0.1.
"""
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import sqlite3
import time

from barriga_ia_narrativa import (
    ErrorNarrativa, generar_local, preparar_solicitud,
)
from barriga_ia_por_bloques import ensamblar_por_bloques
from barriga_ia_fidelidad import auditar_fidelidad

DEFAULT_DB = Path(__file__).resolve().parents[1] / "local-data" / "guiones-locales.sqlite3"


def validar_solicitud(idea, duracion):
    if not isinstance(idea, str) or not 5 <= len(idea.strip()) <= 500:
        raise ErrorNarrativa("La idea debe contener entre 5 y 500 caracteres")
    if type(duracion) is not int or not 20 <= duracion <= 60:
        raise ErrorNarrativa("La duración debe estar entre 20 y 60 segundos")


def ejecutar_motor(idea, modelo, duracion=35):
    """Generar, medir fidelidad, ensamblar y exigir revisión humana.

    Si se cambia la premisa, no ensambla ni marca el guion como apto.
    Máximo dos intentos de borrador; los fallos también quedan persistibles.
    """
    validar_solicitud(idea, duracion)
    inicio = time.monotonic()
    idea = idea.strip()
    prompt = preparar_solicitud(idea, "leyendas", "ficcion", duracion=duracion)
    prompt += (
        "\nPREMISA INMUTABLE DEL AUTOR: " + json.dumps(idea, ensure_ascii=False)
        + "\nEl conflicto, objeto central, personajes definidos y pistas "
          "temporales de esa premisa son OBLIGATORIOS. "
          "No sustituyas cartas por ríos, objetos mágicos ni conflictos "
          "nuevos. Evita preguntas al espectador. "
          "Devuelve JSON válido y respeta la duración."
    )
    intentos_borrador = []
    borrador = None
    razones = []
    for numero in (1, 2):
        propuesta = generar_local(
            prompt if numero == 1 else (
                prompt + "\nREINTENTO POR DESVIACION DE PREMISA. "
                "La anterior salida fue RECHAZADA por: "
                + "; ".join(razones)
                + ". Reescribe desde la premisa original y cambia "
                  "completamente la trama incorrecta."
            ),
            modelo=modelo,
            temperatura=0.25 if numero == 1 else 0.4
        )
        borrador = propuesta
        razones = auditar_fidelidad(idea, propuesta)
        intentos_borrador.append({
            "intento": numero,
            "motivos_fidelidad": razones,
            "borrador": propuesta,
            "fidelidad_estructural_aprobada": not razones,
        })
        if not razones:
            break
    if razones:
        return {
            "version": 2,
            "idea": idea,
            "modelo": modelo,
            "duracion_objetivo": duracion,
            "estado": "PREMISA_DESVIADA",
            "motivos_fidelidad": razones,
            "apto_para_revision_humana": False,
            "aprobacion_humana": False,
            "publicacion_automatica_autorizada": False,
            "guion": borrador,
            "guion_estructurado_completo": False,
            "evaluacion": None,
            "informe": {"estado": "PREMISA_DESVIADA",
                        "intentos_borrador": intentos_borrador},
            "segundos_inferencia": round(time.monotonic() - inicio, 1),
        }

    informe = ensamblar_por_bloques(
        borrador, duracion=duracion, modelo=modelo, premisa=idea)
    completo = informe.get("guion")
    if not isinstance(completo, dict):
        completo = borrador
    motivos_finales = auditar_fidelidad(idea, completo)
    eval_final = informe.get("evaluacion")
    estado = ("PREMISA_DESVIADA" if motivos_finales
              else informe.get("estado", "INCOMPLETO"))
    aceptable = bool(
        not motivos_finales and eval_final
        and eval_final.get("apto_para_revision_humana")
        and estado == "REVISION_HUMANA_PENDIENTE"
    )
    return {
        "version": 2,
        "idea": idea,
        "modelo": modelo,
        "duracion_objetivo": duracion,
        "estado": estado,
        "motivos_fidelidad": motivos_finales,
        "apto_para_revision_humana": aceptable,
        "aprobacion_humana": False,
        "publicacion_automatica_autorizada": False,
        "guion": completo,
        "guion_estructurado_completo": isinstance(informe.get("guion"), dict),
        "evaluacion": eval_final,
        "informe": dict(informe, intentos_borrador=intentos_borrador),
        "segundos_inferencia": round(time.monotonic() - inicio, 1),
    }


def inicializar(db=DEFAULT_DB):
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "posix":
        try:
            db.parent.chmod(0o700) if db.parent.name == "local-data" else None
        except OSError:
            pass
    with closing(sqlite3.connect(str(db), timeout=15)) as con:
        con.execute("""CREATE TABLE IF NOT EXISTS generaciones (
            id TEXT PRIMARY KEY,
            fecha TEXT NOT NULL,
            estado TEXT NOT NULL,
            titulo TEXT NOT NULL,
            datos TEXT NOT NULL
        )""")
        con.commit()
    if os.name == "posix":
        try:
            db.chmod(0o600)
        except OSError:
            pass
    return db


def guardar_generacion(resultado, db=DEFAULT_DB):
    db = inicializar(db)
    ident = "BI-" + secrets.token_hex(10)
    fecha = datetime.now(timezone.utc).isoformat()
    guion = resultado.get("guion") or {}
    titulo = guion.get("titulo", "Guion sin título")
    if not isinstance(titulo, str):
        titulo = "Guion sin título"
    with closing(sqlite3.connect(str(db), timeout=15)) as con:
        con.execute(
            "INSERT INTO generaciones (id,fecha,estado,titulo,datos) VALUES (?,?,?,?,?)",
            (ident, fecha, str(resultado.get("estado", "INCOMPLETO")),
             titulo[:200], json.dumps(resultado, ensure_ascii=False))
        )
        con.commit()
    return ident


def listar_generaciones(db=DEFAULT_DB, limite=25):
    db = inicializar(db)
    if type(limite) is not int or not 1 <= limite <= 100:
        raise ValueError("Límite de historial inválido")
    with closing(sqlite3.connect(str(db), timeout=15)) as con:
        rows = con.execute(
            "SELECT id,fecha,estado,titulo FROM generaciones "
            "ORDER BY fecha DESC,id DESC LIMIT ?", (limite,)
        ).fetchall()
    return [dict(zip(("id", "fecha", "estado", "titulo"), row))
            for row in rows]


def abrir_generacion(ident, db=DEFAULT_DB):
    if (not isinstance(ident, str) or not ident.startswith("BI-")
            or len(ident) != 23 or any(c not in "0123456789abcdef"
                                       for c in ident[3:])):
        return None
    db = inicializar(db)
    with closing(sqlite3.connect(str(db), timeout=15)) as con:
        row = con.execute(
            "SELECT datos FROM generaciones WHERE id=?", (ident,)
        ).fetchone()
    return json.loads(row[0]) if row else None
