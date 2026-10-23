# Primera prueba real Studio ↔ Barriga IA

**Estado:** prototipo, no aprobado para producción ni ejecución nocturna. Los archivos existentes de `main` NO se modifican.

## Copiar y pegar en Terminal (desde cualquier carpeta)

```bash
cd "$HOME/barriga-studio" && curl -fLsS "https://raw.githubusercontent.com/Elkinbarrigamora-arte/barriga-studio/test/prueba-previa-nocturna-20261022/tools/puente_local.py" -o "$HOME/Desktop/puente_local.py" && python3 "$HOME/Desktop/puente_local.py" --studio "$PWD"
```

Se abrirá el navegador en `http://127.0.0.1:8766/`. En **Creador de videos con IA**, escribe una idea en el guion y usa **Completar guion con Barriga IA**. Tras confirmar que sustituirás el texto existente, la aplicación envía una petición privada al modelo local de Ollama. Deben aparecer **GANCHO**, **HISTORIA** y **OFERTA O CIERRE**, junto con nombre del modelo y segundos de respuesta.

No se sobrescribe `index.html`: se lee desde el repositorio local y se le inserta temporalmente el botón al servir la página. El botón no genera video. Guardar el proyecto sigue sujeto al método existente del Studio y debe comprobarse. **Ctrl+C** detiene la prueba.

## Evidencia necesaria para marcarlo como validado
1. El navegador abre el Studio en 127.0.0.1.
2. Tras pulsar el botón, Ollama genera un guion original con tres partes.
3. El guion generado queda visible en el cuadro de texto del Studio.
4. Un borrador guardado se conserva tras recargar (sin reemplazar proyectos previos).

La prueba solo expone un servidor HTTP en `127.0.0.1`, utiliza un token efímero por sesión y valida el origen de las peticiones POST. No se usan APIs externas de pago. No activar servidor nocturno todavía.

## No implementado
Persistencia autenticada entre dispositivos, motor de video neuronal, producción MP4, voces por personaje, investigación autónoma y evaluación audiovisual completa.
