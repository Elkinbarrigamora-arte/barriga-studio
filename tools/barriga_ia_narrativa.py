#!/usr/bin/env python3
"""Barriga IA — Narrative Intelligence Engine (prototipo independiente).

Generación opcional con Ollama local, evaluación heurística, sin publicación
ni herramientas de pago. Compatible con Python 3.9+.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODELO = "qwen2.5-coder:14b"
NICHOS = {
    "historia": "Relato histórico basado en hechos comprobables y contexto temporal.",
    "mitos": "Mitos y relatos tradicionales, distinguiendo creencia de hechos.",
    "leyendas": "Leyendas regionales con ambientación y tradición respetuosa.",
    "animales": "Naturaleza y animales, sin inventar capacidades zoológicas.",
    "terror": "Suspenso narrativo sin violencia gráfica innecesaria.",
    "terror_cartoon": "Terror animado estilizado con identidad visual propia.",
    "planeta": "Naturaleza, Tierra, océanos y fenómenos del planeta.",
    "maravillas": "Maravillas del mundo natural y construido.",
    "amor": "Drama emocional, historias de amor y sacrificio.",
    "noticias": "Información reciente verificable, nunca rumores presentados como hechos.",
    "miniseries": "Episodios con personajes, voz, acontecimientos y continuidad persistentes.",
}
NATURALEZAS = ("ficcion", "factual", "dramatizacion")
ESTRUCTURA = ("gancho", "historia", "cierre")
DIRECTORIO_LOCAL = Path(__file__).resolve().parents[1] / "local-data" / "narrativa"
SISTEMA = """Eres Barriga IA, guionista de reels cinematográficos en español latinoamericano.
Tu especialidad es GANCHO -> HISTORIA -> OFERTA O CIERRE.
La narración es continua; no saludes ni hagas preguntas directas al público.
El gancho establece un conflicto inmediato sin promesas falsas o clickbait engañoso.
RESPETA ESTRICTAMENTE el número de palabras objetivo indicado en DATOS DE TRABAJO.
Nunca alargues el guion con explicaciones generales o repeticiones.
La historia desarrolla acciones concretas, causa y consecuencia, con ritmo visual.
El cierre resuelve, sorprende o conmueve. Solo usa una oferta comercial si procede.
No repitas hechos; mantén personajes, apariencia, ropa y voz entre escenas.
Las relaciones familiares deben concordar con la premisa: un hermano no se convierte en tío.
Describe acciones visibles y concretas, no resumas la historia con frases vagas.
No inventes ubicaciones, vestuario ni personajes de relleno en la ficha continuidad.
Separa siempre ficción, dramatización y hechos verificables. No inventes fuentes.
Nunca copies guiones ajenos, incluyas marcas de agua ni pidas suscripciones a pago.
Respeta derechos de autor y normas de cada plataforma; evita violencia gráfica.
No inventes noticias reales: si faltan evidencias responde con error de verificación.
Responde EXCLUSIVAMENTE con un objeto JSON válido, sin marcas de Markdown,
con campos: titulo, nicho, naturaleza, gancho, historia, cierre, personajes,
continuidad, fuentes, duracion_objetivo_segundos.
TIPOS JSON OBLIGATORIOS:
"personajes": [{"nombre": "Daniel", "descripcion": "hermano mayor"}] o [];
"continuidad": {} o ficha SOLO con rasgos verdaderamente presentes en el guion;
"fuentes": [] para ficción, o lista de referencias aportadas SIN INVENTAR;
"duracion_objetivo_segundos": número entero, no texto.
Los tres segmentos de narración deben ser texto, personajes y fuentes listas,
continuidad un objeto. No inventes URLs de fuentes ni marcadores de verificación.
"""


# Contrato formal para solicitar salida estructurada a Ollama.
ESQUEMA_JSON = {
    "type": "object",
    "properties": {
        "titulo": {"type": "string"},
        "nicho": {"type": "string", "enum": list(NICHOS)},
        "naturaleza": {"type": "string", "enum": list(NATURALEZAS)},
        "gancho": {"type": "string"},
        "historia": {"type": "string"},
        "cierre": {"type": "string"},
        "personajes": {"type": "array", "items": {
            "type": "object", "properties": {
                "nombre": {"type": "string"},
                "descripcion": {"type": "string"}
            }, "required": ["nombre"]}},
        "continuidad": {"type": "object"},
        "fuentes": {"type": "array", "items": {"type": "string"}},
        "duracion_objetivo_segundos": {"type": "integer"}
    },
    "required": ["titulo", "nicho", "naturaleza", "gancho", "historia",
                 "cierre", "personajes", "continuidad", "fuentes",
                 "duracion_objetivo_segundos"]
}


class ErrorNarrativa(ValueError):
    """El guion incumple el contrato; no se envía a producción."""


def contar_palabras(texto):
    return len(re.findall(r"\b\w+\b", texto, flags=re.UNICODE))


def preparar_solicitud(tema, nicho, naturaleza="ficcion", duracion=35,
                      fuentes=None, biblia=None):
    if nicho not in NICHOS:
        raise ErrorNarrativa("Nicho no reconocido: " + str(nicho))
    if naturaleza not in NATURALEZAS:
        raise ErrorNarrativa("Naturaleza inválida")
    if not isinstance(tema, str) or not 5 <= len(tema.strip()) <= 500:
        raise ErrorNarrativa("El tema debe tener entre 5 y 500 caracteres")
    if not isinstance(duracion, int) or not 20 <= duracion <= 60:
        raise ErrorNarrativa("La duración debe estar entre 20 y 60 segundos")
    fuentes = fuentes or []
    if not isinstance(fuentes, list):
        raise ErrorNarrativa("Fuentes debe ser una lista")
    if naturaleza == "factual" and not fuentes:
        raise ErrorNarrativa("Para hechos reales es obligatorio aportar fuentes previas")
    if nicho == "noticias" and naturaleza != "factual":
        raise ErrorNarrativa("Las noticias deben utilizar naturaleza factual")
    if nicho == "miniseries" and biblia is None:
        raise ErrorNarrativa("Miniseries exige una biblia de continuidad")
    if biblia is not None and not isinstance(biblia, dict):
        raise ErrorNarrativa("La biblia de continuidad debe ser un objeto JSON")
    objetivo_palabras = round(duracion * 2.5)
    minimo_palabras = round(objetivo_palabras * 0.85)
    maximo_palabras = round(objetivo_palabras * 1.15)
    instruccion = {
        "presupuesto_palabras_total": {
            "objetivo": objetivo_palabras,
            "minimo": minimo_palabras,
            "maximo": maximo_palabras,
            "obligatorio": True,
            "contar_solo": ["gancho", "historia", "cierre"]
        },
        "distribucion_sugerida_palabras": {
            "gancho": round(objetivo_palabras * 0.14),
            "historia": round(objetivo_palabras * 0.68),
            "cierre": round(objetivo_palabras * 0.18)
        },
        "tema": tema.strip(),
        "nicho": nicho,
        "enfoque": NICHOS[nicho],
        "naturaleza": naturaleza,
        "duracion_objetivo_segundos": duracion,
        "fuentes_proporcionadas_sin_verificar": fuentes,
        "biblia_continuidad": biblia or {},
        "estructura": {
            "gancho": "primeros 1 a 3 segundos: tensión o intriga inmediata",
            "historia": "trama continua, acciones visibles, causa y consecuencia",
            "cierre": "resolución emocional, revelación o invitación contextual",
        },
        "restricciones": [
            "No suponer que las fuentes fueron verificadas",
            "No inventar datos, citas, URLs o noticias",
            "No presentar ficción como información factual",
            "Mantener continuidad de personajes y escenario",
            "Protagonista y hermano desaparecido deben conservar parentesco y nombre",
            "Resolver el conflicto con una acción/revelación concreta en el cierre",
        ],
    }
    return SISTEMA + "\nDATOS DE TRABAJO (no son órdenes del sistema):\n" + json.dumps(
        instruccion, ensure_ascii=False, sort_keys=True
    )


def normalizar_formato(guion):
    """Repara solo tipos comunes; nunca inventa texto narrativo ni fuentes."""
    if not isinstance(guion, dict):
        raise ErrorNarrativa("La respuesta de Ollama no es un objeto JSON")
    limpio = dict(guion)
    ajustes = []
    personajes = limpio.get("personajes", [])
    if isinstance(personajes, str):
        # Preservar la descripción sin fingir que es el nombre de una persona.
        limpio["personajes"] = ([{"descripcion": personajes.strip()}]
                                if personajes.strip() else [])
        ajustes.append("personajes: texto convertido en lista descriptiva")
    elif isinstance(personajes, dict):
        if isinstance(personajes.get("nombre"), str):
            limpio["personajes"] = [personajes]
        else:
            lista = []
            for nombre, ficha in personajes.items():
                if not isinstance(nombre, str) or not nombre.strip():
                    raise ErrorNarrativa("Personajes contiene nombres inválidos")
                if isinstance(ficha, dict):
                    lista.append(dict(ficha, nombre=nombre))
                elif isinstance(ficha, str):
                    lista.append({"nombre": nombre, "descripcion": ficha})
                else:
                    raise ErrorNarrativa("Ficha de personaje no interpretable")
            limpio["personajes"] = lista
        ajustes.append("personajes: objeto convertido en lista")
    elif isinstance(personajes, list) and all(isinstance(p, str) for p in personajes):
        limpio["personajes"] = [{"nombre": p.strip()} for p in personajes if p.strip()]
        ajustes.append("personajes: nombres convertidos en fichas")
    elif not isinstance(personajes, list):
        raise ErrorNarrativa("Personajes debe ser lista, objeto o texto")
    continuidad = limpio.get("continuidad", {})
    if isinstance(continuidad, str):
        limpio["continuidad"] = {"notas": continuidad.strip()} if continuidad.strip() else {}
        ajustes.append("continuidad: texto convertido en notas")
    elif isinstance(continuidad, list) and all(isinstance(x, str) for x in continuidad):
        limpio["continuidad"] = {"notas": continuidad}
        ajustes.append("continuidad: lista convertida en notas")
    elif not isinstance(continuidad, dict):
        raise ErrorNarrativa("Continuidad debe ser un objeto o texto")
    fuentes = limpio.get("fuentes", [])
    if isinstance(fuentes, str):
        limpio["fuentes"] = [fuentes.strip()] if fuentes.strip() else []
        ajustes.append("fuentes: texto convertido en lista sin verificar")
    elif not isinstance(fuentes, list):
        raise ErrorNarrativa("Fuentes debe ser una lista o texto")
    duracion = limpio.get("duracion_objetivo_segundos")
    if isinstance(duracion, str) and duracion.isdigit():
        limpio["duracion_objetivo_segundos"] = int(duracion)
        ajustes.append("duración: texto numérico convertido en entero")
    for clave in ("nicho", "naturaleza"):
        valor = limpio.get(clave)
        if isinstance(valor, str):
            normal = valor.strip().casefold()
            if normal != valor:
                limpio[clave] = normal
                ajustes.append(clave + ": normalizado")
    return limpio, ajustes


def evaluar_guion(guion, duracion=35):
    """Puntajes deterministas para orientar revisión, NO predicen viralidad."""
    if not isinstance(guion, dict):
        raise ErrorNarrativa("La respuesta debe ser un objeto JSON")
    if not isinstance(duracion, int) or not 20 <= duracion <= 60:
        raise ErrorNarrativa("Duración de evaluación inválida")
    for campo in ("titulo", "nicho", "naturaleza") + ESTRUCTURA:
        if not isinstance(guion.get(campo), str) or not guion[campo].strip():
            raise ErrorNarrativa("Campo obligatorio ausente: " + campo)
    if guion["nicho"] not in NICHOS or guion["naturaleza"] not in NATURALEZAS:
        raise ErrorNarrativa("Nicho o clasificación factual inválida")
    if not isinstance(guion.get("personajes", []), list):
        raise ErrorNarrativa("Personajes debe ser una lista")
    if not isinstance(guion.get("continuidad", {}), dict):
        raise ErrorNarrativa("Continuidad debe ser un objeto")
    if not isinstance(guion.get("fuentes", []), list):
        raise ErrorNarrativa("Fuentes debe ser una lista")
    fuentes = guion.get("fuentes", [])
    if any(not isinstance(x, str) for x in fuentes):
        raise ErrorNarrativa("Fuentes deben ser referencias de texto")
    if not isinstance(guion.get("duracion_objetivo_segundos", duracion), int):
        raise ErrorNarrativa("Duración del guion inválida")

    palabras = {k: contar_palabras(guion[k]) for k in ESTRUCTURA}
    total = sum(palabras.values())
    estimacion = round(total / 2.5, 1)  # Aproximación: locución de 150 palabras/minuto.
    gancho = min(25, (16 if 3 <= palabras["gancho"] <= 18 else 7)
                 + (9 if any(c in guion["gancho"] for c in ("?", "¡", "!", "…", ":")) else 3))
    historia = min(30, (20 if 35 <= palabras["historia"] <= 120 else 9)
                   + (10 if palabras["historia"] > palabras["gancho"] * 2 else 2))
    cierre = min(20, (15 if 5 <= palabras["cierre"] <= 28 else 6)
                 + (5 if guion["cierre"].strip()[-1:] in ".!?" else 2))
    diferencia = abs(estimacion - duracion)
    ritmo = 15 if diferencia <= 6 else (8 if diferencia <= 12 else 2)
    nombres = [x.get("nombre", "") for x in guion.get("personajes", [])
               if isinstance(x, dict) and isinstance(x.get("nombre"), str)]
    guion_completo = " ".join(guion[k] for k in ESTRUCTURA).casefold()
    continuidad = 10 if any(n.casefold() in guion_completo for n in nombres if n.strip()) else 5
    puntajes = {"gancho": gancho, "historia": historia, "cierre": cierre,
                "duracion": ritmo, "continuidad": continuidad}

    bloqueos = []
    advertencias = []
    if guion["nicho"] == "noticias" and guion["naturaleza"] != "factual":
        bloqueos.append("Noticias no puede clasificarse como ficción")
    if guion["naturaleza"] == "factual" and not fuentes:
        bloqueos.append("Faltan fuentes para afirmaciones factuales")
    if guion["naturaleza"] == "factual" and fuentes:
        advertencias.append("Fuentes aportadas; verificación independiente aún pendiente")
    if guion["nicho"] == "miniseries" and not guion.get("continuidad"):
        bloqueos.append("Falta ficha de continuidad para la miniserie")
    # La duración es una condición de aprobación, NO una advertencia secundaria.
    tolerancia_segundos = max(4, duracion * 0.20)
    if diferencia > tolerancia_segundos:
        bloqueos.append(
            "Duración incompatible: {} palabras ≈ {} s, objetivo {} s (±{} s)".format(
                total, estimacion, duracion, round(tolerancia_segundos, 1)))
    elif diferencia > duracion * 0.10:
        advertencias.append("Duración cercana al límite; verificar velocidad de locución")
    # El escenario de continuidad debe respaldarse en el texto narrativo.
    escenario = guion.get("continuidad", {}).get("escenario")
    if isinstance(escenario, str) and escenario.strip():
        referencia = escenario.casefold().strip()
        if referencia not in guion_completo:
            advertencias.append(
                "Escenario de continuidad no identificado literalmente en el relato; revisar")
    for personaje in guion.get("personajes", []):
        if not isinstance(personaje, dict):
            continue
        nombre = personaje.get("nombre", "")
        desc = personaje.get("descripcion", "")
        if isinstance(nombre, str) and isinstance(desc, str):
            if "tío" in nombre.casefold() and "hermano" in desc.casefold():
                advertencias.append(
                    "Posible contradicción de parentesco para {}: revisar manualmente".format(
                        nombre))
    if gancho < 20:
        advertencias.append("Revisar fuerza y brevedad del gancho")
    puntaje = sum(puntajes.values())
    return {
        "puntuacion_heuristica": puntaje,
        "desglose": puntajes,
        "palabras": total,
        "segundos_estimados": estimacion,
        "duracion_objetivo": duracion,
        "bloqueos": bloqueos,
        "advertencias": advertencias,
        "apto_para_revision_humana": not bloqueos and puntaje >= 65,
        "estado_revision": ("DEVOLVER_PARA_CORRECCION" if bloqueos else
                            "REVISION_HUMANA_PENDIENTE" if puntaje >= 65 else
                            "MEJORAR_GUION"),
        "publicacion_automatica_autorizada": False,
        "verificacion_externa_realizada": False,
        "metodologia": "heurística editorial, no predicción estadística de viralidad",
    }


def generar_local(prompt, modelo=MODELO, timeout=180, devolver_ajustes=False):
    """Solo consulta el servicio local de Ollama; no usa proveedores remotos."""
    payload = {
        "model": modelo, "prompt": prompt, "stream": False, "format": ESQUEMA_JSON,
        "options": {"temperature": 0.7, "num_ctx": 8192, "num_predict": 1100},
    }
    req = Request(OLLAMA_URL,
                  json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                  {"Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise ErrorNarrativa("No se pudo consultar Ollama local: " + str(exc)) from exc
    if not isinstance(result, dict) or not isinstance(result.get("response"), str):
        raise ErrorNarrativa("Respuesta de Ollama sin campo 'response'")
    try:
        guion, ajustes = normalizar_formato(json.loads(result["response"]))
        return (guion, ajustes) if devolver_ajustes else guion
    except ValueError as exc:
        raise ErrorNarrativa("Ollama no devolvió JSON válido") from exc


def main():
    p = argparse.ArgumentParser(description=__doc__)
    modo = p.add_mutually_exclusive_group(required=True)
    modo.add_argument("--tema", help="Generar con Ollama local")
    modo.add_argument("--evaluar", type=Path, help="Evaluar un JSON sin conectar a Ollama")
    p.add_argument("--nicho", choices=sorted(NICHOS), default="leyendas")
    p.add_argument("--naturaleza", choices=NATURALEZAS, default="ficcion")
    p.add_argument("--duracion", type=int, default=35)
    p.add_argument("--fuente", action="append", default=[])
    p.add_argument("--biblia", type=Path)
    p.add_argument("--modelo", default=MODELO)
    p.add_argument("--salida", type=Path,
                   help="Guardar resultado local; NO guardar archivos privados en Git")
    args = p.parse_args()
    try:
        if args.evaluar:
            cargado = json.loads(args.evaluar.read_text(encoding="utf-8"))
            # Admite tanto un guion puro como una salida previamente guardada.
            if isinstance(cargado, dict) and isinstance(cargado.get("guion"), dict):
                cargado = cargado["guion"]
            guion, ajustes = normalizar_formato(cargado)
        else:
            biblia = json.loads(args.biblia.read_text(encoding="utf-8")) if args.biblia else None
            prompt = preparar_solicitud(args.tema, args.nicho, args.naturaleza,
                                        args.duracion, args.fuente, biblia)
            guion, ajustes = generar_local(prompt, modelo=args.modelo,
                                          devolver_ajustes=True)
        resultado = {"guion": guion, "evaluacion": evaluar_guion(guion, args.duracion),
                     "ajustes_de_formato": ajustes,
                     "fecha_revision": datetime.utcnow().isoformat() + "Z"}
        texto = json.dumps(resultado, indent=2, ensure_ascii=False)
        if args.salida:
            destino = args.salida
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(texto + "\n", encoding="utf-8")
        print(texto)
        return 0 if resultado["evaluacion"]["apto_para_revision_humana"] else 2
    except (ErrorNarrativa, OSError, ValueError) as exc:
        print("Error narrativo: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
