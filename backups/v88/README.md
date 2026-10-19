# Barriga Studio — versión 88

Copia completa del código y recursos del proyecto publicado, incluidos servidor, interfaz, pruebas, migraciones y manifiesto. No contiene node_modules, claves de producción ni proyectos de usuarios.

Sitio: https://barriga-studio.sturdysnipe8.chatgpt.site/studio/

Proyecto Sites: appgprj_6ac9279142e881918864b413032701e2
Commit fuente: ece5def3da6f8aa243a1f15d30363a14e5fc4b7a
SHA256 del archivo reconstruido: 81d0a48fd898d7ef0b6c7e4db426de2c86f156f18ace9dc19d86baeb34dec152

Restauración desde esta carpeta:

```sh
cat source.tar.gz.part00 source.tar.gz.part01 source.tar.gz.part02 > source.tar.gz
sha256sum source.tar.gz
mkdir restored
tar -xzf source.tar.gz -C restored
```

Ruta de actualización: abrir el proyecto Sites existente, conservar su .openai/hosting.json, restaurar o editar el código, ejecutar pruebas y compilación, sincronizar el repositorio fuente Sites, guardar versión y desplegar sobre el mismo proyecto. Este respaldo GitHub no despliega automáticamente. No usar el index.html aislado en la raíz del repositorio como aplicación completa.

Validación: compilación y 25 pruebas pasaron. Publicación 88 confirmada. Prueba de video real de 30 segundos, voces por personaje e iPhone pendiente: falta FAL_KEY, acceso y saldo verificables; la integración fal.ai actual solo prepara solicitudes, no envía generaciones.
