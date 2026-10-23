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


def limites_de_bloques(duracion):
    """Distribuir una narración a ~150 palabras/minuto y gancho de 2–3 s."""
    if type(duracion) is not int or not 20 <= duracion <= 60:
        raise ErrorNarrativa("Duración fuera de rango (20 a 60 segundos)")
    total = round(duracion * 2.5)
    cierre = round(total * 0.18)
    historia = total - 7 - cierre
    return {
        "gancho": (5, 8),
        "historia": (max(12, historia - 2), historia + 5),
        "cierre": (max(10, cierre - 3), cierre + 2),
    }


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
            "motivo": "No cumple el mínimo y máximo del bloque",
        }
    if nombre == "gancho":
        # Prompt compacto y ejemplo de LONGITUD, no de hechos de la historia.
        ej = '{"texto": "¡La carta de ayer reveló algo imposible!"}'
        contexto_corto = json.dumps({
            "titulo": original.get("titulo", ""),
            "gancho_original": original.get("gancho", "")[:180],
            "anterior_rechazado": (
                {"palabras": anterior["palabras"],
                 "texto": anterior["texto"][:90]} if anterior else None),
        }, ensure_ascii=False)
        return (
            "Eres un editor de titulares de suspenso. Escribe UNA sola oración "
            "original sobre la premisa indicada, ENTRE 5 Y 8 PALABRAS. "
            "Ejemplo de LONGITUD (no copies su contenido): " + ej + ". "
            "Prohibido incluir historia, explicación, moraleja o más de una oración. "
            "Solo JSON con un campo texto. Premisa: " + contexto_corto
        )
    instruccion = (
        "ESCRIBE SOLO LA SECCION '{}' DE UNA HISTORIA PARA REEL. "
        "Debe contener ENTRE {} Y {} PALABRAS, ambas inclusive. "
        "Si escribes más palabras, la sección se descartará. "
        "Devuelve exclusivamente un JSON del tipo {{\"texto\": \"...\"}}. "
        "No devuelvas título, personajes, explicación ni ninguna otra sección.\\n"
    ).format(nombre.upper(), minimo, maximo)
    return instruccion + json.dumps(payload, ensure_ascii=False, sort_keys=True)


def generar_texto_local(prompt, modelo=MODELO, timeout=150, num_predict=240):
    """Llamada únicamente a la instancia local de Ollama, sin APIs pagas."""
    datos = {
        "model": modelo,
        "prompt": prompt,
        "format": ESQUEMA_TEXTO,
        "stream": False,
        "options": {
            "temperature": 0.2,
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


def ensamblar_por_bloques(original, duracion=35, modelo=MODELO,
                          max_intentos=2, generador=generar_texto_local,
                          gancho_aprobado=None):
    """Máximo seis llamadas y ningún recorte ciego de frases/palabras.

    Preserva todos los intentos y produce guion completo SOLO si se
    generaron gancho, historia y cierre dentro de sus límites.
    """
    if type(max_intentos) is not int or not 1 <= max_intentos <= 2:
        raise ErrorNarrativa("Se permiten 1 o 2 intentos por bloque")
    if not isinstance(original, dict):
        raise ErrorNarrativa("Se requiere un guion de partida")
    evaluacion_original = evaluar_guion(original, duracion)
    if original["naturaleza"] == "factual" or original["nicho"] == "noticias":
        raise ErrorNarrativa(
            "Prohibido reescribir automáticamente información factual o noticias")
    limites = limites_de_bloques(duracion)
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
        "historial_bloques": [],
        "bloques_aprobados_en_longitud": {},
        "guion": None,
        "evaluacion": None,
        "estado": "INCOMPLETO",
        "publicacion_automatica_autorizada": False,
        "nota": "Control de longitud, no verificación semántica ni prueba de viralidad",
    }
    aprobados = {}
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
        previo = None
        exitoso = False
        for numero in range(1, max_intentos + 1):
            prompt = prompt_para_bloque(bloque, original, aprobados, limites, previo)
            try:
                if generador is generar_texto_local:
                    limite_tokens = {"gancho": 75, "historia": 230,
                                     "cierre": 115}[bloque]
                    texto = generador(
                        prompt, modelo=modelo, num_predict=limite_tokens)
                else:
                    texto = generador(prompt, modelo=modelo)
                palabras = contar_palabras(texto)
                minimo, maximo = limites[bloque]
                valido = minimo <= palabras <= maximo
                informe = {
                    "bloque": bloque,
                    "intento": numero,
                    "texto": texto,
                    "palabras": palabras,
                    "limites": [minimo, maximo],
                    "longitud_valida": valido,
                }
            except (ErrorNarrativa, ValueError, OSError) as exc:
                informe = {
                    "bloque": bloque, "intento": numero, "texto": "",
                    "palabras": 0, "limites": list(limites[bloque]),
                    "longitud_valida": False, "error": str(exc),
                }
            resultado["historial_bloques"].append(informe)
            previo = informe
            if informe["longitud_valida"]:
                aprobados[bloque] = informe["texto"]
                resultado["bloques_aprobados_en_longitud"][bloque] = informe["palabras"]
                exitoso = True
                break
        if not exitoso:
            resultado["estado"] = "BLOQUE_RECHAZADO_" + bloque.upper()
            resultado["incidencia"] = (
                "Ollama no logró {} entre {} y {} palabras en {} intentos".format(
                    bloque, *limites[bloque], max_intentos))
            return resultado

    nuevo = dict(original)
    nuevo.update(aprobados)
    nuevo["duracion_objetivo_segundos"] = duracion
    evaluacion = evaluar_guion(nuevo, duracion)
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
    parser.add_argument("--gancho-aprobado", default=None,
                        help="Gancho manual de 5 a 8 palabras para saltar su generación")
    args = parser.parse_args()

    try:
        if args.revisar_archivo.resolve() == args.salida.resolve():
            raise ErrorNarrativa("No se permite sobrescribir el guion original")
        if args.salida.exists():
            raise ErrorNarrativa(
                "La salida ya existe: elige otro nombre para conservar trabajos")
        original = leer_guion_guardado(args.revisar_archivo)
        resultado = ensamblar_por_bloques(
            original, duracion=args.duracion,
            max_intentos=args.max_intentos, modelo=args.modelo,
            gancho_aprobado=args.gancho_aprobado)
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
            "numero_llamadas_ollama": sum(
                1 for intento in resultado["historial_bloques"]
                if intento.get("origen") != "APROBADO_MANUALMENTE"),
            "bloques_aprobados_en_longitud": resultado["bloques_aprobados_en_longitud"],
            "bloqueos": eval_final["bloqueos"] if eval_final else [],
            "advertencias": eval_final["advertencias"] if eval_final else [],
            "incidencia": resultado.get("incidencia"),
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
