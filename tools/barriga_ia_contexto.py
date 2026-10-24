#!/usr/bin/env python3
"""Contrato editorial y audiovisual independiente del motor de video.

La continuidad se activa únicamente por una orden explícita. Un plan de escenas
NO significa que exista un video, una voz o una imagen generados.
"""
import json
import re

from barriga_ia_narrativa import ErrorNarrativa


def normalizar_contexto(contexto=None):
    """Normaliza un encargo sin heredar series de generaciones anteriores."""
    if contexto is None:
        contexto = {}
    if not isinstance(contexto, dict):
        raise ErrorNarrativa("El contexto editorial debe ser un objeto JSON")
    modo = contexto.get("modo", "independiente")
    if modo not in ("independiente", "serie"):
        raise ErrorNarrativa("El modo debe ser independiente o serie")
    serie_id = contexto.get("serie_id")
    biblia = contexto.get("biblia")
    if modo == "independiente":
        if serie_id is not None or biblia is not None:
            raise ErrorNarrativa("Un Reel independiente no puede heredar una serie")
        serie_id, biblia = None, None
    else:
        if (not isinstance(serie_id, str) or not
                re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", serie_id)):
            raise ErrorNarrativa("La serie necesita un identificador válido")
        if not isinstance(biblia, dict) or not biblia:
            raise ErrorNarrativa("La serie necesita su biblia de continuidad")
        if len(json.dumps(biblia, ensure_ascii=False)) > 6000:
            raise ErrorNarrativa("La biblia de serie es demasiado extensa")
    video = contexto.get("video", {})
    if not isinstance(video, dict):
        raise ErrorNarrativa("Los parámetros de video deben ser un objeto")
    formato = video.get("formato", "9:16")
    if formato not in ("9:16", "16:9"):
        raise ErrorNarrativa("Formato de video no admitido")
    estilo = video.get("estilo_visual", "cinematográfico")
    voz = video.get("voz", "por definir")
    for campo, valor in (("estilo visual", estilo), ("voz", voz)):
        if not isinstance(valor, str) or not 1 <= len(valor.strip()) <= 120:
            raise ErrorNarrativa("Parámetro inválido: " + campo)
    return {
        "modo": modo,
        "serie_id": serie_id,
        "biblia": biblia,
        "video": {"formato": formato, "estilo_visual": estilo.strip(),
                  "voz": voz.strip()},
    }


def instrucciones_editoriales(contexto):
    if contexto["modo"] == "independiente":
        continuidad = (
            "MODO REEL INDEPENDIENTE: no continúes historias ni arrastres "
            "personajes, rasgos o acontecimientos de otras generaciones. "
            "Solo la premisa actual decide personajes y hechos.")
    else:
        continuidad = (
            "MODO SERIE EXPLÍCITO: conserva únicamente la siguiente biblia "
            "de continuidad de esta serie, sin incorporar datos de otras: "
            + json.dumps({"serie_id": contexto["serie_id"],
                          "biblia": contexto["biblia"]},
                         ensure_ascii=False, sort_keys=True))
    return (
        "\nDIRECCIÓN EDITORIAL: eres guionista de Reels y microdocumentales. "
        "Gancho concreto, desarrollo causal y cierre resolutivo; oferta "
        "comercial solo si el usuario la pidió o es pertinente. "
        "Distingue dramatización de información factual. "
        + continuidad + "\nDIRECCIÓN AUDIOVISUAL: el guion alimentará un "
        "plan de escenas para Barriga Studio. Mantén identidad de personajes, "
        "apariencia, ambiente y voz solo dentro de este proyecto; no prometas "
        "que el video ya fue producido."
    )


def crear_plan_video(guion, duracion, contexto):
    """Prepara tres segmentos para un futuro adaptador de video, sin renderizar."""
    if not isinstance(guion, dict):
        return None
    if type(duracion) is not int or not 20 <= duracion <= 60:
        raise ErrorNarrativa("Duración de video inválida")
    gancho_fin = min(3, duracion)
    cierre_inicio = duracion - max(4, round(duracion * .18))
    bloques = (("gancho", 0, gancho_fin),
               ("historia", gancho_fin, cierre_inicio),
               ("cierre", cierre_inicio, duracion))
    escenas = []
    for nombre, inicio, fin in bloques:
        escenas.append({
            "bloque": nombre, "inicio_segundos": inicio,
            "fin_segundos": fin,
            "narracion": str(guion.get(nombre, "")),
            "guia_visual": "Pendiente de desglose visual y revisión editorial",
        })
    return {
        "version": 1,
        "estado": "PLAN_PENDIENTE_DE_REVISION",
        "video_generado": False,
        "voz_generada": False,
        "modo": contexto["modo"],
        "serie_id": contexto["serie_id"],
        "biblia_serie": contexto["biblia"] if contexto["modo"] == "serie" else None,
        "formato": contexto["video"]["formato"],
        "estilo_visual": contexto["video"]["estilo_visual"],
        "voz": contexto["video"]["voz"],
        "duracion_objetivo_segundos": duracion,
        "escenas": escenas,
    }
