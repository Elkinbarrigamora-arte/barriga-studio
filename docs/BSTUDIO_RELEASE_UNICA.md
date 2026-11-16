# B STUDIO Élite — Política de versión única y publicación controlada

## Objetivo
Una sola aplicación oficial de Barriga Studio, con una única URL de producción y una única versión marcada como vigente. Las ramas de GitHub, copias de seguridad y entornos de prueba son **internos** y no deben presentarse al usuario como versiones alternativas.

## Fuente de verdad
1. **Producción actual:** mantener activa la última versión desplegada hasta que la candidata esté completamente comprobada.
2. **Mac del propietario:** contiene modificaciones y motores que todavía no están reflejados en GitHub; su inventario y respaldo son pasos imprescindibles.
3. **GitHub `main`:** será el código fuente canónico después de reconciliar los archivos reales, revisar secretos y fusionar la candidata verificada.
4. **Proyectos y voces:** datos persistentes separados del código; nunca reemplazar ni borrar por una actualización.

## Puertas obligatorias antes de publicar
- [x] 96 pruebas unitarias Python en la candidata PR #10 (GitHub Actions).
- [x] 69 pruebas de navegador del editor en Chromium.
- [x] 40 pruebas del puente integrado en Chromium + WebKit.
- [x] 24 pruebas de la misma ruta original `/studio` con overlay en Chromium + WebKit.
- [x] 1 smoke test audiovisual FFmpeg con medios sintéticos.
- [ ] Auditoría completa de los cambios que solo existen en la Mac, conservando archivos no versionados.
- [ ] Copia de seguridad restaurable y prueba de restauración (incluido almacenamiento de proyectos).
- [ ] Inventario de voces existentes, licencias e identidad de personajes, sin volver a crearlas.
- [ ] Recuperar el archivo real de la tarea PoYo `0AHQMX2G2T4ZZE6O` sin nuevo cargo.
- [ ] Generación de escenas reales, continuidad, descarga y montaje real de un reel de 35 segundos con voz.
- [ ] Pruebas de todos los controles de la versión desplegable, sin botones rotos ni simulación de funciones no conectadas.
- [ ] Seguridad, autenticación, persistencia tras cerrar/reabrir, comprobación de gastos y despliegue con rollback.
- [ ] Comprobación posterior al despliegue de la URL oficial y los proyectos existentes.

**Regla:** si una casilla crítica está pendiente o falla, NO se publica ni se declara una versión final.

## Contrato de evidencia audiovisual
- Un estado de proyecto al 100 %, `final=true` o “listo para descargar” no basta por sí solo para afirmar que existe un MP4.
- La aplicación debe distinguir explícitamente entre **montaje de imágenes con movimiento de cámara** y **video generado por un motor neuronal**.
- Solo declarar un MP4 disponible cuando exista un archivo real no vacío, con ruta/URL verificable, tamaño y SHA-256 registrados, y FFprobe confirme contenedor, pista de video, duración y pista de audio cuando corresponda.
- La señal de audio no demuestra que el diálogo sea inteligible: la revisión de voz y sincronización sigue siendo una puerta separada.
- La sincronización de proyectos debe conservar un identificador estable e idempotencia. No crear copias automáticas ni borrar/reconciliar originales sin comparar primero sus revisiones y recursos.

## Auditoría CI — 16-nov-2026

### Candidata PR #10
- Rama: `feat/bstudio-elite-recovery-qa-20261110`.
- HEAD verificado: `37cc4d36132f6a64cb78831c79853938af87823d`.
- `main` verificado: `a07670c566b6c3cb04f387a553b80fffeacb08a9`; la candidata está 73 commits por delante y 0 por detrás.
- GitHub Actions run **43099601405**, completado con éxito el 11-nov-2026: 96 pruebas Python + 69 Chromium + 40 Chromium/WebKit + 24 Chromium/WebKit + 1 smoke FFmpeg sintético = **230 comprobaciones automatizadas**.
- El smoke FFmpeg usa medios sintéticos. Las pruebas de navegador usan fixtures/simulaciones del servidor; no certifican la Mac, sus voces, sus archivos ni el motor neuronal real.

### Propuesta hija PR #11 — no integrada
- Rama: `fix/bstudio-reel-track-qa-20261111`; HEAD `c6a368030ac33b0b6eb627d6cc4fb655d7360b91`.
- GitHub Actions run **43074604284**, completado con éxito el 11-nov-2026: 32 pruebas Python + 71 Chromium + 1 smoke FFmpeg sintético = **104 comprobaciones** en esa rama.
- Aporta validación de redirecciones/hosts PoYo, verificación FFprobe antes de conservar el archivo, rechazo de IDs de tarea discordantes, publicación atómica sin sobrescritura, SHA-256 y comprobación independiente de duración/señal de audio.
- Esta ejecución es independiente de la suite PR #10. La rama hija comparte un ancestro anterior y está divergida respecto del HEAD actual de PR #10 (8 commits por delante y 45 por detrás desde el ancestro común). No contar sus pruebas como integración certificada ni fusionarla directamente: reconciliar los cambios sobre el HEAD actual de PR #10 y volver a ejecutar la suite completa.

## Protocolo de Mac
El código de la Mac tiene cambios locales modificados y archivos sin seguimiento. No ejecutar `git reset --hard`, `git clean -fd`, `git checkout` sobre la carpeta principal, ni sobrescribir `index.html` o voces; usar un entorno separado y respaldo comprobado.

El script `tools/bstudio_mac_preflight.py` hace un inventario local de solo lectura de Git, FFmpeg, Node, carpetas de motores y puertos. El script no lee claves ni modifica datos, pero no sustituye pruebas reales.

## Etiquetado y reversión
- Identificador único de release: `BSTUDIO-ELITE-YYYYMMDD-N`.
- Cambios a `main` mediante revisión y CI aprobada; fusionar solo tras reconciliar la Mac.
- Despliegue sobre URL existente, nunca mediante una segunda web paralela.
- Antes de desplegar: snapshot de código, datos, esquemas, trabajos y referencias de proyecto.
- Después de desplegar: prueba funcional y rollback disponible para restaurar código y datos en caso de regresión.
- Mantener registro de compilación, hash Git, pruebas, fecha, estado, proveedor y presupuesto.

## Estado actual
**CANDIDATA EN REVISIÓN. NO PUBLICADA.** La candidata PR #10 supera 230 comprobaciones automatizadas de CI. La propuesta hija PR #11 tiene 104 comprobaciones propias, pero sigue separada y requiere reconciliación. La versión local de Mac, los cambios no publicados, las voces existentes, el MP4 PoYo real, el reel real de 35 segundos, la persistencia y el rollback todavía requieren verificación. No fusionar ni desplegar hasta completar todas las puertas críticas.
