#!/usr/bin/env python3
"""Reanudar sexta prueba sin regenerar un gancho aprobado.

Mantiene cada intento y bloque previamente aprobado, consulta exclusivamente
Ollama local y nunca declara aprobado contenido que no haya superado controles.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys

from barriga_ia_narrativa import ErrorNarrativa, contar_palabras, evaluar_guion
from barriga_ia_por_bloques import (
    limites_de_bloques, detectar_problemas_editoriales, generar_texto_local,
)

BLOQUES = ("gancho", "historia", "cierre")


def texto_canonico(texto):
    return " ".join(re.findall(r"\w+", texto.casefold(), re.UNICODE))


def oraciones_completas(texto):
    """Control conservador de truncamiento, sin fingir análisis gramatical."""
    texto = texto.strip()
    if not texto or texto[-1] not in ".!?…»”":
        return False
    if re.search(r"(?:,|;|:|[-–—])\s*$", texto):
        return False
    if texto.count("«") != texto.count("»"):
        return False
    if texto.count("“") != texto.count("”"):
        return False
    if texto.count("(") != texto.count(")"):
        return False
    if re.search(r"\b(?:de|del|a|en|con|por|para|que|y|o|pero|sin|su|un|una)\s*[.!?…»”]$", texto.casefold()):
        return False
    return True


def validar_bloque(texto, bloque, original, limites, rechazados):
    motivos = []
    n = contar_palabras(texto)
    minimo, maximo = limites[bloque]
    if not minimo <= n <= maximo:
        motivos.append("Extensión {} fuera de {} a {} palabras".format(n, minimo, maximo))
    if not oraciones_completas(texto):
        motivos.append("Oración incompleta, truncada o puntuación de cierre inválida")
    if texto_canonico(texto) in rechazados:
        motivos.append("Repetición literal de una versión previamente rechazada")
    motivos += detectar_problemas_editoriales(texto, original, bloque)
    return list(dict.fromkeys(motivos))


def cargar_sexta(ruta, duracion):
    registro = json.loads(Path(ruta).read_text(encoding="utf-8"))
    if not isinstance(registro, dict) or not isinstance(registro.get("guion_original"), dict):
        raise ErrorNarrativa("El JSON no contiene guion_original recuperable")
    original = registro["guion_original"]
    if original.get("naturaleza") == "factual" or original.get("nicho") == "noticias":
        raise ErrorNarrativa("La reescritura factual exige revisión humana")
    if not isinstance(registro.get("historial_bloques"), list):
        raise ErrorNarrativa("Falta historial de bloques para recuperar")
    historial = registro["historial_bloques"]
    limites = limites_de_bloques(duracion)
    aprobados = {}
    for bloque in BLOQUES:
        candidatos = [
            x for x in historial if isinstance(x, dict)
            and x.get("bloque") == bloque and x.get("aceptable_para_ensamblaje") is True
            and isinstance(x.get("texto"), str)
        ]
        if not candidatos:
            break
        elegido = candidatos[-1]
        problemas = validar_bloque(elegido["texto"], bloque, original, limites, set())
        if problemas:
            raise ErrorNarrativa(
                "Bloque {} anteriormente aprobado no pasó nueva validación: {}".format(
                    bloque, "; ".join(problemas)))
        aprobados[bloque] = elegido["texto"]
    if "gancho" not in aprobados:
        raise ErrorNarrativa("No se encontró gancho aprobado para conservar")
    if contar_palabras(aprobados["gancho"]) != 7:
        raise ErrorNarrativa("La recuperación exige gancho aprobado de siete palabras")
    if "historia" in aprobados and "cierre" in aprobados:
        raise ErrorNarrativa("El archivo ya contiene un guion completo")
    return registro, original, historial, aprobados, limites


def prompt_historia(original, gancho, limites, rechazados, intento):
    minimo, maximo = limites["historia"]
    # No reinyectar los párrafos rechazados: dan lugar a respuestas repetidas.
    nombres = [
        x.get("nombre") for x in original.get("personajes", [])
        if isinstance(x, dict) and isinstance(x.get("nombre"), str)
    ]
    contexto = {
        "gancho_fijo": gancho,
        "personajes_permitidos": nombres,
        "situacion_original": original.get("historia", "")[:450],
        "cierre_original": original.get("cierre", "")[:150],
        "numero_intento": intento,
        "requisitos": [
            "Historia continua en español, acciones visibles, causa y efecto",
            "Preservar el misterio central y la relación de hermanos",
            "No inventar nombres ajenos ni cambiar la identidad de los personajes",
            "No anticipar el cierre; terminar en una oración COMPLETA con punto",
            "Una sola clave JSON texto, sin otros campos",
        ],
        "motivos_rechazo": [
            "La versión anterior incumplió longitud, integridad o unicidad"
        ],
        "cantidad_versiones_previas_rechazadas": len(rechazados),
    }
    encabezado = (
        "Redacta SOLO EL DESARROLLO de este relato, sin gancho ni cierre. "
        "ENTRE {} Y {} PALABRAS, sin excepción. "
        "Escribe {} oraciones de acciones concretas. "
        "Termina SIEMPRE con punto final y nunca dejes frases inconclusas. "
        "No repitas respuestas previas rechazadas. "
        "Devuelve SOLO JSON: {{\"texto\": \"...\"}}. "
    ).format(minimo, maximo, 5 if intento == 1 else 6)
    if intento > 1:
        encabezado += (
            "ESTRATEGIA ALTERNATIVA: olvida la redacción anterior, "
            "reconstruye cinco hechos del conflicto cronológicamente, "
            "con una acción por oración y sin resumen genérico. "
        )
    return encabezado + json.dumps(contexto, ensure_ascii=False)


def prompt_cierre(original, aprobados, limites, rechazados, intento):
    minimo, maximo = limites["cierre"]
    datos = {
        "gancho_fijo": aprobados["gancho"],
        "historia_fija": aprobados["historia"],
        "cierre_original": original.get("cierre", "")[:250],
        "versiones_rechazadas": len(rechazados),
    }
    return (
        "Genera SOLO EL CIERRE, {} a {} palabras, español latinoamericano. "
        "Resuelve mediante un suceso visible el misterio del gancho. "
        "Sin personajes nuevos, sin muletillas, ni recapitulación. "
        "Termina en punto, con una frase completa. "
        "Intento {}: si es segundo intento, cambia el enfoque narrativo. "
        "Solo JSON {{\"texto\": \"...\"}}. "
    ).format(minimo, maximo, intento) + json.dumps(datos, ensure_ascii=False)


def reanudar(registro, original, historial, aprobados, limites,
            duracion=35, velocidad_ppm=150, max_intentos=3,
            generador=None, modelo=None):
    if type(max_intentos) is not int or not 1 <= max_intentos <= 3:
        raise ErrorNarrativa("Máximo de 1 a 3 intentos por bloque pendiente")
    if not 100 <= velocidad_ppm <= 220:
        raise ErrorNarrativa("Velocidad de narración fuera de 100–220 ppm")
    from barriga_ia_narrativa import MODELO
    if generador is None:
        generador = generar_texto_local
    if modelo is None:
        modelo = MODELO
    historial_nuevo = list(historial)
    fijos = dict(aprobados)
    todos_rechazados = {
        bloque: {
            texto_canonico(x["texto"]) for x in historial
            if isinstance(x, dict) and x.get("bloque") == bloque
            and isinstance(x.get("texto"), str) and x["texto"].strip()
            and not x.get("aceptable_para_ensamblaje", False)
        } for bloque in BLOQUES
    }
    resultado = {
        "guion_original": original,
        "historial_bloques": historial_nuevo,
        "bloques_aprobados_en_longitud": {
            k: contar_palabras(v) for k, v in fijos.items()},
        "bloques_preservados": sorted(fijos.keys()),
        "estado": "EN_REVISION",
        "guion": None,
        "evaluacion": None,
        "velocidad_narracion_ppm": velocidad_ppm,
        "publicacion_automatica_autorizada": False,
        "verificacion_semantica_humana_pendiente": True,
    }
    for bloque in BLOQUES:
        if bloque in fijos:
            continue
        for intento in range(1, max_intentos + 1):
            if bloque == "historia":
                prompt = prompt_historia(
                    original, fijos["gancho"], limites,
                    todos_rechazados[bloque], intento)
            else:
                prompt = prompt_cierre(
                    original, fijos, limites, todos_rechazados[bloque], intento)
            try:
                if generador is generar_texto_local:
                    texto = generador(
                        prompt, modelo=modelo, timeout=180,
                        num_predict=(310 if bloque == "historia" else 110),
                        temperatura=(0.3 if intento == 1 else 0.75))
                else:
                    texto = generador(prompt, modelo=modelo)
                motivos = validar_bloque(
                    texto, bloque, original, limites, todos_rechazados[bloque])
            except (ValueError, OSError, ErrorNarrativa) as exc:
                texto = ""
                motivos = ["Error de inferencia: " + str(exc)]
            paso = {
                "bloque": bloque, "intento": intento,
                "texto": texto, "palabras": contar_palabras(texto),
                "motivos_rechazo": motivos,
                "aceptable_para_ensamblaje": not motivos,
                "origen": "OLLAMA_LOCAL",
            }
            historial_nuevo.append(paso)
            if motivos:
                if texto:
                    todos_rechazados[bloque].add(texto_canonico(texto))
                continue
            fijos[bloque] = texto
            resultado["bloques_aprobados_en_longitud"][bloque] = paso["palabras"]
            break
        if bloque not in fijos:
            resultado["estado"] = "BLOQUE_RECHAZADO_" + bloque.upper()
            resultado["incidencia"] = (
                "El bloque {} no cumplió controles en {} intentos nuevos".format(
                    bloque, max_intentos))
            return resultado
    guion = dict(original)
    guion.update(fijos)
    guion["duracion_objetivo_segundos"] = duracion
    rep = evaluar_guion(guion, duracion)
    words = sum(contar_palabras(guion[x]) for x in BLOQUES)
    segundos = round(words * 60 / velocidad_ppm, 1)
    diferencia = abs(segundos - duracion)
    margen = max(3, duracion * .12)
    if diferencia > margen:
        rep["bloqueos"].append(
            "Duración a {} ppm: {} s fuera de {}±{} s".format(
                velocidad_ppm, segundos, duracion, round(margen, 1)))
    rep["segundos_estimados_velocidad_configurada"] = segundos
    rep["velocidad_narracion_ppm"] = velocidad_ppm
    rep["apto_para_revision_humana"] = rep["apto_para_revision_humana"] and not rep["bloqueos"]
    rep["estado_revision"] = (
        "REVISION_HUMANA_PENDIENTE" if rep["apto_para_revision_humana"]
        else "DEVOLVER_PARA_CORRECCION")
    resultado["guion"] = guion
    resultado["evaluacion"] = rep
    resultado["estado"] = rep["estado_revision"]
    return resultado


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--recuperar", type=Path, required=True)
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--duracion", type=int, default=35)
    ap.add_argument("--velocidad-ppm", type=int, default=150)
    ap.add_argument("--max-intentos", type=int, default=3)
    ap.add_argument("--modelo", default=None)
    args = ap.parse_args()
    try:
        if args.recuperar.resolve() == args.salida.resolve():
            raise ErrorNarrativa("Se prohíbe sobrescribir el archivo fuente")
        if args.salida.exists():
            raise ErrorNarrativa("La salida ya existe; no se sobrescribe")
        registro, original, historial, aprobados, limites = cargar_sexta(
            args.recuperar, args.duracion)
        resultado = reanudar(registro, original, historial, aprobados, limites,
                            duracion=args.duracion,
                            velocidad_ppm=args.velocidad_ppm,
                            max_intentos=args.max_intentos, modelo=args.modelo)
        resultado["fecha_revision"] = datetime.utcnow().isoformat() + "Z"
        args.salida.parent.mkdir(parents=True, exist_ok=True)
        with args.salida.open("x", encoding="utf-8") as f:
            json.dump(resultado, f, ensure_ascii=False, indent=2)
            f.write("\n")
        evaluation = resultado["evaluacion"]
        resumen = {
            "estado": resultado["estado"],
            "gancho_preservado": resultado["bloques_preservados"],
            "historia_palabras": (
                contar_palabras(resultado["guion"]["historia"])
                if resultado["guion"] else None),
            "palabras_totales": evaluation["palabras"] if evaluation else None,
            "segundos_estimados": (
                evaluation["segundos_estimados_velocidad_configurada"]
                if evaluation else None),
            "velocidad_ppm": args.velocidad_ppm,
            "intentos_nuevos": len(resultado["historial_bloques"]) - len(historial),
            "bloqueos": evaluation["bloqueos"] if evaluation else [],
            "advertencias": evaluation["advertencias"] if evaluation else [],
            "incidencia": resultado.get("incidencia"),
            "archivo_guardado": str(args.salida),
            "publicacion_automatica_autorizada": False,
        }
        print(json.dumps(resumen, ensure_ascii=False, indent=2))
        return 0 if resultado["estado"] == "REVISION_HUMANA_PENDIENTE" else 2
    except (ErrorNarrativa, OSError, ValueError) as exc:
        print("Error de recuperación narrativa: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
