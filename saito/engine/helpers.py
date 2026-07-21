"""
Operaciones basicas sobre la imagen.

Cada funcion recibe un arreglo numpy con los canales RGB en el rango [0, 1] y
devuelve otro del mismo tipo. Son las piezas con las que se arman los filtros.
"""

import numpy as np


def lum(rgb):
    """Luminancia percibida segun Rec.601. Devuelve un arreglo (alto, ancho)."""
    return rgb[..., 0] * 0.299 + rgb[..., 1] * 0.587 + rgb[..., 2] * 0.114


def contrast(rgb, amount):
    """Sube o baja el contraste alrededor del gris medio. 0 no cambia nada."""
    return (rgb - 0.5) * (1.0 + amount) + 0.5


def saturation(rgb, amount):
    """Ajusta la saturacion. -1 deja la imagen en gris; positivo agrega color."""
    g = lum(rgb)[..., None]
    return g + (rgb - g) * (1.0 + amount)


def desaturate(rgb, amount):
    """Mezcla hacia gris. 0 mantiene el color, 1 lo quita del todo."""
    g = lum(rgb)[..., None]
    return rgb * (1.0 - amount) + g * amount


def fade(rgb, amount):
    """Look descolorido: levanta los negros y baja un poco el contraste."""
    return rgb * (1.0 - 0.28 * amount) + 0.12 * amount


def tint(rgb, mult):
    """Multiplica cada canal por un factor, para dar un tono de color."""
    return rgb * np.array(mult, dtype=np.float32)


def colormap(t, stops):
    """Convierte un mapa de grises (alto, ancho) a color usando paradas de color.

    Cada parada es (posicion, (r, g, b)) con la posicion entre 0 y 1.
    """
    pos = np.array([s[0] for s in stops])
    cols = np.array([s[1] for s in stops])
    r = np.interp(t, pos, cols[:, 0])
    g = np.interp(t, pos, cols[:, 1])
    b = np.interp(t, pos, cols[:, 2])
    return np.stack([r, g, b], axis=-1)


def grain(rgb, amount, seed=1234):
    """Suma ruido monocromatico, el mismo en R, G y B, para simular grano de film."""
    rng = np.random.default_rng(seed)
    noise = rng.normal(0.0, amount * 0.16, size=rgb.shape[:2])[..., None]
    return rgb + noise


def vignette(rgb, amount):
    """Oscurece las esquinas de forma radial."""
    h, w = rgb.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = (w - 1) / 2, (h - 1) / 2
    d = np.sqrt(((xx - cx) / cx) ** 2 + ((yy - cy) / cy) ** 2) / np.sqrt(2)
    m = 1.0 - amount * np.clip((d - 0.35) / 0.65, 0, 1) ** 2 * 0.95
    return rgb * m[..., None]


def chroma(rgb, px):
    """Corre el rojo y el azul unos pixeles a los lados. Es el sangrado de color."""
    px = int(px)
    if px <= 0:
        return rgb
    out = rgb.copy()
    out[..., 0] = np.roll(rgb[..., 0], px, axis=1)
    out[..., 2] = np.roll(rgb[..., 2], -px, axis=1)
    return out


def scanlines(rgb, strength):
    """Oscurece una fila de cada dos, como una pantalla de tubo vieja."""
    lines = np.ones(rgb.shape[0], dtype=np.float32)
    lines[::2] = 1.0 - 0.5 * strength
    return rgb * lines[:, None, None]


def rgb_mask(rgb, strength):
    """Resalta un canal por columna para imitar los subpixeles de un monitor CRT."""
    w = rgb.shape[1]
    m = np.ones((w, 3), dtype=np.float32) * (1.0 - 0.35 * strength)
    m[0::3, 0] = 1.0
    m[1::3, 1] = 1.0
    m[2::3, 2] = 1.0
    return rgb * m[None, :, :]


def leak(rgb, amount, origin=(1.0, 0.0), color=(1.0, 0.5, 0.2), reach=0.7):
    """Agrega una fuga de luz calida desde una esquina, mezclada en modo trama."""
    h, w = rgb.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    nx, ny = xx / max(1, w - 1), yy / max(1, h - 1)
    d = np.sqrt((nx - origin[0]) ** 2 + (ny - origin[1]) ** 2)
    g = np.clip(1.0 - d / reach, 0, 1) ** 2 * amount
    add = g[..., None] * np.array(color, dtype=np.float32)
    return 1.0 - (1.0 - rgb) * (1.0 - add)


def glitch(rgb, amt):
    """Corta la imagen en franjas horizontales y las desplaza al azar."""
    out = chroma(rgb, max(2, int(amt * 12)))
    h = out.shape[0]
    rng = np.random.default_rng(7)
    for _ in range(int(amt * 8) + 3):
        y0 = int(rng.integers(0, h))
        band = int(rng.integers(3, max(4, h // 14)))
        sh = int(rng.integers(-int(amt * 45) - 1, int(amt * 45) + 1))
        out[y0:y0 + band] = np.roll(out[y0:y0 + band], sh, axis=1)
    return out
