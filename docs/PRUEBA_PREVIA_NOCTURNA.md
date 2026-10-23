# Prueba previa obligatoria: Barriga IA + Barriga Studio

Antes de autorizar una noche de trabajo automatizado, debemos tener pruebas y evidencias reales. Esta rama **no modifica el software en producción**, no activa agentes y no toca el LaunchAgent existente.

## Ejecutar desde la carpeta barriga-studio en el Mac

Descargar el archivo de prueba desde esta rama y guardarlo en el Escritorio; inspeccionarlo antes de ejecutarlo.

```bash
curl -fL "https://raw.githubusercontent.com/Elkinbarrigamora-arte/barriga-studio/test/prueba-previa-nocturna-20261022/tools/prueba_integracion.py" -o "$HOME/Desktop/prueba_integracion.py"
python3 "$HOME/Desktop/prueba_integracion.py" --studio "$PWD" --salida "$HOME/Desktop/barriga-prueba.json"
```

El reporte marca las etapas OK, FALLO, NO_PROBADA, PARCIAL y SOLO_DIAGNOSTICO. La prueba de inferencia llama únicamente a Ollama local en 127.0.0.1:11434; no utiliza API de pago. Un código de salida 2 indica que **la cadena completa aún no está demostrada**.

## Portones faltantes antes de trabajo nocturno

- Una instrucción de Studio debe llegar a Barriga IA por un enlace **privado y autenticado** y regresar con una respuesta real.
- Una investigación debe consultar una fuente autorizada, registrar evidencia y recibir evaluación; nunca basta con registrar tareas pendientes.
- Una generación de cinco segundos debe crear un archivo MP4 que se reproduzca, con **movimiento corporal real**, no solo zoom o paneo.
- El supervisor debe registrar y recuperar tareas sin repetirlas; limitar consumo de CPU/RAM, tiempo y reintentos.
- Revisar derechos de uso y privacidad de todas las integraciones externas.
- Requerir autorización antes de activar una jornada nocturna; no activar pagos.

Este script no puede certificar movimiento real ni integración si aún no existen. Conserva el resultado explícito como NO_PROBADO hasta obtener pruebas reales.
