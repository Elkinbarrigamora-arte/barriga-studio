#!/usr/bin/env python3
"""Puente LOCAL de Barriga IA: diagnóstico y continuación segura de narrativa.

No escucha puertos, no sube datos a GitHub, no publica y no ejecuta en segundo
plano. El propietario lo inicia manualmente en la Mac.
"""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
MOTOR = ROOT / "tools" / "barriga_ia_continuar.py"


def estado(root=ROOT):
    """Información local sin exponer guiones ni secretos."""
    try:
        with socket.create_connection(("127.0.0.1", 11434), timeout=1):
            ollama = True
    except OSError:
        ollama = False
    prueba = root / "local-data" / "narrativa" / "septima-prueba.json"
    fragmentos = []
    if prueba.is_file():
        try:
            obj = json.loads(prueba.read_text(encoding="utf-8"))
            fragmentos = [
                x for x in ("gancho", "historia_1", "historia_2", "cierre")
                if isinstance(obj.get("bloques_conservados", {}), dict)
                and isinstance(obj["bloques_conservados"].get(x), str)
            ]
        except (OSError, ValueError, TypeError):
            pass
    return {"modo": "LOCAL_MANUAL", "ollama_disponible": ollama,
            "archivo_septima_existe": prueba.is_file(),
            "fragmentos_detectados": fragmentos,
            "publicacion_automatica": False, "red_publica": False}


def continuar(origen, salida, duracion=35, max_intentos=2, root=ROOT):
    origen, salida = Path(origen).resolve(), Path(salida).resolve()
    carpeta = (root / "local-data" / "narrativa").resolve()
    if carpeta not in origen.parents or carpeta not in salida.parents:
        raise ValueError("Solo se permiten informes dentro de local-data/narrativa")
    if not origen.is_file():
        raise ValueError("No existe el informe de entrada")
    if salida.exists() or origen == salida:
        raise ValueError("La salida ya existe o coincide con el origen")
    if not 20 <= duracion <= 60 or max_intentos not in (1, 2):
        raise ValueError("Duracion o numero de intentos no permitido")
    return subprocess.run([
        sys.executable, str(root / "tools" / "barriga_ia_continuar.py"),
        "--desde", str(origen), "--salida", str(salida),
        "--duracion", str(duracion), "--max-intentos", str(max_intentos),
    ], cwd=root, check=False).returncode


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    grupo = ap.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--estado", action="store_true")
    grupo.add_argument("--continuar", action="store_true")
    ap.add_argument("--desde", type=Path,
                    default=ROOT / "local-data/narrativa/septima-prueba.json")
    ap.add_argument("--salida", type=Path,
                    default=ROOT / "local-data/narrativa/octava-prueba.json")
    ap.add_argument("--duracion", type=int, default=35)
    ap.add_argument("--max-intentos", type=int, default=2)
    args = ap.parse_args()
    if args.estado:
        print(json.dumps(estado(), ensure_ascii=False, indent=2))
        return 0
    try:
        return continuar(args.desde, args.salida, args.duracion, args.max_intentos)
    except ValueError as exc:
        print("Puente detenido: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
