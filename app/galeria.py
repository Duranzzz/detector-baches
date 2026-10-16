"""Galería para probar el detector con imágenes que ya existen, sin cámara.

  python app/galeria.py

Fuentes: las 718 imágenes de prueba del dataset (con sus baches marcados a mano), las fotos externas de
app/muestras y cualquier imagen que se abra con el botón. Recuadros: azul = bache detectado, naranja punteado =
dudoso (confianza entre umbral - 0,10 y el umbral), verde punteado = bache real según la etiqueta.

Teclas: flechas izquierda/derecha cambian de imagen, 1/2/3 fijan el umbral en 0,25/0,35/0,50, d muestra los
dudosos, e las etiquetas reales, r abre una imagen al azar, s guarda la captura en resultados/capturas.
"""
import queue
import random
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, font as tkfont, ttk

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from PIL import Image, ImageDraw, ImageFont, ImageTk  # noqa: E402

HERE = Path(__file__).resolve().parent.parent  # raiz del proyecto
PESOS = HERE / "modelo" / "best.pt"
PRUEBA_IMG = HERE / "repo" / "dataset" / "images" / "test"
PRUEBA_LAB = HERE / "repo" / "dataset" / "labels" / "test"
MUESTRAS = HERE / "app" / "muestras"
CAPTURAS = HERE / "resultados" / "capturas"
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
NMS_IOU = 0.5          # mismo filtro de repetidos que webcam.py
CONF_PREDICCION = 0.05  # se predice una vez con umbral bajo y se filtra al dibujar

CREDITOS = {
    "kyiv.jpg": "Роман Рябенко · CC0 · Wikimedia Commons",
    "monaghan.jpg": "Computerfan0 · CC0 · Wikimedia Commons",
    "montreal.jpg": "Miguel Tremblay · dominio público · Wikimedia Commons",
    "potomac.jpg": "Ser Amantio di Nicolao · CC BY-SA 4.0 · Wikimedia Commons",
    "alcantarilla.jpg": "Thomas Booker · CC BY-SA 4.0 · Wikimedia Commons",
}

# paleta (la misma de la presentación)
FONDO, PANEL, TINTA, GRIS = "#F5F3EE", "#1C2430", "#1C2430", "#6B7280"
LIENZO, BLANCO, BOTON, BOTON_HOVER = "#EAEEF2", "#FFFDF8", "#2E3A4A", "#3A4859"
AZUL, NARANJA, VERDE, CLARO = "#1F5FBF", "#D9620F", "#2E9E6A", "#F5F3EE"


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def fuente_pil(tam, negrita=False):
    nombres = ["seguisb.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"] if negrita else ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"]
    for n in nombres:
        for base in ("C:/Windows/Fonts/", "/usr/share/fonts/truetype/dejavu/", "/Library/Fonts/", ""):
            try:
                return ImageFont.truetype(base + n, tam)
            except OSError:
                pass
    return ImageFont.load_default()


def num(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


def leer_etiquetas(img_path, w, h):
    lab = PRUEBA_LAB / (Path(img_path).stem + ".txt")
    cajas = []
    if lab.exists():
        for linea in lab.read_text().splitlines():
            p = linea.split()
            if len(p) == 5:
                cx, cy, bw, bh = (float(v) for v in p[1:])
                cajas.append(((cx - bw / 2) * w, (cy - bh / 2) * h, (cx + bw / 2) * w, (cy + bh / 2) * h))
    return cajas


def iou(a, b):
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    union = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / union if union > 0 else 0.0


def aciertos(dets, reales):
    """Baches reales encontrados: emparejamiento voraz por confianza, IoU >= 0,5 (igual que umbrales.py)."""
    libres = list(reales)
    n = 0
    for d in sorted(dets, key=lambda d: -d[4]):
        mejor = max(libres, key=lambda r: iou(d, r), default=None)
        if mejor is not None and iou(d, mejor) >= 0.5:
            libres.remove(mejor)
            n += 1
    return n


class Detector(threading.Thread):
    """Carga el modelo y atiende pedidos en segundo plano para que la ventana no se congele."""

    def __init__(self):
        super().__init__(daemon=True)
        self.pedidos, self.respuestas = queue.Queue(), queue.Queue()
        self.listo = False

    def run(self):
        from ultralytics import YOLO
        modelo = YOLO(str(PESOS))
        self.listo = True
        self.respuestas.put(("listo", None, None))
        while True:
            ruta = self.pedidos.get()
            t = time.perf_counter()
            r = modelo.predict(str(ruta), conf=CONF_PREDICCION, iou=NMS_IOU, imgsz=640, verbose=False)[0]
            ms = (time.perf_counter() - t) * 1000
            dets = [tuple(b) + (float(c),) for b, c in zip(r.boxes.xyxy.cpu().numpy().tolist(), r.boxes.conf.cpu().numpy())]
            self.respuestas.put((ruta, dets, ms))


class Boton(tk.Label):
    """Botón plano con hover, para que la interfaz no tenga el aspecto gris de Windows 95."""

    def __init__(self, padre, texto, accion, fondo=BOTON, hover=BOTON_HOVER, color=CLARO, activo_fondo=None, **kw):
        super().__init__(padre, text=texto, bg=fondo, fg=color, cursor="hand2", padx=kw.pop("padx", 14), pady=kw.pop("pady", 7), **kw)
        self.fondo, self.hover, self.activo_fondo, self.activo, self.accion = fondo, hover, activo_fondo, False, accion
        self.bind("<Button-1>", lambda e: self.accion())
        self.bind("<Enter>", lambda e: self.configure(bg=self.hover if not self.activo else self.activo_fondo))
        self.bind("<Leave>", lambda e: self.pintar())

    def marcar(self, activo):
        self.activo = activo
        self.pintar()

    def pintar(self):
        self.configure(bg=self.activo_fondo if (self.activo and self.activo_fondo) else self.fondo)


class Galeria:
    def __init__(self, raiz):
        self.raiz = raiz
        self.esc = raiz.winfo_fpixels("1i") / 96  # escala de pantalla (125 %, 150 %...)
        raiz.title("Detector de baches · Galería de prueba")
        raiz.configure(bg=FONDO)
        raiz.geometry(f"{self.px(1360)}x{self.px(820)}")
        raiz.minsize(self.px(1000), self.px(620))
        try:
            raiz.state("zoomed")  # maximizada en Windows
        except tk.TclError:
            pass

        self.f = {k: tkfont.Font(family="Segoe UI", size=s, weight=w) for k, (s, w) in {
            "titulo": (15, "bold"), "sub": (9, "normal"), "normal": (10, "normal"), "negrita": (10, "bold"),
            "nombre": (13, "bold"), "chico": (8, "normal"), "chip": (10, "bold")}.items()}

        self.fuentes = {"prueba": sorted(p for p in PRUEBA_IMG.glob("*") if p.suffix.lower() in IMG_EXT) if PRUEBA_IMG.exists() else [],
                        "externas": sorted(p for p in MUESTRAS.glob("*") if p.suffix.lower() in IMG_EXT),
                        "abiertas": []}
        self.fuente = "prueba" if self.fuentes["prueba"] else "externas"
        self.idx, self.pagina, self.por_pagina = 0, 0, 8
        self.umbral, self.ver_dudosos, self.ver_reales = 0.35, True, True
        self.cache_dets, self.ms = {}, {}
        self.img, self.ruta, self.tk_img, self.miniaturas = None, None, None, []
        self.cache_vista = None

        self.det = Detector()
        self.det.start()
        self.construir()
        self.teclas()
        self.cambiar_fuente(self.fuente)
        self.raiz.after(40, self.revisar_respuestas)

    def px(self, n):
        return int(round(n * self.esc))

    # ------------------------------------------------------------------ interfaz
    def construir(self):
        lado = tk.Frame(self.raiz, bg=PANEL, width=self.px(340))
        lado.pack(side="left", fill="y")
        lado.pack_propagate(False)

        cab = tk.Frame(lado, bg=PANEL)
        cab.pack(fill="x", padx=self.px(22), pady=(self.px(22), self.px(14)))
        logo_ruta = HERE / "app" / "recursos" / "logo_ucb.png"
        if logo_ruta.exists():
            lg = Image.open(logo_ruta)
            lg.thumbnail((self.px(44), self.px(60)), Image.LANCZOS)
            self.logo = ImageTk.PhotoImage(lg)
            tk.Label(cab, image=self.logo, bg=PANEL).pack(side="left", padx=(0, self.px(12)))
            self.raiz.iconphoto(True, self.logo)
        tit = tk.Frame(cab, bg=PANEL)
        tit.pack(side="left", fill="x")
        tk.Label(tit, text="Detector de baches", font=self.f["titulo"], bg=PANEL, fg=CLARO, anchor="w").pack(fill="x")
        tk.Label(tit, text="Galería de imágenes de prueba", font=self.f["sub"], bg=PANEL, fg="#9AA4AF", anchor="w").pack(fill="x")

        seg = tk.Frame(lado, bg=PANEL)
        seg.pack(fill="x", padx=self.px(22), pady=(self.px(4), self.px(10)))
        self.b_fuente = {}
        for clave, txt in (("prueba", f"Prueba ({len(self.fuentes['prueba'])})"), ("externas", f"Fotos externas ({len(self.fuentes['externas'])})")):
            b = Boton(seg, txt, lambda c=clave: self.cambiar_fuente(c), font=self.f["negrita"], activo_fondo=AZUL)
            b.pack(side="left", expand=True, fill="x", padx=(0, self.px(6)))
            self.b_fuente[clave] = b
        if not self.fuentes["prueba"]:
            self.b_fuente["prueba"].configure(fg="#6B7280", cursor="arrow")
            self.b_fuente["prueba"].accion = lambda: self.aviso("Falta el dataset: ejecuta setup_y_correr.bat para descargarlo.")

        Boton(lado, "＋  Abrir otra imagen…", self.abrir, fondo=PANEL, hover=BOTON, color="#C9D2DC",
              font=self.f["normal"], highlightthickness=1, highlightbackground="#3A4859").pack(fill="x", padx=self.px(22), pady=(0, self.px(12)))

        leyenda = tk.Frame(lado, bg=PANEL)
        leyenda.pack(side="bottom", fill="x", padx=self.px(22), pady=(self.px(6), self.px(18)))
        for col, txt in ((AZUL, "Bache detectado"), (NARANJA, "Dudoso: pasaría a revisión"), (VERDE, "Bache real (marcado a mano)")):
            fila = tk.Frame(leyenda, bg=PANEL)
            fila.pack(fill="x", pady=1)
            tk.Label(fila, text="■", fg=col, bg=PANEL, font=self.f["negrita"]).pack(side="left")
            tk.Label(fila, text=txt, fg="#C9D2DC", bg=PANEL, font=self.f["sub"]).pack(side="left", padx=self.px(6))

        pag = tk.Frame(lado, bg=PANEL)
        pag.pack(side="bottom", fill="x", padx=self.px(22), pady=self.px(8))
        Boton(pag, "‹", lambda: self.mover_pagina(-1), font=self.f["negrita"], padx=12).pack(side="left")
        self.l_pagina = tk.Label(pag, text="", font=self.f["normal"], bg=PANEL, fg="#C9D2DC")
        self.l_pagina.pack(side="left", expand=True)
        Boton(pag, "›", lambda: self.mover_pagina(1), font=self.f["negrita"], padx=12).pack(side="left")
        Boton(pag, "Al azar", self.azar, font=self.f["normal"]).pack(side="left", padx=(self.px(8), 0))

        self.grilla = tk.Canvas(lado, bg=PANEL, highlightthickness=0)
        self.grilla.pack(fill="both", expand=True, padx=self.px(16))
        self.grilla.bind("<Button-1>", self.click_miniatura)
        self.grilla.bind("<MouseWheel>", lambda e: self.mover_pagina(-1 if e.delta > 0 else 1))
        self.grilla.bind("<Configure>", self.ajustar_grilla)

        # zona principal
        main = tk.Frame(self.raiz, bg=FONDO)
        main.pack(side="left", fill="both", expand=True)

        top = tk.Frame(main, bg=BLANCO, height=self.px(78))
        top.pack(fill="x")
        top.pack_propagate(False)
        info = tk.Frame(top, bg=BLANCO)
        info.pack(side="left", padx=self.px(24), fill="y")
        self.l_nombre = tk.Label(info, text="", font=self.f["nombre"], bg=BLANCO, fg=TINTA, anchor="w")
        self.l_nombre.pack(fill="x", pady=(self.px(14), 0))
        self.l_detalle = tk.Label(info, text="", font=self.f["sub"], bg=BLANCO, fg=GRIS, anchor="w")
        self.l_detalle.pack(fill="x")
        self.chips = tk.Frame(top, bg=BLANCO)
        self.chips.pack(side="right", padx=self.px(20))

        self.lienzo = tk.Canvas(main, bg=LIENZO, highlightthickness=0)
        self.lienzo.pack(fill="both", expand=True)
        self.lienzo.bind("<Configure>", lambda e: self.programar_dibujo())

        abajo = tk.Frame(main, bg=BLANCO, height=self.px(84))
        abajo.pack(fill="x")
        abajo.pack_propagate(False)
        ctrl = tk.Frame(abajo, bg=BLANCO)
        ctrl.pack(side="left", padx=self.px(24), fill="y")
        fila = tk.Frame(ctrl, bg=BLANCO)
        fila.pack(pady=(self.px(14), 0), anchor="w")
        tk.Label(fila, text="Confianza mínima", font=self.f["negrita"], bg=BLANCO, fg=TINTA).pack(side="left")
        self.l_umbral = tk.Label(fila, text="", font=self.f["negrita"], bg=BLANCO, fg=AZUL, width=5)
        self.l_umbral.pack(side="left")
        estilo = ttk.Style()
        estilo.theme_use("clam")
        estilo.configure("Umbral.Horizontal.TScale", background=BLANCO, troughcolor="#D8DDE3", sliderthickness=self.px(18),
                         bordercolor=BLANCO, lightcolor=AZUL, darkcolor=AZUL)
        self.deslizador = ttk.Scale(ctrl, from_=0.10, to=0.90, orient="horizontal", length=self.px(230),
                                    style="Umbral.Horizontal.TScale", command=lambda v: self.fijar_umbral(float(v), desde_deslizador=True))
        self.deslizador.pack(anchor="w", pady=(self.px(4), 0))

        pres = tk.Frame(abajo, bg=BLANCO)
        pres.pack(side="left", padx=self.px(8))
        self.b_pres = {}
        for v in (0.25, 0.35, 0.50):
            b = Boton(pres, num(v), lambda v=v: self.fijar_umbral(v), fondo="#E4E8ED", hover="#D3DAE2", color=TINTA,
                      activo_fondo=NARANJA, font=self.f["negrita"])
            b.pack(side="left", padx=self.px(3))
            self.b_pres[v] = b

        ver = tk.Frame(abajo, bg=BLANCO)
        ver.pack(side="left", padx=self.px(10))
        self.b_dud = Boton(ver, "Dudosos", self.alternar_dudosos, fondo="#E4E8ED", hover="#D3DAE2", color=TINTA, activo_fondo="#F6D3B8", font=self.f["normal"])
        self.b_dud.pack(side="left", padx=self.px(3))
        self.b_real = Boton(ver, "Baches reales", self.alternar_reales, fondo="#E4E8ED", hover="#D3DAE2", color=TINTA, activo_fondo="#BFE3D0", font=self.f["normal"])
        self.b_real.pack(side="left", padx=self.px(3))

        nav = tk.Frame(abajo, bg=BLANCO)
        nav.pack(side="right", padx=self.px(24))
        Boton(nav, "◀", lambda: self.mover(-1), font=self.f["negrita"]).pack(side="left", padx=self.px(3))
        Boton(nav, "▶", lambda: self.mover(1), font=self.f["negrita"]).pack(side="left", padx=self.px(3))
        Boton(nav, "Guardar", self.guardar, fondo=AZUL, hover="#2C6FD6", font=self.f["negrita"]).pack(side="left", padx=(self.px(10), 0))

        self.fijar_umbral(self.umbral)
        self.b_dud.marcar(True)
        self.b_real.marcar(True)

    def teclas(self):
        r = self.raiz
        r.bind("<Right>", lambda e: self.mover(1))
        r.bind("<Left>", lambda e: self.mover(-1))
        r.bind("<Next>", lambda e: self.mover_pagina(1))
        r.bind("<Prior>", lambda e: self.mover_pagina(-1))
        for k, v in (("1", 0.25), ("2", 0.35), ("3", 0.50)):
            r.bind(k, lambda e, v=v: self.fijar_umbral(v))
        r.bind("d", lambda e: self.alternar_dudosos())
        r.bind("e", lambda e: self.alternar_reales())
        r.bind("r", lambda e: self.azar())
        r.bind("s", lambda e: self.guardar())
        r.bind("<Escape>", lambda e: r.destroy())

    # ------------------------------------------------------------------ navegación
    @property
    def lista(self):
        return self.fuentes[self.fuente]

    def cambiar_fuente(self, clave):
        if not self.fuentes[clave]:
            return
        self.fuente, self.idx = clave, 0
        for c, b in self.b_fuente.items():
            b.marcar(c == clave)
        self.b_real.configure(fg=TINTA if clave == "prueba" else "#A0A8B2")
        self.mostrar(0)

    def mostrar(self, i):
        if not self.lista:
            return
        self.idx = i % len(self.lista)
        self.pagina = self.idx // self.por_pagina
        self.ruta = self.lista[self.idx]
        self.img = Image.open(self.ruta).convert("RGB")
        self.cache_vista = None
        if self.ruta not in self.cache_dets:
            self.det.pedidos.put(self.ruta)
        self.dibujar_miniaturas()
        self.actualizar_textos()
        self.dibujar()

    def mover(self, d):
        self.mostrar(self.idx + d)

    def mover_pagina(self, d):
        paginas = max(1, (len(self.lista) + self.por_pagina - 1) // self.por_pagina)
        self.pagina = (self.pagina + d) % paginas
        self.dibujar_miniaturas()

    def azar(self):
        if self.lista:
            self.mostrar(random.randrange(len(self.lista)))

    def abrir(self):
        rutas = filedialog.askopenfilenames(title="Elegir imágenes", filetypes=[("Imágenes", "*.jpg *.jpeg *.png *.bmp *.webp")])
        if rutas:
            nuevas = [Path(r) for r in rutas]
            self.fuentes["abiertas"] = nuevas
            self.fuente, self.idx = "abiertas", 0
            for b in self.b_fuente.values():
                b.marcar(False)
            self.b_real.configure(fg="#A0A8B2")
            self.mostrar(0)

    # ------------------------------------------------------------------ miniaturas
    def dibujar_miniaturas(self):
        g = self.grilla
        g.delete("all")
        self.miniaturas = []
        w_tot = self.px(340 - 32)
        tw, th, gap = (w_tot - self.px(12)) // 2, self.px(104), self.px(12)
        ini = self.pagina * self.por_pagina
        for k, ruta in enumerate(self.lista[ini:ini + self.por_pagina]):
            fila, col = divmod(k, 2)
            x, y = col * (tw + gap), fila * (th + self.px(14))
            try:
                im = Image.open(ruta).convert("RGB")
                im.thumbnail((tw * 2, th * 2))
                # recorte centrado para que todas las miniaturas tengan el mismo tamaño
                kx = max(tw / im.width, th / im.height)
                im = im.resize((max(tw, int(im.width * kx)), max(th, int(im.height * kx))), Image.LANCZOS)
                l, t = (im.width - tw) // 2, (im.height - th) // 2
                im = im.crop((l, t, l + tw, t + th))
            except OSError:
                im = Image.new("RGB", (tw, th), "#2E3A4A")
            foto = ImageTk.PhotoImage(im)
            self.miniaturas.append(foto)
            g.create_image(x, y, image=foto, anchor="nw", tags=(f"m{ini + k}",))
            if ini + k == self.idx:
                g.create_rectangle(x - 3, y - 3, x + tw + 3, y + th + 3, outline=NARANJA, width=self.px(3))
            g.create_text(x + 6, y + th - 6, text=str(ini + k + 1), anchor="sw", fill="white", font=self.f["chico"])
        paginas = max(1, (len(self.lista) + self.por_pagina - 1) // self.por_pagina)
        self.l_pagina.configure(text=f"Página {self.pagina + 1} de {paginas}")

    def ajustar_grilla(self, e):
        th = self.px(104) + self.px(14)
        filas = max(1, (e.height + self.px(14)) // th)
        if filas * 2 != self.por_pagina:
            self.por_pagina = filas * 2
            self.pagina = self.idx // self.por_pagina
        self.dibujar_miniaturas()

    def click_miniatura(self, e):
        for item in self.grilla.find_overlapping(e.x, e.y, e.x, e.y):
            for tag in self.grilla.gettags(item):
                if tag.startswith("m"):
                    self.mostrar(int(tag[1:]))
                    return

    # ------------------------------------------------------------------ controles
    def fijar_umbral(self, v, desde_deslizador=False):
        self.umbral = round(min(0.90, max(0.10, v)), 2)
        self.l_umbral.configure(text=num(self.umbral))
        if not desde_deslizador:
            self.deslizador.set(self.umbral)
        for p, b in self.b_pres.items():
            b.marcar(abs(p - self.umbral) < 0.005)
        self.programar_dibujo()

    def alternar_dudosos(self):
        self.ver_dudosos = not self.ver_dudosos
        self.b_dud.marcar(self.ver_dudosos)
        self.programar_dibujo()

    def alternar_reales(self):
        self.ver_reales = not self.ver_reales
        self.b_real.marcar(self.ver_reales)
        self.programar_dibujo()

    def aviso(self, texto):
        self.l_detalle.configure(text=texto, fg=NARANJA)

    # ------------------------------------------------------------------ resultados
    def revisar_respuestas(self):
        try:
            while True:
                ruta, dets, ms = self.det.respuestas.get_nowait()
                if ruta == "listo":
                    self.actualizar_textos()
                    continue
                self.cache_dets[ruta], self.ms[ruta] = dets, ms
                if ruta == self.ruta:
                    self.actualizar_textos()
                    self.dibujar()
                    sig = self.lista[(self.idx + 1) % len(self.lista)] if self.lista else None
                    if sig is not None and sig not in self.cache_dets:
                        self.det.pedidos.put(sig)  # adelanta la siguiente para que pasar de imagen sea instantáneo
        except queue.Empty:
            pass
        self.raiz.after(40, self.revisar_respuestas)

    def clasificar(self):
        dets = self.cache_dets.get(self.ruta)
        if dets is None:
            return None, [], []
        piso = max(0.10, self.umbral - 0.10)
        return dets, [d for d in dets if d[4] >= self.umbral], [d for d in dets if piso <= d[4] < self.umbral]

    def reales(self):
        if self.fuente != "prueba" or self.img is None:
            return []
        return leer_etiquetas(self.ruta, *self.img.size)

    def actualizar_textos(self):
        if self.ruta is None:
            return
        self.l_nombre.configure(text=self.ruta.name)
        if self.fuente == "prueba":
            det = f"Conjunto de prueba · imagen {self.idx + 1} de {len(self.lista)} · no se usó para entrenar"
        elif self.fuente == "externas":
            det = f"Foto externa · {CREDITOS.get(self.ruta.name, 'Wikimedia Commons')}"
        else:
            det = f"Imagen abierta · {self.ruta.parent}"
        self.l_detalle.configure(text=det, fg=GRIS)

        for w in self.chips.winfo_children():
            w.destroy()
        dets, ok, dud = self.clasificar()
        if not self.det.listo:
            self.chip("Cargando el detector…", GRIS)
            return
        if dets is None:
            self.chip("Analizando…", GRIS)
            return
        self.chip(f"{len(ok)} {'bache' if len(ok) == 1 else 'baches'}", AZUL)
        if dud:
            self.chip(f"{len(dud)} {'dudoso' if len(dud) == 1 else 'dudosos'}", NARANJA)
        if self.fuente == "prueba":
            r = self.reales()
            if r:
                self.chip(f"Encontró {aciertos(ok, r)} de {len(r)} reales", VERDE)
            else:
                self.chip("Sin baches reales", VERDE)
        self.chip(f"{self.ms.get(self.ruta, 0):.0f} ms", GRIS)

    def chip(self, texto, color):
        tk.Label(self.chips, text=texto, bg=color, fg="white", font=self.f["chip"], padx=self.px(12), pady=self.px(5)).pack(side="left", padx=self.px(4))

    # ------------------------------------------------------------------ dibujo
    def programar_dibujo(self):
        if getattr(self, "_pendiente", None):
            self.raiz.after_cancel(self._pendiente)
        self._pendiente = self.raiz.after(15, self.dibujar)

    def anotar(self, im, k):
        """Dibuja los recuadros sobre im (ya escalada por k respecto del original)."""
        d = ImageDraw.Draw(im, "RGBA")
        lado = min(im.size)
        grosor = max(2, int(lado / 220))
        fs = max(13, min(26, int(lado * 0.032)))
        f = fuente_pil(fs, negrita=True)
        _, ok, dud = self.clasificar()
        if self.ver_reales:
            for b in self.reales():
                self.rect_punteado(d, [v * k for v in b], rgb(VERDE), grosor, largo=grosor * 3)
        if self.ver_dudosos:
            for b in dud:
                caja = [v * k for v in b[:4]]
                self.rect_punteado(d, caja, rgb(NARANJA), grosor + 1, largo=grosor * 5)
                self.etiqueta(d, caja, f"¿bache? {num(b[4])}", rgb(NARANJA), f)
        for b in ok:
            caja = [v * k for v in b[:4]]
            d.rectangle(caja, outline=rgb(AZUL), width=grosor + 1)
            L = max(8, int(min(caja[2] - caja[0], caja[3] - caja[1]) * 0.18))
            for px_, py_, sx, sy in ((caja[0], caja[1], 1, 1), (caja[2], caja[1], -1, 1), (caja[0], caja[3], 1, -1), (caja[2], caja[3], -1, -1)):
                d.line([(px_ + sx * L, py_), (px_, py_), (px_, py_ + sy * L)], fill=rgb(AZUL), width=grosor * 3)
            self.etiqueta(d, caja, f"bache {num(b[4])}", rgb(AZUL), f)

    @staticmethod
    def etiqueta(d, caja, texto, color, f):
        x0, y0 = caja[0], caja[1]
        l, t, r, b = d.textbbox((0, 0), texto, font=f)
        w, h = r - l + 16, b - t + 10
        y = y0 - h if y0 - h >= 0 else y0
        d.rounded_rectangle([x0, y, x0 + w, y + h], radius=6, fill=color + (235,))
        d.text((x0 + 8 - l, y + 5 - t), texto, font=f, fill=(255, 255, 255))

    @staticmethod
    def rect_punteado(d, caja, color, grosor, largo):
        x0, y0, x1, y1 = caja
        for (ax, ay, bx, by) in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
            dist = max(abs(bx - ax), abs(by - ay))
            n = max(1, int(dist / (largo * 2)))
            for i in range(n + 1):
                s, e = i / n * 1.0, min(1.0, (i + 0.5) / n)
                if s >= 1.0:
                    break
                d.line([(ax + (bx - ax) * s, ay + (by - ay) * s), (ax + (bx - ax) * e, ay + (by - ay) * e)], fill=color, width=grosor)

    def dibujar(self):
        self._pendiente = None
        c = self.lienzo
        cw, ch = c.winfo_width(), c.winfo_height()
        if self.img is None or cw < 50 or ch < 50:
            return
        pad = self.px(28)
        iw, ih = self.img.size
        k = min((cw - 2 * pad) / iw, (ch - 2 * pad) / ih, 2.0)
        tam = (max(1, int(iw * k)), max(1, int(ih * k)))
        if self.cache_vista is None or self.cache_vista[0] != tam:
            self.cache_vista = (tam, self.img.resize(tam, Image.LANCZOS))
        vista = self.cache_vista[1].copy()
        self.anotar(vista, k)
        self.tk_img = ImageTk.PhotoImage(vista)
        c.delete("all")
        x0, y0 = (cw - tam[0]) // 2, (ch - tam[1]) // 2
        c.create_rectangle(x0 + 6, y0 + 8, x0 + tam[0] + 6, y0 + tam[1] + 8, fill="#D3D9E0", outline="")  # sombra
        c.create_image(x0, y0, image=self.tk_img, anchor="nw")
        if self.cache_dets.get(self.ruta) is None:
            txt = "Cargando el detector…" if not self.det.listo else "Analizando…"
            c.create_rectangle(cw // 2 - self.px(110), y0 + self.px(16), cw // 2 + self.px(110), y0 + self.px(56), fill=PANEL, outline="")
            c.create_text(cw // 2, y0 + self.px(36), text=txt, fill=CLARO, font=self.f["negrita"])
        self.actualizar_textos()

    # ------------------------------------------------------------------ guardar
    def guardar(self):
        if self.img is None or self.cache_dets.get(self.ruta) is None:
            return
        im = self.img.copy()
        self.anotar(im, 1.0)
        CAPTURAS.mkdir(parents=True, exist_ok=True)
        destino = CAPTURAS / f"{self.ruta.stem}_galeria_conf{int(self.umbral * 100)}.jpg"
        im.save(destino, quality=92)
        self.l_detalle.configure(text=f"Captura guardada en {destino.relative_to(HERE)}", fg=VERDE)
        print("Captura guardada en", destino, flush=True)


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)  # nitidez en pantallas con escala 125 % o 150 %
        except (AttributeError, OSError):
            pass
    print("[Inicio] Abriendo la galería; el detector se carga en segundo plano...", flush=True)
    raiz = tk.Tk()
    Galeria(raiz)
    raiz.mainloop()


if __name__ == "__main__":
    main()
