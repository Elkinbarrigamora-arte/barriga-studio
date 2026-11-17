# Revalidación operativa B STUDIO — 17-nov-2026 05:55 UTC

## Fuente y alcance
Lecturas autenticadas de Barriga Studio y GitHub realizadas en este ciclo. No se accedió al equipo local, a PoYo ni al Site de aprendizaje. Este registro es evidencia de estado, no certificación de producción.

## Dispositivo, Core y motores
- Barriga Studio respondió a las 2026-11-17T05:55:58.236Z.
- Único dispositivo registrado: «Mi computador Windows», emparejado pero desconectado; sin `lastSeenAt` ni informe. La Mac del propietario no aparece registrada.
- Core: `configured=false`, `selected=false`, `enabled=false`, `gatewayConnected=false`, `inferenceVerified=false`; sin modelo seleccionado.
- La narración local gratuita aparece como capacidad del dispositivo. No acredita el banco de voces del propietario.
- `ownVideoConfigured=false`, `privateVideoReady=false`, `privateSpeechReady=false`.
- La capacidad declarada de exportación es montaje en navegador con escenas, narración y movimiento de cámara; no equivale a generación neuronal de movimiento.

## Reproducción de issue #12
Proyecto consultado: `077d6bce-53cb-4676-ba1a-b07903e0f8fc`, «Mis últimas gotas para ti» (copia del dispositivo), revisión `0b196e44-c7b4-48d1-bb75-82b10b6e2b74`.
- Seis escenas, todas `mediaType=image`, de cinco segundos cada una.
- `audioReady=true`, `localNarration=true`, `videoPreparation=null`.
- Estado: `percent=100`, `complete=true`, `final=true`, etapa «Montaje final completado» y etiqueta «Video listo para descargar».
- El snapshot no expone ruta/URL de MP4, ID de artefacto, tamaño, SHA-256 ni resultado FFprobe.
- Se reproduce la inconsistencia de issue #12: estado final sin evidencia de archivo en el snapshot. Esto no demuestra que no exista un archivo externo no expuesto por el conector.
- No se editó, borró ni deduplicó ningún proyecto.

## PoYo
- El inventario de generación de Barriga Studio no consulta PoYo; sus trabajos recientes son de tipo imagen.
- No hay una acción de conector PoYo disponible en esta ejecución. El task `0AHQMX2G2T4ZZE6O` no se consultó en el proveedor ni se recuperó.
- El recuperador de la rama PR #13 usa la consulta CLI `task get --format json`, no `submit`; maneja 401/403 sin exponer stderr y exige host HTTPS permitido, coincidencia del task_id, MP4 y FFprobe antes de publicar atómicamente sin sobrescribir.
- No ejecutar ese recuperador fuera de la Mac autenticada con su llavero. No repetir consultas fallidas como nuevas generaciones.

## GitHub y CI
- Repositorio: `Elkinbarrigamora-arte/barriga-studio`; rama predeterminada `main`.
- PR #10: abierta, DRAFT, base `main`, HEAD `0cf6e7475d8ac627517c76c6cf8504817904f361`. `main` = `a07670c566b6c3cb04f387a553b80fffeacb08a9`; comparación: 74 commits ahead, 0 behind. CI run `43966314947`: 96 Python + 69 editor Chromium + 40 puente Chromium/WebKit + 24 ruta /studio Chromium/WebKit + 1 smoke FFmpeg sintético = 230 comprobaciones.
- PR #13: abierta, DRAFT, base exacta en PR #10 HEAD. Rama `feat/bstudio-recovery-audio-guard-20261116`, HEAD documental actual `a18b1dd408a5d28b1a4b460c90c11776667a0cce`; el HEAD de código probado es `a04109cfdf1fb46788bee12c9f6e931722d2a3f9`. Comparación: 20 commits ahead, 0 behind respecto de PR #10.
- CI run `44020713842`, asociado al HEAD documental `a18b1dd...`, terminó con ambos jobs exitosos. Logs revisados: 102 pruebas Python OK; 71 editor Chromium; 40 puente Chromium/WebKit; 24 ruta /studio Chromium/WebKit; smoke FFmpeg/FFprobe sintético de 35 s aprobado, rechazando narración silenciosa y MP4 truncado. Total: 238 comprobaciones.
- Las 238 pruebas de PR #13 no se suman a las 230 de PR #10. Son pruebas automatizadas con fixtures y medios sintéticos; no certifican Mac, voces reales, proveedor PoYo ni motor neuronal real.
- La comparación entre `a04109c` y `a18b1dd` confirma que el único cambio de ese último commit fue documentación (`docs/BSTUDIO_RELEASE_UNICA.md`).

## Site de aprendizaje
No existe una acción de conector disponible en esta ejecución para el Site `appgprj_6ac9279142e881918864b413032701e2` ni para `GET /api/ai/learning` / `POST {"action":"tick"}`. No se obtuvieron credenciales, no se consultó la campaña y no se envió ningún tick. No se debe inferir que la campaña esté activa o pausada.

## Decisiones
- Sin merge, despliegue ni cambios en `main`.
- Sin generación nueva ni consumo de créditos.
- Mantener PR #10 y PR #13 en borrador.
- Bloqueo operativo para la validación local: registrar y conectar la Mac real, respaldar y reconciliar sus archivos sin sobrescribirlos. Hasta entonces no declarar recuperado el MP4, conectadas las voces ni certificado el reel real de 35 s.

## Secuencia de archivado

El snapshot de rama descrito arriba se tomó antes de crear este archivo: en ese instante PR #13 apuntaba a `a18b1dd408a5d28b1a4b460c90c11776667a0cce`. Este documento se añadió después como commit exclusivamente documental; la consulta de Actions para ese commit de archivo devolvió cero ejecuciones. El CI 44020713842 valida el snapshot anterior y no se atribuye a este nuevo archivo.
