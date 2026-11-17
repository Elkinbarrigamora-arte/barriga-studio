# Diagnóstico operativo de B STUDIO — 2026-11-17

> Privacidad: se omitieron identificadores, revisiones y títulos de proyectos del propietario; se conservan únicamente estados técnicos necesarios para la auditoría.


**Tipo:** evidencia de solo lectura obtenida mediante los conectores autenticados disponibles.  
**No es:** certificación del equipo Mac, consulta directa a PoYo, prueba de inferencia ni autorización de despliegue.

## Estado del dispositivo y Core

Consulta de Barriga Studio: `2026-11-17T03:00:19.035Z`.

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
- La lista de 25 proyectos recientes contiene varias copias con títulos repetidos, en particular «proyecto narrativo del propietario» y «otro proyecto del propietario». No deduplicar ni borrar automáticamente: primero se debe comparar el almacenamiento local real y hacer respaldo verificable.

## Estado de GitHub observado

Repositorio: `Elkinbarrigamora-arte/barriga-studio`.

- `main`: `a07670c566b6c3cb04f387a553b80fffeacb08a9`.
- PR #10 sigue abierta y en borrador; base `main`, HEAD `0cf6e7475d8ac627517c76c6cf8504817904f361`.
- PR #13 sigue abierta y en borrador; base `feat/bstudio-elite-recovery-qa-20261110`, cuyo HEAD coincide exactamente con PR #10. HEAD actual de PR #13: `5aaa4de9553c6c7c823904805cda04812ff155a5`.
- La comparación actual de PR #10 con `main` confirma 74 commits por delante y 0 por detrás; no se ha fusionado ni desplegado.
- Actions run `43966314947` validó PR #10: 96 pruebas Python, 69 de editor Chromium, 40 del puente Chromium/WebKit, 24 de la ruta /studio Chromium/WebKit y 1 smoke FFmpeg sintético = **230 comprobaciones**.
- Actions run `44007706113` validó el HEAD actual de PR #13: 102 pruebas Python, 71 de editor Chromium, 40 del puente Chromium/WebKit, 24 de la ruta /studio Chromium/WebKit y 1 smoke FFmpeg/FFprobe sintético = **238 comprobaciones**.
- Los medios de FFmpeg son sintéticos; CI no certifica el equipo, el banco de voces real, la tarea PoYo ni un motor neuronal conectado.

## Revalidación de proyecto y dispositivo — 2026-11-17 03:59 UTC

La lectura autenticada más reciente confirma:

- El único dispositivo registrado sigue siendo **Mi computador Windows**, emparejado pero desconectado; la Mac no aparece registrada.
- Core sigue sin configurar y sin inferencia verificada.
- `ownVideoConfigured=false`, `privateVideoReady=false`, `privateSpeechReady=false`.
- El proyecto más reciente de la misma historia, ID `[ID DE PROYECTO OMITIDO]`, contiene el mismo guion de «proyecto narrativo del propietario», seis escenas y `mediaType=image` en todas. Informa `audioReady=true` y `localNarration=true`, pero `videoPreparation=null`; aun así, el estado reporta `percent=100`, `complete=true`, `final=true` y etiqueta «Video listo para descargar».
- El snapshot no expone ruta de MP4, ID de artefacto, tamaño, SHA-256 ni metadatos de FFprobe. Por tanto, la etiqueta final **no está respaldada por evidencia de archivo**. Esto reproduce el defecto de issue #12 en una copia más reciente; no demuestra por sí solo que no exista un archivo fuera de lo expuesto por el conector.
- La copia anterior `[ID DE PROYECTO OMITIDO]` sigue mostrando 80 %, seis imágenes, narración local y `complete=false/final=false`.
- El inventario de trabajos recientes sigue mostrando solo trabajos de imagen; no consulta PoYo y no permite concluir si la tarea externa existe o no.

No se modificó, eliminó ni deduplicó ningún proyecto. La corrección de issue #12 requiere una puerta de estado basada en un MP4 asociado al proyecto y validado, más una regresión específica; las pruebas de CI actuales no demuestran que esa puerta ya esté implementada.

## Próximas puertas bloqueantes

1. Conectar y autenticar la Mac real sin detener procesos ni tocar sus archivos locales.
2. Respaldar y reconciliar el árbol local, proyectos, voces y recursos antes de activar el gateway.
3. Consultar la misma tarea PoYo existente `0AHQMX2G2T4ZZE6O`; nunca usar `submit` ni reintentar generación.
4. Recuperar el MP4, verificarlo con FFprobe y SHA-256, y escuchar la voz existente.
5. Corregir y probar la puerta de estado de issue #12: seis imágenes + narración local + ausencia de MP4 nunca pueden producir `complete/final` ni «Video listo».
6. Probar el reel real de 35 s, persistencia tras cierre, controles de la URL oficial, restauración del respaldo y rollback.

Hasta completar esas pruebas, no fusionar PR #13 o PR #10, no desplegar, no habilitar motores no verificados y no consumir créditos de generación.
