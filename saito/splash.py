"""
Pantalla de arranque estilo pantalla azul de Windows NT.

Al abrir la app aparece una pantalla azul con los archivos del proyecto y los
filtros listados como si fueran drivers, revelados linea por linea. Termina con
`DVD_SAITO> execute dvdsaito.exe` y despues aparece la app.

Es una clase de la que hereda la ventana principal. `_reveal` usa metodos de la
ventana (deiconify, _set_appwindow) para mostrar la app cuando la animacion
termina, y se puede saltar con un clic o una tecla.
"""

import re
import random
import ctypes
import tkinter as tk

from .theme import BSOD_BLUE
from . import engine as eng


class SplashMixin:
    def _bsod_lines(self):
        """Arma las lineas de la pantalla azul a partir de los archivos y filtros."""
        rng = random.Random(1998)
        names = ["dvdsaito.exe", "app.py", "image_engine.py", "reconstruir.bat",
                 "saito.ico", "LEEME.txt", "pillow.dll", "numpy.dll",
                 "tkinter.dll", "tkinterdnd2.sys", "imagetk.sys", "ctypes.dll"]
        for fname in eng.FILTERS:
            if fname == "Original":
                continue
            names.append(re.sub(r"[^a-z0-9]", "", fname.lower()) + ".sys")
        names = names[:44]

        rows = []
        base = 0x80100000
        for nm in names:
            stamp = rng.randint(0x2bc00000, 0x2be80000)
            rows.append(f"{base:08x} {stamp:08x} - {nm}")
            base += rng.randint(0x1000, 0x9000)

        half = (len(rows) + 1) // 2
        left, right = rows[:half], rows[half:]
        hdr = "Dll Base Date Stamp - Name"
        out = [
            "*** STOP: 0x0000001E (0x80000003,0x80106fc0,0x8025ea21,0xfd6829e8)",
            "Unhandled Kernel exception c0000047 from fa8418b4 (8025ea21,fd6829e8)",
            "",
            f"{hdr:<44}{hdr}",
        ]
        for i in range(half):
            r = right[i] if i < len(right) else ""
            out.append(f"{left[i]:<44}{r}")
        out += ["", "Address dword dump Dll Base" + " " * 28 + "- Name"]
        addr = 0x801afc20
        for nm in ("app.py", "image_engine.py", "dvdsaito.exe",
                   "app.py", "image_engine.py", "dvdsaito.exe"):
            d = " ".join(f"{rng.randint(0, 0xffffffff):08x}" for _ in range(4))
            out.append(f"{addr:08x} {d} : {nm}")
            addr += 0x10
        out += [
            "",
            "Kernel Debugger Using: COM2 (Port 0x2f8, Baud Rate 19200)",
            "Restart and set the recovery options in the system control panel",
            "or the /CRASHDEBUG system start option. If this message reappears,",
            "contact your system administrator or technical support group.",
            "",
            "DVD_SAITO> execute dvdsaito.exe",
        ]
        return out

    def _run_splash(self):
        sp = tk.Toplevel(self)
        self._splash_win = sp
        sp.overrideredirect(True)
        sp.configure(bg=BSOD_BLUE)
        # mismo tamano y posicion que la ventana principal, no pantalla completa
        m = re.match(r"(\d+)x(\d+)\+(-?\d+)\+(-?\d+)", self.geometry())
        if m:
            w, h, x, y = (int(v) for v in m.groups())
        else:
            w, h, x, y = 1040, 740, 120, 80
        sp.geometry(f"{w}x{h}")
        sp.attributes("-topmost", True)
        sp.update_idletasks()
        # una ventana sin marco ignora la posicion via tkinter; la fijamos con la API
        try:
            hwnd = ctypes.windll.user32.GetParent(sp.winfo_id())
            ctypes.windll.user32.SetWindowPos(hwnd, 0, x, y, w, h, 0x0014)
        except Exception:
            sp.geometry(f"{w}x{h}+{x}+{y}")

        txt = tk.Text(sp, bg=BSOD_BLUE, fg="#ffffff", bd=0, highlightthickness=0,
                      wrap="none", font=("Fixedsys", 12), padx=26, pady=20,
                      insertwidth=0, cursor="none")
        txt.pack(fill="both", expand=True)
        for ev in ("<Button-1>", "<Key>"):
            sp.bind(ev, lambda e: self._reveal())
        try:
            sp.focus_force()
        except Exception:
            pass

        lines = self._bsod_lines()

        def add(i):
            if not sp.winfo_exists():
                return
            if i < len(lines):
                txt.insert("end", lines[i] + "\n")
                txt.see("end")
                sp.after(48, lambda: add(i + 1))     # unos 2 segundos de animacion
            else:
                sp.after(1000, self._reveal)          # deja la ultima linea 1 segundo

        add(0)
        self.after(12000, self._reveal)   # por si algo se traba, muestra la app igual

    def _reveal(self):
        if self._revealed:
            return
        self._revealed = True
        try:
            if self._splash_win and self._splash_win.winfo_exists():
                self._splash_win.destroy()
        except Exception:
            pass
        self.deiconify()
        self.lift()
        self.after(10, self._set_appwindow)
