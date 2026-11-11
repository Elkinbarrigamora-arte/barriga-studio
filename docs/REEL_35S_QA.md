# B STUDIO Élite · Ensamblaje verificado de reels

Este módulo **no llama a PoYo ni gasta créditos**. Usa únicamente clips de video existentes y una voz previamente generada. La aplicación final todavía necesita integrar estos módulos en su backend y biblioteca.

## Entradas

Requiere FFmpeg y FFprobe, instalados en la Mac y disponibles desde Terminal.

Guardar un JSON de manifiesto como ejemplo (sustituir las rutas por archivos existentes y verificados):

```json
{
  "target_seconds": 35,
  "voice": "/Users/USUARIO/Movies/BarrigaStudio/voz-final-es.wav",
  "scenes": [
    {"file": "/Users/USUARIO/Movies/BarrigaStudio/escena-1.mp4", "seconds": 5},
    {"file": "/Users/USUARIO/Movies/BarrigaStudio/escena-2.mp4", "seconds": 5},
    {"file": "/Users/USUARIO/Movies/BarrigaStudio/escena-3.mp4", "seconds": 5},
    {"file": "/Users/USUARIO/Movies/BarrigaStudio/escena-4.mp4", "seconds": 5},
    {"file": "/Users/USUARIO/Movies/BarrigaStudio/escena-5.mp4", "seconds": 5},
    {"file": "/Users/USUARIO/Movies/BarrigaStudio/escena-6.mp4", "seconds": 5},
    {"file": "/Users/USUARIO/Movies/BarrigaStudio/escena-7.mp4", "seconds": 5}
  ]
}
```

Los archivos se deben medir realmente: escenas más cortas que su tiempo asignado se rechazan (sin congelar fotogramas para simular movimiento). La narración debe medir 35 ±0,5 segundos para evitar cortar el final de las frases.

## Ejecución

```bash
python3 tools/bstudio_reel_assemble.py manifest.json --dry-run
python3 tools/bstudio_reel_assemble.py manifest.json
```

Salida predeterminada: `~/Movies/BarrigaStudio/reel-35s.mp4`. El sistema impide sobreescribir ese archivo por accidente. La exportación usa H.264/AAC MP4, 480×854, 30 fps, con audio obligatorio. FFprobe comprueba la duración, dimensiones y pistas después de exportar. Un error no publica un MP4 como final.

## Estado actual

- Programa y pruebas unitarias en una rama GitHub separada.
- Prueba de integración **con archivos reales de la Mac pendiente**.
- No se han conectado las voces existentes; el módulo recibe un archivo final de narración cuando esté verificado.
- No existe todavía garantía de 35 segundos en la generación de PoYo: el pipeline solo ensambla duraciones validadas y no hace supuestos sobre el proveedor.
