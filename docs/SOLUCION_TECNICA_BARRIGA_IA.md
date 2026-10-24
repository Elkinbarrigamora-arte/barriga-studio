# Solución técnica v0.1: motor narrativo unificado y puente privado

## Alcance y límites

Esta reparación vive únicamente en la rama experimental
\`fix/barriga-ia-reanudar-sexta-20261023\`, PR #6. No se integra
automáticamente en \`main\` ni se publica en el dominio actual.

Se preservan \`index.html\`, \`assets/studio-mejoras.js\` y todos los borradores
de \`localStorage\`. El puente añade funciones solo cuando se abre en
\`127.0.0.1:8766\` con la Mac encendida.

**No es una herramienta de producción de videos.** No conecta voz,
generación visual, sincronización en la nube, publicación en redes
ni actividades con el equipo apagado. No usa APIs pagas.

## Flujo implementado

1. Studio local: ingresar idea de ficción y tocar **Generar y validar guion**.
2. \`POST /api/guion\`, protegido por origen y token local, con longitud acotada.
3. \`barriga_ia_servicio_local.ejecutar_motor\` invoca
   \`preparar_solicitud\` y \`generar_local\` desde el motor narrativo.
4. El borrador pasa a \`ensamblar_por_bloques\`, con presupuestos de palabras,
   controles editoriales y estados explícitos.
5. Se guarda **todo** el resultado (incluidos fallos editoriales) en SQLite bajo
   \`local-data/guiones-locales.sqlite3\`.
6. La interfaz puede listar versiones con \`GET /api/historial\` y recuperarlas
   mediante \`GET /api/guion/BI-...\`; recuperar un registro no borra otros.
7. Un estado \`REVISION_HUMANA_PENDIENTE\` significa solo **apto para revisión**,
   no aprobado por un humano. \`publicacion_automatica_autorizada\` sigue en falso.

La revisión editorial humana sigue siendo imprescindible. El motor NO garantiza
causalidad, originalidad, precisión ni continuidad audiovisual. Por defecto este
puente trabaja con ficción del nicho leyendas; los demás nichos deberán
integrarse con clasificación y fuentes adecuadas antes de usarse en producción.

## Prueba segura en la Mac

Requiere Python 3 y Ollama local con \`qwen2.5-coder:14b\`.

~~~bash
cd "$HOME/Barriga-IA-Pruebas"
git fetch origin fix/barriga-ia-reanudar-sexta-20261023
git switch --detach FETCH_HEAD
python3 -m unittest discover -s tests -v
python3 tools/puente_local.py --studio "$PWD" --puerto 8766
~~~

Abrir \`http://127.0.0.1:8766/\`, introducir una premisa de ficción,
pulsar el botón de generación y comprobar estado, guion e historial.
Cerrar y reabrir el navegador **mientras el servidor siga ejecutándose** y
probar **Recuperar guion**. Para detener el puente, \`Ctrl+C\`.

**No ejecutar una segunda instancia si el puerto 8766 ya está ocupado**.
El archivo de base de datos sobrevive a reinicios del puente y no se sube
a Git gracias a \`.gitignore\` (\`local-data/\`).

## Criterios para aceptar el módulo

- La API deniega solicitudes sin token o con origen POST no autorizado.
- La generación aprobada se almacena con un identificador único.
- Una generación rechazada también se almacena; jamás aparece como aprobada.
- Al reiniciar el puente, el historial continúa disponible.
- Las pruebas CI Python 3.9 y 3.11 pasan.
- **Prueba manual pendiente**: generación real con Ollama y apertura del
  historial en Safari/Chrome; ninguna prueba simulada sustituye este paso.

## Siguientes entregas de ingeniería

1. Eliminar duplicación de flujos narrativos y convertir
   \`barriga_ia_por_bloques.py\` en el único ensamblador para todos los nichos.
2. Unificar el almacenamiento del **proyecto**, no solamente las versiones de
   guiones, con escenas, estado, referencias, audio y permisos.
3. Conectar el Studio alojado a una API privada **autenticada** con un servidor
   realmente accesible. El puente \`127.0.0.1\` no se puede invocar desde el
   dominio alojado o desde otro dispositivo.
4. Ensayar voces e imagen/video real con recursos autorizados, medir duraciones,
   producir un MP4 verificable y activar las cuatro revisiones y cuatro filtros.
5. Integración del planificador de 30 contenidos únicamente tras aprobación
   humana y confirmación de que cada archivo final se reproduce.

## Seguridad

El repositorio de GitHub es público. No subir archivos de \`local-data\`,
datos personales, guiones privados, fotografías ni contraseñas.
El token se genera de forma efímera al iniciar el puente y nunca se almacena
en Git. Su función es proteger la API local, no autenticar usuarios del Studio
remoto. El servidor escucha solo en \`127.0.0.1\`.
