# Barriga Studio — Auditoría e implementación de interfaz
**Fecha:** 2026-10-24  
**Rama experimental:** `fix/barriga-ia-reanudar-sexta-20261023`  
**Evidencia probada:** commit `b6543eacb36cdef4eea6e1a645aa0ca3fa03d657`, GitHub Actions ejecución `40133145967`

## Resumen ejecutivo
Se conservó el proyecto existente en HTML, CSS y JavaScript, sus IDs, sus funciones de guardado y restauración, y la integración experimental con Ollama mediante `tools/puente_local.py`.

Se incorporó una capa modular de interfaz con navegación, portada cinematográfica vectorial original, guía de cinco pasos, editor en cuatro columnas, selector visual de plantillas, preferencias de narración, vista previa de archivos audiovisuales reales y herramientas para la gestión de proyectos.

**No es una reproducción pixel-perfect**: la referencia visual de 1536 × 1024 no está incorporada al repositorio como archivo de comparación y los recursos originales 3D no están disponibles. No se afirmó generación neuronal de video, síntesis de voz ni sincronización remota.

## Cambios realizados
- `index.html`: carga aditiva de los nuevos archivos, conservando la estructura y los controles históricos.
- `assets/studio-interfaz.css`: diseño oscuro cinematográfico y responsive; proporción inicial 27/40/16/17 en escritorio; cinco pasos.
- `assets/studio-interfaz.js`: reutilización de controles existentes, selector de plantillas, contador de caracteres, visor de imagen, preferencias de idioma/música, reproductor de archivos MP4/WebM, descarga del archivo local cargado, buscador, favoritos y filtros.
- `assets/banner-personajes.svg`: ilustración independiente y editable de fresa, piña, naranja y personaje de cabello rojo. No es una imagen completa de la interfaz.
- `assets/studio-mejoras.js`: reparación de importación de respaldo para conservar `ideaOriginal`, `ultimoGuion` y textos completos sin truncamientos silenciosos.
- `tests/test_studio_interfaz.py`: pruebas regresivas de estructura, seguridad de datos y sintaxis JavaScript.
- `tests/smoke_studio_chromium.py`: capturas de la interfaz realmente renderizada.
- `tests/studio_browser_interactions.py`: prueba de interfaz real con Chromium y proyectos aislados.
- `.github/workflows/test-barriga-ia-calendario.yml`: validación automática, capturas y evidencias descargables.

## Validaciones completadas
**GitHub Actions / commit probado:** `b6543eac...`  
**Python 3.9:** 185 pruebas de `unittest` aprobadas.  
**Python 3.11:** 185 pruebas de `unittest` aprobadas.  
**Chromium:** 28 comprobaciones interactivas aprobadas en almacenamiento efímero, entre ellas:
- Montaje del editor con cuatro columnas.
- Selección efectiva de plantilla y tipo de voz.
- Persistencia de preferencia musical.
- Contador de caracteres y miniatura de PNG.
- Guardado del proyecto y sus opciones de formato y duración.
- Estados de borrador, filtros Todos/Favoritos/En proceso/Completados, buscador y cambio de vista.
- Duplicación sin sobrescribir y creación de un segundo proyecto independiente.
- Importación JSON conservando tanto la premisa como el último guion.
- Carga y **reproducción efectiva de un MP4 real de prueba**, lectura de duración y descarga de ese archivo local.
- Acción de generación neuronal deshabilitada cuando no existe motor verificado.
- Vista móvil a 390 píxeles sin desbordamiento horizontal global.
- Sin excepciones JavaScript en el recorrido probado.

**Capturas generadas en el navegador real:** `escritorio-1536x1024.png` y `movil-390x844.png`. Se almacenan como artifacts de la ejecución de GitHub Actions junto con el frontend usado para reproducirlas.

## Diferencias visuales y limitaciones pendientes
1. **Alta — Identidad 3D:** el SVG original es ilustración vectorial estilizada, no réplica exacta de frutas 3D y personaje anime de la referencia. Hacen falta ilustraciones originales o recursos equivalentes aprobados.
2. **Alta — Comparación pixel a pixel:** no existe en el repositorio una imagen de referencia versionada para comparación automatizada de métricas de geometría, color o similitud. Se revisaron las capturas y se corrigieron altura de tarjetas y disposición móvil, pero no se declara equivalencia exacta.
3. **Alta — Generación audiovisual:** no se verificó un motor generativo de video/voz; `Generar video` sigue inhabilitado. El visor reproduce archivos locales, no videos producidos por Barriga IA.
4. **Media — Recursos de plantillas:** algunas miniaturas usan recursos de demostración o ilustraciones reutilizadas; faltan imágenes finales específicas de cada plantilla.
5. **Media — Música y voz:** el selector permite elegir preferencias, pero no sintetiza voz, no mezcla audio y todavía no mantiene preferencias musicales individuales por proyecto.
6. **Media — Archivos adjuntos:** la miniatura de imagen se visualiza localmente pero el archivo seleccionado no se sincroniza ni persiste entre sesiones.
7. **Media — Estado de proyectos:** los borradores existentes se conservan; el filtrado por progreso depende de estados efectivamente guardados. No existe aún un sistema de renderizado asíncrono verificable para progreso en vivo.
8. **Media — Usuarios:** el selector de idioma ofrece español; el inglés figura deshabilitado. El perfil no inicia sesión ni inventa autenticación.
9. **Media — Navegador del propietario:** los tests se ejecutaron en Chromium de GitHub Actions, no en Safari del Mac del propietario. La integración real con Ollama en su equipo no se comprobó en esta auditoría.
10. **Baja — Calidad visual fina:** faltan ajuste tipográfico/espaciado pixel a pixel y pruebas manuales de zoom y accesibilidad exhaustiva.

## Integridad y seguridad
- **Sin cambios en `main`** y sin despliegue.
- **Sin migración ni eliminación de `barriga-studio-projects-v1`** en `localStorage`.
- Respaldos históricos e historial SQLite del puente local no se tocan por esta capa.
- El CI crea su propio navegador y sus propios proyectos de prueba; **no accede al almacenamiento de Safari del usuario**.
- No se habilitan APIs externas de pago ni cobros.
- La ilustración se sirve como SVG local, no como una captura aplanada de la página.

## Instrucciones de prueba en el Mac
1. Guarda el trabajo actual y descarga el respaldo JSON en **Mis proyectos**.
2. Si el puente en puerto 8766 está generando guiones, espera a que termine.
3. En `~/Barriga-IA-Pruebas`, actualiza desde `origin/fix/barriga-ia-reanudar-sexta-20261023` mediante `git fetch` y `git switch --detach FETCH_HEAD` después de revisar `git status`.
4. Detén con `Control+C` el servidor anterior. Inicia `python3 tools/puente_local.py --studio "$PWD" --puerto 8766`.
5. Abre `http://127.0.0.1:8766/` en Safari y revisa las cuatro columnas, el historial y los proyectos locales.

## Estado de entrega
**Fase de interfaz funcional implementada y validada en Chromium. Fidelidad gráfica exacta y motores multimedia reales pendientes.**  
La siguiente etapa de entrenamiento o ajuste de Barriga IA requiere decisión y ejecución separadas, después de que el propietario revise la interfaz y confirme los recursos visuales faltantes.
