# Barriga Studio

Plataforma audiovisual en desarrollo para **Barriga IA + Barriga Studio**.

## Qué funciona en `main`

- Creador de borradores con las tres plantillas acordadas, formato, duración, voz prevista y campo de referencia.
- Abrir y guardar proyectos **en el navegador actual** mediante `localStorage`.
- Descargar guion en texto.
- **Respaldo JSON y restauración aditiva** desde «Mis proyectos», sin sobrescribir proyectos existentes.
- Duplicar y eliminar proyectos con confirmación.
- Indicador editorial de palabras y duración aproximada de narración: **no equivale a una voz generada ni garantiza que el guion dure lo indicado**.

### Cómo proteger tus proyectos

En el apartado **Mis proyectos**, pulsa **Descargar respaldo JSON** y guarda el archivo fuera del navegador. Usa **Restaurar respaldo** para recuperarlos en otro navegador/equipo.

**Advertencia:** borrar datos de navegación puede eliminar los borradores locales. El respaldo es manual: no existe todavía sincronización autenticada, almacenamiento entre dispositivos ni recuperación en la nube.

## Arquitectura actual

| Archivo | Función |
|---|---|
| `index.html` | Interfaz actual; conserva intactos los controles y datos existentes |
| `assets/studio-mejoras.js` | Respaldo, restauración, duplicación, eliminación y verificación editorial |
| `backups/v88/` | Archivos de respaldo históricos del repositorio; no se ejecutan por defecto |
| `tools/puente_local.py` | Puente experimental local, ejecutado **solo manualmente**, con Ollama en 127.0.0.1:11434 y Studio en 127.0.0.1:8766 |

El puente **experimental** de guiones con Ollama existe ahora en `main`, pero requiere ejecutarse manualmente y verificar su comportamiento en la Mac. No se inicia al abrir Studio ni constituye todavía sincronización remota, producción audiovisual o funcionalidad desplegada. Las pruebas previas y diagnósticos adicionales permanecen en `test/prueba-previa-nocturna-20261022`.

## Probar el primer puente local sin API de pago

Con el repositorio actualizado y Ollama encendido, desde `barriga-studio`:

```bash
python3 tools/puente_local.py --studio "$PWD"
```

Se abre una página **solo local** en `http://127.0.0.1:8766`. Escribe una idea en el campo de guion y pulsa **Completar guion con Barriga IA**. El modelo local devolverá un guion con gancho, historia y oferta/cierre, si responde con JSON válido. `Ctrl+C` detiene el servidor. No se edita `index.html` ni se activa ningún servicio de fondo.

**Pendiente:** comprobar la llamada real en la Mac y la persistencia del guion; esto no genera videos ni voces.

### Puente experimental de imágenes con Draw Things

El mismo puente local (`tools/puente_local.py`) puede conectar el generador
de imágenes de Draw Things a un panel **Barriga IA · Imágenes**. Requiere
Draw Things abierto, con API HTTP habilitada en `127.0.0.1:7860`, y el
modelo deseado cargado en esa aplicación. Desde una Terminal en la Mac:

```bash
cd "$HOME/barriga-studio"
python3 tools/puente_local.py --studio "$PWD"
```

Abre `http://127.0.0.1:8766` si no se abre automáticamente. En el creador,
pulsa **Comprobar conexión**, elige el perfil *Planeta*, *Esmeralda* o
*Universo*, modifica la descripción y pulsa **Generar imagen**. La vista
previa aparece en la misma página. **Descargar imagen** guarda el resultado
por decisión explícita del usuario. Los pasos, la guía y la semilla se pueden
ajustar para comparar variantes; los valores están limitados para evitar
solicitudes accidentales demasiado grandes. Una generación puede tardar
varios minutos.

La respuesta viaja directamente entre Draw Things, el servidor local y el
navegador: **no se sube a GitHub ni a un servicio externo**. No se guardan
automáticamente prompts, imágenes ni proyectos, ni se reentrenan pesos.
La integración es experimental y la calidad requiere validación visual con
una generación real en la Mac; no crea video ni voz.

**Importante sobre proyectos existentes:** `127.0.0.1:8766` es un origen
distinto al dominio publicado de Studio. Por la separación de almacenamiento
del navegador, los proyectos existentes en el sitio publicado **no aparecen
automáticamente** en el puente local. Antes de mover proyectos, descarga su
respaldo JSON desde el origen donde estén guardados; la restauración aditiva
es manual. No borres datos del navegador.

Comprobación de código sin Draw Things:

```bash
python3 -m unittest discover -s tests -p 'test_*.py'
```

## Comprobaciones confirmadas en el Mac (prueba aportada por el propietario, 22 oct 2026)

- Ollama local: disponible.
- Modelo `qwen2.5-coder:14b`: respuesta real `BARRIGA_OK` en 4,8 segundos.
- Supervisor: `SOLO_DIAGNOSTICO`, revisión cada 900 segundos; **no es un agente de desarrollo autónomo**.
- `FFmpeg`: no detectado en PATH.
- API Draw Things, video neuronal, voz persistente, IA ↔ Studio autenticados, agentes de investigación y MP4 de prueba: **no probados**.

## Flujo objetivo (aún no implementado por completo)

1. Guion de 30–40 segundos: gancho → historia → oferta/cierre. La historia debe permanecer continua.
2. Proyecto con referencias persistentes de personajes, escenas y voces.
3. Motores verificados de imagen, voz y video real, cada uno identificado por su capacidad.
4. Cuatro análisis de calidad y cuatro filtros finales.
5. Canasta de aprobación y almacén de 30 videos aprobados.
6. Estados persistentes, reintentos limitados, seguridad y recuperación de trabajos.
7. Conexión privada y autenticada Mac ↔ Studio y sincronización entre dispositivos.

**La versión actual NO genera video neuronal ni voces profesionales.** La animación de una imagen o el movimiento de cámara no se deben declarar como generación neuronal de personajes.

## Desarrollo local de la interfaz estática

Desde la carpeta `barriga-studio`, abrir un servidor local de archivos:

```bash
python3 -m http.server 8080 --bind 127.0.0.1
```

Visitar `http://127.0.0.1:8080`. Esta prueba sirve solo la interfaz estática y **no conecta Ollama ni genera videos**.

## Seguridad y versiones

- Rama de recuperación: `backup/main-antes-reparacion-20261022`.
- Se mantiene la clave de proyectos `barriga-studio-projects-v1` para conservar borradores.
- No se instalan APIs de pago, no se publican puertos de la Mac ni se habilita trabajo nocturno.
- **Atención:** a 22 oct 2026, el repositorio de GitHub aparece como **público**. No incluir proyectos privados, secretos, credenciales ni referencias personales en archivos versionados.
- Un cambio en GitHub `main` **no garantiza** actualización automática del dominio del Studio: la ruta de despliegue debe comprobarse.


## Barriga IA: desarrollo local sobre el Studio principal (experimental)

El coordinador de `tools/agente_desarrollo.py` usa **Ollama local** para proponer cambios reales en el código del proyecto. Trabaja directamente sobre la rama **main local** de la Mac, crea una rama de respaldo por fase, valida la sintaxis y registra un commit por fase aprobada. Las cinco fases son: **guiones, escenas, proyectos, motores y control de calidad**.

Para ejecutarlo, abre una **nueva pestaña de Terminal** (puedes mantener abierto el puente de guiones) y pega:

```bash
cd "$HOME/barriga-studio" && git pull --ff-only origin main && python3 tools/agente_desarrollo.py --studio "$PWD" --ciclos 5
```

**Requisitos:** Ollama encendido con el modelo `qwen2.5-coder:14b`, Git limpio, Python 3 y Node.js para validar modificaciones JavaScript. Si falta Node, el agente se detiene y muestra el motivo; no instala software por su cuenta.

La ejecución **no es continua, no entrena pesos, no modifica automáticamente Ollama y no publica commits en GitHub**. No ejecuta comandos propuestos por el modelo, no permite escribir fuera de las carpetas autorizadas y bloquea modificaciones a su propio ejecutor. Si una propuesta no supera validación, revierte los archivos afectados. Reanudar la ejecución omite las fases cuyos commits ya se registraron.

**Alcance de la prueba:** se probaron con éxito cuatro verificaciones unitarias del coordinador en un entorno aislado (rutas protegidas, parche exacto, commit con respaldo y reversión por JavaScript defectuoso). **No** se ha ejecutado aún este coordinador con Ollama en la Mac ni se ha demostrado producción audiovisual. Validar sintaxis no equivale a probar la interfaz completa. Consulta [el plan maestro](docs/PLAN_MAESTRO.md).
