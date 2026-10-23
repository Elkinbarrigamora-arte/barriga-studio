# Barriga Studio — puente de colaboración

## Alcance

ChatGPT puede enviar órdenes técnicas PREDEFINIDAS a bridge/ordenes.json mediante GitHub. El Mac consulta la lista por HTTPS cada 180 segundos aproximadamente mientras esté encendido y despierto.
Las acciones permitidas son: diagnostico, auditoria_interfaz, revision_proyectos, pruebas_agente.
No hay ejecución de comandos ni código recibidos de GitHub. No hay puertos entrantes ni servicios de pago.

El repositorio ES PUBLICO: las órdenes y los resultados técnicos resumidos serán visibles en internet si el usuario activa la publicación. Nunca se envían contraseñas, guiones, imágenes, proyectos ni registros privados. El puente inicial NO concede acceso directo de ChatGPT a la Terminal.

## Instalación en macOS

Desde la carpeta ~/barriga-studio:

    cd "$HOME/barriga-studio" && git fetch origin && git merge --no-edit origin/main
    python3 tools/puente_colaboracion.py --instalar --publicar

La opción --publicar autoriza la publicación únicamente de resultados técnicos genéricos en el repositorio PUBLICO. Si no deseas publicarlos, omite la opción. Para publicar se requieren credenciales Git existentes con acceso de escritura.

Se instala un LaunchAgent de usuario. No requiere permisos de administrador. Funciona durante sesiones activas; no ejecuta tareas cuando la Mac está apagada. No funciona durante determinadas fases de reposo.

## Comprobación

    python3 tools/puente_colaboracion.py --estado
    python3 tools/puente_colaboracion.py --una-vez

## Seguridad y límites

1. La lista de acciones y los IDs son estrictamente validados; no acepta órdenes shell ni argumentos arbitrarios.
2. Cada orden se ejecuta una sola vez y se registra en un directorio privado local.
3. Límites de tamaño y tiempo de red y bloqueo de ejecución simultánea.
4. Los resultados publicados no contienen rutas personales, contenidos de proyectos, salida completa de pruebas ni mensajes internos de error.
5. Los resultados se publican mediante un CLON AISLADO: nunca ejecuta reset ni push sobre ~/barriga-studio.
6. Si fallan los permisos para subir estados, los resultados siguen disponibles localmente.
7. No sincroniza ni reemplaza código automáticamente; las mejoras se revisan y se integran por separado.

## Desinstalar

    launchctl bootout "gui/$(id -u)/com.barriga.studio.puente"
    rm "$HOME/Library/LaunchAgents/com.barriga.studio.puente.plist"

La desinstalación no borra proyectos ni respaldos.

## Siguiente etapa

Conectar cambios de interfaz y persistencia mediante actualizaciones revisadas de GitHub, sin sobrescribir los commits locales existentes. La ejecución arbitraria o el control remoto completo NO están habilitados.
