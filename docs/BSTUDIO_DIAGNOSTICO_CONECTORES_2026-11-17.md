# Diagnóstico operativo de B STUDIO — 2026-11-17

**Tipo:** evidencia de solo lectura obtenida mediante los conectores autenticados disponibles.  
**No es:** certificación del equipo Mac, consulta directa a PoYo, prueba de inferencia ni autorización de despliegue.

## Estado del dispositivo y Core

Consulta de Barriga Studio: `2026-11-17T01:56:52.974Z`.

- Existe un registro de dispositivo emparejado llamado **Mi computador Windows**, pero `connected=false` y no tiene `lastSeenAt`.
- La Mac del estudio no aparece entre los dispositivos registrados.
- Core está sin configurar: `configured=false`, `selected=false`, `enabled=false`, `gatewayConnected=false`, `inferenceVerified=false`; no hay modelo seleccionado.
- La consulta del conector no ofrece control remoto del equipo ni ejecución continua.

## Capacidades audiovisuales reportadas

- Hay narración local gratuita disponible en el dispositivo; esto no demuestra que el banco de voces existente esté conectado al servidor ni que una voz concreta pueda exportarse.
- La exportación reportada es montaje en navegador con escenas, narración y movimiento de cámara.
- `ownVideoConfigured=false`, `privateVideoReady=false` y `privateSpeechReady=false`.
- No presentar el montaje del navegador como generación neuronal de movimiento.

## Inventario reciente visible en el conector

La consulta de trabajos devuelve únicamente los últimos estados guardados y no consulta proveedores externos:

- Los 25 trabajos recientes expuestos son de tipo `image`; el resultado no contiene un trabajo de video ni el task_id PoYo `0AHQMX2G2T4ZZE6O`.
- Esto **no demuestra** que la tarea PoYo no exista; solo confirma que no está en ese inventario del estudio.
- La lista de 25 proyectos recientes contiene varias copias con títulos repetidos, en particular «Mis últimas gotas para ti» y «Un mango maduro y un mango». No deduplicar ni borrar automáticamente: primero se debe comparar el almacenamiento local real y hacer respaldo verificable.

## Estado de GitHub observado

Repositorio: `Elkinbarrigamora-arte/barriga-studio`.

- `main`: `a07670c566b6c3cb04f387a553b80fffeacb08a9`.
- PR #10 sigue abierta y en borrador; base `main`, HEAD `0cf6e7475d8ac627517c76c6cf8504817904f361`.
- PR #13 sigue abierta y en borrador; base `feat/bstudio-elite-recovery-qa-20261110`, HEAD `b3dc4084edf80adad6461ee36aa71ed1f67ce05d`.
- Actions run `43992043162` terminó con ambos trabajos exitosos sobre el merge ref de PR #13: 102 pruebas Python, 71 de navegador del editor, 40 del puente Chromium/WebKit, 24 de la ruta /studio Chromium/WebKit y 1 smoke FFmpeg sintético. Total: 238 comprobaciones.
- Los medios de FFmpeg son sintéticos; la CI no certifica el equipo, el banco de voces real, la tarea PoYo ni un motor neuronal conectado.

## Próximas puertas bloqueantes

1. Conectar y autenticar la Mac real sin detener procesos ni tocar sus archivos locales.
2. Respaldar y reconciliar el árbol local, proyectos, voces y recursos antes de activar el gateway.
3. Consultar la misma tarea PoYo existente `0AHQMX2G2T4ZZE6O`; nunca usar `submit` ni reintentar generación.
4. Recuperar el MP4, verificarlo con FFprobe y SHA-256, y escuchar la voz existente.
5. Probar el reel real de 35 s, persistencia tras cierre, controles de la URL oficial, restauración del respaldo y rollback.

Hasta completar esas pruebas, no fusionar PR #13 o PR #10, no desplegar, no habilitar motores no verificados y no consumir créditos de generación.
