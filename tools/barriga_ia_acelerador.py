#!/usr/bin/env python3
"""Telemetría ligera por solicitud para Ollama local, sin guardar prompts."""
from contextlib import contextmanager
from contextvars import ContextVar
import time

_ACTUAL = ContextVar("barriga_ia_metricas_ollama", default=None)


@contextmanager
def medir_solicitud():
    llamadas = []
    token = _ACTUAL.set(llamadas)
    try:
        yield llamadas
    finally:
        _ACTUAL.reset(token)


def iniciar_llamada(modelo, fase):
    llamadas = _ACTUAL.get()
    if llamadas is None:
        return None
    entrada = {
        "modelo": str(modelo), "fase": fase,
        "inicio": time.monotonic(),
        "segundos": None, "tokens_generados": None,
        "tokens_entrada": None, "segundos_evaluacion": None,
        "estado": "en_proceso",
    }
    llamadas.append(entrada)
    return entrada


def finalizar_llamada(entrada, respuesta=None, error=False):
    if entrada is None:
        return
    entrada["segundos"] = round(time.monotonic() - entrada.pop("inicio"), 3)
    entrada["estado"] = "error" if error else "completada"
    if not isinstance(respuesta, dict):
        return
    for clave, destino in (
        ("eval_count", "tokens_generados"),
        ("prompt_eval_count", "tokens_entrada"),
    ):
        valor = respuesta.get(clave)
        if type(valor) is int and valor >= 0:
            entrada[destino] = valor
    nanos = respuesta.get("eval_duration")
    if type(nanos) is int and nanos > 0:
        entrada["segundos_evaluacion"] = round(nanos / 1e9, 3)


def resumen(llamadas):
    cantidad_tokens = sum(
        e["tokens_generados"] for e in llamadas
        if type(e.get("tokens_generados")) is int
    )
    segundos_eval = sum(
        e["segundos_evaluacion"] for e in llamadas
        if type(e.get("segundos_evaluacion")) in (float, int)
    )
    return {
        "llamadas_ollama": len(llamadas),
        "errores_ollama": sum(e.get("estado") == "error" for e in llamadas),
        "tokens_generados": cantidad_tokens,
        "tokens_por_segundo": (
            round(cantidad_tokens / segundos_eval, 2)
            if segundos_eval > 0 else None
        ),
        "segundos_ollama": round(sum(
            e.get("segundos") or 0 for e in llamadas
        ), 3),
        "detalle": [
            {k: v for k, v in e.items() if k != "inicio"}
            for e in llamadas
        ],
    }
