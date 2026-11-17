# Revalidación operativa de B STUDIO — 2026-11-17 08:01 UTC

> Privacidad: se omitieron identificadores, revisiones y títulos de proyectos del propietario; se conservan únicamente estados técnicos necesarios para la auditoría.


**Alcance:** lectura autenticada de solo lectura del estudio, proyectos, repositorio y ejecuciones CI. No es certificación del equipo Mac ni autorización de publicación.

## Dispositivo, Core y medios

Barriga Studio respondió a las **2026-11-17T08:01:24.945Z**.

- El único dispositivo registrado en la respuesta es **Mi computador Windows**, emparejado pero desconectado (paired=true, connected=false, lastSeenAt=null). La Mac no aparece en el inventario devuelto.
- Core continúa sin configurar ni verificar: configured=false, selected=false, enabled=false, gatewayConnected=false, inferenceVerified=false, sin modelo.
- La narración local gratuita aparece disponible, pero no demuestra que el banco de voces existente del propietario esté conectado.
- ownVideoConfigured=false, privateVideoReady=false, privateSpeechReady=false. La exportación descrita por el conector es montaje en navegador con escenas, narración y movimiento de cámara; no demuestra generación neuronal de movimiento.

## Reproducción fresca de issue #12

Proyecto consultado: **[ID DE PROYECTO OMITIDO]**, revisión [ID DE PROYECTO OMITIDO], título «proyecto narrativo del propietario» (copia del dispositivo).

- Seis escenas, cada una de cinco segundos; todas tienen mediaType=image.
- audioReady=true, localNarration=true, videoPreparation=null.
- A pesar de lo anterior, el snapshot informa percent=100, complete=true, final=true, etapa «Montaje final completado» y etiqueta «Video listo para descargar».
- También marca como completados los pasos «Imágenes y clips» y «Archivo final».
- La respuesta no expone ruta/URL de MP4, ID de artefacto, tamaño, SHA-256 ni resultado FFprobe.

**Conclusión limitada:** el estado final no queda respaldado por evidencia de archivo en el snapshot del proyecto. Esto reproduce el caso de issue #12. No demuestra que no exista un archivo externo que el conector no exponga.

El inventario reciente muestra varias copias de proyectos con títulos repetidos. No se modificó, eliminó ni deduplicó ningún proyecto.

## GitHub y CI revalidados

Repositorio: Elkinbarrigamora-arte/barriga-studio; rama predeterminada: main.

### PR #10 — candidata oficial

- Estado: abierta, en borrador; base main.
- HEAD: 0cf6e7475d8ac627517c76c6cf8504817904f361.
- Comparación fresca: **74 commits ahead / 0 behind** respecto de main, cuyo SHA es a07670c566b6c3cb04f387a553b80fffeacb08a9.
- Actions run **43966314947**: ambos jobs completados con éxito; 96 pruebas Python + 69 editor Chromium + 40 puente Chromium/WebKit + 24 ruta original /studio Chromium/WebKit + 1 smoke FFmpeg sintético = **230 comprobaciones**.

### PR #13 — reconciliación separada

- Estado: abierta, en borrador; base exacta en el HEAD de PR #10.
- HEAD: 32f4f5c040b9e2770fc252139e4082b7f7858ac4.
- Comparación fresca: **23 commits ahead / 0 behind** respecto de PR #10.
- Actions run **44035497788**: ambos jobs completados con éxito. Los logs confirman 102 pruebas Python, 71 editor Chromium, 40 puente Chromium/WebKit, 24 ruta original /studio Chromium/WebKit y un smoke FFmpeg/FFprobe con pistas sintéticas de video y audio de 35 segundos = **238 comprobaciones**.
- El smoke es sintético; no certifica un reel real, la voz del propietario, el equipo, PoYo ni un motor neuronal conectado.

Las 230 comprobaciones de PR #10 y las 238 de PR #13 pertenecen a ramas distintas y no se suman como una sola certificación. No se fusionó ni desplegó ninguna candidata.

## PoYo y Site de aprendizaje

- No hay acción de conector PoYo disponible en esta ejecución. No se consultó el task existente 0AHQMX2G2T4ZZE6O, no se llamó a submit, no se descargó archivo y no se consumieron créditos.
- El listado autenticado de sitios web devolvió una lista vacía. No hay un identificador de sitio/credencial actual que pueda asociarse de forma segura al proyecto Site appgprj_6ac9279142e881918864b413032701e2 mediante los conectores disponibles.
- No se ejecutaron GET /api/ai/learning ni POST {"action":"tick"}; no se puede inferir que la campaña esté activa o pausada.

## Decisión de seguridad

Mantener PR #10 y PR #13 en borrador. No fusionar, desplegar, generar ni gastar créditos. No reconciliar la Mac sin inventario y respaldo restaurable. El paso local indispensable sigue siendo registrar y conectar la Mac real del propietario; para la tarea de aprendizaje también se necesita que el Site aparezca en un conector accesible con su identificador de sitio verificable.
