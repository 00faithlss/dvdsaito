"""
Manejo de la ventana propia (sin marco del sistema).

La app dibuja su propia barra de titulo Windows 98, asi que aca esta lo que
normalmente hace Windows: mover la ventana, redimensionarla desde los bordes,
minimizar, maximizar en el monitor correcto y aparecer en la barra de tareas.

Es una clase de la que hereda la ventana principal; usa atributos que esa
ventana define (self.maxed, self._drag, etc.).
"""

import ctypes
import tkinter as tk

from .theme import FACE


class WindowMixin:
    def _hwnd(self):
        return ctypes.windll.user32.GetParent(self.winfo_id())

    def _set_appwindow(self):
        """Hace que la ventana sin marco aparezca en la barra de tareas."""
        try:
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            u = ctypes.windll.user32
            hwnd = self._hwnd()
            st = u.GetWindowLongW(hwnd, GWL_EXSTYLE)
            st = (st & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            u.SetWindowLongW(hwnd, GWL_EXSTYLE, st)
            self.wm_withdraw()
            self.after(10, self.wm_deiconify)
        except Exception:
            pass

    def _on_deiconify(self, event=None):
        # al restaurar desde la barra de tareas hay que volver a sacar el marco
        if self.minimized:
            self.minimized = False
            self.overrideredirect(True)
            self.after(10, self._set_appwindow)

    def _center(self):
        w, h = 1040, 740
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{max(0, (sh - h) // 2 - 20)}")

    def _minimize(self):
        # para minimizar hay que devolver el marco un momento; se saca al restaurar
        self.update_idletasks()
        self.overrideredirect(False)
        self.state("iconic")
        self.minimized = True

    def _monitor_workarea(self):
        """Area util del monitor donde esta la ventana, contando varios monitores."""
        class RECT(ctypes.Structure):
            _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long),
                        ("r", ctypes.c_long), ("b", ctypes.c_long)]

        class MI(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("mon", RECT), ("work", RECT),
                        ("flags", ctypes.c_ulong)]
        u = ctypes.windll.user32
        hmon = u.MonitorFromWindow(self._hwnd(), 2)   # el monitor mas cercano
        mi = MI()
        mi.cb = ctypes.sizeof(MI)
        u.GetMonitorInfoW(hmon, ctypes.byref(mi))
        r = mi.work
        return r.l, r.t, r.r - r.l, r.b - r.t

    def _toggle_max(self):
        if not self.maxed:
            self._normal_geo = self.geometry()
            try:
                x, y, w, h = self._monitor_workarea()
            except Exception:
                x, y, w, h = 0, 0, self.winfo_screenwidth(), self.winfo_screenheight()
            self.geometry(f"{w}x{h}+{x}+{y}")
            self.maxed = True
        else:
            if self._normal_geo:
                self.geometry(self._normal_geo)
            self.maxed = False

    def _close(self):
        self.destroy()

    # --- arrastre de la ventana desde la barra de titulo ---
    def _start_move(self, e):
        self._drag = (e.x_root - self.winfo_rootx(), e.y_root - self.winfo_rooty())

    def _do_move(self, e):
        if self.maxed:
            return
        self.geometry(f"+{e.x_root - self._drag[0]}+{e.y_root - self._drag[1]}")

    # --- redimension desde los bordes ---
    def _resize(self, e, side):
        if self.maxed:
            return
        gx, gy = self.winfo_pointerx(), self.winfo_pointery()
        x0, y0 = self.winfo_rootx(), self.winfo_rooty()
        w, h = self.winfo_width(), self.winfo_height()
        if "e" in side:
            w = max(self._min_w, gx - x0)
        if "s" in side:
            h = max(self._min_h, gy - y0)
        self.geometry(f"{w}x{h}")

    def _add_resizers(self, parent):
        """Franjas finas en el borde derecho e inferior para poder redimensionar."""
        e = tk.Frame(parent, cursor="size_we", bg=FACE)
        e.place(relx=1.0, rely=0.0, anchor="ne", relheight=1.0, width=3)
        e.bind("<B1-Motion>", lambda ev: self._resize(ev, "e"))
        s = tk.Frame(parent, cursor="size_ns", bg=FACE)
        s.place(relx=0.0, rely=1.0, anchor="sw", relwidth=1.0, height=3)
        s.bind("<B1-Motion>", lambda ev: self._resize(ev, "s"))
