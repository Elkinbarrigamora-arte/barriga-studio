# Barriga IA — investigación autónoma local (versión de prueba)

## Objetivo
Leer información pública verificable sobre motores abiertos de IA, registrar fecha, fuente y enlace, y proponer qué vale la pena probar en Barriga Studio. **No copia plataformas comerciales**, no instala herramientas ni modelos y no genera videos.

## Fuentes iniciales
- Versiones públicas de Ollama (GitHub Atom).
- Versiones públicas de ComfyUI (GitHub Atom).
- Versiones públicas de llama.cpp (GitHub Atom).

ClipShort es una referencia de experiencia de usuario; este módulo **no afirma poder investigar su plataforma de manera automática**. Solo añadir una fuente suya si se verifica que publica novedades accesibles y autorizadas.

## Privacidad
Los resultados se guardan únicamente bajo `~/Library/Application Support/BarrigaStudio/Investigacion/`, fuera del repositorio público y fuera del navegador. Los títulos y resúmenes son datos externos **no confiables**: nunca se ejecutan, ni se interpretan como órdenes. No se publican guiones, personajes, imágenes o proyectos.

## Cómo probar
Desde Terminal:

```bash
cd "$HOME/barriga-studio"
python3 -m unittest discover -s tests -p 'test_investigador_autonomo.py' -v
python3 tools/investigador_autonomo.py --una-vez
```

Los informes son `hallazgos.json` y `ultimo_reporte.json` en la carpeta privada indicada. El resultado `SIN_FUENTES` significa que no se recuperó ningún canal: no hay que inventar hallazgos.

## Ejecución periódica (solo tras aprobar pruebas)
`python3 tools/investigador_autonomo.py --preparar-programacion` escribe el LaunchAgent, **sin activarlo**. Si luego el usuario decide activarlo, ejecutar `launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/com.barriga.studio.investigacion.plist"`. El intervalo es cada 12 horas mientras el Mac esté activo. Desactivar: `launchctl bootout "gui/$(id -u)/com.barriga.studio.investigacion"`.

## Próximo paso
Añadir conectores de fuentes que tengan acceso público permitido (blogs y documentación); opcionalmente pedir a Ollama una síntesis con referencias, aislando contenido externo y verificando cada propuesta antes de hacer cambios.
