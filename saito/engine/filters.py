"""
Los filtros de la app y como se agrupan.

Cada filtro toma un arreglo RGB en [0, 1] y devuelve otro igual. Algunos
efectos (espejo, ojo de pez, dibujo, comic, relieve) trabajan mejor con PIL o
moviendo pixeles, asi que estan aparte y se aplican en otra etapa del pipeline.

Al final estan `FILTER_CATEGORIES` (que filtros aparecen en cada categoria) y
`FILTERS`, que asocia cada nombre con su funcion de color y una lista de
efectos extra (pixelado, JPEG, fecha, etc.) que agrega ese preset.
"""

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from .helpers import (lum, contrast, saturation, desaturate, fade, tint,
                      colormap, grain, vignette, chroma, scanlines, rgb_mask,
                      leak, glitch)


def f_original(rgb):
    return rgb


# ------------------------------------------------------------------- Digicam
def f_ccd(rgb):
    # camara digital vieja: color saturado, con punch y un toque calido.
    out = saturation(rgb, 0.28)
    out = contrast(out, 0.14)
    out = tint(out, (1.03, 1.0, 0.99))
    return grain(out, 0.10)


def f_digicam03(rgb):
    out = contrast(rgb, 0.20)
    out = saturation(out, -0.05)
    out = vignette(out, 0.25)
    return grain(out, 0.12)


def f_proccd(rgb):
    out = tint(rgb, (0.97, 1.02, 1.07))    # frio, tirando a verde azulado
    out = desaturate(out, 0.08)
    return contrast(out, 0.10)


def f_ixus(rgb):
    out = saturation(rgb, 0.15)
    out = contrast(out, 0.10)
    out = tint(out, (1.05, 1.0, 0.95))
    out = vignette(out, 0.25)
    return grain(out, 0.10)


def f_webcam(rgb):
    out = desaturate(rgb, 0.20)
    out = tint(out, (1.0, 1.06, 0.98))     # verdoso
    out = contrast(out, -0.05)
    return grain(out, 0.22)


def f_iphone4(rgb):
    out = contrast(rgb, 0.12)
    out = tint(out, (0.99, 1.02, 1.03))
    return saturation(out, 0.05)


def f_nokia(rgb):
    out = contrast(rgb, 0.25)
    out = saturation(out, 0.10)
    return tint(out, (0.98, 1.0, 1.04))


def f_cctv(rgb):
    g = lum(rgb)[..., None]
    out = g * np.array([0.6, 1.0, 0.7], dtype=np.float32)   # verde de monitor
    out = contrast(out, 0.15)
    return scanlines(out, 0.4)


def f_nightvision(rgb):
    g = lum(rgb)
    out = np.stack([g * 0.15, np.clip(g * 1.25, 0, 1.4), g * 0.15], axis=-1)
    out = grain(out, 0.20)
    return vignette(out, 0.5)


# ---------------------------------------------------------------- Analogico
def f_disposable(rgb):
    out = saturation(rgb, 0.10)
    out = contrast(out, 0.15)
    out = tint(out, (1.05, 1.0, 0.96))
    out = vignette(out, 0.35)
    return grain(out, 0.18)


def f_huji(rgb):
    out = fade(rgb, 0.20)
    out = tint(out, (1.05, 1.0, 0.96))
    out = saturation(out, 0.05)
    out = leak(out, 0.55, origin=(1.0, 0.15), color=(1.0, 0.35, 0.25))
    return grain(out, 0.12)


def f_polaroid(rgb):
    out = fade(rgb, 0.55)
    out = saturation(out, -0.12)
    out = tint(out, (1.05, 1.02, 0.95))
    return contrast(out, -0.08)


def f_portra(rgb):
    out = tint(rgb, (1.03, 1.0, 0.98))
    out = fade(out, 0.12)
    out = saturation(out, -0.02)
    return contrast(out, -0.03)


def f_velvia(rgb):
    out = saturation(rgb, 0.35)
    out = contrast(out, 0.15)
    return tint(out, (1.0, 1.0, 1.03))


def f_kodakgold(rgb):
    out = tint(rgb, (1.06, 1.02, 0.9))
    out = saturation(out, 0.15)
    return contrast(out, 0.05)


def f_crossprocess(rgb):
    l = lum(rgb)[..., None]
    shadow = np.array([0.0, 0.5, 0.55])    # sombras hacia cian
    high = np.array([1.0, 0.95, 0.2])      # luces hacia amarillo
    t = shadow * (1 - l) + high * l
    out = rgb * 0.7 + t * 0.3
    out = contrast(out, 0.25)
    return saturation(out, 0.10)


def f_fadematte(rgb):
    out = fade(rgb, 0.5)
    out = saturation(out, -0.1)
    return contrast(out, -0.1)


def f_sepia(rgb):
    l = lum(rgb)[..., None]
    return np.clip(l * np.array([1.07, 0.82, 0.57]), 0, 1)


def f_noir(rgb):
    return contrast(desaturate(rgb, 1.0), 0.4)


def f_lightleak(rgb):
    out = fade(rgb, 0.1)
    out = leak(out, 0.7, origin=(1.0, 0.0), color=(1.0, 0.5, 0.15))
    return leak(out, 0.35, origin=(0.0, 1.0), color=(1.0, 0.2, 0.3))


def f_filmburn(rgb):
    out = contrast(rgb, 0.1)
    out = leak(out, 0.9, origin=(1.0, 0.5), color=(1.0, 0.35, 0.05), reach=0.9)
    return vignette(out, 0.3)


def f_lomo(rgb):
    out = saturation(rgb, 0.3)
    out = contrast(out, 0.2)
    out = tint(out, (1.03, 1.0, 0.98))
    return vignette(out, 0.6)


# ------------------------------------ Artistico (mueve pixeles o usa PIL) ---
def mirror(rgb):
    """Refleja la mitad izquierda sobre la derecha."""
    h, w = rgb.shape[:2]
    half = w // 2
    out = rgb.copy()
    out[:, w - half:] = rgb[:, :half][:, ::-1]
    return out


def fisheye(rgb, amount):
    """Abomba el centro de la imagen, como un lente ojo de pez."""
    h, w = rgb.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    cx, cy = (w - 1) / 2.0, (h - 1) / 2.0
    nx, ny = (xx - cx) / cx, (yy - cy) / cy
    r = np.clip(np.sqrt(nx ** 2 + ny ** 2), 1e-6, None)
    scale = (r ** (1.0 + amount)) / r
    srcx = np.clip(cx + (xx - cx) * scale, 0, w - 1).astype(np.int32)
    srcy = np.clip(cy + (yy - cy) * scale, 0, h - 1).astype(np.int32)
    return rgb[srcy, srcx]


def pil_sketch(img):
    """Dibujo a lapiz: divide el gris por su version invertida y desenfocada."""
    g = img.convert("L")
    inv = ImageOps.invert(g)
    blur = inv.filter(ImageFilter.GaussianBlur(radius=max(2, int(img.width * 0.02))))
    a = np.asarray(g, dtype=np.float32)
    b = np.asarray(blur, dtype=np.float32)
    res = np.where(b >= 255, 255.0, np.minimum(255.0, a * 255.0 / (255.0 - b + 1e-3)))
    return Image.fromarray(np.clip(res, 0, 255).astype(np.uint8), "L").convert("RGB")


def pil_comic(img):
    """Caricatura: suaviza el color, lo reduce a pocos tonos y marca los bordes."""
    smooth = img.convert("RGB").filter(ImageFilter.MedianFilter(size=3))
    poster = np.asarray(ImageOps.posterize(smooth, 3)).copy()
    edges = np.asarray(img.convert("L").filter(ImageFilter.FIND_EDGES)) > 45
    poster[edges] = (20, 20, 20)
    return Image.fromarray(poster, "RGB")


def pil_emboss(img):
    """Relieve, con el filtro de PIL."""
    return img.convert("RGB").filter(ImageFilter.EMBOSS)


# ------------------------------------------------------------------- Lo-Fi
def f_potato(rgb):
    out = saturation(rgb, 0.05)
    return grain(out, 0.12)


def f_pixel(rgb):
    return rgb


def f_deepfry(rgb):
    out = saturation(rgb, 0.7)
    out = contrast(out, 0.4)
    out = tint(out, (1.1, 1.0, 0.9))
    return out


def f_dither(rgb):
    return contrast(rgb, 0.1)


def f_gameboy(rgb):
    return rgb


def f_halftone(rgb):
    return contrast(rgb, 0.15)


def f_posterize(rgb):
    return saturation(rgb, 0.2)


# ------------------------------------------------------------------ VHS / TV
def f_vhs(rgb):
    out = desaturate(rgb, 0.22)
    out = fade(out, 0.35)
    out = tint(out, (1.0, 1.03, 1.0))
    shift = max(1, rgb.shape[1] // 300)
    out = chroma(out, shift)
    return scanlines(out, 0.25)


def f_camcorder(rgb):
    out = saturation(rgb, -0.1)
    out = contrast(out, -0.03)
    out = tint(out, (1.0, 1.02, 0.99))
    return scanlines(out, 0.3)


def f_crt(rgb):
    out = contrast(rgb, 0.1)
    out = rgb_mask(out, 0.6)
    return scanlines(out, 0.5)


def f_glitch(rgb):
    return glitch(rgb, 0.6)


def f_chromatic(rgb):
    shift = max(2, rgb.shape[1] // 120)
    return chroma(rgb, shift)


def f_thermal(rgb):
    l = lum(rgb)
    stops = [
        (0.0, (0.0, 0.0, 0.2)), (0.25, (0.35, 0.0, 0.6)),
        (0.5, (0.9, 0.0, 0.25)), (0.7, (1.0, 0.5, 0.0)),
        (0.86, (1.0, 0.9, 0.1)), (1.0, (1.0, 1.0, 1.0)),
    ]
    return colormap(l, stops)


def f_static(rgb):
    out = desaturate(rgb, 0.5)
    out = contrast(out, -0.05)
    out = grain(out, 0.45)
    return scanlines(out, 0.35)


# ------------------------------------------------------------------ Estetico
def f_bleach_bypass(rgb):
    # mezcla la imagen con su version en gris usando "overlay", despues
    # desatura y sube contraste: el look plateado y crudo tipico.
    gray = desaturate(rgb, 1.0)
    overlay = np.where(gray < 0.5, 2 * rgb * gray, 1 - 2 * (1 - rgb) * (1 - gray))
    out = rgb * 0.4 + overlay * 0.6
    out = desaturate(out, 0.45)
    return contrast(out, 0.28)


def f_teal_orange(rgb):
    l = lum(rgb)[..., None]
    shadow = np.array([0.0, 0.42, 0.5])
    high = np.array([1.0, 0.6, 0.22])
    t = shadow * (1 - l) + high * l
    out = rgb * 0.75 + t * 0.25
    out = contrast(out, 0.18)
    return saturation(out, 0.12)


def f_candy(rgb):
    out = saturation(rgb, 0.4)
    out = tint(out, (1.05, 1.0, 1.08))
    return fade(out, 0.3)


def f_vaporwave(rgb):
    l = lum(rgb)[..., None]
    shadow = np.array([0.35, 0.0, 0.5])    # violeta
    high = np.array([0.1, 0.9, 0.95])      # cian
    t = shadow * (1 - l) + high * l
    out = rgb * 0.65 + t * 0.35
    out = saturation(out, 0.2)
    return leak(out, 0.35, origin=(0.5, 0.0), color=(1.0, 0.4, 0.8))


def f_neon(rgb):
    out = saturation(rgb, 0.45)
    out = tint(out, (1.06, 0.98, 1.08))
    return contrast(out, 0.2)


def f_duotone(rgb):
    l = lum(rgb)[..., None]
    dark = np.array([0.10, 0.0, 0.22])
    light = np.array([1.0, 0.45, 0.7])
    return dark * (1 - l) + light * l


def f_solarize(rgb):
    out = np.where(rgb < 0.5, rgb, 1.0 - rgb)
    return contrast(out, 0.15)


def f_jet_black(rgb):
    out = contrast(rgb, 0.35)
    out = np.clip((out - 0.06) / 0.94, 0, 1)   # aplasta los negros
    out = desaturate(out, 0.18)
    return tint(out, (1.0, 1.0, 1.03))


def f_dream(rgb):
    out = fade(rgb, 0.2)
    return saturation(out, 0.05)


def f_infrared(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    out = np.stack([np.clip(g * 1.2, 0, 1), r * 0.8, b * 0.9], axis=-1)
    return saturation(out, 0.2)


def f_goldenhour(rgb):
    out = tint(rgb, (1.1, 1.0, 0.85))
    l = lum(out)
    out = out + 0.15 * (l ** 2)[..., None] * np.array([1.0, 0.6, 0.2])
    return contrast(out, 0.05)


# ---------------------------------------------------------------------------
# Que filtros van en cada categoria (asi se ordenan en la interfaz).
# ---------------------------------------------------------------------------
FILTER_CATEGORIES = {
    "Digicam": [
        "CCD", "Digicam 0.3MP", "ProCCD", "IXUS", "Webcam",
        "iPhone 4", "Nokia", "CCTV", "Visión Nocturna",
    ],
    "Analógico": [
        "Desechable", "Huji 98", "Polaroid", "Portra", "Velvia",
        "Kodak Gold", "Cross Process", "Fade Mate", "Sepia", "Noir",
        "Fuga de Luz", "Film Burn", "Lomo",
    ],
    "Artístico": [
        "Sketch", "Comic", "Relieve", "Ojo de Pez", "Espejo",
    ],
    "Lo-Fi": [
        "Potato", "Pixelado", "Deep Fry", "Dither", "Game Boy",
        "Halftone", "Posterize",
    ],
    "VHS / TV": [
        "VHS", "Camcorder", "CRT", "Glitch", "Chromatic",
        "Thermal", "Estática",
    ],
    "Estético": [
        "Bleach Bypass", "Teal & Orange", "Candy", "Vaporwave", "Neon",
        "Duotone", "Solarize", "Jet Black", "Dream", "Infrarrojo", "Golden Hour",
    ],
}

# Cada entrada: nombre -> (funcion de color, efectos extra en dominio PIL).
# Claves de los extra: lowres, jpeg, halftone(px), dither(colores), gameboy,
# posterize(bits), bloom, sharpen, datestamp, geom, pil.
FILTERS = {
    "Original": (f_original, {}),
    # Digicam
    "CCD": (f_ccd, {}),
    "Digicam 0.3MP": (f_digicam03, {"lowres": 0.4, "jpeg": 0.35}),
    "ProCCD": (f_proccd, {"jpeg": 0.15}),
    "IXUS": (f_ixus, {"lowres": 0.15}),
    "Webcam": (f_webcam, {"lowres": 0.5, "jpeg": 0.3}),
    "iPhone 4": (f_iphone4, {"jpeg": 0.1, "lowres": 0.1}),
    "Nokia": (f_nokia, {"lowres": 0.4, "jpeg": 0.25, "posterize": 5}),
    "CCTV": (f_cctv, {"lowres": 0.4, "jpeg": 0.3, "datestamp": True}),
    "Visión Nocturna": (f_nightvision, {"bloom": 0.4}),
    # Analogico
    "Desechable": (f_disposable, {}),
    "Huji 98": (f_huji, {"datestamp": True}),
    "Polaroid": (f_polaroid, {}),
    "Portra": (f_portra, {}),
    "Velvia": (f_velvia, {}),
    "Kodak Gold": (f_kodakgold, {}),
    "Cross Process": (f_crossprocess, {}),
    "Fade Mate": (f_fadematte, {}),
    "Sepia": (f_sepia, {}),
    "Noir": (f_noir, {}),
    "Fuga de Luz": (f_lightleak, {}),
    "Film Burn": (f_filmburn, {"bloom": 0.3}),
    "Lomo": (f_lomo, {}),
    # Artistico
    "Sketch": (f_original, {"pil": pil_sketch}),
    "Comic": (f_original, {"pil": pil_comic}),
    "Relieve": (f_original, {"pil": pil_emboss}),
    "Ojo de Pez": (f_original, {"geom": lambda rgb: fisheye(rgb, 0.6)}),
    "Espejo": (f_original, {"geom": mirror}),
    # Lo-Fi
    "Potato": (f_potato, {"lowres": 0.6, "jpeg": 0.6}),
    "Pixelado": (f_pixel, {"lowres": 0.78}),
    "Deep Fry": (f_deepfry, {"jpeg": 0.8, "sharpen": 0.8}),
    "Dither": (f_dither, {"dither": 4}),
    "Game Boy": (f_gameboy, {"gameboy": True}),
    "Halftone": (f_halftone, {"halftone": 6}),
    "Posterize": (f_posterize, {"posterize": 3}),
    # VHS / TV
    "VHS": (f_vhs, {"jpeg": 0.1}),
    "Camcorder": (f_camcorder, {"lowres": 0.2, "datestamp": True}),
    "CRT": (f_crt, {"bloom": 0.3}),
    "Glitch": (f_glitch, {"jpeg": 0.3}),
    "Chromatic": (f_chromatic, {}),
    "Thermal": (f_thermal, {}),
    "Estática": (f_static, {"lowres": 0.3, "jpeg": 0.2}),
    # Estetico
    "Bleach Bypass": (f_bleach_bypass, {}),
    "Teal & Orange": (f_teal_orange, {}),
    "Candy": (f_candy, {}),
    "Vaporwave": (f_vaporwave, {"bloom": 0.3}),
    "Neon": (f_neon, {"bloom": 0.5}),
    "Duotone": (f_duotone, {}),
    "Solarize": (f_solarize, {}),
    "Jet Black": (f_jet_black, {}),
    "Dream": (f_dream, {"bloom": 0.6}),
    "Infrarrojo": (f_infrared, {}),
    "Golden Hour": (f_goldenhour, {"bloom": 0.3}),
}
