"""
Ventana principal de DVD Saito.

Arma la interfaz Windows 98 (barra de titulo, menu, vista previa y panel de
controles) y conecta cada control con el motor de imagen. El manejo de la
ventana, la pantalla de arranque y el dialogo Acerca de estan en otros modulos.
"""

import os
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk, ImageOps

from . import engine as eng
from .theme import (BASE, HAS_DND, DND_FILES, resource_path,
                    FACE, HILITE, SHADOW, NAVY, BLACK, WHITE, TROUGH,
                    FONT, FONT_B, PANEL_W, MAX_PREVIEW, ICON_FILE)
from .window import WindowMixin
from .splash import SplashMixin
from .dialogs import win98_dialog


class Saito(WindowMixin, SplashMixin, BASE):
    def __init__(self, intro=False):
        super().__init__()
        self.title("DVD Saito")
        self.configure(bg=FACE)
        self.geometry("1040x740")
        self.minsize(900, 640)

        # estado
        self.original = None
        self.preview_src = None
        self._history = []          # imagenes base previas, para deshacer un aplicado
        self.settings = dict(eng.DEFAULTS)
        self.filter_btns = {}
        self.aspect_btns = {}
        self.scales = {}
        self.value_lbls = {}
        self._thumb_refs = {}
        self._render_job = None
        self.view_w, self.view_h = 780, 640
        self._display_img = None
        self._icon_small = None
        self._drag = (0, 0)
        self.maxed = False
        self.minimized = False
        self._normal_geo = None
        self._revealed = False
        self._splash_win = None

        self._load_icon()
        self._build()
        self._show_placeholder()
        self._setup_dnd()

        # ventana propia; opcionalmente con la pantalla de arranque antes
        self._min_w, self._min_h = 820, 560
        self.update_idletasks()
        self._center()
        self.overrideredirect(True)
        self.bind("<Map>", self._on_deiconify)
        if intro:
            self.withdraw()
            self.after(60, self._run_splash)
        else:
            self.after(10, self._set_appwindow)

    # -------------------------------------------------------------- icono
    def _load_icon(self):
        try:
            ic = Image.open(resource_path(ICON_FILE)).convert("RGB")
            self._icon_big = ImageTk.PhotoImage(ImageOps.pad(ic, (64, 64), color=(0, 0, 0)))
            self.iconphoto(True, self._icon_big)
            self._icon_small = ImageTk.PhotoImage(ImageOps.pad(ic, (16, 16), color=(0, 0, 0)))
        except Exception:
            self._icon_small = None

    # ----------------------------------------------------- helpers de estilo
    def _btn(self, parent, text, cmd):
        return tk.Button(parent, text=text, command=cmd, font=FONT, bg=FACE, fg=BLACK,
                         activebackground=FACE, relief="raised", bd=2, padx=8, pady=2)

    def _group(self, parent, title):
        lf = tk.LabelFrame(parent, text=" " + title + " ", bg=FACE, fg=BLACK, font=FONT,
                           bd=2, relief="groove", labelanchor="nw")
        lf.pack(fill="x", padx=5, pady=(4, 3))
        return lf

    def _winbtn(self, parent, glyph, cmd):
        b = tk.Button(parent, text=glyph, command=cmd, font=("Tahoma", 8, "bold"),
                      bg=FACE, fg=BLACK, activebackground=FACE, relief="raised", bd=2,
                      width=2, padx=0, pady=0, takefocus=0, highlightthickness=0)
        b.pack(side="right", padx=(0, 2), pady=2)
        return b

    # ================================================================== UI
    def _build(self):
        # marco exterior con borde biselado
        outer = tk.Frame(self, bd=2, relief="raised", bg=FACE)
        outer.pack(fill="both", expand=True)
        outer.grid_columnconfigure(0, weight=1)
        outer.grid_rowconfigure(3, weight=1)

        # barra de titulo gris
        tb = tk.Frame(outer, bg=FACE, height=24)
        tb.grid(row=0, column=0, sticky="ew")
        tb.grid_propagate(False)
        if self._icon_small is not None:
            ic = tk.Label(tb, image=self._icon_small, bg=FACE)
            ic.pack(side="left", padx=(4, 3))
            ic.bind("<Button-1>", self._start_move)
            ic.bind("<B1-Motion>", self._do_move)
        self.title_lbl = tk.Label(tb, text="DVD Saito", bg=FACE, fg=BLACK, font=FONT_B)
        self.title_lbl.pack(side="left")
        self._winbtn(tb, "✕", self._close)
        self._winbtn(tb, "□", self._toggle_max)
        self._winbtn(tb, "–", self._minimize)
        for wdg in (tb, self.title_lbl):
            wdg.bind("<Button-1>", self._start_move)
            wdg.bind("<B1-Motion>", self._do_move)
            wdg.bind("<Double-Button-1>", lambda e: self._toggle_max())
        tk.Frame(outer, height=1, bg=SHADOW).grid(row=1, column=0, sticky="ew")

        self._build_menubar(outer)

        # contenido: vista previa a la izquierda, panel a la derecha
        content = tk.Frame(outer, bg=FACE)
        content.grid(row=3, column=0, sticky="nsew", padx=4, pady=(2, 2))
        content.grid_rowconfigure(0, weight=1)
        content.grid_columnconfigure(0, weight=1)

        self.pv = tk.Frame(content, bg=BLACK, bd=2, relief="sunken")
        self.pv.grid(row=0, column=0, sticky="nsew", padx=(0, 4))
        self.pv.bind("<Configure>", self._on_view_resize)
        self.canvas = tk.Label(self.pv, bg=BLACK, bd=0)
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")

        self._build_panel(content)

        # barra de estado con el grip de redimension
        sf = tk.Frame(outer, bg=FACE)
        sf.grid(row=4, column=0, sticky="ew")
        sf.grid_columnconfigure(0, weight=1)
        self.status = tk.Label(sf, text="  Listo.  Arrastra una imagen para abrirla.",
                               bd=1, relief="sunken", anchor="w", bg=FACE, fg=BLACK, font=FONT)
        self.status.grid(row=0, column=0, sticky="ew")
        grip = tk.Canvas(sf, width=18, height=18, bg=FACE, highlightthickness=0,
                         cursor="size_nw_se")
        grip.grid(row=0, column=1, sticky="se")
        for (gx, gy) in [(13, 4), (13, 8), (13, 12), (9, 8), (9, 12), (5, 12)]:
            grip.create_rectangle(gx, gy, gx + 2, gy + 2, fill=SHADOW, outline=HILITE)
        grip.bind("<B1-Motion>", lambda ev: self._resize(ev, "se"))

        self._add_resizers(outer)

    def _build_menubar(self, parent):
        mb = tk.Frame(parent, bg=FACE, bd=1, relief="raised")
        mb.grid(row=2, column=0, sticky="ew")

        def menu(label):
            m = tk.Menubutton(mb, text=label, font=FONT, bg=FACE, fg=BLACK, padx=8, pady=2,
                              relief="flat", activebackground=NAVY, activeforeground=WHITE)
            dd = tk.Menu(m, tearoff=0, font=FONT, bg=FACE, fg=BLACK,
                         activebackground=NAVY, activeforeground=WHITE, bd=1)
            m.config(menu=dd)
            m.pack(side="left")
            return dd

        arch = menu("Archivo")
        arch.add_command(label="Abrir imagen...", command=self.open_image)
        arch.add_command(label="Guardar como...", command=self.save_image)
        arch.add_separator()
        arch.add_command(label="Salir", command=self.destroy)

        img = menu("Imagen")
        img.add_command(label="Aplicar efecto", command=self.apply_effect)
        img.add_command(label="Deshacer aplicar", command=self.undo_apply)
        img.add_separator()
        img.add_command(label="Restablecer ajustes", command=self.reset_all)

        ayuda = menu("Ayuda")
        ayuda.add_command(label="Acerca de DVD Saito...", command=self._about)

    def _about(self):
        win98_dialog(self, self._icon_small, "Acerca de DVD Saito", "made by @descansandoo")

    def _build_panel(self, content):
        outer = tk.Frame(content, bg=FACE, bd=2, relief="raised", width=PANEL_W)
        outer.grid(row=0, column=1, sticky="ns")
        outer.grid_propagate(False)

        cv = tk.Canvas(outer, bg=FACE, highlightthickness=0, bd=0)
        vs = tk.Scrollbar(outer, orient="vertical", command=cv.yview)
        cv.configure(yscrollcommand=vs.set)
        vs.pack(side="right", fill="y")
        cv.pack(side="left", fill="both", expand=True)
        panel = tk.Frame(cv, bg=FACE)
        win = cv.create_window((0, 0), window=panel, anchor="nw")

        def fits():
            bbox = cv.bbox("all")
            return not bbox or (bbox[3] - bbox[1]) <= cv.winfo_height()

        def panel_cfg(e):
            cv.configure(scrollregion=cv.bbox("all"))
            if fits():
                cv.yview_moveto(0.0)

        def cv_cfg(e):
            cv.itemconfig(win, width=e.width)
            if fits():
                cv.yview_moveto(0.0)

        def wheel(e):
            # solo desplazar cuando el contenido no entra completo
            if not fits():
                cv.yview_scroll(int(-e.delta / 120), "units")
            else:
                cv.yview_moveto(0.0)

        panel.bind("<Configure>", panel_cfg)
        cv.bind("<Configure>", cv_cfg)
        cv.bind_all("<MouseWheel>", wheel)

        # acciones
        bar = tk.Frame(panel, bg=FACE)
        bar.pack(fill="x", padx=5, pady=(6, 2))
        self._btn(bar, "Abrir", self.open_image).pack(side="left", padx=(0, 4))
        self.save_btn = self._btn(bar, "Guardar", self.save_image)
        self.save_btn.pack(side="left", padx=4)
        self.reset_btn = self._btn(bar, "Restablecer", self.reset_all)
        self.reset_btn.pack(side="left", padx=4)
        self.save_btn.config(state="disabled")
        self.reset_btn.config(state="disabled")
        cmp = self._btn(bar, "Ver original", None)
        cmp.pack(side="left", padx=4)
        cmp.bind("<ButtonPress-1>", lambda e: self._show_compare(True))
        cmp.bind("<ButtonRelease-1>", lambda e: self._show_compare(False))

        # aplicar el efecto actual para encadenar otro encima
        self.apply_btn = self._btn(panel, "Aplicar efecto", self.apply_effect)
        self.apply_btn.pack(fill="x", padx=5, pady=(0, 4))
        self.apply_btn.config(state="disabled")

        g = self._group(panel, "Filtros")
        cats = list(eng.FILTER_CATEGORIES.keys())
        self.cat_var = tk.StringVar(value=cats[0])
        om = tk.OptionMenu(g, self.cat_var, *cats, command=self._on_category)
        om.config(font=FONT, bg=FACE, fg=BLACK, activebackground=NAVY, activeforeground=WHITE,
                  relief="raised", bd=2, highlightthickness=0, anchor="w", padx=6)
        om["menu"].config(font=FONT, bg=FACE, fg=BLACK, activebackground=NAVY, activeforeground=WHITE)
        om.pack(fill="x", padx=6, pady=(2, 3))
        self._btn(g, "Sin filtro (Original)", lambda: self.set_filter("Original")).pack(
            fill="x", padx=6, pady=(0, 3))
        self.filter_grid = tk.Frame(g, bg=FACE)
        self.filter_grid.pack(fill="x", padx=4, pady=2)
        self.current_category = cats[0]
        self._populate_filters(cats[0])
        self._add_scale(g, "filter_strength", "Intensidad del filtro", 0, 1)

        g = self._group(panel, "Ajustes de color")
        self._add_scale(g, "brightness", "Brillo", -1, 1)
        self._add_scale(g, "contrast", "Contraste", -1, 1)
        self._add_scale(g, "saturation", "Saturación", -1, 1)
        self._add_scale(g, "temperature", "Temperatura", -1, 1)
        self._add_scale(g, "tint", "Tinte", -1, 1)
        self._add_scale(g, "highlights", "Altas luces", -1, 1)
        self._add_scale(g, "shadows", "Sombras", -1, 1)
        self._add_scale(g, "sharpen", "Nitidez / desenfoque", -1, 1)

        g = self._group(panel, "Textura")
        self._add_scale(g, "grain", "Grano", 0, 1)
        self._add_scale(g, "vignette", "Viñeta", 0, 1)
        self._add_scale(g, "fade", "Desvanecido", 0, 1)

        g = self._group(panel, "Lo-Fi / extras")
        self._add_scale(g, "lowres", "Baja resolución", 0, 1)
        self._add_scale(g, "jpeg", "Compresión JPEG", 0, 1)
        self._add_scale(g, "leak", "Fuga de luz", 0, 1)
        self.date_var = tk.IntVar(value=0)
        tk.Checkbutton(g, text="Sello de fecha", variable=self.date_var, bg=FACE, fg=BLACK,
                       font=FONT, activebackground=FACE, anchor="w",
                       command=self._toggle_date).pack(fill="x", padx=6, pady=(3, 0))
        drow = tk.Frame(g, bg=FACE)
        drow.pack(fill="x", padx=6, pady=(0, 4))
        tk.Label(drow, text="Formato:", bg=FACE, fg=BLACK, font=FONT).pack(side="left")
        self._date_fmts = {
            "AAAA MM DD": "ymd",
            "MM/DD/AAAA": "mdy",
            "DD/MM/AAAA": "dmy",
            "'AA MM DD": "apos",
            "Japones": "jp",
        }
        self.date_fmt_var = tk.StringVar(value="AAAA MM DD")
        dfm = tk.OptionMenu(drow, self.date_fmt_var, *self._date_fmts, command=self._set_date_fmt)
        dfm.config(font=FONT, bg=FACE, fg=BLACK, activebackground=NAVY, activeforeground=WHITE,
                   relief="raised", bd=2, highlightthickness=0, anchor="w", padx=6)
        dfm["menu"].config(font=FONT, bg=FACE, fg=BLACK, activebackground=NAVY, activeforeground=WHITE)
        dfm.pack(side="left", fill="x", expand=True, padx=(4, 0))

        # fecha del sello: se llena sola con la de la foto y se puede escribir a mano
        frow = tk.Frame(g, bg=FACE)
        frow.pack(fill="x", padx=6, pady=(2, 4))
        tk.Label(frow, text="Fecha:", bg=FACE, fg=BLACK, font=FONT).pack(side="left")
        self.date_entry = tk.Entry(frow, width=11, font=FONT, bg=WHITE, fg=BLACK,
                                   relief="sunken", bd=2, justify="center")
        self.date_entry.pack(side="left", padx=(4, 4))
        self._btn(frow, "Usar", self.apply_manual_date).pack(side="left")
        self.date_src = tk.Label(frow, text="", bg=FACE, fg=SHADOW, font=FONT)
        self.date_src.pack(side="left", padx=(6, 0))
        self.date_entry.bind("<Return>", lambda e: self.apply_manual_date())

        g = self._group(panel, "Proporciones / estirado")
        ag = tk.Frame(g, bg=FACE)
        ag.pack(fill="x", padx=6, pady=(2, 2))
        for i, name in enumerate(eng.ASPECTS):
            b = self._btn(ag, name, lambda n=name: self.set_aspect(n))
            b.config(padx=4)
            b.grid(row=i // 3, column=i % 3, padx=2, pady=2, sticky="ew")
            self.aspect_btns[name] = b
        for cc in range(3):
            ag.grid_columnconfigure(cc, weight=1)
        self._add_scale(g, "stretch_x", "Ancho (estirar)", 0.5, 2.0)
        self._add_scale(g, "stretch_y", "Alto (estirar)", 0.5, 2.0)

        # tamano exacto escribiendo los pixeles a mano
        mrow = tk.Frame(g, bg=FACE)
        mrow.pack(fill="x", padx=6, pady=(6, 4))
        tk.Label(mrow, text="Tamaño px:", bg=FACE, fg=BLACK, font=FONT).pack(side="left")
        self.w_entry = tk.Entry(mrow, width=6, font=FONT, bg=WHITE, fg=BLACK,
                                relief="sunken", bd=2, justify="right")
        self.w_entry.pack(side="left", padx=(4, 2))
        tk.Label(mrow, text="x", bg=FACE, fg=BLACK, font=FONT).pack(side="left")
        self.h_entry = tk.Entry(mrow, width=6, font=FONT, bg=WHITE, fg=BLACK,
                                relief="sunken", bd=2, justify="right")
        self.h_entry.pack(side="left", padx=(2, 4))
        self._btn(mrow, "Aplicar", self.apply_manual_size).pack(side="left")
        self.w_entry.bind("<Return>", lambda e: self.apply_manual_size())
        self.h_entry.bind("<Return>", lambda e: self.apply_manual_size())

        self._highlight(self.aspect_btns, "Original")

    def _add_scale(self, parent, key, label, lo, hi):
        row = tk.Frame(parent, bg=FACE)
        row.pack(fill="x", padx=6, pady=(3, 0))
        tk.Label(row, text=label, bg=FACE, fg=BLACK, font=FONT, anchor="w").pack(side="left")
        val = tk.Label(row, text="", bg=FACE, fg=BLACK, font=FONT, width=6, anchor="e")
        val.pack(side="right")
        self.value_lbls[key] = val
        sc = tk.Scale(parent, from_=lo, to=hi, orient="horizontal", showvalue=0,
                      resolution=0.01, bg=FACE, troughcolor=TROUGH, highlightthickness=0,
                      bd=2, relief="sunken", sliderrelief="raised", sliderlength=18, width=12,
                      command=lambda v, k=key: self.on_slider(k, v))
        sc.set(self.settings[key])
        sc.pack(fill="x", padx=6, pady=(0, 2))
        self.scales[key] = sc
        self._update_value_label(key)

    # ------------------------------------------------------- drag & drop
    def _setup_dnd(self):
        if not HAS_DND:
            return
        try:
            self.drop_target_register(DND_FILES)
            self.dnd_bind("<<Drop>>", self._on_drop)
            self.canvas.drop_target_register(DND_FILES)
            self.canvas.dnd_bind("<<Drop>>", self._on_drop)
        except Exception:
            pass

    def _on_drop(self, event):
        data = event.data.strip()
        if data.startswith("{"):
            path = data[1:data.find("}")]
        else:
            path = data.split()[0]
        self._load_path(path)

    # ----------------------------------------------------------- acciones
    def open_image(self):
        path = filedialog.askopenfilename(
            title="Elegir una imagen",
            filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.webp *.tiff"),
                       ("Todos los archivos", "*.*")])
        if path:
            self._load_path(path)

    def _load_path(self, path):
        try:
            img = Image.open(path).convert("RGB")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir la imagen:\n{e}")
            return
        self.original = img
        prev = img.copy()
        prev.thumbnail((MAX_PREVIEW, MAX_PREVIEW), Image.LANCZOS)
        self.preview_src = prev
        self._history = []
        self.save_btn.config(state="normal")
        self.reset_btn.config(state="normal")
        self.apply_btn.config(state="normal")
        dt, src = self._photo_date(path, img)
        self._set_stamp_date(dt, src)
        self.status.config(text=f"  {os.path.basename(path)}   -   {img.width} x {img.height} px"
                                f"   -   fecha: {dt.strftime('%d/%m/%Y')} ({src})")
        self._populate_filters(self.current_category)
        self.render()
        self._sync_size_entries()

    def save_image(self):
        if self.original is None:
            return
        path = filedialog.asksaveasfilename(
            title="Guardar imagen", defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg")])
        if not path:
            return
        try:
            out = eng.process(self.original, self.settings)
            if path.lower().endswith((".jpg", ".jpeg")):
                out.save(path, quality=95)
            else:
                out.save(path)
            self.status.config(text=f"  Guardado: {path}")
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo guardar:\n{e}")

    # ----------------------------------------------------------- filtros
    def _populate_filters(self, category):
        for w in self.filter_grid.winfo_children():
            w.destroy()
        self.filter_btns = {}
        cols = 2
        has_img = self.preview_src is not None
        for i, name in enumerate(eng.FILTER_CATEGORIES[category]):
            b = tk.Button(self.filter_grid, text=name, font=FONT, bg=FACE, fg=BLACK,
                          activebackground=FACE, relief="raised", bd=2, compound="top",
                          command=lambda n=name: self.set_filter(n))
            if not has_img:
                b.config(height=1)
            b.grid(row=i // cols, column=i % cols, padx=2, pady=2, sticky="ew")
            self.filter_btns[name] = b
        for c in range(cols):
            self.filter_grid.grid_columnconfigure(c, weight=1)
        self._highlight(self.filter_btns, self.settings["filter"])
        self._make_thumbs()

    def _make_thumbs(self):
        """Genera una miniatura de la foto con cada filtro de la categoria actual."""
        if self.preview_src is None:
            return
        src = self.preview_src.copy()
        src.thumbnail((104, 104), Image.LANCZOS)
        for name, btn in self.filter_btns.items():
            try:
                out = eng.process(src, {"filter": name})
            except Exception:
                continue
            w = 100
            h = max(1, int(w * out.height / out.width))
            ph = ImageTk.PhotoImage(out.resize((w, h), Image.LANCZOS))
            self._thumb_refs[name] = ph
            btn.config(image=ph, compound="top")

    def _on_category(self, category):
        self.current_category = category
        self._populate_filters(category)

    def _toggle_date(self):
        self.settings["datestamp"] = bool(self.date_var.get())
        self.render()

    def _set_date_fmt(self, label):
        self.settings["date_fmt"] = self._date_fmts.get(label, "ymd")
        if self.date_var.get():
            self.render()

    # ------------------------------------------------------ fecha del sello
    def _photo_date(self, path, img):
        """Busca la fecha de la foto: primero en los metadatos EXIF (fecha de
        captura), si no, la fecha del archivo. Devuelve (datetime, origen)."""
        try:
            ex = img.getexif()
            raw = None
            try:
                raw = ex.get_ifd(0x8769).get(36867)   # fecha de captura
            except Exception:
                pass
            raw = raw or ex.get(306)                   # fecha general del EXIF
            if raw:
                return datetime.strptime(str(raw)[:19], "%Y:%m:%d %H:%M:%S"), "EXIF"
        except Exception:
            pass
        try:
            return datetime.fromtimestamp(os.path.getmtime(path)), "archivo"
        except Exception:
            return datetime.now(), "hoy"

    def _set_stamp_date(self, dt, src):
        self._img_date_iso = dt.strftime("%Y-%m-%d")
        self._img_date_src = src
        self.settings["date_value"] = self._img_date_iso
        if hasattr(self, "date_entry"):
            self.date_entry.delete(0, "end")
            self.date_entry.insert(0, dt.strftime("%d/%m/%Y"))
            self.date_src.config(text=f"({src})")

    def apply_manual_date(self):
        """Toma la fecha escrita en el campo (DD/MM/AAAA) y la usa en el sello."""
        raw = self.date_entry.get().strip()
        dt = None
        for pat in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y"):
            try:
                dt = datetime.strptime(raw, pat)
                break
            except ValueError:
                pass
        if dt is None:
            self.status.config(text="  Fecha no valida. Usa el formato DD/MM/AAAA.")
            return
        self._set_stamp_date(dt, "manual")
        if self.date_var.get():
            self.render()
        self.status.config(text=f"  Fecha del sello: {dt.strftime('%d/%m/%Y')}")

    def set_filter(self, name):
        self.settings["filter"] = name
        self._highlight(self.filter_btns, name)
        self.render()

    def set_aspect(self, name):
        self.settings["aspect"] = name
        self.settings["out_w"] = 0     # el aspecto reemplaza al tamano manual
        self.settings["out_h"] = 0
        self._highlight(self.aspect_btns, name)
        self.render()
        self._sync_size_entries()

    def on_slider(self, key, value):
        self.settings[key] = float(value)
        if key in ("stretch_x", "stretch_y"):
            self.settings["out_w"] = 0   # estirar con el slider borra el tamano manual
            self.settings["out_h"] = 0
            self._sync_size_entries()
        self._update_value_label(key)
        self.schedule_render()

    def apply_manual_size(self):
        """Estira la imagen al tamano exacto en pixeles que escribio el usuario."""
        if self.original is None:
            self.status.config(text="  Abre una imagen primero.")
            return
        try:
            w = int(float(self.w_entry.get()))
            h = int(float(self.h_entry.get()))
        except (ValueError, TypeError):
            self.status.config(text="  Escribe numeros validos de ancho y alto.")
            return
        if w < 1 or h < 1:
            self.status.config(text="  El tamaño debe ser mayor que cero.")
            return
        w, h = min(w, 20000), min(h, 20000)
        self.settings["out_w"] = w
        self.settings["out_h"] = h
        self.render()
        self.status.config(text=f"  Tamaño de salida: {w} x {h} px")

    def _sync_size_entries(self):
        """Muestra en los campos el tamano de salida actual de la imagen."""
        if self.original is None or not hasattr(self, "w_entry"):
            return
        w, h = eng.output_size(self.original.size, self.settings)
        self.w_entry.delete(0, "end")
        self.w_entry.insert(0, str(w))
        self.h_entry.delete(0, "end")
        self.h_entry.insert(0, str(h))

    # -------------------------------------------- aplicar / deshacer / reset
    def _reset_settings_ui(self):
        self.settings = dict(eng.DEFAULTS)
        for k, sc in self.scales.items():
            sc.set(self.settings[k])
            self._update_value_label(k)
        self.date_var.set(0)
        # la fecha detectada de la foto se conserva aunque se restablezca lo demas
        self.settings["date_value"] = getattr(self, "_img_date_iso", "")
        self._highlight(self.filter_btns, "Original")
        self._highlight(self.aspect_btns, "Original")
        self._sync_size_entries()

    def reset_all(self):
        self._reset_settings_ui()
        self.render()

    def _rebase(self, new_base):
        """Reemplaza la imagen base y deja los ajustes en cero para seguir editando."""
        self.original = new_base
        prev = new_base.copy()
        prev.thumbnail((MAX_PREVIEW, MAX_PREVIEW), Image.LANCZOS)
        self.preview_src = prev
        self._reset_settings_ui()
        self._populate_filters(self.current_category)
        self.render()

    def apply_effect(self):
        """Fija el efecto actual en la imagen para poder ponerle otro encima."""
        if self.original is None:
            return
        try:
            baked = eng.process(self.original, self.settings)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo aplicar el efecto:\n{e}")
            return
        self._history.append(self.original)
        if len(self._history) > 15:
            self._history.pop(0)
        self._rebase(baked)
        self.status.config(text="  Efecto aplicado. Puedes agregar otro encima.")

    def undo_apply(self):
        if not self._history:
            self.status.config(text="  No hay efectos aplicados para deshacer.")
            return
        self._rebase(self._history.pop())
        self.status.config(text="  Se deshizo el ultimo efecto aplicado.")

    # ------------------------------------------------------------- render
    def schedule_render(self):
        if self._render_job:
            self.after_cancel(self._render_job)
        self._render_job = self.after(15, self.render)

    def render(self):
        self._render_job = None
        if self.preview_src is None:
            return
        s = self.settings
        ow, oh = int(s.get("out_w", 0) or 0), int(s.get("out_h", 0) or 0)
        if ow > 0 and oh > 0:
            # en la vista previa usamos el mismo aspecto pero a menor tamano,
            # asi no reescalamos a la resolucion completa en cada cambio
            sc = min(MAX_PREVIEW / ow, MAX_PREVIEW / oh, 1.0)
            s = {**s, "out_w": max(1, round(ow * sc)), "out_h": max(1, round(oh * sc))}
        out = eng.process(self.preview_src, s)
        self._display(out)

    def _display(self, pil_img):
        box_w = max(50, self.view_w - 16)
        box_h = max(50, self.view_h - 16)
        w, h = pil_img.size
        scale = min(box_w / w, box_h / h)
        dw, dh = max(1, int(w * scale)), max(1, int(h * scale))
        self._display_img = ImageTk.PhotoImage(pil_img.resize((dw, dh), Image.LANCZOS))
        self.canvas.config(image=self._display_img, text="")

    def _show_compare(self, show_original):
        if self.preview_src is None:
            return
        if show_original:
            self._display(self.preview_src)
        else:
            self.render()

    def _show_placeholder(self):
        self.canvas.config(image="", text="[ sin imagen ]\n\nArrastra una imagen aquí\n"
                           "o usa el menú  Archivo > Abrir imagen", fg="#c0c0c0",
                           font=("MS Sans Serif", 10))

    # ------------------------------------------------------------ helpers
    def _on_view_resize(self, event):
        self.view_w, self.view_h = event.width, event.height
        if self.preview_src is not None:
            self.schedule_render()

    def _highlight(self, btns, active):
        for name, b in btns.items():
            if name == active:
                b.config(bg=NAVY, fg=WHITE, relief="sunken")
            else:
                b.config(bg=FACE, fg=BLACK, relief="raised")

    def _update_value_label(self, key):
        v = self.settings[key]
        if key in ("stretch_x", "stretch_y"):
            txt = f"{v:.2f}x"
        elif key in ("filter_strength", "grain", "vignette", "fade",
                     "lowres", "jpeg", "leak"):
            txt = f"{int(v * 100)}%"
        else:
            txt = f"{v:+.2f}" if v else "0"
        self.value_lbls[key].config(text=txt)
