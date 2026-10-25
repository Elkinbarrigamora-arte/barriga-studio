"""Cliente limitado para generar una imagen con Draw Things en esta misma Mac.

No envía archivos ni proyectos a servicios externos. La salida permanece en memoria
hasta que el navegador la muestra o el usuario la descarga explícitamente.
"""
import base64
import binascii
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DRAW_THINGS = "http://127.0.0.1:7860"
MAX_REPLY = 32 * 1024 * 1024
MAX_IMAGE = 20 * 1024 * 1024

PRESETS = {
    "planeta": {
        "name": "Planeta desde órbita",
        "prompt": (
            "A single Earth-like exoplanet seen from high orbit, real NASA-style "
            "spacecraft photograph, entire curved planetary disk against black space, "
            "fine layered cloud systems, atmospheric haze and limb scattering, "
            "physically plausible sunlight, accurate terminator line, natural colors, "
            "subtle surface geography, distant stars barely visible, telephoto optics"
        ),
    },
    "esmeralda": {
        "name": "Esmeralda macro",
        "prompt": (
            "Exactly one natural Colombian emerald-cut emerald gemstone, professional "
            "100mm macro product photograph, realistic polished facets, visible subtle "
            "mineral inclusions and internal refraction, restrained highlights, "
            "deep natural green hue, diffused studio softboxes, black velvet surface, "
            "black backdrop, tack-sharp central facets, genuine fine-jewelry photography"
        ),
    },
    "universo": {
        "name": "Universo profundo",
        "prompt": (
            "Long-exposure astronomical photograph of a distant spiral galaxy, "
            "realistic star-field density, subtle dusty arms and glowing core, "
            "high dynamic range with controlled highlights, delicate color variation, "
            "deep black sky, fine astrophotographic grain, observatory imaging"
        ),
    },
    "libre": {"name": "Descripción personalizada", "prompt": ""},
}

NEGATIVE = (
    "cartoon, anime, painting, concept art, digital illustration, game art, "
    "3d render, CGI, plastic, toy, childish drawing, flat textures, fantastical "
    "lighting, extreme glow, oversaturated colors, multiple subjects, collage, "
    "distorted geometry, blurry, text, watermark, signature, logo"
)


class DrawThingsError(RuntimeError):
    """Error presentable sin filtrar rutas ni respuestas privadas."""


def build_payload(args):
    if not isinstance(args, dict):
        raise ValueError("Solicitud inválida")
    preset = args.get("preset", "planeta")
    if not isinstance(preset, str) or preset not in PRESETS:
        raise ValueError("Perfil de imagen desconocido")
    prompt = args.get("prompt", "")
    if not isinstance(prompt, str) or not 8 <= len(prompt.strip()) <= 1800:
        raise ValueError("Describe la imagen con 8 a 1800 caracteres")
    steps = args.get("steps", 35)
    guidance = args.get("guidance_scale", 6)
    seed = args.get("seed", -1)
    if isinstance(steps, bool) or type(steps) is not int or not 20 <= steps <= 45:
        raise ValueError("Los pasos deben estar entre 20 y 45")
    if (isinstance(guidance, bool) or type(guidance) not in (int, float)
            or not 3 <= guidance <= 8):
        raise ValueError("La guía debe estar entre 3 y 8")
    if isinstance(seed, bool) or type(seed) is not int or not -1 <= seed < 2**31:
        raise ValueError("Semilla inválida")
    return {
        "prompt": prompt.strip(),
        "negative_prompt": NEGATIVE,
        "width": 1024,
        "height": 1024,
        "steps": steps,
        "guidance_scale": guidance,
        "seed": seed,
        "batch_size": 1,
        "batch_count": 1,
    }


def _read_limited(response):
    data = response.read(MAX_REPLY + 1)
    if len(data) > MAX_REPLY:
        raise DrawThingsError("La respuesta de Draw Things es demasiado grande")
    return data


def check_connection():
    try:
        with urlopen(DRAW_THINGS + "/", timeout=5) as response:
            if response.status != 200:
                raise DrawThingsError("Draw Things no respondió correctamente")
            data = json.loads(_read_limited(response))
        if not isinstance(data, dict):
            raise ValueError("configuración no disponible")
        return {"activo": True, "modelo": str(data.get("model", "no indicado"))[:200]}
    except (HTTPError, URLError, TimeoutError, OSError, ValueError,
            json.JSONDecodeError) as exc:
        raise DrawThingsError(
            "Draw Things no está disponible en 127.0.0.1:7860; "
            "abre la aplicación y activa su servidor API"
        ) from exc


def generate_image(payload):
    request = Request(
        DRAW_THINGS + "/sdapi/v1/txt2img",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=900) as response:
            if response.status != 200:
                raise DrawThingsError("El generador no devolvió HTTP 200")
            result = json.loads(_read_limited(response))
        images = result.get("images") if isinstance(result, dict) else None
        if not isinstance(images, list) or len(images) != 1 or not isinstance(images[0], str):
            raise DrawThingsError("Draw Things no devolvió exactamente una imagen")
        encoded = images[0].split(",")[-1]
        image = base64.b64decode(encoded, validate=True)
        if not image or len(image) > MAX_IMAGE:
            raise DrawThingsError("La imagen recibida está vacía o excede el límite")
        if image.startswith(b"\x89PNG\r\n\x1a\n"):
            return image, "image/png"
        if image.startswith(b"\xff\xd8\xff"):
            return image, "image/jpeg"
        raise DrawThingsError("Draw Things devolvió un formato de imagen desconocido")
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise DrawThingsError(
            "Falló la generación local; comprueba Draw Things, el modelo y su memoria"
        ) from exc
    except (ValueError, TypeError, binascii.Error) as exc:
        raise DrawThingsError("Draw Things devolvió una respuesta ilegible") from exc
