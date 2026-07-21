"""
Ventana de dialogo con el estilo Windows 98 de la app.

Se usa para el "Acerca de". Es una ventana propia (sin marco del sistema y sin
el sonido de alerta que hace messagebox), con barra de titulo gris, el icono,
un boton de cerrar y un boton Aceptar.
"""

import re
import ctypes
import tkinter as tk

from .theme import FACE, BLACK, SHADOW, FONT, FONT_B


def win98_dialog(parent, icon, title, message):
    d = tk.Toplevel(parent, bg=FACE)
    d.overrideredirect(True)
    d.transient(parent)

    box = tk.Frame(d, bd=2, relief="raised", bg=FACE)
    box.pack(fill="both", expand=True)

    tb = tk.Frame(box, bg=FACE, height=22)
    tb.pack(fill="x")
    if icon is not None:
        tk.Label(tb, image=icon, bg=FACE).pack(side="left", padx=(4, 3), pady=2)
    tk.Label(tb, text=title, bg=FACE, fg=BLACK, font=FONT_B).pack(side="left")
    tk.Button(tb, text="✕", command=d.destroy, font=("Tahoma", 8, "bold"), bg=FACE,
              fg=BLACK, activebackground=FACE, relief="raised", bd=2, width=2, padx=0,
              pady=0, takefocus=0, highlightthickness=0).pack(side="right", padx=(0, 2), pady=2)
    tk.Frame(box, height=1, bg=SHADOW).pack(fill="x")

    tk.Label(box, text=message, bg=FACE, fg=BLACK, font=FONT, padx=30, pady=22).pack()
    ok = tk.Button(box, text="Aceptar", command=d.destroy, font=FONT, bg=FACE, fg=BLACK,
                   activebackground=FACE, relief="raised", bd=2, padx=18, pady=2)
    ok.pack(pady=(0, 14))
    ok.focus_set()
    d.bind("<Return>", lambda e: d.destroy())
    d.bind("<Escape>", lambda e: d.destroy())

    # centrar sobre la ventana principal
    d.update_idletasks()
    pw, ph = d.winfo_reqwidth(), d.winfo_reqheight()
    m = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", parent.geometry())
    if m:
        mw, mh, mx, my = (int(v) for v in m.groups())
    else:
        mw, mh = parent.winfo_width(), parent.winfo_height()
        mx, my = parent.winfo_rootx(), parent.winfo_rooty()
    px = mx + (mw - pw) // 2
    py = my + (mh - ph) // 2
    d.geometry(f"{pw}x{ph}")
    d.update_idletasks()
    # igual que el splash: la posicion se fija con la API por ser ventana sin marco
    try:
        hwnd = ctypes.windll.user32.GetParent(d.winfo_id())
        ctypes.windll.user32.SetWindowPos(hwnd, 0, px, py, 0, 0, 0x0015)
    except Exception:
        d.geometry(f"{pw}x{ph}+{px}+{py}")
    d.lift()
    d.grab_set()
    return d
