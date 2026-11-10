# B STUDIO ÉLITE — Orden ejecutiva de ingeniería y arquitectura

**Estado:** documento de ejecución versionado, no declaración de que todo esté implementado.  
**Rol solicitado:** arquitectura de software, dirección técnica audiovisual, integración de sistemas distribuidos, SRE, control de calidad y automatización de producción.

## 1. Mandato técnico

Transformar Barriga Studio y Barriga IA en una plataforma audiovisual confiable, con orquestación modular de modelos externos y locales. No exigir entrenamiento de nuevos pesos neuronales para cumplir las funciones de dirección: combinar planificación, memoria de proyectos, herramientas, validadores y evaluación comparativa.

**La meta de excelencia se mide por tareas concretas, no por una afirmación no verificable de ser superior a otros modelos de IA.**

## 2. Fuente de verdad y seguridad de datos

- Proteger todos los proyectos y voces existentes; antes de tocar la Mac, conservar los cambios locales fuera de Git.
- Respetar el worktree de PoYo separado del proyecto principal.
- No publicar credenciales, imágenes privadas, videos, archivos personales ni datos de clientes en el repositorio GitHub, actualmente público.
- Mantener compatibilidad con la clave de proyectos legacy `barriga-studio-projects-v1`.
- Cada producción debe incluir ID estable, versión del guion, fichas de personajes, voz, referencias, proveedor, costo, estado, task_id, archivos, hashes y fecha.
- No confundir «listo», «en cola», «generado» y «exportado con audio». Los estados deben proceder de verificaciones.

## 3. Arquitectura objetivo

```text
App / B STUDIO
    -> API autenticada (identidad, límites, validación)
    -> Barriga IA Director (guion -> escenas -> assets -> motor adecuado)
    -> Registro persistente de proyectos y trabajos
    -> Cola de producción + reservas de presupuesto + idempotencia
    -> Adaptadores video (PoYo Wan, otros proveedores verificados)
    -> Registro de voces existentes / motor de narración verificado
    -> Descarga y validación de medios (ffprobe / checksums)
    -> Ensamblaje FFmpeg (sincronización, mezcla, 9:16)
    -> Revisión de continuidad y calidad
    -> MP4 final, vista previa real, biblioteca y notificación
```

**Separación obligatoria:** la aplicación controla la experiencia; el backend custodia credenciales; los proveedores renderizan; Barriga IA coordina; los verificadores deciden si un resultado cumple.

## 4. Estados de trabajo y prevención de duplicados

`draft -> approved -> queued -> running -> provider_finished -> downloaded -> media_verified -> audio_mixed -> qa_passed -> published`

Estados alternativos: `needs_attention`, `failed`, `cancelled`.

- Guardar el ID de tarea del proveedor antes de cualquier espera.
- Reanudar consultando el MISMO task_id. Un timeout de consulta nunca debe disparar otra generación.
- Cada escena tiene una clave de idempotencia; no reutilizar una orden de cobro sin comprobar si existe trabajo previo.
- Registrar falla, causa, intento, costo estimado y resultado sin perder archivos parciales.
- Recuperación de trabajos tras reiniciar el proceso, con almacenamiento real y no solo localStorage.

## 5. Política de gasto

- Presupuesto inicial acordado: **US$5** para pruebas de generación.
- PoYo Wan 2.2 Fast: **480p / 6 créditos por generación** según tarifa pública. La CLI ya registró una prueba con estado `succeeded` y 6 créditos.
- Una estimación local no sustituye el saldo, facturación y límites del proveedor.
- Bloquear reintentos de pago automáticos y realizar pruebas unitarias sin llamadas pagadas.
- No ampliar el techo de US$5 por frases genéricas sobre «recursos necesarios»; la ampliación requiere una cifra aprobada y controles verificables.

## 6. Audio y video

**Video:** recuperar primero la tarea PoYo ya generada `0AHQMX2G2T4ZZE6O`, comprobar duración real, ancho/alto, formato, movimiento y MP4. Continuar con texto-a-video o imagen-a-video según el objetivo y el soporte real de referencias. No prometer continuidad perfecta del proveedor.

**Voces:** el usuario indica que el banco de voces está listo. Antes de sustituirlo, inventariar las voces existentes (idioma, ID, licencia, archivo, calidad, latencia), hacer una prueba reproducible y conectar el audio existente a la línea de tiempo.

**Montaje:** objetivo de reel de **35 segundos** vertical 9:16, sin fotogramas perdidos ni escenas vacías. La música y el sonido requieren fuentes autorizadas. El MP4 final debe incluir audio, y la narración debe medirse contra la línea de tiempo real.

## 7. Puertas de calidad (aceptación medible)

1. El proveedor marca `succeeded`, existe un URL completo y se descarga un archivo MP4 no vacío.
2. FFprobe verifica pista de video, resolución y duración real; para una versión completa: 35 s objetivo (tolerancia 0,5 s).
3. Existe pista de audio verificada y voz inteligible en español; revisión de sincronización en escenas habladas.
4. Personajes, vestuario, escenario y acciones pasan inspección visual de continuidad por escena.
5. Los trabajos y rutas de medios sobreviven reinicio/cierre; no hay envíos duplicados por reintentos.
6. Descarga final desde la app; historial con miniaturas, estado verificado, archivos y costos.
7. No se registran claves en Git, terminales de diagnóstico, vistas de proyecto ni archivos de video.
8. Pruebas automáticas sin consumo + prueba real pequeña dentro del presupuesto, documentadas por versión.

## 8. Orden de implementación

- **P0: desbloqueo del MP4 existente.** Usar `@poyoapi/cli task get TASK_ID --format json` aprovechando el llavero de macOS, descargar el archivo y verificarlo sin volver a generar.
- **P1: autosalvado, recuperación y trabajos persistentes.** Sustituir dependencia exclusiva del navegador por persistencia verificable; preservar proyectos actuales.
- **P2: adaptadores de video/audio y fichas de continuidad.** Conectar motores disponibles y voces ya producidas; fallar explícitamente cuando falte un componente.
- **P3: montaje y exportación.** Integrar FFmpeg y validación de salida con narración y 9:16.
- **P4: orquestador Barriga IA.** Planner + ejecutor de herramientas + memoria de proyectos + evaluadores + revisiones, con pruebas y sin autoconcederse permisos.
- **P5: despliegue y observabilidad.** Pruebas end-to-end, historial, costo por reel, métricas y notificación de finalización comprobada.

## 9. Trabajo verificable en esta rama

- `tools/bstudio_poyo_recover.py`: recuperación de tarea EXISTENTE por CLI en JSON; archivo completo; rechazo de destinos inseguros; validación mínima MP4 y FFprobe cuando esté disponible.
- `tests/test_bstudio_poyo_recover.py`: pruebas unitarias desconectadas de cuentas y sin cargos.
- `.github/workflows/poyo-recovery-test.yml`: ejecución de pruebas en GitHub Actions, sujetas a que Actions esté habilitado.
- **No realizado todavía:** ejecución en la Mac, descarga y análisis del video real, ensamblaje de 35 segundos, conexión de voces y despliegue en la aplicación principal. Son hitos sujetos a pruebas, no a suposiciones.

## 10. Próximo comando operativo sin nuevo gasto

Desde la carpeta separada de la Mac:

```bash
cd "$HOME/barriga-studio-poyo"
git fetch origin
git worktree add --detach "$HOME/barriga-studio-elite" origin/feat/bstudio-elite-recovery-qa-20261110
python3 "$HOME/barriga-studio-elite/tools/bstudio_poyo_recover.py" 0AHQMX2G2T4ZZE6O
```

La clave de PoYo no se vuelve a pegar; la CLI la recupera del llavero. El comando consulta una tarea existente y descarga su MP4 si está disponible; no usa `submit`.

**No ejecutar repetidamente el bloque completo:** el comando `git worktree add` crea una carpeta nueva y puede fallar si ya existe. Después usar únicamente el último comando de recuperación.
