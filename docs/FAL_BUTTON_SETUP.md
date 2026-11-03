# Botón Generar video con fal.ai — prototipo aislado

Esta rama añade un **servidor local adicional**, sin modificar el index.html ni los proyectos locales. El nuevo panel se inyecta en la página **solo** cuando se abre desde este servidor. No cambia la versión publicada ni otros puentes existentes.

## Instalación segura en Mac (sin cambiar de rama)

Desde la misma Terminal con FAL_KEY cargada:

```bash
cd "$HOME/barriga-studio"
git fetch origin feat/fal-generate-button-20261103
git show origin/feat/fal-generate-button-20261103:tools/fal_studio_server.py > tools/fal_studio_server.py
git show origin/feat/fal-generate-button-20261103:assets/fal-video-button.js > assets/fal-video-button.js
.venv/bin/python tools/fal_studio_server.py --studio "$PWD" --port 8877
```

**Revisar primero si existen archivos con esos mismos nombres para no sobrescribirlos.** El servidor abre http://127.0.0.1:8877/. El puerto 8877 evita conflictos habituales con otros servicios; si está ocupado, elegir otro puerto. Para detener: Ctrl+C.

## Uso

1. En el editor, escribe una URL **HTTPS pública** de imagen (no el campo de archivos locales). No copies la URL en formatos Markdown `[https://...](https://...)`.
2. Describe movimiento de 5 segundos.
3. Haz clic en **Generar video (con confirmación de costo)**.
4. Confirma expresamente cada generación: el cálculo estimado del proveedor es US$0,15; no hay todavía un tope automatizado de gasto.
5. Visualiza el MP4 y usa **Abrir MP4 / Guardar como**.

## Limitaciones importantes

- La generación genera cargos por solicitud, incluso si el resultado no es satisfactorio. Falta validar facturación real por cuenta.
- Para impedir ejecuciones involuntarias, no hay reintentos automáticos; una sola solicitud simultánea.
- La clave `FAL_KEY` vive solo en el proceso local, nunca en navegador, HTML versionado o repositorio.
- El servidor escucha solo en 127.0.0.1. Comprueba que usas esa dirección. No abrirlo públicamente.
- El panel solo acepta una imagen alojada bajo HTTPS por URL; la subida de imagen privada/local queda para la siguiente fase.
- Este prototipo no almacena el MP4 en la biblioteca, no genera voz, no mantiene continuidad entre múltiples clips ni incluye acceso remoto. **No equivale todavía a la integración final en producción.**
- La duración solicitada es 120 fotogramas / 24 fps, que apunta a 5 segundos; la duración real puede variar.
- Es prudente respaldar proyectos antes de probar y evitar ejecutar varias copias del servidor.
