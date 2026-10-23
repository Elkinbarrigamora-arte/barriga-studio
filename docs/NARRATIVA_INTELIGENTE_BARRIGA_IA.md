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
