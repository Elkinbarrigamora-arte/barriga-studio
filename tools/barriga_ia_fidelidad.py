#!/usr/bin/env python3
"""Auditoría conservadora de fidelidad de guiones a la premisa del usuario.

Solo detecta desvíos observables de palabras, anclajes y tiempo.
NO sustituye la revisión humana de causalidad o coherencia semántica.
"""
import math
import re
import unicodedata

VACIAS = {
    "un", "una", "uno", "unos", "unas", "el", "la", "lo", "los", "las",
    "en", "al", "del", "de", "y", "o", "su", "sus", "por", "para",
    "que", "con", "como", "se", "le", "les", "a", "ante", "es", "era",
    "fue", "esta", "este", "estos", "estas", "sobre", "desde", "hasta",
    "hace", "sin", "entre", "tiene", "tenia", "despues", "antes", "pero",
    "cada", "todo", "todos", "todas", "cuando", "habia", "habian",
}
# Anclajes físicos que no deberían desaparecer ni quedar solo en el gancho.
OBJETOS_NARRATIVOS = {
    "carta", "sobre", "fotografia", "foto", "mensaje", "diario",
    "reloj", "llave", "cinta", "telefono", "libro", "mapa",
    "billete", "caja", "anillo", "espejo", "medalla",
}
NUMEROS = {
    "uno": "1", "una": "1", "dos": "2", "tres": "3",
    "cuatro": "4", "cinco": "5", "diez": "10",
    "veinte": "20", "treinta": "30", "cuarenta": "40",
    "cincuenta": "50", "cien": "100",
}


def normalizar(texto):
    ascii_texto = "".join(
        c for c in unicodedata.normalize("NFD", texto.casefold())
        if unicodedata.category(c) != "Mn"
    )
    return re.findall(r"[a-z0-9]+", ascii_texto)


def _canon(palabra):
    return NUMEROS.get(palabra, palabra)


def auditar_fidelidad(idea, guion):
    """Lista de rechazos detectables; lista vacía NO es aprobación semántica."""
    if not isinstance(idea, str) or not isinstance(guion, dict):
        return ["Premisa o guion inválido para auditar fidelidad"]
    partes = [guion.get(k, "") for k in ("gancho", "historia", "cierre")]
    if any(not isinstance(p, str) or not p.strip() for p in partes):
        return ["Gancho, historia o cierre ausente"]
    gancho, historia, cierre = partes
    original = normalizar(idea)
    relato = normalizar(" ".join(partes))
    desarrollo = set(normalizar(historia + " " + cierre))
    conjunto = set(relato)
    palabras_clave = list(dict.fromkeys(
        _canon(p) for p in original if len(p) >= 4 and p not in VACIAS
    ))
    problemas = []
    if palabras_clave:
        presentes = [_canon(p) for p in palabras_clave if _canon(p) in conjunto]
        # No tratar puntuación/estilo como error; comprobar conceptos anclados.
        minimo = min(len(palabras_clave), max(2, math.ceil(len(palabras_clave) * .55)))
        if len(presentes) < minimo:
            faltantes = [p for p in palabras_clave if p not in conjunto]
            problemas.append(
                "Premisa desviada: el guion omite conceptos esenciales: "
                + ", ".join(faltantes[:7])
            )
    # Pistas temporales explícitas no se pueden sustituir silenciosamente.
    if "ayer" in original and "ayer" not in conjunto:
        problemas.append("Pista temporal omitida: ayer")
    # El objeto central no puede mencionarse únicamente en el gancho.
    for objeto in set(original) & OBJETOS_NARRATIVOS:
        if objeto not in desarrollo:
            problemas.append("Objeto de la premisa desaparece del desarrollo: " + objeto)
    # Una fecha antigua no puede reemplazar una duración definida por el usuario.
    concepto_original = [_canon(p) for p in original]
    concepto_relato = {_canon(p) for p in relato}
    for j in range(len(original) - 1):
        unidad = original[j + 1]
        numero = concepto_original[j]
        if unidad in {"anos", "meses", "dias"} and (
                numero.isdecimal() and numero not in concepto_relato):
            problemas.append(
                "Duración temporal omitida: {} {}".format(numero, unidad))
    if "¿" in gancho or ("?" in gancho and "¿" not in gancho):
        problemas.append("Gancho interrogativo dirigido al espectador")
    return list(dict.fromkeys(problemas))
