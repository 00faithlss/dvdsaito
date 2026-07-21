"""
El pipeline que junta todo.

`process` recibe una imagen PIL y el diccionario de ajustes, y devuelve la
imagen editada. El orden importa: primero el filtro y el color, despues la
textura y la geometria de pixel, luego los efectos de PIL y al final el
estirado, para que el grano tambien se estire.

`DEFAULTS` es el estado inicial de la edicion y `ASPECTS` las relaciones de
aspecto disponibles.
"""

import numpy as np
from PIL import Image, ImageFilter

from .helpers import grain, vignette, leak
from .filters import FILTERS, f_original
from .adjustments import apply_color
from . import effects


DEFAULTS = {
    "filter": "Original",
    "filter_strength": 1.0,    # 0..1, cuanto se mezcla el filtro
    # color
    "brightness": 0.0,         # -1..1
    "contrast": 0.0,           # -1..1
    "saturation": 0.0,         # -1..1
    "temperature": 0.0,        # -1..1, frio o calido
    "tint": 0.0,               # -1..1, verde o magenta
    "highlights": 0.0,         # -1..1
    "shadows": 0.0,            # -1..1
    "sharpen": 0.0,            # -1..1, desenfoque o nitidez
    # textura
    "grain": 0.0,              # 0..1
    "vignette": 0.0,           # 0..1
    "fade": 0.0,               # 0..1
    # lo-fi
    "lowres": 0.0,             # 0..1, baja resolucion
    "jpeg": 0.0,               # 0..1, compresion
    "leak": 0.0,               # 0..1, fuga de luz
    "datestamp": False,        # sello de fecha
    "date_fmt": "ymd",         # formato del sello: ymd, mdy, dmy, apos, jp
    "date_value": "",          # fecha a estampar "AAAA-MM-DD"; vacio = hoy
    # proporciones
    "aspect": "Original",      # deforma para alcanzar una relacion, no recorta
    "stretch_x": 1.0,          # 0.5..2.0, ancho
    "stretch_y": 1.0,          # 0.5..2.0, alto
    "out_w": 0,                # tamano exacto en px; 0 significa usar aspect/stretch
    "out_h": 0,
}

# Relacion = ancho / alto. None deja la imagen como esta.
ASPECTS = {
    "Original": None,
    "1:1": 1.0,
    "4:3": 4 / 3,
    "3:4": 3 / 4,
    "16:9": 16 / 9,
    "9:16": 9 / 16,
}


def output_size(size, s):
    """Calcula el tamano final de la imagen segun los ajustes de proporcion.

    Si hay un tamano manual en px (out_w y out_h), gana ese. Si no, usa la
    relacion de aspecto y los multiplicadores de ancho y alto.
    """
    w0, h0 = size
    ow = int(s.get("out_w", 0) or 0)
    oh = int(s.get("out_h", 0) or 0)
    if ow > 0 and oh > 0:
        return max(1, ow), max(1, oh)
    w, h = w0, h0
    ratio = ASPECTS.get(s["aspect"])
    if ratio:
        h = int(round(w0 / ratio))
    w = max(1, int(round(w * s["stretch_x"])))
    h = max(1, int(round(h * s["stretch_y"])))
    return w, h


def apply_geometry(img, s):
    """Estira la imagen al tamano calculado. Deforma en vez de recortar."""
    w, h = output_size(img.size, s)
    if (w, h) != img.size:
        img = img.resize((w, h), Image.LANCZOS)
    return img


def process(img, settings):
    """Aplica la edicion completa y devuelve una imagen PIL nueva."""
    s = {**DEFAULTS, **settings}
    rgb = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    original = rgb.copy()

    func, post = FILTERS.get(s["filter"], (f_original, {}))

    # 1) filtro de color, mezclado segun la intensidad
    if s["filter"] != "Original":
        filtered = np.clip(func(rgb.copy()), 0, 1)
        k = float(s["filter_strength"])
        rgb = original * (1 - k) + filtered * k

    # 2) ajustes de color del usuario
    rgb = apply_color(rgb, s)

    # 3) textura y fuga de luz
    if s["grain"]:
        rgb = grain(rgb, s["grain"])
    if s["vignette"]:
        rgb = vignette(rgb, s["vignette"])
    if s["leak"]:
        rgb = leak(rgb, s["leak"] * 0.8, origin=(1.0, 0.0), color=(1.0, 0.5, 0.2))

    # geometria de pixel del preset (espejo, ojo de pez)
    if "geom" in post:
        rgb = post["geom"](rgb)

    rgb = np.clip(rgb, 0, 1)
    out = Image.fromarray((rgb * 255).astype(np.uint8), "RGB")

    # transformacion PIL del preset (dibujo, comic, relieve)
    if "pil" in post:
        out = post["pil"](out)

    # 4) efectos de pixel, combinando lo del preset con los sliders del usuario
    lowres = max(post.get("lowres", 0), s["lowres"])
    jpeg = max(post.get("jpeg", 0), s["jpeg"])
    bloom = post.get("bloom", 0)
    tone = post.get("halftone", 0)
    colors = post.get("dither", 0)
    gb = post.get("gameboy", False)
    poster = post.get("posterize", 0)
    sharpen_total = s["sharpen"] + post.get("sharpen", 0)
    stamp = post.get("datestamp", False) or s["datestamp"]

    if bloom:
        out = effects.bloom(out, bloom)
    if gb:
        out = effects.gameboy(out)
    elif colors:
        out = effects.dither(out, colors)
    elif poster:
        out = effects.posterize(out, poster)
    if tone:
        out = effects.halftone(out, tone)
    if lowres:
        out = effects.pixelate(out, lowres)
    if jpeg:
        out = effects.jpeg(out, jpeg)

    if sharpen_total > 0:
        out = out.filter(ImageFilter.UnsharpMask(radius=2, percent=int(sharpen_total * 150)))
    elif sharpen_total < 0:
        out = out.filter(ImageFilter.GaussianBlur(radius=-sharpen_total * 3))

    if stamp:
        out = effects.datestamp(out, s.get("date_fmt", "ymd"), s.get("date_value", ""))

    # 5) estirado al final, asi el grano y la textura tambien se estiran
    out = apply_geometry(out, s)
    return out
