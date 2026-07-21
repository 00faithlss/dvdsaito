"""
Ajustes de color que controla el usuario con los sliders.

Toma el arreglo RGB y el diccionario de valores, y aplica brillo, contraste,
luces y sombras, temperatura, tinte, saturacion y descolorido en ese orden.
"""

import numpy as np

from .helpers import lum, contrast, saturation, fade


def apply_color(rgb, s):
    out = rgb
    if s["brightness"]:
        out = out * (1.0 + 0.8 * s["brightness"])
    if s["contrast"]:
        out = contrast(out, s["contrast"])

    # luces y sombras por separado, segun que tan claro es cada pixel
    if s["highlights"] or s["shadows"]:
        l = lum(np.clip(out, 0, 1))
        if s["highlights"]:
            out = out + s["highlights"] * 0.35 * (l ** 2)[..., None]
        if s["shadows"]:
            out = out + s["shadows"] * 0.35 * ((1 - l) ** 2)[..., None]

    if s["temperature"]:
        out = out.copy()
        out[..., 0] *= (1.0 + 0.3 * s["temperature"])   # mas rojo = mas calido
        out[..., 2] *= (1.0 - 0.3 * s["temperature"])
    if s["tint"]:
        out = out.copy()
        out[..., 1] *= (1.0 - 0.22 * s["tint"])          # verde contra magenta

    if s["saturation"]:
        out = saturation(out, s["saturation"])
    if s["fade"]:
        out = fade(out, s["fade"])
    return out
