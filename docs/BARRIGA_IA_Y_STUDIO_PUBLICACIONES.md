# Barriga IA + Barriga Studio — entrega experimental 01

## Principio de arquitectura

**Barriga IA es independiente de Barriga Studio.** El código de planificación
y el almacén se encuentran en \`tools/barriga_ia_calendario.py\`, sin importar
código del navegador, sin abrir puertos ni contactar plataformas. Studio es un
panel **opcional y de solo lectura** en \`studio-publicaciones.html\`.

La pantalla principal \`index.html\`, los tres estilos y los proyectos
guardados previamente no se modifican con esta entrega. No se fusiona nada
automáticamente con \`main\`.

## Alcance realmente implementado en esta rama

| Capacidad | Estado |
| --- | --- |
| Plantilla de 30 días × 2 horarios: 03:30 / 17:30 | Implementada en planificador local |
| Zona horaria \`America/Bogota\` | Definida para horarios y registros |
| Almacén de máximo 30 videos, SQLite persistente | Implementado; datos fuera del repositorio |
| Título y exactamente cinco hashtags únicos | Validados al ingreso |
| Requerir confirmación manual de aprobación | Implementado |
| No asignar dos veces el mismo vídeo / no pisar un turno ocupado | Implementado |
| Exportar CSV local para revisión | Implementado |
| Panel opcional que abre CSV local sin transferirlo | Implementado |
| Cuatro analizadores + cuatro filtros de calidad | **Pendientes** |
| Diagnóstico completo de decodificación de video/sonido | **Pendiente**: solo hay comprobación básica de contenedor MP4 |
| Generación real de imágenes, videos, voces y montaje | **No disponible en este módulo** |
| Autenticación y conexión privada IA ↔ Studio | **Pendiente** |
| Conectores oficiales / subida / confirmación y métricas sociales | **Pendientes** |
| Publicación real en redes al apagar la Mac | **No activada** |

**Importante:** 60 horarios no significa 60 contenidos preparados ni 60
publicaciones confirmadas. Los turnos se crean vacíos y solo pueden asignarse
a videos ingresados manualmente. El CSV es un borrador para programar
manualmente los archivos en las herramientas oficiales de cada plataforma.
Ningún CSV programa por sí solo una publicación.

## Puesta en marcha local (Python 3.11+)

Desde la raíz del repositorio y con la Mac encendida para preparar el plan:

\`\`\`sh
python3 tools/barriga_ia_calendario.py planificar --desde 2026-10-24
python3 tools/barriga_ia_calendario.py estado
python3 tools/barriga_ia_calendario.py exportar --salida local-data/calendario.csv
python3 -m unittest discover -s tests -p "test_barriga_ia_calendario.py" -v
\`\`\`

Por defecto se creará \`local-data/barriga-ia.sqlite3\`. Este directorio está
excluido de Git. La aplicación no registra automáticamente los clips ya
existentes en Studio.

### Ejemplo de manifiesto local

Crear \`local-data/video1.json\` **solo después** de revisar y aprobar un video
real (la ruta debe existir y corresponder a un archivo MP4):

\`\`\`json
{
  "id": "video1",
  "archivo": "/ruta/privada/video-final.mp4",
  "titulo": "El secreto de las profundidades",
  "hashtags": ["#Oceano", "#Naturaleza", "#Misterios", "#Animales", "#Ciencia"],
  "aprobacion_manual": true
}
\`\`\`

\`\`\`sh
python3 tools/barriga_ia_calendario.py ingresar --manifiesto local-data/video1.json
python3 tools/barriga_ia_calendario.py asignar --id video1 --fecha 2026-10-24 --hora 17:30
python3 tools/barriga_ia_calendario.py exportar --salida local-data/calendario.csv
\`\`\`

Abrir \`studio-publicaciones.html\` localmente desde el navegador y seleccionar
el CSV para visualizar los horarios. **Este panel no publica, no carga el CSV
a una web y no modifica la base de datos de Barriga IA.**

### Publicar con Mac apagada

Para publicar cuando el ordenador ya esté apagado:

1. Producir y aprobar el **MP4 final real** antes de apagar la Mac.
2. Subirlo mientras hay conexión a una herramienta de programación **oficial y
   compatible de cada red**; revisar restricciones de cuenta, contenido y región.
3. Confirmar por separado que la plataforma **aceptó la programación** y
   registrar su identificador y hora.
4. Solo entonces apagar la Mac. El contenido aceptado por la plataforma
   se publicará desde su infraestructura, sujeto al correcto funcionamiento
   de sus servicios, restricciones y controles.

No se han realizado las etapas 2 ni 3 desde nuestro código.
La programación a nivel local no sustituye la confirmación externa.

## Próximos desarrollos en paralelo, sin romper Studio

**Barriga IA (núcleo):** incorporar cuatro analizadores, cuatro filtros,
verificación de reproducción real, estados verificables de publicación por
plataforma, auditoría, permisos, memoria, retentativas sin duplicados y
conectores oficiales solo después de autorización y pruebas.

**Barriga Studio (panel):** agregar una vista autenticada del almacén y
calendario vía servicio privado, preservar los proyectos existentes y probar
exportación, continuidad de personajes, video real y múltiples voces. El
HTML de esta primera entrega es independiente; todavía no hay API conectada.

## Seguridad y costes

- Repositorio público: **no añadir** archivos multimedia privados, JSON con
  rutas o datos sensibles, tokens, claves ni bases SQLite.
- Cualquier publicación futura requerirá aprobación explícita y permisos
  oficiales. Las API sociales están desactivadas.
- No se contrata ni habilita ningún servicio de pago.
- Sin una computadora o servicio encendido, **no se puede afirmar** que Barriga
  IA seguirá investigando o generando nuevos videos cuando la Mac se apague.
  Solo la programación externa ya aceptada podrá operar sin ella.
