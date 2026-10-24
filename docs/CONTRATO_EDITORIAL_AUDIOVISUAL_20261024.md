# Barriga IA ↔ Barriga Studio: contrato editorial y audiovisual

**Estado:** primera integración experimental en `fix/barriga-ia-reanudar-sexta-20261023`.
No está desplegada en `main`, no entrena pesos y no renderiza video.

## Traducción de los requisitos del autor

| Instrucción natural | Requisito verificable |
| --- | --- |
| «Hoy un Reel de esmeraldas y mañana uno de dinosaurios» | Cada creación usa `modo=independiente` por defecto; no se incorporan hechos, personajes ni cronologías de otras generaciones. |
| «Solo cuando te diga serie» | `modo=serie` requiere `serie_id` explícito y una biblia previamente guardada por el editor. |
| «Sigue la historia de Pepito y Pepita» | La biblia se recupera por identificador exacto desde SQLite y entra únicamente en el prompt de ese episodio. |
| «Actúa como creadora de Reels, narradora y guionista» | Identidad editorial estable: gancho concreto → desarrollo causal → cierre verificable; oferta comercial solo cuando corresponda. |
| «Que todo sea uniforme con la aplicación de video» | Cada guion registra una estructura `plan_video` con tiempos por bloque, voz, estilo visual, formato, modo y referencia a la misma serie. |
| «Aprende de mis correcciones» | Requisito pendiente: memoria de preferencias editoriales con confirmación humana, aislada de la memoria argumental. No se usan automáticamente borradores rechazados. |

## Contrato HTTP inicial

**Guardar/actualizar manualmente la ficha de una serie:**

```http
POST /api/serie
Content-Type: application/json
Origin: http://127.0.0.1:8766
X-Barriga-Token: <token del puente local>

{"serie_id":"pepito-pepita","biblia":{"descripcion":"Pepito usa sombrero rojo; Pepita viste azul. La puerta del castillo sigue cerrada."}}
```

Los cambios preservan versiones anteriores en la tabla
`versiones_memorias_series`. La ficha vigente se recupera mediante
`GET /api/serie/pepito-pepita`. Ninguna ficha se crea a partir de un guion
rechazado ni de una coincidencia temática automática.

**Nuevo Reel independiente (omitir `contexto` produce el mismo modo):**

```json
{
  "idea": "Una esmeralda aparece en el lecho del río.",
  "duracion_objetivo_segundos": 35,
  "contexto": {
    "modo": "independiente",
    "video": {"formato": "9:16", "estilo_visual": "cinematográfico", "voz": "Español femenino"}
  }
}
```

**Capítulo de serie registrada:**

```json
{
  "idea": "Pepita abre una puerta y descubre una pista.",
  "duracion_objetivo_segundos": 35,
  "contexto": {
    "modo": "serie",
    "serie_id": "pepito-pepita",
    "video": {"formato": "9:16", "estilo_visual": "Animación 3D", "voz": "Español femenino"}
  }
}
```

La API consulta la biblia vigente; no acepta una ficha improvisada dentro de
la solicitud de generación. La respuesta y el registro de historial incluyen
`contexto_editorial` y `plan_video`.

## Contrato audiovisual

`plan_video` es un **plan estructurado**, no un archivo generado. Posee:

- `estado=PLAN_PENDIENTE_DE_REVISION`;
- `video_generado=false` y `voz_generada=false`;
- tres segmentos temporales contiguos: `gancho`, `historia`, `cierre`;
- narración exacta de cada bloque y duración total solicitada;
- formato, voz y estilo provenientes de la configuración del editor;
- `serie_id` y `biblia_serie` solo en capítulos de una serie explícita.

Cuando se conecte un motor audiovisual real, debe consumir este contrato,
producir tomas/referencias visuales verificables, mantener una identidad de
personaje por serie cuando exista y devolver un estado de renderizado real.
Hasta entonces «Generar video» permanece deshabilitado: no se simula
producción multimedia.

## Límites y próximos pasos

1. **Memoria de capítulos aprobados:** hoy la biblia se edita y guarda
   manualmente. Falta un flujo editorial para incorporar automáticamente
   nuevos hechos solo cuando el autor apruebe el capítulo.
2. **Memoria editorial transversal:** definir preferencias y correcciones
   aprobadas sin contaminar fichas de series ni crear continuidad implícita.
3. **Contenido factual:** la ruta del editor sigue centrada en ficción; un
   microdocumental con afirmaciones científicas, históricas o noticiosas
   requiere fuentes y verificación antes de presentarse como verdadero.
4. **Motor audiovisual:** la interfaz actual permite cargar y previsualizar
   videos locales, pero todavía no genera tomas, voces o renderizado.
5. **Prueba real en Mac:** las pruebas de regresión no ejecutan Ollama ni
   certifican calidad creativa o consistencia visual de imágenes generadas.

## Invariantes de seguridad

- Sin modificación de `main`, de los proyectos ya guardados, ni de guiones
  anteriores.
- Las memorias de series se aíslan por ID; el modo independiente no recupera
  ninguna.
- Solo el editor registra o modifica una biblia de continuidad.
- Nada se publica automáticamente. Todo guion permanece sujeto a revisión
  humana y no hay entrenamiento de pesos.
