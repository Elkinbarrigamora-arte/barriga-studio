# B STUDIO Élite · Puente unificado de guiones y videos

## Estado real

Este puente está implementado en una rama protegida. **Aún no está publicado en la aplicación web oficial.** Sirve la interfaz de la Mac sin modificar su archivo index.html ni sus proyectos.

### Comportamiento verificable

- El mismo servidor local incluye el editor, Barriga IA, la galería MP4 y el registro de motores.
- Guiones: consulta el inventario Ollama real y, con `--model auto` (predeterminado), selecciona únicamente un modelo de texto ya instalado, priorizando `qwen2.5-coder:14b`. No descarga modelos automáticamente. El botón permanece deshabilitado si no está disponible. El contenido se genera únicamente cuando lo solicita el usuario y no sustituye texto previo sin confirmación.
- Galería: reproduce y descarga MP4/MOV que existan realmente en la carpeta `~/Movies/BarrigaStudio`; ofrece HTTP Range para la reproducción en Safari. El botón **Importar MP4 existente** copia localmente el archivo seleccionado (máximo 250 MB) sin sobrescribir ni borrar el original. La aceptación básica de un MP4 no equivale a validar códecs o movimiento real; para eso se utiliza FFprobe.
- PoYo: recupera solamente un task_id preexistente usando las credenciales de la CLI local. No genera otro video ni gasta créditos; HTTP 401/403 se presenta como error y no como éxito.
- Voces: con `--voices-dir` apuntando a la carpeta real del banco ya existente, muestra y reproduce archivos WAV/MP3/M4A/AAC desde Safari, sin copiarlos ni volver a generarlos. Si no se indica la carpeta, muestra el bloqueo explícito.
- Motores: Barriga IA (Ollama), PoYo (recuperación de video existente), voces (carpeta de audios), fal.ai (pendiente de conexión), Draw Things/Kling (pendiente de validación). El catálogo no declara que todo esté operativo.
- Seguridad: limitado a 127.0.0.1, token de sesión, no lectura arbitraria de archivos, no enlaces simbólicos, sin claves en el repositorio.

### Integración en la ÚNICA plataforma oficial B STUDIOS ÉLITE

El equipo tiene su propia versión avanzada en `~/barriga-studio`, servida
en **http://127.0.0.1:8766/studio**. Esta dirección se conserva.

La rama GitHub no contiene todo el servidor central de la Mac,
`tools/puente_central.py`, ni sus proyectos y recursos locales.
No fusionar la rama con la versión antigua de `main` ni copiar archivos
de la Mac a repositorios públicos.

El lanzador `tools/bstudio_elite_start.py` utiliza un gateway privado:
inicia el puente central ORIGINAL en un puerto interno, muestra exactamente
la MISMA ruta oficial /studio en 8766 y añade el panel de guiones, videos y
voces sin editar el código del puente ni sus archivos de proyectos.
Preserva y reenvía las rutas, métodos HTTP y APIs de la aplicación existente.

**Una sola URL visible, una sola plataforma; dos procesos internos.**

#### Activación protegida

Si está abierto el servidor 8766 en una Terminal, verifica primero que no
haya trabajos en curso y detén ese servidor con Ctrl+C. El instalador jamás
detiene un proceso ajeno automáticamente.

```bash
BRIDGE_DIR="$HOME/barriga-studio-bridge-elite"
if [ -d "$BRIDGE_DIR/.git" ]; then
  git -C "$BRIDGE_DIR" pull --ff-only || exit 1
elif [ ! -e "$BRIDGE_DIR" ]; then
  git clone --depth 1 --single-branch \
    --branch feat/bstudio-elite-recovery-qa-20261110 \
    https://github.com/Elkinbarrigamora-arte/barriga-studio.git "$BRIDGE_DIR" || exit 1
else
  echo "La carpeta de integración existe y no es un repositorio Git. No se modificó." >&2
  exit 1
fi
python3 "$BRIDGE_DIR/tools/bstudio_elite_start.py" \
  --studio "$HOME/barriga-studio" \
  --media-dir "$HOME/Movies/BarrigaStudio" \
  --task-id 0AHQMX2G2T4ZZE6O
```

**Única dirección de Safari:** http://127.0.0.1:8766/studio

No cambia el origen del navegador: se preservan los proyectos guardados en
localStorage de Safari. No inicia nuevas generaciones ni cobra créditos.
Cuando la Terminal se cierre, el proceso iniciado también se detendrá.
No afirmar ejecución permanente mientras el computador está apagado.

Para usar el banco de voces existente agrega `--voices-dir "RUTA_REAL_DEL_BANCO"`.
Si no se encuentra la carpeta, se informa el error en vez de regenerar las voces.

Si alguno de los puertos ya está ocupado o el central original no responde
en /studio, el lanzador se bloquea sin detener trabajos ajenos.
La generación audiovisual final aún necesita verificación con archivos,
motores y voces auténticos en la Mac.

### Antes de publicar

1. Confirmar la última versión local real y conservar respaldo verificable de proyectos.
2. Probar Ollama en la Mac y comprobar generación/guardado de un guion nuevo.
3. Descargar y reproducir un MP4 real de PoYo, resolviendo el HTTP 403 con el proveedor si persiste.
4. Conectar el banco de voces existente y verificar pista de audio en la exportación.
5. Verificar una generación real por cada adaptador de video adicional antes de habilitarlo.
6. Ejecutar la suite completa y verificar la URL oficial con plan de reversión.

No activar APIs pagadas ni publicar una rama candidata como versión final sin cumplir los puntos críticos.

### Reversión en la Mac y registro de aceptación

1. **Antes de detener el Studio:** confirma que no haya trabajos en curso. Registra de forma privada la versión del checkout del gateway, la carpeta, el intérprete y el comando con los que se inició el servidor original, sin volcar variables de entorno ni credenciales. Respalda los cambios locales, proyectos, estado persistente y recursos que usa esa instalación. Conserva aparte cualquier exportación de proyectos del navegador: no contiene por sí sola los archivos de la Mac.
2. **Comprueba que el respaldo se pueda restaurar** en un destino aislado antes de cambiar el proceso activo. No borres datos del perfil habitual ni importes un respaldo de prueba a las colas o proyectos originales.
3. **Valida la misma URL oficial tras iniciar el gateway:** abre proyectos previos y verifica su estado tras cerrar y reabrir Safari; prueba un guion con un modelo Ollama instalado; reproduce una voz existente; recupera el ID PoYo ya creado y comprueba que el archivo se abre y se descarga. Registra el tamaño, la duración y el SHA-256 del MP4 sin publicar enlaces firmados. Marca como pendientes los controles sin una prueba real y comprueba que estén deshabilitados. Para el reel final, escucha la voz en español, revisa su sincronización y comprueba que el MP4 descargado conserva los 35 segundos y ambas pistas.
4. **Si la verificación falla:** comprueba primero que ningún trabajo nuevo dependa del gateway. Si está inactivo, detén solo la sesión del lanzador que acabas de iniciar y vuelve a ejecutar el comando original en su carpeta. Verifica que `http://127.0.0.1:8766/studio` vuelve a mostrar la aplicación y los proyectos previos en el perfil habitual. No sustituyas el `index.html` ni limpies el almacenamiento. No restaures datos en el perfil habitual a ciegas: si hubo cambios de datos, compara primero el estado actual con la copia para no perder trabajos posteriores.

Registra la comprobación de cada paso junto al commit probado. Los resultados del servidor simulado y de CI no cuentan como verificación de la Mac.

### Pruebas automáticas

- Python: python3 -m unittest discover -s tests -p 'test_bstudio_*.py' -v
- JavaScript: node --check assets/bstudio-runtime.js
- Playwright: npm run test:ui y npm run test:bridge
- FFmpeg: python3 tests/ffmpeg_smoke.py

Las pruebas de CI no sustituyen la validación con la Mac física.
