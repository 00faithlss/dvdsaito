"""
Soporte de video de DVD Saito.

Lee los cuadros con ffmpeg (viene dentro de imageio-ffmpeg), les aplica el mismo
motor que a las imagenes (filtros, ajustes y estirado) y los vuelve a escribir
en un mp4, conservando el audio original si tiene.
"""

import re
import subprocess

import numpy as np
import imageio_ffmpeg as iff
from PIL import Image

from . import engine as eng

VIDEO_EXTS = (".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv")


def is_video(path):
    return path.lower().endswith(VIDEO_EXTS)


def _real_fps(path, fallback):
    """Tasa de cuadros con la que ffmpeg entrega el video. En videos de frame
    rate variable (Medal, capturas de pantalla, celulares) el 'fps' promedio es
    menor que el 'tbr' real (23.93 vs 60); ffmpeg entrega a la tbr, asi que esa
    es la que hay que usar o el video sale en camara lenta."""
    try:
        r = subprocess.run([iff.get_ffmpeg_exe(), "-hide_banner", "-i", path],
                           capture_output=True, text=True, errors="replace",
                           creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for line in r.stderr.splitlines():
            if "Video:" in line:
                m = re.search(r" ([0-9]+\.?[0-9]*) tbr", line)
                if m and 1 <= float(m.group(1)) <= 240:
                    return float(m.group(1))
                break
    except Exception:
        pass
    return fallback


def open_video(path):
    """Devuelve (primer cuadro como imagen PIL, meta). meta trae size, fps y duracion."""
    gen = iff.read_frames(path)
    try:
        meta = next(gen)
        meta["fps"] = _real_fps(path, meta.get("fps") or 25)
        w, h = meta["size"]
        frame = next(gen)
    finally:
        gen.close()
    img = Image.frombytes("RGB", (w, h), frame)
    return img, meta


def _even(n):
    return max(2, n - (n % 2))


def export_video(src_path, dst_path, settings, meta, progress=None, cancelled=None,
                 max_quality=False):
    """Procesa cada cuadro de src_path y escribe el resultado en dst_path.

    progress(n_cuadros) se llama despues de cada cuadro; cancelled() permite
    abortar. Con max_quality se usa h264 casi sin perdida (crf 8, preset slow)
    y audio a 320k. Devuelve el numero de cuadros escritos.
    """
    w, h = meta["size"]
    ow, oh = eng.output_size((w, h), settings)
    ow, oh = _even(ow), _even(oh)       # h264 yuv420p necesita medidas pares
    s = {**settings, "out_w": ow, "out_h": oh}

    fps = meta.get("fps", 25)
    reader = iff.read_frames(src_path, output_params=["-r", str(fps)])
    next(reader)                        # el primer elemento es la meta
    has_audio = bool(meta.get("audio_codec"))
    if max_quality:
        extra = ["-crf", "8", "-preset", "slow", "-b:a", "320k"]
        q = None
    else:
        extra, q = None, 7
    writer = iff.write_frames(dst_path, (ow, oh), fps=fps,
                              quality=q, macro_block_size=2, output_params=extra,
                              audio_path=src_path if has_audio else None,
                              audio_codec="aac" if has_audio else None)
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


def preview_frames(path, meta, max_side):
    """Genera cuadros ya reducidos (lado mayor max_side) para reproducir en la
    vista previa. Se detiene al terminar el video; el que llama lo reinicia."""
    w, h = meta["size"]
    k = min(1.0, max_side / max(w, h))
    pw, ph = _even(int(w * k)), _even(int(h * k))
    gen = iff.read_frames(path, output_params=["-r", str(meta.get("fps", 25)),
                                               "-vf", f"scale={pw}:{ph}"])
    try:
        next(gen)
        for raw in gen:
            yield Image.frombytes("RGB", (pw, ph), raw)
    finally:
        gen.close()
