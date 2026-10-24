#!/usr/bin/env python3
"""Barriga IA — continuar una prueba rechazada sin repetir el gancho aprobado.

V0.7: historia en dos microescenas, cierre separado, Ollama local solamente.
No publica ni sustituye los archivos de entrada. Python 3.9+.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

from barriga_ia_narrativa import (
    ErrorNarrativa, MODELO, contar_palabras, evaluar_guion,
)
from barriga_ia_por_bloques import (
    generar_texto_local, limites_de_bloques, detectar_problemas_editoriales,
)

ETAPAS = ("historia_1", "historia_2", "cierre")


def recuperar_gancho(path):
    """Leer el último gancho aceptado en un informe sin asumir guion terminado."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("guion_original"), dict):
        raise ErrorNarrativa("El archivo no contiene el borrador original recuperable")
    original = data["guion_original"]
    if original.get("naturaleza") not in ("ficcion", "dramatizacion"):
        raise ErrorNarrativa("No se reescriben materiales factuales sin verificar")
    if original.get("nicho") == "noticias":
        raise ErrorNarrativa("No se reescriben noticias")
    candidatos = [
        item for item in data.get("historial_bloques", [])
        if isinstance(item, dict) and item.get("bloque") == "gancho"
        and item.get("aceptable_para_ensamblaje") is True
        and isinstance(item.get("texto"), str)
    ]
    if candidatos:
        gancho = candidatos[-1]["texto"].strip()
    else:
        # Los informes V0.7 de continuación guardan el gancho aprobado
        # en bloques_conservados, no en historial_bloques.
        conservados = data.get("bloques_conservados", {})
        gancho = conservados.get("gancho") if isinstance(conservados, dict) else None
        if not isinstance(gancho, str) or not gancho.strip():
            raise ErrorNarrativa("No hay un gancho validado recuperable en este archivo")
        gancho = gancho.strip()
    a, b = limites_de_bloques(35)["gancho"]
    if not a <= contar_palabras(gancho) <= b:
        raise ErrorNarrativa("El gancho recuperado no cumple el rango 5 a 8")
    if detectar_problemas_editoriales(gancho, original, "gancho"):
        raise ErrorNarrativa("El gancho recuperado contiene indicios editoriales")
    return original, gancho


def limites_escenas(duracion):
    """Dos fragmentos cuyo total cae en el intervalo ya fijado para historia."""
    if duracion < 20 or duracion > 60:
        raise ErrorNarrativa("Duración no válida")
    minimo, maximo = limites_de_bloques(duracion)["historia"]
    mitad_min = minimo // 2
    mitad_max = maximo // 2
    return {
        "historia_1": (mitad_min, mitad_max),
        "historia_2": (minimo - mitad_min, maximo - mitad_max),
        "cierre": limites_de_bloques(duracion)["cierre"],
    }


def armar_instruccion(etapa, gancho, escritos, original, premisa, limites,
                     intento_previo=None):
    lo, hi = limites[etapa]
    permitidos = [
        item.get("nombre") for item in original.get("personajes", [])
        if isinstance(item, dict) and isinstance(item.get("nombre"), str)
    ]
    if etapa == "historia_1":
        tarea = ("Primera mitad del desarrollo: mostrar la carta y la fecha de ayer "
                 "con una acción visible; no resolver aún el misterio.")
        contexto = {"gancho": gancho}
    elif etapa == "historia_2":
        tarea = ("Segunda mitad del desarrollo: continuar inmediatamente la acción "
                 "previa con causa y consecuencia; preparar una revelación, "
                 "sin resolverla ni inventar nuevos protagonistas.")
        contexto = {"gancho": gancho, "desarrollo_previo": escritos["historia_1"]}
    else:
        tarea = ("Cerrar el conflicto mediante una revelación visible, concreta e "
                 "inesperada; sin moraleja genérica ni añadir personajes.")
        contexto = {"gancho": gancho,
                    "historia": escritos["historia_1"] + " " + escritos["historia_2"]}
    contenido = {
        "premisa_que_debe_respetarse": premisa,
        "personajes_de_referencia": permitidos,
        "contexto_continuidad": contexto,
        "tarea": tarea,
    }
    feedback = ""
    if intento_previo:
        feedback = (
            " INTENTO ANTERIOR RECHAZADO: "
            + json.dumps({
                "palabras": intento_previo.get("palabras"),
                "motivos": intento_previo.get("motivos_rechazo", []),
                "NO_repetir_texto": intento_previo.get("texto", "")[:130],
            }, ensure_ascii=False))
    return (
        "Escribe SOLO la parte {} de un microguion de suspenso en español colombiano. "
        "OBLIGATORIO ENTRE {} Y {} PALABRAS. Un solo párrafo. "
        "No repitas textos descartados, no agregues a Pepe ni nombres nuevos, "
        "no introduzcas hechos no preparados por la premisa. "
        "NO redactes un guion completo ni expliques tu trabajo. "
        "Solo JSON con un único campo texto. "
        "Datos: {}{}".format(
            etapa.upper(), lo, hi,
            json.dumps(contenido, ensure_ascii=False), feedback)
    )


def recuperar_bloques_previamente_aprobados(path, original, gancho, duracion):
    """Reanudar exclusivamente fragmentos aceptados en el informe anterior."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    previos = data.get("bloques_conservados", {})
    if not isinstance(previos, dict) or previos.get("gancho") != gancho:
        return {}
    limites = limites_escenas(duracion)
    recuperados = {}
    for etapa in ETAPAS:
        if etapa not in previos:
            break  # No saltar etapas ni confiar en fragmentos posteriores aislados.
        texto = previos[etapa]
        if not isinstance(texto, str):
            break
        minimo, maximo = limites[etapa]
        bloque = "cierre" if etapa == "cierre" else "historia"
        if not (minimo <= contar_palabras(texto) <= maximo):
            break
        if detectar_problemas_editoriales(texto, original, bloque):
            break
        recuperados[etapa] = texto
    return recuperados


def continuar_en_escenas(original, gancho, premisa, duracion=35, modelo=MODELO,
                         max_intentos=2, generador=None, bloques_previos=None):
    if generador is None:
        generador = generar_texto_local
    if max_intentos not in (1, 2):
        raise ErrorNarrativa("Máximo uno o dos intentos por fragmento")
    if original.get("naturaleza") not in ("ficcion", "dramatizacion"):
        raise ErrorNarrativa("La continuación no admite materiales factuales")
    limites = limites_escenas(duracion)
    historia = dict(bloques_previos or {})
    reporte = {
        "guion_original": original,
        "gancho_recuperado": gancho,
        "bloques_conservados": {"gancho": gancho, **historia},
        "limites": {k: list(v) for k, v in limites.items()},
        "historial_intentos": [],
        "guion": None,
        "evaluacion": None,
        "estado": "INCOMPLETO",
        "publicacion_automatica_autorizada": False,
        "revision_semantica_realizada": False,
    }
    for etapa in ETAPAS:
        if etapa in historia:
            continue
        anterior = None
        valido = False
        for numero in range(1, max_intentos + 1):
            prompt = armar_instruccion(etapa, gancho, historia, original,
                                      premisa, limites, anterior)
            try:
                if generador is generar_texto_local:
                    texto = generador(
                        prompt, modelo=modelo,
                        num_predict=110 if etapa != "cierre" else 70,
                        temperatura=0.2 if numero == 1 else 0.6,
                    )
                else:
                    texto = generador(prompt, modelo=modelo)
                numero_palabras = contar_palabras(texto)
                minimo, maximo = limites[etapa]
                razones = []
                if not minimo <= numero_palabras <= maximo:
                    razones.append("Longitud {} fuera de {} a {} palabras".format(
                        numero_palabras, minimo, maximo))
                bloque_para_revision = (
                    "cierre" if etapa == "cierre" else "historia")
                razones += detectar_problemas_editoriales(
                    texto, original, bloque_para_revision, anterior)
                detalle = {
                    "etapa": etapa, "intento": numero, "texto": texto,
                    "palabras": numero_palabras,
                    "motivos_rechazo": razones,
                    "valido_en_estructura": not razones,
                }
            except (ErrorNarrativa, OSError, ValueError) as exc:
                detalle = {
                    "etapa": etapa, "intento": numero, "texto": "", "palabras": 0,
                    "motivos_rechazo": [str(exc)],
                    "valido_en_estructura": False,
                }
            reporte["historial_intentos"].append(detalle)
            anterior = detalle
            if detalle["valido_en_estructura"]:
                historia[etapa] = detalle["texto"]
                reporte["bloques_conservados"][etapa] = detalle["texto"]
                valido = True
                break
        if not valido:
            reporte["estado"] = "FRAGMENTO_RECHAZADO_" + etapa.upper()
            reporte["incidencia"] = (
                "El fragmento {} no cumplió tras {} intentos".format(
                    etapa, max_intentos))
            return reporte

    final = dict(original)
    final["gancho"] = gancho
    final["historia"] = historia["historia_1"] + " " + historia["historia_2"]
    final["cierre"] = historia["cierre"]
    final["duracion_objetivo_segundos"] = duracion
    final_evaluado = evaluar_guion(final, duracion)
    reporte["guion"] = final
    reporte["evaluacion"] = final_evaluado
    reporte["estado"] = final_evaluado["estado_revision"]
    return reporte


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--desde", type=Path, required=True,
                    help="Informe anterior con un gancho aceptado")
    ap.add_argument("--salida", type=Path, required=True)
    ap.add_argument("--duracion", type=int, default=35)
    ap.add_argument("--modelo", default=MODELO)
    ap.add_argument("--max-intentos", type=int, default=2)
    ap.add_argument("--premisa", default=(
        "Daniel halla una carta de su hermano desaparecido hace treinta "
        "años. La carta fue escrita ayer; revelar el secreto mediante una acción."))
    opts = ap.parse_args()
    try:
        if opts.desde.resolve() == opts.salida.resolve():
            raise ErrorNarrativa("El archivo original nunca se puede sobrescribir")
        if opts.salida.exists():
            raise ErrorNarrativa("La salida ya existe; usar otro nombre")
        original, gancho = recuperar_gancho(opts.desde)
        previos = recuperar_bloques_previamente_aprobados(opts.desde, original, gancho, opts.duracion)
        resultado = continuar_en_escenas(
            original, gancho, opts.premisa, duracion=opts.duracion,
            modelo=opts.modelo, max_intentos=opts.max_intentos,
            bloques_previos=previos)
        resultado["fecha_revision"] = datetime.utcnow().isoformat() + "Z"
        opts.salida.parent.mkdir(parents=True, exist_ok=True)
        with opts.salida.open("x", encoding="utf-8") as target:
            json.dump(resultado, target, indent=2, ensure_ascii=False)
            target.write("\n")
        ultimo = resultado["historial_intentos"][-1] if resultado["historial_intentos"] else None
        evaluacion = resultado.get("evaluacion") or {}
        resumen = {
            "estado": resultado["estado"],
            "gancho_reutilizado": gancho,
            "etapas_aprobadas_en_extensión": list(resultado["bloques_conservados"]),
            "llamadas_ollama": len(resultado["historial_intentos"]),
            "palabras_finales": evaluacion.get("palabras"),
            "segundos_estimados": evaluacion.get("segundos_estimados"),
            "objetivo_segundos": opts.duracion,
            "ultimo_fragmento_rechazado": ultimo if resultado.get("incidencia") else None,
            "bloqueos": evaluacion.get("bloqueos", []),
            "advertencias": evaluacion.get("advertencias", []),
            "archivo_guardado": str(opts.salida),
            "apto_para_revision_humana": evaluacion.get("apto_para_revision_humana", False),
            "publicacion_automatica_autorizada": False,
        }
        print(json.dumps(resumen, indent=2, ensure_ascii=False))
        return 0 if resumen["apto_para_revision_humana"] else 2
    except (ErrorNarrativa, OSError, ValueError, TypeError) as exc:
        print("Error en continuación: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
