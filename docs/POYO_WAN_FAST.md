# PoYo Wan 2.2 Fast · Barriga Studio

**Estado:** adaptador experimental en rama separada; NO conectado a interfaz; NO se ha generado video ni cobrado nada.

Fuente técnica: https://poyo.ai/models/wan-2-2-fast/llms.txt

- API submit: `POST https://api.poyo.ai/api/generate/submit`
- API status: `GET https://api.poyo.ai/api/generate/status/{task_id}`
- Modelo: `wan2.2-text-to-video-fast`
- Prototipo: `9:16`, `480p`, texto a video
- Tarifa publicada: 0.03 USD (6 créditos) por generación 480p, no por segundo
- Límite acordado para pruebas: 5 USD
- Estado final: `finished` o `failed`; video en `data.files`

## Probar sin gastar

Desde el repositorio actualizado a esta rama:

```bash
python3 tools/poyo_wan_fast.py --prompt "A cowboy riding at sunset, cinematic tracking shot"
```

Imprime la solicitud que enviaría y **DRY_RUN_NO_CHARGE**. No necesita clave ni hace llamadas externas.

## Consultar una tarea ya creada

Poner la API key en una variable de entorno **solo en la Mac**, nunca en GitHub ni en chats.

```bash
export POYO_API_KEY="TU_CLAVE_PRIVADA"
python3 tools/poyo_wan_fast.py --status ID_DE_TAREA
```

Consultar estado no envía una generación nueva.

## Enviar una generación pagada (solo con autorización de gasto)

```bash
python3 tools/poyo_wan_fast.py --prompt "A cowboy riding at sunset, cinematic tracking shot" --confirm-charge
```

El programa reserva un estimado de 0.03 USD en `~/.barriga-studio/poyo-budget.json` antes de enviar. Esto es **un control local orientativo**, NO un límite de facturación del proveedor; no cubre otras aplicaciones, máquinas o procesos concurrentes. En respuesta incierta, deja la reserva para evitar un reintento automático que podría duplicar costos. Revisar tareas y cargos en PoYo antes de intentar de nuevo. Los proyectos y la clave no se suben al repositorio.

## Próxima fase

1. Verificar saldo en PoYo y duración real de salida de un clip.
2. Probar una sola generación con presupuesto autorizado.
3. Integrar UI con estados persistentes y previsualización real.
4. Añadir flujo imagen a video (referencias de personajes) y combinación MP4 con voz existente.
5. Probar FFmpeg y almacenamiento persistente, aún no verificados.

No considerar 35 segundos como siete clips garantizados: la duración por generación no está confirmada.
