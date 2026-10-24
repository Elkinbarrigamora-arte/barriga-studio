#!/usr/bin/env python3
"""Inventario local y recomendación conservadora para entrenar Barriga IA.

Solo consulta el sistema: NO instala paquetes, NO ejecuta inferencias,
NO modifica modelos, NO instala servicios residentes y NO escribe archivos.
Compatibilidad: Python 3.9+.
"""
import importlib.util
import json
import platform
import re
import shutil
import subprocess
from pathlib import Path


GIB = 1024 ** 3


def _command(argv, seconds=8):
    try:
        result = subprocess.run(
            argv, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=seconds, check=False)
        return result.stdout.strip() if result.returncode == 0 else ""
    except (OSError, subprocess.TimeoutExpired):
        return ""


def _chip_type():
    raw = _command(["system_profiler", "SPHardwareDataType", "-json"], seconds=14)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        nodes = data.get("SPHardwareDataType", [])
        if not isinstance(nodes, list):
            return None
        for node in nodes:
            if not isinstance(node, dict):
                continue
            for key in ("chip_type", "cpu_type"):
                value = node.get(key)
                if isinstance(value, str) and len(value) <= 80:
                    # Evitar incluir campos privados como serie o UUID.
                    return value
    except (ValueError, TypeError):
        pass
    return None


def estrategia(memoria_gib, libre_gib, arquitectura, chip=None):
    """Sugerencia informativa, nunca autorización para entrenar."""
    if not isinstance(arquitectura, str) or arquitectura.lower() != "arm64":
        return {
            "nivel": "hardware_no_confirmado",
            "modelo_experimental": None,
            "accion": "Confirmar salida literal de uname -m y chip antes de elegir runtime",
            "entrenamiento_14b_recomendado": False,
        }
    if not isinstance(memoria_gib, (int, float)) or memoria_gib <= 0:
        return {
            "nivel": "memoria_desconocida",
            "modelo_experimental": None,
            "accion": "Confirmar memoria unificada real",
            "entrenamiento_14b_recomendado": False,
        }
    if not isinstance(libre_gib, (int, float)) or libre_gib < 40:
        return {
            "nivel": "espacio_insuficiente_o_no_comprobado",
            "modelo_experimental": None,
            "accion": "Mantener al menos 40 GiB libres antes de probar datasets/checkpoints",
            "entrenamiento_14b_recomendado": False,
        }
    if memoria_gib < 12:
        familia = "1B-2B"
        nivel = "limitado"
    elif memoria_gib < 24:
        familia = "3B"
        nivel = "experimental_3b_4bit"
    elif memoria_gib < 48:
        familia = "3B-7B"
        nivel = "experimental_7b_condicionado"
    else:
        familia = "7B-14B"
        nivel = "experimental_mayor_sujeto_a_prueba"
    return {
        "nivel": nivel,
        "modelo_experimental": familia,
        "accion": (
            "Medir memoria y rendimiento con un adaptador pequeño en MLX "
            "antes de ampliar el tamaño o programar entrenamiento"
        ),
        "entrenamiento_14b_recomendado": False,
        "chip_declarado": chip,
    }


def _modelos_ollama():
    """Inventario de nombres instalados. No carga modelos ni ejecuta inferencia."""
    if shutil.which("ollama") is None:
        return []
    listado = _command(["ollama", "list"], seconds=10)
    resultado = []
    for linea in listado.splitlines()[1:]:
        partes = linea.split()
        if not partes:
            continue
        nombre = partes[0]
        # No incluir IDs, rutas ni otros metadatos privados del entorno.
        if 1 <= len(nombre) <= 140 and re.fullmatch(r"[A-Za-z0-9_.:/-]+", nombre):
            resultado.append(nombre)
    return resultado


def inventario():
    arquitectura = platform.machine()
    raw = _command(["sysctl", "-n", "hw.memsize"]) if platform.system() == "Darwin" else ""
    memoria = int(raw) / GIB if raw.isdigit() and int(raw) > 0 else None
    try:
        free = round(shutil.disk_usage(str(Path.home())).free / GIB, 2)
    except OSError:
        free = None
    chip = _chip_type() if platform.system() == "Darwin" else None
    mlx = importlib.util.find_spec("mlx") is not None
    mlx_lm = importlib.util.find_spec("mlx_lm") is not None
    return {
        "sistema": platform.system(),
        "macos": platform.mac_ver()[0] or None,
        "arquitectura": arquitectura,
        "chip": chip,
        "memoria_unificada_gib": round(memoria, 2) if memoria else None,
        "almacenamiento_libre_gib": free,
        "mlx_instalado": mlx,
        "mlx_lm_instalado": mlx_lm,
        "ollama_cli_instalado": shutil.which("ollama") is not None,
        "modelos_ollama_instalados": _modelos_ollama(),
        "estrategia": estrategia(memoria, free, arquitectura, chip),
        "salvaguardas": {
            "pesos_modificados": False,
            "servicio_residente_instalado": False,
            "entrenamiento_lanzado": False,
            "trabajos_activos_interrumpidos": False,
            "requiere_validacion_de_datos_y_licencia": True,
        },
        "nota": (
            "Inventario de lectura solamente. La elegibilidad no confirma "
            "que MLX pueda entrenar un modelo específico sin probar "
            "pesos, tokenizador y consumo real de memoria."
        ),
    }


def main():
    print(json.dumps(inventario(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
