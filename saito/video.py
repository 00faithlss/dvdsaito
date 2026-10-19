"""
Soporte de video de DVD Saito.

Lee los cuadros con ffmpeg (viene dentro de imageio-ffmpeg), les aplica el mismo
motor que a las imagenes (filtros, ajustes y estirado) y los vuelve a escribir
en un mp4, conservando el audio original si tiene.
"""

import numpy as np
import imageio_ffmpeg as iff
from PIL import Image

from . import engine as eng

VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv")


def is_video(path):
    return path.lower().endswith(VIDEO_EXTS)


def open_video(path):
    """Devuelve (primer cuadro como imagen PIL, meta). meta trae size, fps y duracion."""
    gen = iff.read_frames(path)
    try:
        meta = next(gen)
        w, h = meta["size"]
        frame = next(gen)
    finally:
        gen.close()
    img = Image.frombytes("RGB", (w, h), frame)
    return img, meta


def _even(n):
    return max(2, n - (n % 2))


def export_video(src_path, dst_path, settings, meta, progress=None, cancelled=None):
    """Procesa cada cuadro de src_path y escribe el resultado en dst_path.

    progress(n_cuadros) se llama despues de cada cuadro; cancelled() permite
    abortar. Devuelve el numero de cuadros escritos.
    """
    w, h = meta["size"]
    ow, oh = eng.output_size((w, h), settings)
    ow, oh = _even(ow), _even(oh)       # h264 yuv420p necesita medidas pares
    s = {**settings, "out_w": ow, "out_h": oh}

    reader = iff.read_frames(src_path)
    next(reader)                        # el primer elemento es la meta
    writer = iff.write_frames(dst_path, (ow, oh), fps=meta.get("fps", 25),
                              quality=7, macro_block_size=2,
                              audio_path=src_path if meta.get("audio_codec") else None,
                              audio_codec="aac" if meta.get("audio_codec") else None)
    writer.send(None)
    n = 0
    try:
        for raw in reader:
            if cancelled and cancelled():
                break
            frame = Image.frombytes("RGB", (w, h), raw)
            out = eng.process(frame, s)
            writer.send(np.asarray(out, dtype=np.uint8).tobytes())
            n += 1
            if progress:
                progress(n)
    finally:
        reader.close()
        writer.close()
    return n
