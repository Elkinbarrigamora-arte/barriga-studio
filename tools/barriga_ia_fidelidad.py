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



PARENTESCOS = ("hermano", "hermana", "padre", "madre", "hijo", "hija",
               "esposo", "esposa", "novio", "novia", "amigo", "amiga")
DESAPARICIONES = ("desaparecido", "desaparecida", "desaparecio",
                  "desaparecieron", "extraviado", "extraviada")
CLIMAX = {
    "liber": "liberar", "revel": "revelar",
    "rescat": "rescatar", "arrest": "arrestar",
    "captur": "capturar", "salv": "salvar",
}


def _relacion_vinculada_a_desaparicion(texto, parentesco):
    """No confundir mención de un familiar con quién ha desaparecido.

    Heurística conservadora: un familiar y la desaparición deben compartir
    una cláusula, sin otro parentesco que se convierta en protagonista.
    """
    normal = "".join(
        c for c in unicodedata.normalize("NFD", texto.casefold())
        if unicodedata.category(c) != "Mn"
    )
    for clausula in re.split(r"[.!?;\n]+", normal):
        tokens = re.findall(r"[a-z0-9]+", clausula)
        for i, palabra in enumerate(tokens):
            if palabra != parentesco:
                continue
            # «su hermano Carlos, que había desaparecido hace 20 años».
            for j in range(i + 1, min(len(tokens), i + 9)):
                if tokens[j] in PARENTESCOS and tokens[j] != parentesco:
                    break
                if tokens[j] in DESAPARICIONES:
                    return True
            # «desapareció su hermano».
            for j in range(max(0, i - 4), i):
                if tokens[j] in DESAPARICIONES and not any(
                        x in PARENTESCOS and x != parentesco
                        for x in tokens[j + 1:i]):
                    return True
    return False


def _relaciones_desaparecidas_en_premisa(idea):
    """Extraer sucesos familiares explícitos; no inferir parentescos nuevos."""
    return [p for p in PARENTESCOS
            if _relacion_vinculada_a_desaparicion(idea, p)]


def _acciones_terminales(texto):
    tokens = normalizar(texto)
    return {etiqueta for raiz, etiqueta in CLIMAX.items()
            if any(token.startswith(raiz) for token in tokens)}


def _repeticion_de_cierre(historia, cierre):
    compartidas = _acciones_terminales(historia) & _acciones_terminales(cierre)
    return sorted(compartidas) if len(compartidas) >= 2 else []


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
    for parentesco in _relaciones_desaparecidas_en_premisa(idea):
        if not _relacion_vinculada_a_desaparicion(
                " ".join(partes), parentesco):
            problemas.append(
                "Cambio de protagonista del suceso: en la premisa quien "
                "desaparece es su {}, pero el relato no conserva "
                "ese hecho".format(parentesco))
    repetidas = _repeticion_de_cierre(historia, cierre)
    if repetidas:
        problemas.append(
            "El cierre repite acciones ya resueltas en la historia: "
            + ", ".join(repetidas))
    return list(dict.fromkeys(problemas))
