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
- HEAD anterior documentado: `b3dc4084edf80adad6461ee36aa71ed1f67ce05d`.
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

## Revalidación posterior — 17-nov-2026 03:59 UTC

Esta sección supersede los snapshots anteriores cuando describen el mismo proyecto o rama:

- PR #10 continúa abierta y en borrador, HEAD `0cf6e7475d8ac627517c76c6cf8504817904f361`. `main` no cambió y la comparación confirma 74 commits ahead / 0 behind.
- PR #13 continúa abierta y en borrador, base exacta en PR #10 HEAD, HEAD actual `5aaa4de9553c6c7c823904805cda04812ff155a5`.
- Actions run **44007706113** validó ese HEAD: 102 pruebas Python, 71 editor Chromium, 40 puente Chromium/WebKit, 24 ruta `/studio` Chromium/WebKit y 1 FFmpeg/FFprobe sintético = **238 comprobaciones aprobadas**. Los logs confirman que el smoke produjo un reel sintético de 35 s, rechazó una narración silenciosa, conservó un MP4 sintético válido y rechazó uno truncado. No certifica la Mac ni un MP4 real.
- Una copia más reciente de «Mis últimas gotas para ti», ID `077d6bce-53cb-4676-ba1a-b07903e0f8fc`, contiene seis escenas `mediaType=image`, `audioReady=true`, `localNarration=true`, `videoPreparation=null`, pero informa `percent=100`, `complete=true`, `final=true` y «Video listo para descargar». No expone ruta de MP4, artefacto, tamaño, SHA-256 ni FFprobe. Es evidencia nueva de que issue #12 sigue sin resolverse en los datos observados; no demuestra que no exista un archivo externo al snapshot.
- La copia anterior `d525104e-5f1b-42e3-9328-88c6fb8fef26` sigue en 80 %, `complete=false/final=false`, con las mismas seis imágenes y narración local.
- El conector de Barriga Studio sigue mostrando solo el dispositivo Windows emparejado pero desconectado; la Mac no aparece. Core y los motores privados de video/voz siguen sin verificación.
- El inventario de trabajos sigue mostrando trabajos de imagen, no una consulta a PoYo. El task_id `0AHQMX2G2T4ZZE6O` no se consultó en el proveedor ni se recuperó.
- No hay acción de conector disponible en esta ejecución para consultar el endpoint del Site `appgprj_6ac9279142e881918864b413032701e2`; por ello no se ejecutó GET ni POST `tick`.

**Acción indispensable pendiente:** conectar y registrar la Mac real, sin detener procesos ni sobrescribir archivos locales. Hasta entonces no hay respaldo, recuperación PoYo, inventario verificable de voces ni prueba end-to-end en el equipo.

## Revalidación operativa — 17-nov-2026 04:55 UTC

Esta sección es la lectura autenticada más reciente de este ciclo y sustituye los snapshots anteriores para los mismos objetos:

### Equipo, Core y medios

- Barriga Studio respondió a la consulta autenticada a las 2026-11-17T04:55:31.840Z.
- El único dispositivo registrado sigue siendo Mi computador Windows, emparejado (paired=true) pero desconectado (connected=false), sin lastSeenAt ni informe.
- La Mac del propietario no aparece registrada. El conector de este ciclo no proporciona control remoto de archivos ni ejecución local.
- Core continúa sin configurar ni seleccionar: configured=false, selected=false, enabled=false, gatewayConnected=false, inferenceVerified=false, sin modelo.
- El dispositivo reporta narración local gratuita disponible, pero ownVideoConfigured=false, privateVideoReady=false y privateSpeechReady=false. Esto no acredita conexión del banco de voces del propietario ni un motor neuronal de video.

### Reproducción actual de issue #12

Lectura del proyecto más reciente 077d6bce-53cb-4676-ba1a-b07903e0f8fc («Mis últimas gotas para ti», copia del dispositivo):

- Seis escenas, todas mediaType=image, de 5 segundos cada una.
- audioReady=true, localNarration=true, videoPreparation=null.
- Aun así: percent=100, complete=true, final=true, etapa «Montaje final completado» y etiqueta «Video listo para descargar».
- La respuesta no incluye ruta/URL de MP4, ID de artefacto, tamaño, SHA-256 ni resultado FFprobe.
- Por tanto, el estado de entrega no está respaldado por evidencia de archivo en el snapshot. Esto reproduce el caso de issue #12; no demuestra que no exista un archivo externo que el conector no exponga.

La copia d525104e-5f1b-42e3-9328-88c6fb8fef26 sigue en un estado distinto y no final: seis imágenes, narración local, videoPreparation=null, 80 %, complete=false, final=false, «Escenas listas · falta montar el video».

No se editó, eliminó ni deduplicó ningún proyecto.

### Trabajos y recuperación PoYo

- El inventario consultado devuelve los últimos 25 trabajos guardados, todos de tipo image; las producciones asociadas son estados históricos del estudio.
- Ese inventario no consulta PoYo. El task_id 0AHQMX2G2T4ZZE6O no aparece en la respuesta, lo cual no demuestra que no exista en el proveedor.
- No hay acción de conector PoYo disponible en este ciclo. No se llamó a submit, no se reintentó ninguna tarea y no se generó ni descargó un archivo.

### GitHub y CI revalidados

- Repositorio: Elkinbarrigamora-arte/barriga-studio; rama predeterminada: main.
- PR #10: abierta, en borrador, base main, HEAD 0cf6e7475d8ac627517c76c6cf8504817904f361. Comparación fresca: 74 commits ahead / 0 behind respecto de main (a07670c566b6c3cb04f387a553b80fffeacb08a9). Actions run 43966314947: ambos jobs exitosos; 96 Python + 69 editor Chromium + 40 puente Chromium/WebKit + 24 ruta /studio Chromium/WebKit + 1 FFmpeg sintético = 230 comprobaciones.
- PR #13: abierta, en borrador, base exacta en el HEAD de PR #10. HEAD de código inspeccionado: a04109cfdf1fb46788bee12c9f6e931722d2a3f9. Comparación fresca: 19 commits ahead / 0 behind respecto de PR #10. Actions run 44014307097: ambos jobs exitosos; 102 Python + 71 editor Chromium + 40 puente Chromium/WebKit + 24 ruta /studio Chromium/WebKit + 1 FFmpeg/FFprobe sintético de 35 s = 238 comprobaciones.
- Los logs de run 440143 confirman: 102 pruebas Python OK; 71, 40 y 24 pruebas de navegador aprobadas; el smoke sintético produjo video/audio de 35 s, rechazó narración silenciosa, conservó un MP4 sintético válido y rechazó un archivo truncado.
- Las 238 comprobaciones son de la rama PR #13 y no se suman a las 230 de PR #10. No certifican la Mac, el banco de voces real, el task PoYo ni el motor neuronal. El commit de esta sección, si lo hubiera, es documental y no debe confundirse con el HEAD de código probado.

### Site de aprendizaje y decisiones de seguridad

- No hay una acción de conector disponible para el Site appgprj_6ac9279142e881918864b413032701e2 ni para sus rutas GET /api/ai/learning y POST {"action":"tick"} en esta ejecución. No se obtuvo estado del Site y no se envió ningún tick.
- No hubo generación pagada, consumo de créditos, cambios en main, merge ni despliegue.

**Bloqueo operativo único para la validación local:** registrar y conectar la Mac real del estudio en el conector. Hasta entonces no ejecutar el recuperador PoYo que depende del llavero de macOS, no reconciliar archivos locales, no declarar las voces conectadas y no certificar el reel real. Mantener PR #10 y PR #13 en borrador.
