#!/usr/bin/env python3
"""Barriga IA: microguion en tres bloques con presupuestos de palabras.

Este prototipo emplea exclusivamente Ollama local y NO publica contenidos.
Solo revisa ficción/dramatización; cada parte tiene como máximo dos intentos.
Nunca modifica el JSON original ni inventa un éxito editorial.
Compatible con Python 3.9 o posterior.
"""
import argparse
from datetime import datetime
import json
import re
from pathlib import Path
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

from barriga_ia_narrativa import (
    MODELO, OLLAMA_URL, ErrorNarrativa, contar_palabras, evaluar_guion,
    leer_guion_guardado,
)

ESQUEMA_TEXTO = {
    "type": "object",
    "properties": {"texto": {"type": "string"}},
    "required": ["texto"],
}


def limites_de_bloques(duracion, palabras_por_minuto=150):
    """Presupuestos de palabras para una velocidad de locución configurable."""
    if type(duracion) is not int or not 20 <= duracion <= 60:
        raise ErrorNarrativa("Duración fuera de rango (20 a 60 segundos)")
    if type(palabras_por_minuto) is not int or not 120 <= palabras_por_minuto <= 210:
        raise ErrorNarrativa("Velocidad de narración: 120 a 210 ppm")
    total = round(duracion * palabras_por_minuto / 60)
    cierre = round(total * 0.18)
    historia = total - 7 - cierre
    return {
        "gancho": (5, 8),
        "historia": (max(12, historia - 2), historia + 5),
        "cierre": (max(10, cierre - 3), cierre + 2),
    }


def detectar_problemas_editoriales(texto, original, bloque, anterior=None):
    """Controles conservadores: repetición, nombres no aportados y giro temporal.

    No son una verificación semántica de calidad; solo bloquean indicios claros.
    """
    problemas = []
    if anterior and isinstance(anterior.get("texto"), str):
        a = " ".join(anterior["texto"].casefold().split()).strip(" .!¿?¡")
        b = " ".join(texto.casefold().split()).strip(" .!¿?¡")
        if a and a == b:
            problemas.append("Respuesta repetida literalmente tras un rechazo")
    original_texto = " ".join(
        str(original.get(campo, "")) for campo in
        ("titulo", "gancho", "historia", "cierre")
    )
    for ficha in original.get("personajes", []):
        if isinstance(ficha, dict):
            original_texto += " " + str(ficha.get("nombre", ""))
    # Ignorar mayúsculas dentro de citas: son diálogos o texto de la carta,
    # no necesariamente nombres de personajes.
    sin_citas = re.sub(r"([\x27\x22“‘])(?:(?!\1).)*?([\x27\x22”’])", lambda m: " " * len(m.group()), texto)
    # Solo flaggear mayúsculas interiores, no arranques normales de oración.
    for coincide in re.finditer(r"\b[A-ZÁÉÍÓÚÑ][a-záéíóúñ]{2,}\b", sin_citas):
        posicion = coincide.start()
        antes = texto[:posicion].rstrip()
        if not antes or antes[-1] in ".!?¡¿:;":
            continue
        nombre = coincide.group()
        if not re.search(
            r"(?<!\w)" + re.escape(nombre) + r"(?!\w)",
            original_texto, flags=re.IGNORECASE | re.UNICODE
        ):
            problemas.append("Posible personaje o nombre nuevo: " + nombre)
    if bloque == "gancho":
        origen = (str(original.get("gancho", "")) + " " +
                  str(original.get("historia", ""))[:350]).casefold()
        if re.search(r"\bayer\b", origen) and not re.search(
            r"\bayer\b|\banoche\b|\bd[ií]a anterior\b|"
            r"\bnoche anterior\b|\bv[ií]spera\b", texto.casefold()
        ):
            problemas.append("Se perdió la pista temporal esencial: ayer")
    # Ollama puede llegar al límite de tokens en medio de una oración.
    # La puntuación final no certifica coherencia semántica; sí evita cortes evidentes.
    final = texto.strip().rstrip('”"’\')]}')
    if not re.search(r"[.!?…]$", final):
        problemas.append("Oración incompleta: no hay puntuación final")
    if re.search(r"\b(\w+)(?:\s+\1){3,}\b", texto, re.IGNORECASE | re.UNICODE):
        problemas.append("Repetición mecánica de palabras consecutivas")
    # Mantener únicos los avisos.
    return list(dict.fromkeys(problemas))


def proponer_gancho_seguro(original, limites, premisa=None):
    """Gancho determinista solo con datos verificables en el borrador/premisa.

    Nunca decide el misterio por su cuenta ni atribuye la carta al hermano.
    Si los datos no sustentan una regla o una frase extractiva, retorna None.
    """
    if not isinstance(original, dict):
        raise ErrorNarrativa("El borrador original debe ser un objeto")
    if premisa is not None and (
            not isinstance(premisa, str) or
            not 10 <= len(premisa.strip()) <= 500):
        raise ErrorNarrativa("La premisa debe tener de 10 a 500 caracteres")
    texto_base = premisa or " ".join(
        str(original.get(campo, "")) for campo in ("gancho", "historia", "cierre"))
    base = texto_base.casefold()
    # Importante: el hermano NO se presenta como autor de la carta, porque
    # la premisa solo dice que alguien la escribió ayer.
    hechos_necesarios = (
        re.search(r"\bherman[oa]s?\b", base),
        re.search(r"\bdesaparec\w*\b", base),
        re.search(r"\bcarta\b", base),
        re.search(r"\bayer\b", base),
        re.search(r"\bescrib\w*\b|\bfechad[ao]\b", base),
    )
    if all(hechos_necesarios):
        candidato = "¡La carta de su hermano fue escrita ayer!"
        if limites["gancho"][0] <= contar_palabras(candidato) <= limites["gancho"][1]:
            return {"texto": candidato, "origen": "REGLA_FIEL_A_PREMISA",
                    "regla": "carta_hermano_desaparecido_escrita_ayer"}
    # Ruta general: extraer una oración completa del gancho existente.
    # No cortar por longitud ni crear nuevas relaciones/personajes.
    gancho_original = original.get("gancho", "")
    if isinstance(gancho_original, str):
        palabras_premisa = set()
        if premisa:
            vacias = {"el", "la", "los", "las", "un", "una", "uno",
                      "de", "del", "en", "por", "y", "o", "a", "que",
                      "su", "sus", "con", "al", "se", "pero", "hace",
                      "fue", "es", "como", "cuando", "lo"}
            palabras_premisa = {
                p for p in re.findall(r"\b\w+\b", premisa.casefold(),
                                       flags=re.UNICODE)
                if p not in vacias and len(p) >= 4
            }
        for candidato in re.split(r"(?<=[.!?…])\s+", gancho_original.strip()):
            if premisa:
                palabras_candidato = set(re.findall(
                    r"\b\w+\b", candidato.casefold(), flags=re.UNICODE))
                # No aceptar un fragmento corto que ni siquiera trate la premisa.
                if len(palabras_premisa & palabras_candidato) < 2:
                    continue
            if (limites["gancho"][0] <= contar_palabras(candidato)
                    <= limites["gancho"][1]
                    and not detectar_problemas_editoriales(
                        candidato, original, "gancho")):
                return {"texto": candidato, "origen": "EXTRACTIVO_BORRADOR",
                        "regla": "oracion_completa_sin_reescritura"}
    return None


def prompt_para_bloque(nombre, original, generado, limites, anterior=None):
    """Pedir una sola parte; no pasar todas las instrucciones largas antiguas."""
    minimo, maximo = limites[nombre]
    if nombre == "gancho":
        # Evitar pasar el relato completo: favorece respuestas largas en modelos pequeños.
        # El gancho debe atacar el conflicto que ya aparece en el borrador.
        contexto = {
            "gancho_original": original.get("gancho", "")[:260],
            "titulo": original.get("titulo", ""),
            "instruccion": "Una oración muy breve, con intriga y sin revelar el final.",
        }
    elif nombre == "historia":
        contexto = {
            "gancho_definitivo": generado["gancho"],
            "borrador_de_desarrollo": original.get("historia", "")[:1600],
            "instruccion": (
                "Acciones visibles, secuencia causal, conserva parentescos y "
                "el mismo misterio; prepara un desenlace revelador."
            ),
        }
    elif nombre == "cierre":
        contexto = {
            "gancho_definitivo": generado["gancho"],
            "desarrollo_definitivo": generado["historia"],
            "cierre_original": original.get("cierre", "")[:450],
            "instruccion": (
                "Revelación concreta que responda al conflicto; sin moralejas "
                "ni finales genéricos. Sin personajes nuevos."
            ),
        }
    else:
        raise ErrorNarrativa("Bloque desconocido: " + str(nombre))
    payload = {
        "rol": "Guionista de microvideo en español latinoamericano",
        "seccion": nombre,
        "cantidad_de_palabras": {
            "minimo": minimo, "maximo": maximo,
            "regla": "OBLIGATORIA; cuenta las palabras ANTES de responder",
        },
        "titulo_original": original.get("titulo", ""),
        "personajes_ya_definidos": original.get("personajes", []),
        "naturaleza": original.get("naturaleza"),
        "datos": contexto,
        "forma": 'Una sola frase o pasaje breve dentro de {"texto": "..."}',
        "restricciones": [
            "Solo responder JSON valido con campo texto",
            "No añadir explicaciones fuera del campo texto",
            "No copiar literalmente párrafos largos",
            "Sin palabras inventadas ni faltas de ortografía",
            "Sin nuevos personajes, parentescos o conflictos",
            "Narración continua, no dirigirse al espectador",
        ],
    }
    if anterior:
        payload["intento_anterior_rechazado"] = {
            "texto": anterior["texto"][:120],
            "palabras": anterior["palabras"],
            "motivos": anterior.get("motivos_rechazo", []),
        }
    if nombre == "gancho":
        # Prompt compacto y ejemplo de LONGITUD, no de hechos de la historia.
        ej = '{"texto": "¡La carta de ayer reveló algo imposible!"}'
        contexto_corto = json.dumps({
            "gancho_original": original.get("gancho", "")[:180],
            "personajes_permitidos": [
                x.get("nombre", "") for x in original.get("personajes", [])
                if isinstance(x, dict)
            ],
        }, ensure_ascii=False)
        if anterior:
            # No solicitar el mismo resultado determinista: variar objetivo y
            # prohibir explicitamente repetir la respuesta o inventar nombres.
            return (
                "EDICION DE TITULAR, SEGUNDO INTENTO. El intento anterior fue "
                "RECHAZADO. No lo repitas ni menciones personas nuevas. "
                "Corrige y REEMPLAZA la frase previa con un titular distinto. "
                "ENTRE 5 Y 8 PALABRAS; preservar el misterio central. "
                "Si el guion dice AYER, incluye AYER. "
                "Nombres propios SOLO si estan permitidos en el contexto. "
                "Unicamente JSON con la clave texto. "
                "Motivos del rechazo: "
                + json.dumps(anterior.get("motivos_rechazo", []),
                             ensure_ascii=False)
                + " Frase rechazada: " + json.dumps(
                    anterior.get("texto", "")[:95], ensure_ascii=False)
                + " Contexto: " + contexto_corto
            )
        return (
            "Eres editor de ganchos de suspenso. Entrega UNA frase diferente "
            "del contexto, ENTRE 5 Y 8 PALABRAS. No inventes nombres ni "
            "lugares. Conserva la intriga temporal si menciona AYER. "
            "No escribas la historia o el cierre. "
            "Ejemplo de estructura (no copies): " + ej + ". "
            "Solo JSON con el campo texto. Contexto: " + contexto_corto
        )
    if anterior and nombre in ("historia", "cierre"):
        # Reintento distinto: breve, con causa y efecto, y rechazo explícito.
        return (
            "PLAN ALTERNATIVO PARA {}: reescribe SOLO esta sección en español. "
            "No copies el intento fallido. ENTRE {} Y {} PALABRAS exactas; "
            "termina todas las oraciones con punto. Escribe acciones y "
            "consecuencias en secuencia. No agregues protagonistas, fechas "
            'ni desenlaces ajenos a la premisa. Responde solo {{"texto":"..."}}. '
            "Diagnóstico: "
        ).format(nombre.upper(), minimo, maximo) + json.dumps({
            "motivos_del_rechazo": anterior.get("motivos_rechazo", []),
            "texto_rechazado": anterior.get("texto", "")[:250],
            "gancho_inmutable": generado.get("gancho"),
            "historia_inmutable": generado.get("historia"),
            "borrador_historia": original.get("historia", "")[:850],
            "borrador_cierre": original.get("cierre", "")[:250],
            "personajes_permitidos": original.get("personajes", []),
        }, ensure_ascii=False)
    instruccion = (
        "ESCRIBE SOLO LA SECCION '{}' DE UNA HISTORIA PARA REEL. "
        "Debe contener ENTRE {} Y {} PALABRAS, ambas inclusive. "
        "Si escribes más palabras, la sección se descartará. "
        "Devuelve exclusivamente un JSON del tipo {{\"texto\": \"...\"}}. "
        "No devuelvas título, personajes, explicación ni ninguna otra sección.\\n"
    ).format(nombre.upper(), minimo, maximo)
    return instruccion + json.dumps(payload, ensure_ascii=False, sort_keys=True)


def generar_texto_local(prompt, modelo=MODELO, timeout=150,
                         num_predict=240, temperatura=0.2):
    """Llamada únicamente a la instancia local de Ollama, sin APIs pagas."""
    datos = {
        "model": modelo,
        "prompt": prompt,
        "format": ESQUEMA_TEXTO,
        "stream": False,
        "options": {
            "temperature": temperatura,
            "num_ctx": 4096,
            "num_predict": num_predict,
        },
    }
    req = Request(
        OLLAMA_URL,
        json.dumps(datos, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            envelope = json.loads(resp.read().decode("utf-8"))
        payload = json.loads(envelope["response"])
        texto = payload.get("texto")
    except (URLError, OSError, TimeoutError, KeyError, ValueError, TypeError) as exc:
        raise ErrorNarrativa("Ollama local no devolvió el bloque válido: " + str(exc)) from exc
    if not isinstance(texto, str) or not texto.strip():
        raise ErrorNarrativa("El bloque generado está vacío o es inválido")
    return " ".join(texto.split())


def leer_sesion_por_bloques(ruta):
    """Leer el sexto informe fallido o un guion crudo sin sobrescribirlo."""
    datos = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if not isinstance(datos, dict):
        raise ErrorNarrativa("El archivo de entrada debe ser un objeto JSON")
    sesion = datos if isinstance(datos.get("historial_bloques"), list) else None
    if sesion is not None:
        if not isinstance(datos.get("guion_original"), dict):
            raise ErrorNarrativa("Informe sin guion_original: no se puede reanudar")
        return datos["guion_original"], sesion
    return leer_guion_guardado(ruta), None


def recuperar_bloques_aprobados(sesion, original, limites):
    """Preservar únicamente bloques marcados aprobados que sigan siendo válidos."""
    aprobados = {}
    for registro in sesion.get("historial_bloques", []):
        if not isinstance(registro, dict):
            continue
        nombre = registro.get("bloque")
        texto = registro.get("texto")
        if nombre not in limites or not isinstance(texto, str):
            continue
        # Retrocompatibilidad con informes antiguos que guardaban solo longitud_valida.
        marcado = registro.get("aceptable_para_ensamblaje") is True or (
            registro.get("aceptable_para_ensamblaje") is None
            and registro.get("longitud_valida") is True
            and not registro.get("motivos_rechazo") and not registro.get("error"))
        if not marcado or registro.get("motivos_rechazo") or registro.get("error"):
            continue
        menor, mayor = limites[nombre]
        if not menor <= contar_palabras(texto) <= mayor:
            continue
        if detectar_problemas_editoriales(texto, original, nombre):
            continue
        if nombre == "historia" and "gancho" not in aprobados:
            continue
        if nombre == "cierre" and "historia" not in aprobados:
            continue
        aprobados[nombre] = texto
    return aprobados


def normalizar_comparacion(texto):
    return re.sub(r"\s+", " ", texto.casefold()).strip(" .!¡?¿…")


def ensamblar_por_bloques(original, duracion=35, modelo=MODELO,
                          max_intentos=2, generador=None,
                          gancho_aprobado=None, estrategia_gancho="modelo",
                          premisa=None, sesion_previa=None,
                          palabras_por_minuto=150):
    """Máximo seis llamadas y ningún recorte ciego de frases/palabras.

    Preserva todos los intentos y produce guion completo SOLO si se
    generaron gancho, historia y cierre dentro de sus límites.
    """
    if generador is None:
        generador = generar_texto_local
    if type(max_intentos) is not int or not 1 <= max_intentos <= 2:
        raise ErrorNarrativa("Se permiten 1 o 2 intentos por bloque")
    if not isinstance(original, dict):
        raise ErrorNarrativa("Se requiere un guion de partida")
    if estrategia_gancho not in ("modelo", "reglas-primero"):
        raise ErrorNarrativa("Estrategia de gancho desconocida")
    evaluacion_original = evaluar_guion(original, duracion, palabras_por_minuto)
    if sesion_previa is not None and not isinstance(sesion_previa, dict):
        raise ErrorNarrativa("Sesión previa inválida")
    if original["naturaleza"] == "factual" or original["nicho"] == "noticias":
        raise ErrorNarrativa(
            "Prohibido reescribir automáticamente información factual o noticias")
    limites = limites_de_bloques(duracion, palabras_por_minuto)
    if gancho_aprobado is not None:
        if not isinstance(gancho_aprobado, str):
            raise ErrorNarrativa("El gancho aportado debe ser texto")
        gancho_aprobado = " ".join(gancho_aprobado.split())
        menor, mayor = limites["gancho"]
        if not menor <= contar_palabras(gancho_aprobado) <= mayor:
            raise ErrorNarrativa(
                "El gancho indicado debe contener entre {} y {} palabras".format(
                    menor, mayor))
    resultado = {
        "guion_original": original,
        "evaluacion_original": evaluacion_original,
        "limites_bloques": {k: list(v) for k, v in limites.items()},
        "historial_bloques": list(sesion_previa.get("historial_bloques", [])) if sesion_previa else [],
        "registros_recuperados": len(sesion_previa.get("historial_bloques", [])) if sesion_previa else 0,
        "palabras_por_minuto": palabras_por_minuto,
        "bloques_aprobados_en_longitud": {},
        "guion": None,
        "evaluacion": None,
        "estado": "INCOMPLETO",
        "publicacion_automatica_autorizada": False,
        "nota": "Control de longitud, no verificación semántica ni prueba de viralidad",
    }
    aprobados = recuperar_bloques_aprobados(sesion_previa, original, limites) if sesion_previa else {}
    resultado["bloques_aprobados_en_longitud"] = {k: contar_palabras(v) for k, v in aprobados.items()}
    if gancho_aprobado is None and "gancho" not in aprobados and estrategia_gancho == "reglas-primero":
        alternativa = proponer_gancho_seguro(
            original, limites, premisa=premisa)
        if alternativa:
            texto = alternativa["texto"]
            # Controlar el resultado sin asumir que una regla garantiza
            # calidad creativa o causalidad narrativa.
            if detectar_problemas_editoriales(texto, original, "gancho"):
                alternativa = None
            else:
                aprobados["gancho"] = texto
                resultado["bloques_aprobados_en_longitud"]["gancho"] = (
                    contar_palabras(texto))
                resultado["historial_bloques"].append({
                    "bloque": "gancho",
                    "intento": 0,
                    "texto": texto,
                    "palabras": contar_palabras(texto),
                    "limites": list(limites["gancho"]),
                    "longitud_valida": True,
                    "aceptable_para_ensamblaje": True,
                    "origen": alternativa["origen"],
                    "regla": alternativa["regla"],
                    "nota": "Plantilla o frase extractiva, NO generada por Ollama",
                })
    if gancho_aprobado:
        aprobados["gancho"] = gancho_aprobado
        resultado["bloques_aprobados_en_longitud"]["gancho"] = contar_palabras(
            gancho_aprobado)
        resultado["historial_bloques"].append({
            "bloque": "gancho", "intento": 0, "texto": gancho_aprobado,
            "palabras": contar_palabras(gancho_aprobado),
            "limites": list(limites["gancho"]), "longitud_valida": True,
            "origen": "APROBADO_MANUALMENTE",
        })
    for bloque in ("gancho", "historia", "cierre"):
        if bloque in aprobados:
            continue
        previos = [x for x in resultado["historial_bloques"]
                   if isinstance(x, dict) and x.get("bloque") == bloque
                   and not x.get("aceptable_para_ensamblaje")]
        previo = previos[-1] if previos else None
        exitoso = False
        for numero in range(1, max_intentos + 1):
            prompt = prompt_para_bloque(bloque, original, aprobados, limites, previo)
            try:
                if generador is generar_texto_local:
                    limite_tokens = {"gancho": 75, "historia": 230,
                                     "cierre": 115}[bloque]
                    texto = generador(
                        prompt, modelo=modelo, num_predict=limite_tokens,
                        temperatura=(0.2 if numero == 1 else 0.65))
                else:
                    texto = generador(prompt, modelo=modelo)
                palabras = contar_palabras(texto)
                minimo, maximo = limites[bloque]
                valido = minimo <= palabras <= maximo
                motivos = [] if valido else [
                    "Extensión {} palabras fuera de {} a {}".format(
                        palabras, minimo, maximo)]
                motivos += detectar_problemas_editoriales(
                    texto, original, bloque, previo)
                rechazos_anteriores = [
                    x.get("texto", "") for x in resultado["historial_bloques"]
                    if isinstance(x, dict) and x.get("bloque") == bloque
                    and not x.get("aceptable_para_ensamblaje")
                ]
                if normalizar_comparacion(texto) and any(
                    normalizar_comparacion(texto) == normalizar_comparacion(t)
                    for t in rechazos_anteriores if isinstance(t, str)
                ):
                    if "Respuesta repetida literalmente tras un rechazo" not in motivos:
                        motivos.append("Respuesta repetida literalmente tras un rechazo")
                informe = {
                    "bloque": bloque,
                    "intento": numero,
                    "texto": texto,
                    "palabras": palabras,
                    "limites": [minimo, maximo],
                    "longitud_valida": valido,
                    "motivos_rechazo": motivos,
                    "aceptable_para_ensamblaje": valido and not motivos,
                }
            except (ErrorNarrativa, ValueError, OSError) as exc:
                informe = {
                    "bloque": bloque, "intento": numero, "texto": "",
                    "palabras": 0, "limites": list(limites[bloque]),
                    "longitud_valida": False, "error": str(exc),
                    "motivos_rechazo": ["Error local: " + str(exc)],
                    "aceptable_para_ensamblaje": False,
                }
            resultado["historial_bloques"].append(informe)
            previo = informe
            if informe["aceptable_para_ensamblaje"]:
                aprobados[bloque] = informe["texto"]
                resultado["bloques_aprobados_en_longitud"][bloque] = informe["palabras"]
                exitoso = True
                break
        if not exitoso:
            resultado["estado"] = "BLOQUE_RECHAZADO_" + bloque.upper()
            resultado["incidencia"] = (
                "El bloque {} no cumplió longitud o coherencia básica "
                "en {} intentos".format(bloque, max_intentos))
            return resultado

    nuevo = dict(original)
    nuevo.update(aprobados)
    nuevo["duracion_objetivo_segundos"] = duracion
    evaluacion = evaluar_guion(nuevo, duracion, palabras_por_minuto)
    resultado["guion"] = nuevo
    resultado["evaluacion"] = evaluacion
    resultado["estado"] = evaluacion["estado_revision"]
    return resultado


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--revisar-archivo", type=Path, required=True)
    parser.add_argument("--salida", type=Path, required=True)
    parser.add_argument("--duracion", type=int, default=35)
    parser.add_argument("--max-intentos", type=int, default=2)
    parser.add_argument("--modelo", default=MODELO)
    parser.add_argument("--palabras-por-minuto", type=int, default=150,
                        help="Velocidad de voz: 120 a 210 palabras/minuto")
    parser.add_argument("--gancho-aprobado", default=None,
                        help="Gancho manual de 5 a 8 palabras para saltar su generación")
    parser.add_argument("--premisa", default=None,
                        help="Premisa original para reglas fieles; no inventa el autor del misterio")
    parser.add_argument("--estrategia-gancho", choices=("modelo", "reglas-primero"),
                        default="modelo",
                        help="Probar una regla o frase extractiva antes de usar Ollama")
    args = parser.parse_args()

    try:
        if args.revisar_archivo.resolve() == args.salida.resolve():
            raise ErrorNarrativa("No se permite sobrescribir el guion original")
        if args.salida.exists():
            raise ErrorNarrativa(
                "La salida ya existe: elige otro nombre para conservar trabajos")
        original, sesion_previa = leer_sesion_por_bloques(args.revisar_archivo)
        resultado = ensamblar_por_bloques(
            original, duracion=args.duracion,
            max_intentos=args.max_intentos, modelo=args.modelo,
            gancho_aprobado=args.gancho_aprobado,
            estrategia_gancho=args.estrategia_gancho, premisa=args.premisa,
            sesion_previa=sesion_previa, palabras_por_minuto=args.palabras_por_minuto)
        resultado["fecha_revision"] = datetime.utcnow().isoformat() + "Z"
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        with args.salida.open("x", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
            f.write("\n")
        eval_final = resultado["evaluacion"]
        resumen = {
            "estado": resultado["estado"],
            "palabras_iniciales": resultado["evaluacion_original"]["palabras"],
            "palabras_finales": eval_final["palabras"] if eval_final else None,
            "segundos_finales": eval_final["segundos_estimados"] if eval_final else None,
            "objetivo_segundos": args.duracion,
            "registros_recuperados": resultado["registros_recuperados"],
            "palabras_por_minuto": args.palabras_por_minuto,
            "numero_llamadas_ollama": sum(
                1 for intento in resultado["historial_bloques"]
                if intento.get("origen") not in (
                    "APROBADO_MANUALMENTE", "REGLA_FIEL_A_PREMISA",
                    "EXTRACTIVO_BORRADOR")),
            "numero_llamadas_ollama_esta_ejecucion": sum(
                1 for intento in resultado["historial_bloques"][resultado["registros_recuperados"]:]
                if intento.get("origen") not in (
                    "APROBADO_MANUALMENTE", "REGLA_FIEL_A_PREMISA", "EXTRACTIVO_BORRADOR")),
            "bloques_aprobados_en_longitud": resultado["bloques_aprobados_en_longitud"],
            "metodo_gancho": next((
                paso.get("origen", "OLLAMA") for paso in resultado["historial_bloques"]
                if paso["bloque"] == "gancho" and
                   paso.get("aceptable_para_ensamblaje", paso.get("longitud_valida", False))
            ), None),
            "bloqueos": eval_final["bloqueos"] if eval_final else [],
            "advertencias": eval_final["advertencias"] if eval_final else [],
            "incidencia": resultado.get("incidencia"),
            "ultimo_texto_rechazado": (
                resultado["historial_bloques"][-1]["texto"][:180]
                if resultado.get("incidencia") and resultado["historial_bloques"]
                else None),
            "motivos_ultimo_rechazo": (
                resultado["historial_bloques"][-1].get("motivos_rechazo", [])
                if resultado.get("incidencia") and resultado["historial_bloques"]
                else []),
            "apto_para_revision_humana": bool(
                eval_final and eval_final["apto_para_revision_humana"]),
            "archivo_guardado": str(args.salida),
            "publicacion_automatica_autorizada": False,
        }
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
        return 0 if resumen["apto_para_revision_humana"] else 2
    except (ErrorNarrativa, OSError, ValueError) as exc:
        print("Error en ensamblaje narrativo: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
