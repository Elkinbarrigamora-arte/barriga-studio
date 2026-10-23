# Plan maestro · Barriga IA y Barriga Studio

## Objetivo
Convertir el prototipo en una plataforma audiovisual privada, operativa y medible. Barriga IA debe poder proponer cambios de código sobre el Studio, conservar trazabilidad, ejecutar comprobaciones y detenerse ante errores, sin presentarse como inteligencia ilimitada ni afirmar capacidades de motores no probados.

## Flujo del producto
1. Idea → guion original con **gancho, historia y cierre narrativo u oferta comercial** según corresponda.
2. Desglose en escenas con duración y ficha persistente de personajes, rostro, ropa, objetos, posición y movimientos.
3. Elección entre exactamente **Frutas dramáticas 3D**, **Fotorrealismo cinematográfico** y **Animación 3D de personajes humanos**.
4. Voces en español por personaje, con motor confirmado y duración medida.
5. Imágenes y video con movimiento corporal real; mostrar **NO DISPONIBLE** si falta un motor validado.
6. Previsualización real, cuatro revisiones editoriales, cuatro filtros de calidad, descarga de resultado y biblioteca de proyectos.

## Prioridades de ingeniería
- **P0: Autodesarrollo controlado.** Ollama local propone parches; la herramienta comprueba estructura y sintaxis, crea un respaldo Git y guarda commits locales. No ejecuta comandos propuestos por el modelo ni publica cambios automáticamente.
- **P1: Editor modular y revisión profesional de guiones.** Estructura y continuidad, sin romper los proyectos guardados.
- **P2: Escenas y continuidad.** Contratos de datos para personajes, diálogos, referencias, duraciones y estados de trabajo.
- **P3: Persistencia robusta.** Mantener compatibilidad con `barriga-studio-projects-v1` y con respaldo JSON; sincronización autenticada es una tarea separada.
- **P4: Motores reales.** Verificar video, voz, imagen, almacenamiento y FFmpeg antes de habilitar generación.
- **P5: QA, distribución y despliegue.** Pruebas funcionales de navegador, voz/video de 5 segundos, 30 segundos y descarga al dispositivo.

## Límites verificables (23 de octubre de 2026)
- En la Mac: Ollama con `qwen2.5-coder:14b` respondió; el puente local de guiones devolvió HTTP 200 y el usuario vio el resultado.
- El supervisor anterior solo realizaba diagnóstico, no desarrollo autónomo.
- No hay evidencia todavía de video neuronal, voz, sincronización remota ni ejecución automática continua.
- El repositorio GitHub es **público** actualmente. No subir claves, material privado, respaldos con datos, videos ni fotos a GitHub.
- Desarrollo local con herramientas gratuitas. Sin APIs de pago ni apertura pública de puertos.

## Política de ejecución
- Cambiar archivos de producto, no secretos, modelos de IA ni herramientas críticas del agente.
- Bloquear cambios con sintaxis defectuosa y restaurar archivos anteriores.
- Diferenciar validación de sintaxis de pruebas funcionales: una no implica la otra.
- No borrar trabajo sin copia Git. No activar despliegue remoto automático.
- Para iterar en la Mac: ejecutar `python3 tools/agente_desarrollo.py --studio "$PWD" --ciclos 5` después de actualizar la carpeta. Requiere Ollama y Node.js local para validar JS.
