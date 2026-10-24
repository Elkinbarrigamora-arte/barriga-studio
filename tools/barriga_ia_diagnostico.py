#!/usr/bin/env python3
"""Diagnóstico local sin cambios de modelo, sin pagos ni lecturas de archivos privados."""
import json
import platform
import subprocess
from urllib.error import URLError
from urllib.request import Request, urlopen

OLLAMA = "http://127.0.0.1:11434"
MODELO = "qwen2.5-coder:14b"


def _ollama(ruta, datos=None):
    cuerpo = (json.dumps(datos).encode("utf-8") if datos is not None else None)
    req = Request(
        OLLAMA + ruta,
        data=cuerpo,
        headers={"Content-Type": "application/json"} if cuerpo else {},
        method="POST" if cuerpo else "GET",
    )
    try:
        with urlopen(req, timeout=3) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (URLError, OSError, TimeoutError, ValueError):
        return None


def _memoria_mac():
    if platform.system() != "Darwin":
        return None
    try:
        p = subprocess.run(
            ["sysctl", "-n", "hw.memsize"],
            capture_output=True, text=True, check=True, timeout=3,
        )
        return int(p.stdout.strip())
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def diagnosticar(modelo=MODELO):
    sistema = platform.system()
    info = _ollama("/api/ps")
    detalles = _ollama("/api/show", {"model": modelo})
    lista = info.get("models", []) if isinstance(info, dict) else []
    cargados = []
    for m in lista:
        if not isinstance(m, dict):
            continue
        cargados.append({
            "nombre": m.get("name", ""),
            "memoria_modelo_bytes": m.get("size"),
            "memoria_gpu_bytes": m.get("size_vram"),
        })
    detalle = detalles.get("details", {}) if isinstance(detalles, dict) else {}
    cuantizacion = detalle.get("quantization_level") if isinstance(detalle, dict) else None
    return {
        "sistema": sistema,
        "arquitectura": platform.machine(),
        "ram_total_bytes": _memoria_mac(),
        "ollama_responde": info is not None or detalles is not None,
        "modelo_consultado": modelo,
        "cuantizacion_reportada": cuantizacion,
        "modelos_cargados": cargados,
        "metal": ("Compatible con macOS; uso real no verificado por este "
                  "diagnóstico" if sistema == "Darwin" else
                  "No aplica a este sistema"),
        "nota": ("size_vram informa memoria de modelo en GPU cuando Ollama "
                 "la reporta; no certifica por sí solo un backend Metal"),
    }


def main():
    print(json.dumps(diagnosticar(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
