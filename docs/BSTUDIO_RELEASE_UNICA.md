# B STUDIO Élite — Política de versión única y publicación controlada

**Última revisión:** 17-nov-2026.  
**Estado:** candidata en revisión; no publicada ni fusionada.

## Objetivo y fuente de verdad

Una sola aplicación oficial de Barriga Studio, una sola URL de producción y una sola versión vigente. Las ramas de GitHub y las pruebas internas no son productos alternativos.

1. Mantener activa la producción actual hasta certificar la candidata.
2. La Mac del propietario es fuente de datos y código local: contiene modificaciones que no están en GitHub.
3. No reconciliar la Mac contra Git hasta hacer inventario y respaldo verificable.
4. Los proyectos, voces y medios son datos persistentes; no reemplazarlos ni borrarlos durante una actualización.
5. No exigir entrenamiento de pesos: Barriga IA debe coordinar modelos, memoria, herramientas y validadores existentes.

## Puertas obligatorias antes de publicar

- [x] CI offline de la candidata PR #10: 96 pruebas Python.
- [x] Editor: 69 pruebas Chromium.
- [x] Puente integrado: 40 pruebas Chromium + WebKit.
- [x] URL original `/studio` con overlay: 24 pruebas Chromium + WebKit.
- [x] 1 smoke audiovisual FFmpeg/FFprobe con medios sintéticos.
- [ ] Acceso autenticado a la Mac real y auditoría de cambios locales/no versionados.
- [ ] Respaldo restaurable de código, proyectos, voces y medios; prueba de restauración.
- [ ] Inventario y reproducción del banco de voces existente, sin sustituirlo.
- [ ] Recuperación del task PoYo existente `0AHQMX2G2T4ZZE6O`, sin `submit` ni nueva generación.
- [ ] FFprobe + SHA-256 del MP4 recuperado y confirmación de movimiento real.
- [ ] Reel real de 35 s con voz existente, sincronización y continuidad visual.
- [ ] Persistencia tras cerrar/reabrir, reanudación sin duplicados y notificaciones verificadas.
- [ ] Todos los controles de la aplicación probados; funciones no conectadas deshabilitadas y etiquetadas.
- [ ] Seguridad, rollback restaurable y verificación posterior en la URL oficial.

**Regla:** cualquier puerta crítica pendiente bloquea el merge y el despliegue.

## Contrato de evidencia audiovisual

- `100 %`, `complete=true`, `final=true` o «video listo» no prueban que exista un MP4.
- Distinguir montaje de imágenes con movimiento de cámara de video generado por un motor neuronal.
- Solo mostrar descarga cuando exista un archivo real, no vacío y accesible, con tamaño, SHA-256 y FFprobe satisfactorio.
- FFprobe debe comprobar contenedor MP4, pista de video, dimensiones, duración y pista de audio cuando se requiere voz.
- Medir señal de audio no demuestra habla inteligible; escuchar la voz en español y revisar sincronización son puertas separadas.
- Conservar IDs estables, task_id, versiones y claves de idempotencia. Un timeout de consulta nunca debe enviar otra generación.

## Auditoría de ramas y CI — 17-nov-2026

### PR #10 — candidata principal

- URL: https://github.com/Elkinbarrigamora-arte/barriga-studio/pull/10
- Rama: `feat/bstudio-elite-recovery-qa-20261110`.
- HEAD: `0cf6e7475d8ac627517c76c6cf8504817904f361`.
- `main`: `a07670c566b6c3cb04f387a553b80fffeacb08a9`; comparación actual: 74 commits por delante, 0 por detrás.
- Actions run **43966314947**, ambos jobs exitosos: 96 Python + 69 editor Chromium + 40 puente Chromium/WebKit + 24 ruta `/studio` Chromium/WebKit + 1 FFmpeg sintético = **230 comprobaciones**.
- El log confirma que FFmpeg produjo un MP4 sintético con video y audio de duración exacta. No prueba el MP4 PoYo real, la Mac ni las voces reales.
- PR #10 permanece abierta y en borrador.

### PR #11 — rama fuente, no integrada

- Rama: `fix/bstudio-reel-track-qa-20261111`; HEAD `c6a368030ac33b0b6eb627d6cc4fb655d7360b91`.
- Su CI histórico (run **43074604284**) validó 104 comprobaciones en su propia rama.
- No copiarla directamente: parte de un ancestro anterior y está divergida respecto de la candidata actual.

### PR #13 — reconciliación selectiva y separada

- URL: https://github.com/Elkinbarrigamora-arte/barriga-studio/pull/13
- Rama: `feat/bstudio-recovery-audio-guard-20261116`; base explícita: HEAD actual de PR #10.
- HEAD de código probado: `b3dc4084edf80adad6461ee36aa71ed1f67ce05d`.
- El HEAD puede incluir commits documentales posteriores al código probado; comprobar el SHA del código y el resultado CI por separado. La actualización de esta política no modifica el código de ejecución.
- Actions run **43992043162**, ambos jobs exitosos: 102 Python + 71 editor Chromium + 40 puente Chromium/WebKit + 24 ruta `/studio` Chromium/WebKit + 1 smoke FFmpeg/FFprobe sintético = **238 comprobaciones**.
- El smoke adicional rechazó una narración sintética silenciosa, conservó un MP4 sintético válido y rechazó uno truncado.
- Añade validación de redirecciones/hosts PoYo, coincidencia del task_id, FFprobe obligatorio, SHA-256, publicación atómica sin sobrescritura y duración independiente de las pistas de audio/video.
- PR #13 sigue abierta y en borrador. Sus pruebas no se suman a las 230 de PR #10: son una suite sobre una rama hija.
- Las pruebas usan fixtures y medios sintéticos; no certifican el equipo ni proveedores reales.

## Diagnóstico conectado del estudio

Consulta autenticada de solo lectura del 17-nov-2026:

- El único dispositivo registrado es «Mi computador Windows»: emparejado, pero desconectado y sin último contacto.
- La Mac del estudio no aparece entre los dispositivos registrados.
- Core: `configured=false`, `selected=false`, `enabled=false`, `gatewayConnected=false`, `inferenceVerified=false`; no hay modelo seleccionado.
- La narración local gratuita está disponible como capacidad del dispositivo, pero no prueba que el banco de voces del propietario esté conectado.
- `ownVideoConfigured=false`, `privateVideoReady=false`, `privateSpeechReady=false`.
- La exportación reportada es montaje en navegador con escenas, narración y movimiento de cámara; no presentarla como generación neuronal.

### Estado de un proyecto observado

El proyecto `d525104e-5f1b-42e3-9328-88c6fb8fef26` («Mis últimas gotas para ti», una copia del dispositivo) actualmente informa:

- 6 escenas, todas `mediaType=image`.
- `audioReady=true` y `localNarration=true`.
- `videoPreparation=null`.
- Estado 80 %, `complete=false`, `final=false`, etapa «Escenas listas · falta montar el video».

Esta lectura es un snapshot del proyecto y muestra un estado no final coherente. No demuestra que el defecto de issue #12 esté corregido en el código ni sustituye una prueba de regresión en la Mac.

## Recuperación PoYo y datos

- La consulta de trabajos de Barriga Studio devuelve estados guardados de trabajos de imagen; no consulta el proveedor PoYo ni incluye el task_id solicitado.
- Esto no demuestra que la tarea PoYo no exista. La recuperación requiere la Mac y la CLI autenticada en su llavero.
- El script de PR #13 consulta la misma tarea con `task get`; no usa `submit`. Si la autenticación devuelve 401/403, se detiene sin reintentar generación.
- No descargar hasta validar host/redirecciones. No atribuir a la tarea un archivo preexistente sin confirmación del proveedor.

## Issue #12 — estado falso de «video listo»

Issue: https://github.com/Elkinbarrigamora-arte/barriga-studio/issues/12

Mantenerlo abierto hasta:
1. Añadir una prueba de regresión específica para seis imágenes + narración local + ausencia de MP4.
2. Verificar que el código real nunca emita `complete/final` ni enlace de descarga en ese caso.
3. Probar la ruta real en la Mac y confirmar que el estado solo cambia a exportado/validado tras existir el archivo.

## Protocolo de Mac, release y rollback

- No ejecutar `git reset --hard`, `git clean -fd`, checkout sobre la carpeta principal ni sobrescribir `index.html`, voces o proyectos.
- Hacer inventario y snapshot fuera del árbol principal; reconciliar de forma aditiva y revisar diferencias antes de copiar.
- Mantener el worktree PoYo separado del proyecto principal.
- Fusionar solo tras revisión, CI completa y todas las puertas reales aprobadas.
- Desplegar sobre la URL existente `http://127.0.0.1:8766/studio`, nunca como segundo producto.
- Antes del despliegue: snapshot restaurable de código, datos, proyectos, voces, trabajos y referencias.
- Después: comprobar URL, controles, persistencia y restauración; conservar rollback funcional.

**Estado final de esta revisión: CANDIDATAS EN BORRADOR. NO FUSIONAR. NO DESPLEGAR. NO GENERAR NI CONSUMIR CRÉDITOS.**
