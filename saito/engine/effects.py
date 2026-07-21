"""
Efectos que trabajan sobre la imagen ya convertida a PIL.

Van despues de los filtros de color. Aca esta lo que necesita mover o rehacer
pixeles de verdad: bajar la resolucion, comprimir a JPEG, tramar, la paleta de
Game Boy, los puntos de semitono, el brillo y el sello de fecha.
"""

import io
from datetime import datetime

import numpy as np
from PIL import Image, ImageFilter, ImageOps, ImageDraw, ImageFont

from .helpers import lum


def pixelate(img, amount):
    """Achica la imagen y la vuelve a agrandar, para que se vea en bloques."""
    if amount <= 0:
        return img
    w, h = img.size
    f = max(0.03, 1.0 - amount * 0.95)
    small = img.resize((max(1, int(w * f)), max(1, int(h * f))), Image.BILINEAR)
    return small.resize((w, h), Image.NEAREST)


def jpeg(img, amount):
    """Guarda a JPEG con calidad baja y lo vuelve a abrir, dejando los bloques."""
    if amount <= 0:
        return img
    q = max(1, int(round(2 + (1 - amount) * 28)))
    buf = io.BytesIO()
    img.convert("RGB").save(buf, "JPEG", quality=q)
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def posterize(img, bits):
    """Reduce la cantidad de niveles de color."""
    return ImageOps.posterize(img.convert("RGB"), max(1, min(8, int(bits))))


def dither(img, colors):
    """Reduce a pocos colores con tramado Floyd-Steinberg."""
    return img.convert("RGB").quantize(
        colors=max(2, int(colors)), dither=Image.Dither.FLOYDSTEINBERG).convert("RGB")


def gameboy(img):
    """Mapea la luminancia a los cuatro verdes de la Game Boy."""
    arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    l = lum(arr)
    pal = np.array([[15, 56, 15], [48, 98, 48],
                    [139, 172, 15], [155, 188, 15]], dtype=np.float32) / 255.0
    idx = np.clip((l * 4).astype(int), 0, 3)
    return Image.fromarray((pal[idx] * 255).astype(np.uint8), "RGB")


def halftone(img, cell):
    """Semitono: dibuja un punto por celda, mas grande donde la imagen es oscura."""
    cell = max(4, int(cell))
    arr = np.asarray(img.convert("L"), dtype=np.float32) / 255.0
    h, w = arr.shape
    out = Image.new("RGB", (w, h), (250, 250, 245))
    d = ImageDraw.Draw(out)
    for y in range(0, h, cell):
        for x in range(0, w, cell):
            v = float(arr[y:y + cell, x:x + cell].mean())
            r = (1.0 - v) * cell * 0.72
            if r > 0.3:
                cx, cy = x + cell / 2, y + cell / 2
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(18, 18, 20))
    return out


def bloom(img, amount):
    """Toma las zonas brillantes, las desenfoca y las suma para dar un halo."""
    arr = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    l = lum(arr)
    mask = np.clip((l - 0.55) / 0.45, 0, 1)[..., None]
    bright = Image.fromarray((arr * mask * 255).astype(np.uint8), "RGB")
    bright = bright.filter(ImageFilter.GaussianBlur(radius=max(2, int(img.width * 0.012))))
    ba = np.asarray(bright, dtype=np.float32) / 255.0
    out = 1.0 - (1.0 - arr) * (1.0 - ba * amount)
    return Image.fromarray((np.clip(out, 0, 1) * 255).astype(np.uint8), "RGB")


# Que segmentos enciende cada digito en un display de siete segmentos.
#   a          a = arriba      d = abajo
#  f b         b = arriba der  e = abajo izq
#   g          c = abajo der   f = arriba izq
#  e c         g = medio
#   d
_SEGMENTS = {
    "0": "abcdef", "1": "bc", "2": "abdeg", "3": "abcdg", "4": "bcfg",
    "5": "acdfg", "6": "acdefg", "7": "abc", "8": "abcdefg", "9": "abcdfg",
}


def _seg_h(xa, xb, yc, t):
    """Poligono de un segmento horizontal, con las puntas en angulo."""
    return [(xa, yc), (xa + t, yc - t), (xb - t, yc - t),
            (xb, yc), (xb - t, yc + t), (xa + t, yc + t)]


def _seg_v(xc, ya, yb, t):
    """Poligono de un segmento vertical."""
    return [(xc, ya), (xc + t, ya + t), (xc + t, yb - t),
            (xc, yb), (xc - t, yb - t), (xc - t, ya + t)]


def _draw_digit(draw, ch, x, y, w, h, t, color):
    segs = _SEGMENTS.get(ch)
    if not segs:
        return
    x0, x1 = x, x + w
    y0, y1 = y, y + h
    ym = y + h / 2.0
    poly = {
        "a": _seg_h(x0 + t, x1 - t, y0 + t, t),
        "g": _seg_h(x0 + t, x1 - t, ym, t),
        "d": _seg_h(x0 + t, x1 - t, y1 - t, t),
        "f": _seg_v(x0 + t, y0 + t, ym - t, t),
        "b": _seg_v(x1 - t, y0 + t, ym - t, t),
        "e": _seg_v(x0 + t, ym + t, y1 - t, t),
        "c": _seg_v(x1 - t, ym + t, y1 - t, t),
    }
    for s in segs:
        draw.polygon(poly[s], fill=color)


def _jp_font(size):
    """Fuente japonesa para los kanji año/mes/dia. MS Gothic tiene un aire retro."""
    for name in ("msgothic.ttc", "YuGothM.ttc", "YuGothR.ttc"):
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            pass
    return None


def _date_string(fmt, dt):
    """Arma el texto de la fecha segun el formato elegido."""
    y4, y2 = f"{dt.year}", f"{dt.year % 100:02d}"
    mm, dd = f"{dt.month:02d}", f"{dt.day:02d}"
    if fmt == "mdy":
        return f"{mm}/{dd}/{y4}"
    if fmt == "dmy":
        return f"{dd}/{mm}/{y4}"
    if fmt == "apos":
        return f"'{y2} {mm} {dd}"
    if fmt == "jp":
        return f"'{y2}年 {dt.month}月{dd}日"
    return f"{y4} {mm} {dd}"


def datestamp(img, fmt="ymd", when=None):
    """Estampa la fecha con digitos naranjas estilo LCD de camara vieja.

    Cada digito se dibuja con siete segmentos. Segun el formato agrega barras,
    apostrofo o los kanji japoneses. Va abajo a la derecha, con un resplandor,
    como el sello quemado en la foto.

    `when` es la fecha a estampar: un datetime o un texto "AAAA-MM-DD".
    Sin fecha, usa la de hoy.
    """
    if isinstance(when, str) and when:
        try:
            when = datetime.strptime(when, "%Y-%m-%d")
        except ValueError:
            when = None
    dt = when or datetime.now()
    text = _date_string(fmt, dt)
    out = img.convert("RGBA")
    W, H = out.size
    size = max(14, int(H * 0.045))      # los sellos reales son chicos
    dh = size
    dw = int(size * 0.52)               # digitos angostos
    t = max(1, int(size * 0.066))       # segmentos finos, ~13% del alto
    gap = int(size * 0.2)
    space = int(size * 0.4)
    kw = int(size * 0.95)               # ancho de un kanji
    color = (255, 176, 24, 255)
    jp = _jp_font(int(size * 0.92))

    def cw(ch):
        if ch == " ":
            return space
        if ch == "'":
            return int(dw * 0.5)
        if ch in "年月日":
            return kw + gap
        return dw + gap

    total = sum(cw(c) for c in text)
    x = W - total - int(size * 0.7)
    y = H - dh - int(size * 0.8)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for ch in text:
        if ch == " ":
            x += space
        elif ch == "'":
            d.polygon(_seg_v(x + t, y, y + int(dh * 0.3), t), fill=color)
            x += int(dw * 0.5)
        elif ch in "年月日":
            if jp:
                d.text((x, y - int(size * 0.03)), ch, font=jp, fill=color)
            x += kw + gap
        elif ch == "/":
            d.line([(x + dw, y), (x, y + dh)], fill=color, width=int(t * 1.6))
            x += dw + gap
        else:
            _draw_digit(d, ch, x, y, dw, dh, t, color)
            x += dw + gap

    # resplandor: un halo ancho suave y otro cerrado, como luz quemada en la foto
    wide = layer.filter(ImageFilter.GaussianBlur(radius=max(2, size // 5)))
    near = layer.filter(ImageFilter.GaussianBlur(radius=max(1, size // 12)))
    out = Image.alpha_composite(out, wide)
    out = Image.alpha_composite(out, near)
    out = Image.alpha_composite(out, layer)
    return out.convert("RGB")
