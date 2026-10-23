#!/usr/bin/env python3
"""Barriga IA: agente local de ingeniería, sin servidor ni ejecución arbitraria.

La cola es LOCAL y los resultados permanecen en local-data/. ChatGPT puede
revisar cambios de código en GitHub, pero no tiene acceso directo a esta cola.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import uuid
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "local-data" / "agente_colaborativo.sqlite3"
ACTIONS = ("diagnostico", "pruebas", "evaluar_ollama", "auditoria_narrativa", "regresion_narrativa")
MODEL = "qwen2.5-coder:14b"


def connect(db=DB):
    db = Path(db)
    db.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(db), timeout=15)
    connection.execute("""CREATE TABLE IF NOT EXISTS tareas
        (id TEXT PRIMARY KEY, accion TEXT NOT NULL, entrada TEXT NOT NULL,
         estado TEXT NOT NULL, resultado TEXT, creado TEXT NOT NULL,
         actualizado TEXT NOT NULL)""")
    connection.commit()
    return connection


def stamp():
    return datetime.now(timezone.utc).isoformat()


def enqueue(con, accion, entrada=""):
    if accion not in ACTIONS:
        raise ValueError("Accion no autorizada")
    if len(entrada) > 800:
        raise ValueError("Entrada demasiado larga")
    ident = "BI-" + uuid.uuid4().hex[:16]
    now = stamp()
    with con:
        con.execute("INSERT INTO tareas VALUES (?,?,?,?,?,?,?)",
                    (ident, accion, entrada, "PENDIENTE", None, now, now))
    return ident


def run_action(accion, entrada, root=ROOT):
    if accion == "diagnostico":
        git = subprocess.run(["git", "status", "--porcelain"], cwd=root,
                             capture_output=True, text=True, timeout=20)
        return {"git_ok": git.returncode == 0,
                "arbol_limpio": git.returncode == 0 and not git.stdout.strip()}
    if accion == "pruebas":
        test = subprocess.run([sys.executable, "-m", "unittest", "discover",
                               "-s", "tests", "-q"], cwd=root,
                              capture_output=True, text=True, timeout=120)
        return {"aprobadas": test.returncode == 0,
                "codigo_salida": test.returncode,
                "resumen": (test.stderr or test.stdout)[-1800:]}
    if accion == "regresion_narrativa":
        # No confiar en conclusiones de Ollama sin pruebas ejecutadas.
        test = subprocess.run(
            [sys.executable, "-m", "unittest", "discover", "-s", "tests",
             "-p", "test_barriga_ia_*.py", "-v"],
            cwd=root, capture_output=True, text=True, timeout=120)
        output = test.stderr + test.stdout
        import re
        match = re.search(r"Ran (\\d+) tests?", output)
        return {"pruebas_superadas": test.returncode == 0,
                "cantidad": int(match.group(1)) if match else None,
                "errores_detectados": test.returncode != 0,
                "resumen": output[-3500:],
                "cambios_aplicados": False}
    if accion == "auditoria_narrativa":
        files = [
            "tools/barriga_ia_continuar.py",
            "tools/barriga_ia_por_bloques.py",
        ]
        snippets = []
        for rel in files:
            source = (root / rel).read_text(encoding="utf-8")
            if rel.endswith("continuar.py"):
                keys = ("def recuperar_gancho", "def recuperar_bloques_previamente_aprobados")
            else:
                keys = ("def detectar_problemas_editoriales",)
            for key in keys:
                start = source.find(key)
                if start < 0:
                    raise ValueError("Falta funcion requerida: " + key)
                end = source.find("\\ndef ", start + 4)
                snippets.append(rel + " / " + key + "\\n" + source[start:end if end >= 0 else None][:3300])
        evidence = "\\n\\n".join(snippets)
        payload = json.dumps({
            "model": MODEL, "stream": False,
            "prompt": (
                "Actua como revisor de codigo Python. Solo puedes atribuir como "
                "evidencia fragmentos incluidos a continuacion. Separa HECHOS "
                "OBSERVABLES de HIPOTESIS. Busca errores al recuperar los bloques "
                "aprobados y falsos positivos del detector de nombres. "
                "Propone pruebas unitarias concretas; no digas que aplicaste parches.\\n"
                + evidence),
            "options": {"num_predict": 750},
        })
        req = Request("http://127.0.0.1:11434/api/generate",
                      data=payload.encode(), headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=180) as resp:
            data = json.load(resp)
        return {"archivos_examinados": files,
                "diagnostico": str(data.get("response", ""))[:15000],
                "cambios_aplicados": False}
    if accion == "evaluar_ollama":
        if not entrada.strip():
            raise ValueError("Se requiere una tarea de evaluacion")
        payload = json.dumps({"model": MODEL, "stream": False,
                              "prompt": ("Analiza este problema del proyecto, sin ejecutar "
                                         "codigo ni afirmar que aplicaste cambios. "
                                         "Responde con un diagnostico y pasos verificables: "
                                         + entrada),
                              "options": {"num_predict": 500}})
        req = Request("http://127.0.0.1:11434/api/generate",
                      data=payload.encode(), headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=180) as resp:
            data = json.load(resp)
        return {"respuesta": str(data.get("response", ""))[:12000],
                "modelo": MODEL, "cambios_aplicados": False}
    raise ValueError("Accion no autorizada")


def run_next(con, root=ROOT):
    # En caso de cierre abrupto, la tarea queda EN_EJECUCION: revisión manual;
    # no reintentar automáticamente trabajos con efectos desconocidos.
    row = con.execute("SELECT id, accion, entrada FROM tareas WHERE estado='PENDIENTE' "
                      "ORDER BY creado, id LIMIT 1").fetchone()
    if row is None:
        return {"estado": "SIN_TAREAS"}
    ident, accion, entrada = row
    with con:
        updated = con.execute("UPDATE tareas SET estado='EN_EJECUCION', actualizado=? "
                              "WHERE id=? AND estado='PENDIENTE'", (stamp(), ident))
    if updated.rowcount != 1:
        return {"estado": "OCUPADO"}
    try:
        result = run_action(accion, entrada, root)
        status = "TERMINADA"
    except Exception as exc:
        result = {"error_tipo": type(exc).__name__,
                  "detalle": str(exc)[:300]}
        status = "FALLIDA"
    with con:
        con.execute("UPDATE tareas SET estado=?, resultado=?, actualizado=? WHERE id=?",
                    (status, json.dumps(result, ensure_ascii=False), stamp(), ident))
    return {"id": ident, "estado": status, "resultado": result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--agregar", choices=ACTIONS)
    group.add_argument("--ejecutar-siguiente", action="store_true")
    group.add_argument("--estado", action="store_true")
    parser.add_argument("--detalle", default="")
    args = parser.parse_args()
    con = connect()
    try:
        if args.agregar:
            result = {"id": enqueue(con, args.agregar, args.detalle), "estado": "PENDIENTE"}
        elif args.ejecutar_siguiente:
            result = run_next(con)
        else:
            result = {"tareas": [dict(zip(("id", "accion", "estado"), row)) for row
                     in con.execute("SELECT id, accion, estado FROM tareas ORDER BY creado DESC LIMIT 20")],
                     "remoto_conectado": False, "publicacion_automatica": False}
        print(json.dumps(result, ensure_ascii=False, indent=2))
    finally:
        con.close()


if __name__ == "__main__":
    main()
