# Barriga IA — remediación inicial y preparación de aprendizaje continuo

**Fecha:** 2026-10-24  
**Rama de trabajo:** `fix/barriga-ia-reanudar-sexta-20261023`  
**Repositorio:** `Elkinbarrigamora-arte/barriga-studio`

## Qué se implementó realmente

1. **Contrato de duración extremo a extremo.** El selector existente del Studio transmite `duracion_objetivo_segundos` a la API `POST /api/guion`. El servidor valida 20–60 segundos, rechaza booleanos/cadenas no válidas y propaga la duración al motor `ejecutar_motor`. El valor queda guardado en SQLite, vuelve en la API y se presenta en la vista de resultados. Se conserva el valor 35 s como respaldo para clientes antiguos que omitan el campo.
2. **Rechazos narrativos más específicos.** Para premisas donde desaparece un familiar, el verificador exige que la HISTORIA mantenga explícitamente la desaparición y su duración (no basta con colocar esos hechos en el GANCHO). Detecta además patrones acotados de cierre inconcluso como «la organización planeaba matarlo; Juan promete protegerlo», cuando no se explican los hechos concretos que resuelven el misterio. Son **heurísticas conservadoras**, no comprensión semántica garantizada.
3. **Auditoría local sin inferencia.** `tools/barriga_ia_mejora_continua.py` lee el SQLite existente en **modo solo lectura** y emite un resumen estadístico (estados, duración, latencias disponibles, número de llamadas y evaluación heurística). No registra relatos privados en el resumen.
4. **Curación restrictiva de datos.** Opcionalmente permite exportar JSONL solo de generaciones que incluyan simultáneamente `aprobacion_humana: true`, `consentimiento_entrenamiento: true`, `apto_para_revision_humana: true`, estado editorial correcto, campos de guion completos y ninguna alerta de fidelidad. El dataset se crea con permisos 0600 sin sobrescribir otro archivo. Si no hay registros consentidos, no crea dataset. Esto es **preparación de ejemplos**, **no entrenamiento de pesos**.
5. **Regresiones y CI.** Se añadieron casos para duración 30/35/60, rechazos de API malformada, conservación de los 20 años en HISTORIA, cierres sin revelación, ejemplos válidos y selección segura para datasets.

## Evidencia

- GitHub Actions corrida `40137607040`: **196 pruebas de unittest** correctas en Python 3.9 y 3.11; **29 comprobaciones interactivas** del Studio.
- Las pruebas narrativas y los datos de la auditoría provienen de reglas y ejemplos de prueba; **no se ejecutó un benchmark nuevo con Ollama en el Mac**.
- No se tocaron registros reales, no se cambió `main`, no se promovió modelo ni se activaron pagos.

## Cómo usar la auditoría desde la instalación local (una vez actualizada la rama)

```bash
cd "$HOME/Barriga-IA-Pruebas"
python3 tools/barriga_ia_mejora_continua.py
```

Imprime solamente **estadísticas agregadas** de `local-data/guiones-locales.sqlite3`, sin escribir datos. Para consultar los registros disponibles, se necesita acceso a esa base en el Mac. Un número bajo de aprobaciones humanas no indica un defecto de SQLite: actualmente la interfaz no registra consentimiento individual de entrenamiento.

**Exportación condicional explícita** (no ejecutar sin haber otorgado aprobación y permiso por generación):

```bash
python3 tools/barriga_ia_mejora_continua.py \
  --exportar-jsonl "$HOME/barriga-ia-entrenamiento-aprobado.jsonl"
```

Si no existen ejemplos aprobados y consentidos, esta acción produce **cero ejemplos y ningún archivo**. No se entrena ningún modelo. El directorio y los datos de entrenamiento deben permanecer privados.

## Qué falta para el entrenamiento paramétrico real

1. **Acceso y auditoría de hardware:** confirmar chip Apple Silicon o Intel, memoria unificada/RAM, espacio disponible, versión de macOS, uso de GPU y rendimiento de Ollama. No inferir viabilidad de LoRA para un modelo de 14B sin estas mediciones.
2. **Flujo de feedback editorial:** implementar un mecanismo explícito, preferiblemente en una tabla separada y sin sobrescribir generaciones originales, para aprobar/rechazar/corregir y autorizar el uso para entrenamiento. Actualmente las generaciones normales no cuentan con consentimiento explícito.
3. **Dataset suficiente y curado:** coleccionar ejemplos diversos de calidad verificable, con particiones de entrenamiento/validación/test sin contaminación.
4. **Compatibilidad de pesos:** verificar licencia del modelo, formato de pesos entrenables, tokenizador, compatibilidad de MLX/Metal y exportación segura de adaptadores a un runtime de inferencia.
5. **Benchmark de modelos:** establecer línea base con pruebas reales de Ollama y puntuaciones editoriales humanas, no solo validaciones heurísticas.
6. **Orquestación programada:** instalar un proceso local mediante `launchd` únicamente con permiso del usuario, con límites de recursos, pausa, bloqueo de concurrencia, checkpoints y auditoría. Si el Mac se apaga o suspende, el proceso local no trabaja.
7. **Entrenamiento experimental:** realizar una corrida supervisada con autorización de recursos, conservar el modelo base, evaluar el adaptador candidato frente al baseline y no activarlo sin aprobación explícita.

## Orden recomendado para el siguiente ciclo

- Validar la actualización de 30/60 segundos con una generación real de Ollama en el Mac.
- Registrar feedback humano estructurado sin alterar guiones antiguos.
- Ejecutar reporte offline de toda la base.
- Preparar benchmark narrativo y datos consentidos.
- Auditar viabilidad del hardware para un eventual adaptador LoRA/MLX.
- Habilitar tareas periódicas controladas **solo tras autorizar su instalación**.

**Estado:** Remediación de primera prioridad implementada y CI verde; aprendizaje operativo preparado parcialmente; **entrenamiento incremental continuo de pesos y agente residente todavía no implementados ni activados**.
