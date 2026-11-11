# B STUDIO Élite · Puente unificado de guiones y videos

## Estado real

Este puente está implementado en una rama protegida. **Aún no está publicado en la aplicación web oficial.** Sirve la interfaz de la Mac sin modificar su archivo index.html ni sus proyectos.

### Comportamiento verificable

- El mismo servidor local incluye el editor, Barriga IA, la galería MP4 y el registro de motores.
- Guiones: consulta el inventario Ollama real (modelo qwen2.5-coder:14b). El botón permanece deshabilitado si no está disponible. El contenido se genera únicamente cuando lo solicita el usuario y no sustituye texto previo sin confirmación.
- Galería: reproduce y descarga MP4/MOV que existan realmente en la carpeta ~/Movies/BarrigaStudio; ofrece HTTP Range para la reproducción en Safari.
- PoYo: recupera solamente un task_id preexistente usando las credenciales de la CLI local. No genera otro video ni gasta créditos; HTTP 401/403 se presenta como error y no como éxito.
- Motores: Barriga IA (Ollama), PoYo (recuperación de video existente), voces (carpeta de audios), fal.ai (pendiente de conexión), Draw Things/Kling (pendiente de validación). El catálogo no declara que todo esté operativo.
- Seguridad: limitado a 127.0.0.1, token de sesión, no lectura arbitraria de archivos, no enlaces simbólicos, sin claves en el repositorio.

### Inicio de prueba en Mac

Copia el siguiente bloque en Terminal UNA SOLA VEZ. Crea una carpeta independiente y no toca archivos de la versión principal.

```bash
BRIDGE_DIR="$HOME/barriga-studio-bridge-elite"
if [ ! -e "$BRIDGE_DIR" ]; then
  git clone --depth 1 --single-branch \
    --branch feat/bstudio-elite-recovery-qa-20261110 \
    https://github.com/Elkinbarrigamora-arte/barriga-studio.git "$BRIDGE_DIR" || exit 1
fi
python3 "$BRIDGE_DIR/tools/bstudio_unified_bridge.py" \
  --studio "$HOME/barriga-studio" \
  --media-dir "$HOME/Movies/BarrigaStudio" \
  --task-id 0AHQMX2G2T4ZZE6O \
  --port 8781
```

Abre http://127.0.0.1:8781/ en Safari si no abre automáticamente. Puerto 8781 no interfiere con el servidor anterior en 8766. Ctrl+C detiene solamente este puente.

Si la carpeta ~/barriga-studio no es el código más reciente, señala la carpeta correcta con --studio. Una web privada remota puede tener código diferente del repositorio local.

### Antes de publicar

1. Confirmar la última versión local real y conservar respaldo verificable de proyectos.
2. Probar Ollama en la Mac y comprobar generación/guardado de un guion nuevo.
3. Descargar y reproducir un MP4 real de PoYo, resolviendo el HTTP 403 con el proveedor si persiste.
4. Conectar el banco de voces existente y verificar pista de audio en la exportación.
5. Verificar una generación real por cada adaptador de video adicional antes de habilitarlo.
6. Ejecutar la suite completa y verificar la URL oficial con plan de reversión.

No activar APIs pagadas ni publicar una rama candidata como versión final sin cumplir los puntos críticos.

### Pruebas automáticas

- Python: python3 -m unittest discover -s tests -p 'test_bstudio_*.py' -v
- JavaScript: node --check assets/bstudio-runtime.js
- Playwright: npm run test:ui y npm run test:bridge
- FFmpeg: python3 tests/ffmpeg_smoke.py

Las pruebas de CI no sustituyen la validación con la Mac física.
