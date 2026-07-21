"""
Constantes visuales y arranque comun de la interfaz.

Aca estan los colores del tema Windows 98, las fuentes, la ruta a los recursos
(icono), el ajuste de DPI y la clase base de la ventana (con soporte de
arrastrar archivos si esta disponible).
"""

import os
import sys
import ctypes
import tkinter as tk

# --- clase base: con drag & drop si tkinterdnd2 esta instalado ---
try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    BASE = TkinterDnD.Tk
    HAS_DND = True
except Exception:
    BASE = tk.Tk
    DND_FILES = None
    HAS_DND = False

# --- DPI ---
# Le decimos a Windows que la app maneja su propio escalado. Sin esto, al pasar
# la ventana entre monitores de distinta resolucion se ve estirada o borrosa.
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# --- paleta Windows 98 ---
FACE   = "#c0c0c0"     # gris de ventana y botones
LIGHT  = "#dfdfdf"
HILITE = "#ffffff"     # borde claro del bisel (arriba a la izquierda)
SHADOW = "#808080"     # borde oscuro del bisel (abajo a la derecha)
NAVY   = "#000080"     # barra de titulo azul y elementos seleccionados
BLACK  = "#000000"
WHITE  = "#ffffff"
TROUGH = "#87887f"     # canal de los sliders

BSOD_BLUE = "#0000aa"  # azul de la pantalla de arranque

# --- fuentes ---
FONT   = ("MS Sans Serif", 8)
FONT_B = ("MS Sans Serif", 8, "bold")

# --- medidas ---
PANEL_W = 376          # ancho del panel de controles
MAX_PREVIEW = 1200     # lado maximo de la vista previa, para que los sliders fluyan

ICON_FILE = "dvd.webp"


def resource_path(name):
    """Ruta a un archivo de assets, sirve tanto corriendo el codigo como el .exe."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "saito", "assets", name)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", name)
