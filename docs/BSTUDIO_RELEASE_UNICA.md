# B STUDIO Élite — Política de versión única y publicación controlada

## Objetivo
Una sola aplicación oficial de Barriga Studio, con una única URL de producción y una única versión marcada como vigente. Las ramas de GitHub, copias de seguridad y entornos de prueba son **internos** y no deben presentarse al usuario como versiones alternativas.

## Fuente de verdad
1. **Producción actual:** mantener activa la última versión desplegada hasta que la candidata esté completamente comprobada.
2. **Mac del propietario:** contiene modificaciones y motores que todavía no están reflejados en GitHub; su inventario y respaldo son pasos imprescindibles.
3. **GitHub `main`:** será el código fuente canónico después de reconciliar los archivos reales, revisar secretos y fusionar la candidata verificada.
4. **Proyectos y voces:** datos persistentes separados del código; nunca reemplazar ni borrar por una actualización.

## Puertas obligatorias antes de publicar
- [x] 69 pruebas reales de navegador de la interfaz versionada (GitHub Actions, 10-nov-2026).
- [x] 15 pruebas unitarias de recuperación, montaje y seguridad.
- [x] 1 montaje real FFmpeg con insumos sintéticos, video + pista de audio.
- [ ] Auditoría completa de los cambios que solo existen en la Mac, conservando archivos no versionados.
- [ ] Copia de seguridad restaurable y prueba de restauración (incluido almacenamiento de proyectos).
- [ ] Inventario de voces existentes, licencias e identidad de personajes, sin volver a crearlas.
- [ ] Recuperar el archivo real de la tarea PoYo `0AHQMX2G2T4ZZE6O` sin nuevo cargo.
- [ ] Generación de escenas reales, continuidad, descarga y montaje real de un reel de 35 segundos con voz.
- [ ] Pruebas de todos los controles de la versión desplegable, sin botones rotos ni simulación de funciones no conectadas.
- [ ] Seguridad, autenticación, persistencia tras cerrar/reabrir, comprobación de gastos y despliegue con rollback.
- [ ] Comprobación posterior al despliegue de la URL oficial y los proyectos existentes.

**Regla:** si una casilla crítica está pendiente o falla, NO se publica ni se declara una versión final.

## Protocolo de Mac
El código de la Mac tiene cambios locales modificados y archivos sin seguimiento. No ejecutar `git reset --hard`, `git clean -fd`, `git checkout` sobre la carpeta principal, ni sobrescribir `index.html` o voces; usar un entorno separado y respaldo comprobado.

El script `tools/bstudio_mac_preflight.py` hace un inventario local de solo lectura de Git, FFmpeg, Node, carpetas de motores y puertos. El script no lee claves ni modifica datos, pero no sustituye pruebas reales.

La prueba de restauración del navegador usa un JSON descargado por la propia interfaz y verifica que el título y el guion se recuperen completos en un perfil vacío, incluso cuando son largos. Este respaldo cubre los campos de borrador del navegador, no sustituye una copia verificada de videos, voces, colas ni archivos locales de la Mac.

## Etiquetado y reversión
- Identificador único de release: `BSTUDIO-ELITE-YYYYMMDD-N`.
- Cambios a `main` mediante revisión y CI aprobada; fusionar solo tras reconciliar la Mac.
- Despliegue sobre URL existente, nunca mediante una segunda web paralela.
- Antes de desplegar: snapshot de código, datos, esquemas, trabajos y referencias de proyecto.
- Después de desplegar: prueba funcional y rollback disponible para restaurar código y datos en caso de regresión.
- Mantener registro de compilación, hash Git, pruebas, fecha, estado, proveedor y presupuesto.

## Estado actual
**CANDIDATA EN REVISIÓN. NO PUBLICADA.** La aplicación conectada confirma que no hay un motor privado de video/voz completamente validado en su estado actual. La calidad de producción audiovisual y la versión local de Mac aún requieren acceso y verificación.
