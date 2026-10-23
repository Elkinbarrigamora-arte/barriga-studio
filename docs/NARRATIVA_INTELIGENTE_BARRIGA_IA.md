# Narrativa Inteligente — Barriga IA v0.1 (en pruebas)

## Objetivo
Afinar el **proceso de generación de guiones**, no modificar los pesos del modelo.
Barriga IA opera como motor narrativo independiente, y Barriga Studio será el
panel consumidor una vez exista integración privada comprobada.

**Estructura editorial predeterminada:**

1. **Gancho:** conflicto, revelación o curiosidad en los primeros 1–3 segundos.
2. **Historia:** narración continua con causa, acción y consecuencias.
3. **Oferta/cierre:** resolución sorprendente, conmovedora o invitación si procede.

Especialidades: historia, mitos, leyendas, animales, terror,
terror_cartoon, planeta, maravillas, amor, noticias y miniseries.

## Pruebas: primero sin Ollama

Se ejecutan en **Python 3.9.6** y Python 3.11, sin dependencias externas:

~~~sh
python3 -m unittest discover -s tests -p 'test_barriga_ia_narrativa.py' -v
python3 -m unittest discover -s tests -p 'test_barriga_ia_calendario.py' -v
~~~

Las pruebas incluyen tres guiones ficticios de ejemplo, continuidad, bloqueo
de noticias sin fuentes, control estructural y simulación de respuesta local
de Ollama. No equivalen a una prueba de generación real en la Mac.

## Primera generación local: después de probar Ollama

Con Ollama instalado y el modelo qwen2.5-coder:14b disponible:

~~~sh
python3 tools/barriga_ia_narrativa.py \
  --tema "La última noche del farero y la carta que nunca entregó" \
  --nicho leyendas --naturaleza ficcion --duracion 35 \
  --salida local-data/narrativa/primera-prueba.json
~~~

Revisar el JSON: guion contiene las partes y evaluacion incluye
puntuacion_heuristica, desglose, segundos_estimados, bloqueos, advertencias
y apto_para_revision_humana. Un valor alto **no demuestra viralidad**.
Siempre está en falso publicacion_automatica_autorizada.

### Revisión de guiones sin llamar al modelo

~~~sh
python3 tools/barriga_ia_narrativa.py \
  --evaluar local-data/ejemplo-guion.json --duracion 35
~~~

La entrada de evaluación requiere un objeto JSON con:
titulo, nicho, naturaleza, gancho, historia y cierre; acepta además
personajes (lista), continuidad (objeto), fuentes (lista) y
duracion_objetivo_segundos (entero).

### Noticias y hechos comprobables

- Para generar una narración de naturaleza factual, aportar una o varias
  fuentes previas; las noticias deben ser factual.
- La presencia de fuentes **no constituye verificación externa**. Es obligatorio
  revisar fechas, contexto y afirmaciones antes de difundir noticias reales.
- Miniseries exige un JSON de ficha de continuidad (--biblia ruta.json).
- No hay navegación web, creación de video, publicación, conexión social ni
  cambios automáticos de parámetros de Ollama en esta fase.

## Evaluador: límites de la v0.1

La estimación temporal usa aproximadamente **150 palabras/minuto**.
Los puntajes usan reglas reproducibles de longitud, ritmo, puntuación y nombres
de personajes. No determinan originalidad profunda, exactitud histórica,
retención real, derechos de autor ni probabilidad de viralización.
Antes de que un reel pase a la canasta de 30 se requieren los analizadores,
filtros y un MP4 validado en la fase de producción.

## Protección de la versión principal

Este motor vive en la rama experimental, no sobrescribe puente_local.py,
no publica contenido y no incorpora datos privados al repositorio público.
Para probarlo en la Mac usar otra carpeta de trabajo o una rama temporal;
no reemplazar archivos de proyectos activos.

## Hallazgo de prueba real en Mac (23 de octubre de 2026)

El modelo local produjo el relato **«El Misterio de la Carta»**, con 175
palabras y duración estimada de 70 segundos para un objetivo de 35. La
puntuación heurística de 78/100 permitía incorrectamente pasar a revisión
con una desviación de duración del 100%. También aparecieron una relación
familiar ambigua y una localización de continuidad no sustentada en el
relato.

### Corrección v0.2 (experimental)

- La solicitud calcula un presupuesto aproximado de 150 palabras por minuto,
  con tolerancia propuesta ±15% para el prompt (35 s ≈ 88 palabras,
  intervalo deseado de 75 a 101).
- El evaluador **bloquea** guiones que se alejan más de
  `max(4 segundos, 20% de la duración objetivo)` de la duración estimada.
  El guion de 175 palabras debe quedar en `DEVOLVER_PARA_CORRECCION`,
  aunque la puntuación numérica siga siendo alta.
- Se añaden advertencias básicas de posible inconsistencia de parentesco
  y escenario no identificado literalmente en el relato; son pistas,
  **no** verificación semántica exhaustiva.
- El prompt solicita personajes/relaciones consistentes, acciones visuales,
  escenario anclado a la historia y un cierre concreto.
- La opción `--evaluar` acepta tanto un guion JSON como el informe
  previamente guardado que contiene una clave `guion`.
- Código de salida 2 para un guion no apto, incluso cuando se generó
  correctamente. Esto **no** indica fallo de conexión con Ollama.

### Prueba segura del primer resultado sin regenerarlo

~~~sh
cd "$HOME/Barriga-IA-Pruebas"
python3 tools/barriga_ia_narrativa.py \
  --evaluar local-data/narrativa/primera-prueba.json \
  --duracion 35
~~~

El primer resultado queda guardado para comparar. No borrarlo ni reemplazar
el archivo al probar un segundo guion: usar `segunda-prueba.json`.

**Pendiente:** ejecutar producción real en la Mac con el prompt nuevo y revisar
la calidad narrativa humana de personajes, causalidad y cierre.

## Segunda prueba real en Mac — afinamiento v0.3

El segundo guion («La carta del pasado») redujo la extensión de 175 a
**103 palabras**, equivalente a **41,2 segundos estimados**, pero todavía
sobrepasa los 35 segundos solicitados. El evaluador antiguo marcó 87/100
y `REVISION_HUMANA_PENDIENTE` aunque el cierre era genérico y existía
una posible falta ortográfica («forgero»).

### Correcciones implementadas en la rama experimental

- Presupuesto más preciso: 35 segundos = aproximadamente 88 palabras;
  intervalo de solicitud **79–97 palabras** (±10%).
- Bloqueo por diferencia superior al máximo entre tres segundos o el
  12% del objetivo. Para 35 segundos, diferencias superiores a **4,2 s**
  llevan a `DEVOLVER_PARA_CORRECCION`: el resultado de 41,2 s queda bloqueado.
- Alertas heurísticas de muletillas como «resuelven el caso» y «después
  de una serie de», y posibles erratas detectables como «forgero».
- Aviso sobre fichas de continuidad vacías cuando hay personajes.
- El resultado es un **filtro preliminar**, no una garantía de
  causalidad, atractivo emocional, exactitud o potencial viral.
- Se agregaron pruebas de regresión con exactamente 103 palabras,
  comprobación de bloqueos de duración y avisos editoriales.

La revisión del segundo guion **no modifica ni borra su archivo local**:

~~~sh
cd "$HOME/Barriga-IA-Pruebas"
python3 tools/barriga_ia_narrativa.py \
  --evaluar local-data/narrativa/segunda-prueba.json \
  --duracion 35
~~~

Cuando lo devuelva para corrección, no significa que haya fallado Ollama:
significa que el control editorial detectó un resultado no apto.
Conservar la primera y la segunda prueba para comparar con la tercera.


## Tercera prueba real y nueva reparación v0.4

La tercera ejecución local de Ollama devolvió **205 palabras / 82 segundos**,
cuando el objetivo era **35 segundos**. El evaluador rechazó correctamente
el guion con \`DEVOLVER_PARA_CORRECCION\`, pero el modelo no obedeció el
presupuesto narrativo.

### Solución implementada: ciclo limitado de reescritura

- Se puede cargar el guion **ya generado** sin volver a pedir un texto desde
  cero ni modificar los archivos previos.
- Si la duración está fuera del margen aprobado, y se trata de ficción o
  dramatización, Barriga IA pide **hasta dos reescrituras adicionales a
  Ollama local** con la premisa narrativa y un presupuesto concreto.
- Cada intento se evalúa individualmente; se conservan los intentos y los
  resultados completos en el **nuevo** archivo JSON de salida.
- Si alguno queda dentro del control estructural se devuelve para revisión
  editorial humana, sin autorizar publicación.
- Si ambos intentos adicionales fallan, se conserva el último borrador
  evaluable, se informa del rechazo y no se simula éxito.
- **No se reescriben contenidos factuales** automáticamente; requieren
  comprobación de fuentes y edición humana.
- Nunca se sobreescribe el JSON de entrada al usar la revisión de archivo;
  se bloquea una salida que apunte al mismo archivo.
- No es reentrenamiento del modelo, no tiene navegación web, no genera video,
  no publica Reels ni promete calidad viral.

### Paso de prueba en Mac

Actualizar la rama experimental dentro del worktree aislado y ejecutar:

~~~sh
cd "$HOME/Barriga-IA-Pruebas"
git fetch origin feature/barriga-ia-calendario-30-dias-20261023
git switch --detach FETCH_HEAD
python3 tools/barriga_ia_narrativa.py \
  --revisar-archivo local-data/narrativa/tercera-prueba.json \
  --nicho leyendas --naturaleza ficcion --duracion 35 \
  --max-revisiones 2 --resumen \
  --salida local-data/narrativa/cuarta-prueba.json
~~~

El terminal muestra un diagnóstico corto con duración estimada,
número de intentos, bloqueos y advertencias. El JSON de salida conserva
los borradores e informes de cada paso para auditoría.

Nota: devolver un código de salida 2 por "no apto" es intencional;
indica revisión humana necesaria, **no un fallo de Mac o de Ollama**.

Limitación: el control de palabras asume unas 150 palabras/minuto.
Debe cotejarse con la velocidad real de la voz y revisarse semánticamente
para evitar incoherencias entre personajes, escenas y desenlace.


## Cuarta prueba real: el modelo desobedece el presupuesto (v0.5)

Tras dos reescrituras completas, Ollama todavía entregó 192 palabras /
76,8 segundos para un objetivo de 35; el estado siguió correctamente como
\`DEVOLVER_PARA_CORRECCION\`. No se debe insistir con el mismo prompt.

### Nuevo método por bloques, independiente del editor anterior

Se añadió la herramienta \`tools/barriga_ia_por_bloques.py\`, que toma el
JSON local de la cuarta prueba y redacta **tres partes por separado**:

- Gancho: 5–8 palabras (unos 2–3 segundos a 150 ppm).
- Historia: 63–70 palabras para una pieza objetivo de 35 s.
- Cierre: 13–18 palabras para una pieza objetivo de 35 s.

La herramienta valida las palabras de cada pieza y, si no cumplen, permite
**un segundo intento en esa pieza**, sin reiniciar las ya aceptadas. Máximo:
seis llamadas a Ollama, 2 por cada bloque. A diferencia de recortar texto
a ciegas, la IA redacta una nueva versión abreviada. Se conserva la premisa
y las fichas de personajes originales como contexto.

El resultado se vuelve a evaluar globalmente. Puede ser devuelto para
revisión humana: los controles de extensión **no comprueban** continuidad
semántica, resolución emocional ni viralidad. No hay publicación automática.

### Ejecución local, sin sobrescribir los cuatro resultados previos

~~~sh
cd "$HOME/Barriga-IA-Pruebas"
git fetch origin feature/barriga-ia-calendario-30-dias-20261023
git switch --detach FETCH_HEAD
python3 -m unittest discover -s tests -p 'test_barriga_ia_por_bloques.py' -v
python3 tools/barriga_ia_por_bloques.py \
  --revisar-archivo local-data/narrativa/cuarta-prueba.json \
  --duracion 35 \
  --max-intentos 2 \
  --salida local-data/narrativa/quinta-prueba.json
~~~

Si \`quinta-prueba.json\` ya existe, se rechaza la operación y se solicita
otro nombre. El original nunca se reescribe. El archivo nuevo guarda el
historial de todas las piezas probadas y los diagnósticos.

Para contenidos noticiosos o factuales no se ejecuta esta reducción
automática: se necesita revisión humana y verificación de fuentes.

### Limitaciones pendientes

- El modo por bloques ya tiene pruebas simuladas, **aún no se ha probado
  con la instancia real de Ollama en la Mac del usuario**.
- El modelo local podría seguir sin ajustarse incluso por bloques.
- La narración final debe comprobarse con voces reales, pausas, legibilidad,
  continuidad de personajes y calidad humana antes de producción.
- El total máximo de 6 llamadas puede consumir minutos en un Mac sin GPU
  dedicada; no utilizar APIs de pago.


## Quinta prueba real: gancho rechazado (v0.6)

El control por secciones corrió y **10 pruebas locales pasaron**, pero
Ollama no entregó un gancho entre **5 y 8 palabras** en dos intentos.
El informe quedó en \`local-data/narrativa/quinta-prueba.json\`, con
\`BLOQUE_RECHAZADO_GANCHO\` y sin guion final. Esto es una falla de
generación **real**, no de las pruebas simuladas. La herramienta no
inventó aprobación.

### Ajustes posteriores, todavía sin validar en Ollama real

- El prompt del gancho ahora es muy corto, emplea únicamente la premisa
  pertinente y muestra un ejemplo de **longitud** sin copiar el tema.
- Se reduce el presupuesto de generación para el gancho (75 tokens), y
  se diferencian los presupuestos para historia y cierre.
- El JSON anterior se preserva intacto. El usuario puede proporcionar
  voluntariamente un \`--gancho-aprobado\` de 5 a 8 palabras para seguir
  probando historia y cierre sin atascarse en el primer bloque.
  **El gancho manual no se presenta como generado por Ollama.**
- El control no recorta frases automáticamente ni acepta ganchos demasiado
  largos, pues podrían perder coherencia o sentido.
- **Estas mejoras requieren prueba real en la Mac.**

### Diagnóstico de la quinta prueba sin generar nada nuevo

~~~sh
cd "$HOME/Barriga-IA-Pruebas"
python3 -c 'import json; p=json.load(open("local-data/narrativa/quinta-prueba.json")); [print("Intento", x["intento"], "Palabras", x["palabras"], "Texto", repr(x["texto"]), "Error", x.get("error","")) for x in p["historial_bloques"]]'
~~~

### Sexta prueba del gancho revisado (después de la inspección)

Actualizar el worktree y cambiar el archivo de salida por uno nuevo,
por ejemplo \`sexta-prueba.json\`. No volver a apuntar al quinto archivo:
se trata de un resultado histórico.

Si un gancho creado y **aprobado por una persona** debe utilizarse, se
puede pasar \`--gancho-aprobado "¡La carta de ayer rompió treinta años!"\`
(8 palabras) para saltar únicamente el bloque de gancho. Esta opción
no resuelve por sí sola la autonomía completa del motor narrativo.

La duración es aproximada: 150 palabras/minuto. La aprobación final
requiere verificar narración con voz real, pertinencia, continuidad,
gancho y final; ningún puntaje implica viralidad.
