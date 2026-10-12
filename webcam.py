"""Detector de baches en vivo, sobre un video o sobre una imagen, con botones en pantalla.

  python webcam.py                      # webcam 0
  python webcam.py --source 1           # otra camara (por ejemplo una USB)
  python webcam.py --source video.mp4   # un video
  python webcam.py --source foto.jpg    # una imagen
  python webcam.py --source foto.jpg --no-show   # solo guarda la imagen anotada, sin ventana
  python webcam.py --source video.mp4 --no-show  # procesa el video entero y guarda video_anotado.mp4
  python webcam.py --guardar demo.mp4            # en vivo, ademas graba lo que se ve en un .mp4

Botones (clic) o teclas:
  1 / 2 / 3  umbral 0,25 / 0,35 / 0,50     + / -    umbral +-0,05
  espacio    pausa / seguir                s        captura en resultados/capturas
  c          siguiente camara              f        pantalla completa
  q o ESC    salir
"""
import argparse
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from ultralytics import YOLO  # noqa: E402

HERE = Path(__file__).resolve().parent
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
PRESETS = (0.25, 0.35, 0.50)
NMS_IOU = 0.5  # filtro de cajas duplicadas: 0.5 en vez de 0.7 sube el mAP50 y quita cajas dobles (ver nms.py)
CONF_PREDICCION = 0.05  # se predice con un umbral bajo y se filtra al dibujar: cambiar el umbral es instantaneo
WINDOW = "Detector de baches"
BARRA = 88  # alto de la barra de botones, en pixeles

# colores en RGB (se dibuja con Pillow para tener acentos y bordes suaves)
AZUL, NARANJA, OSCURO, BOTON = (31, 95, 191), (217, 98, 15), (28, 36, 48), (46, 58, 74)
CLARO, VERDE, GRIS = (245, 243, 238), (70, 192, 138), (150, 160, 172)

ap = argparse.ArgumentParser(description="Detector de baches con YOLO11n")
ap.add_argument("--source", default="0", help="0 = webcam, 1 = otra camara, o ruta a un video o a una imagen")
ap.add_argument("--weights", default=str(HERE / "modelo" / "best.pt"))
ap.add_argument("--conf", type=float, default=0.35, help="umbral de confianza inicial")
ap.add_argument("--imgsz", type=int, default=640)
ap.add_argument("--ancho", type=int, default=960, help="ancho de la ventana en pixeles")
ap.add_argument("--no-show", action="store_true", help="imagen o video: guarda el resultado anotado sin abrir ventana")
ap.add_argument("--guardar", help="ruta .mp4 donde grabar el video anotado (camara o video)")
ap.add_argument("--nms", type=float, default=NMS_IOU, help="IoU del filtro de cajas duplicadas")
ap.add_argument("--ui-png", help="con una imagen: guarda una captura de la interfaz completa en esta ruta y sale")
args = ap.parse_args()


def fuente(tam, negrita=False):
    nombres = (["seguisb.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"] if negrita
               else ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"])
    for n in nombres:
        for base in ("C:/Windows/Fonts/", "/usr/share/fonts/truetype/dejavu/", "/Library/Fonts/", ""):
            try:
                return ImageFont.truetype(base + n, tam)
            except OSError:
                continue
    return ImageFont.load_default()


F_ETIQUETA, F_HUD, F_BOTON, F_AYUDA, F_AVISO = fuente(22, True), fuente(22, True), fuente(22, True), fuente(18), fuente(26, True)


def num(x, d=2):
    return f"{x:.{d}f}".replace(".", ",")


class App:
    def __init__(self):
        self.model = YOLO(args.weights)
        self.conf = args.conf
        self.pausa = False
        self.salir = False
        self.fps = 0.0
        self.aviso, self.aviso_hasta = "", 0.0
        self.botones = []  # (x1, y1, x2, y2, accion)
        self.pantalla_completa = False
        self.snap_dir = HERE / "resultados" / "capturas"
        self.snap_dir.mkdir(parents=True, exist_ok=True)
        self.dets = np.zeros((0, 5))
        self.frame = None
        self.modo = "camara"
        self.cam_idx = 0
        self.cap = None

    # ---------------------------------------------------------------- deteccion
    def detectar(self, frame):
        r = self.model.predict(frame, conf=min(CONF_PREDICCION, self.conf), iou=args.nms, imgsz=args.imgsz, verbose=False)[0]
        if len(r.boxes):
            self.dets = np.concatenate([r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy()[:, None]], axis=1)
        else:
            self.dets = np.zeros((0, 5))

    def visibles(self):
        return self.dets[self.dets[:, 4] >= self.conf] if len(self.dets) else self.dets

    # ---------------------------------------------------------------- dibujo
    def componer(self, con_barra=True):
        h0, w0 = self.frame.shape[:2]
        esc = args.ancho / w0
        dw, dh = args.ancho, int(round(h0 * esc))
        video = cv2.cvtColor(cv2.resize(self.frame, (dw, dh), interpolation=cv2.INTER_LINEAR), cv2.COLOR_BGR2RGB)
        lienzo = np.empty((dh + (BARRA if con_barra else 0), dw, 3), np.uint8)
        lienzo[:dh] = video
        if con_barra:
            lienzo[dh:] = self._barra(dw, dh)
        lienzo = Image.fromarray(lienzo)
        d = ImageDraw.Draw(lienzo)  # se dibuja opaco, sin capa alfa: mantiene los FPS
        vis = self.visibles()
        for x1, y1, x2, y2, c in vis:
            self._caja(d, x1 * esc, y1 * esc, x2 * esc, y2 * esc, c)
        self._hud(d, len(vis), dw)
        if self.aviso and time.time() < self.aviso_hasta:
            tw = d.textlength(self.aviso, font=F_AVISO)
            d.rounded_rectangle([(dw - tw) / 2 - 24, dh - 82, (dw + tw) / 2 + 24, dh - 30], 26, fill=OSCURO)
            d.text(((dw - tw) / 2, dh - 75), self.aviso, font=F_AVISO, fill=CLARO)
        return cv2.cvtColor(np.asarray(lienzo), cv2.COLOR_RGB2BGR), dh

    def _caja(self, d, x1, y1, x2, y2, c):
        d.rectangle([x1, y1, x2, y2], outline=AZUL, width=3)
        largo = max(10, min(x2 - x1, y2 - y1) * 0.14)
        for px, py, sx, sy in ((x1, y1, 1, 1), (x2, y1, -1, 1), (x1, y2, 1, -1), (x2, y2, -1, -1)):
            d.line([(px + sx * largo, py), (px, py), (px, py + sy * largo)], fill=AZUL, width=8)
        t = f"bache {num(c)}"
        tw = d.textlength(t, font=F_ETIQUETA)
        ty = y1 - 34 if y1 > 40 else y1 + 4
        d.rounded_rectangle([x1, ty, x1 + tw + 20, ty + 30], 8, fill=AZUL)
        d.text((x1 + 10, ty + 2), t, font=F_ETIQUETA, fill=CLARO)

    def _hud(self, d, n, dw):
        if self.modo == "imagen":
            estado, color = "IMAGEN", AZUL
        elif self.pausa:
            estado, color = "PAUSA", NARANJA
        elif self.modo == "video":
            estado, color = "VIDEO", VERDE
        else:
            estado, color = "EN VIVO", VERDE
        partes = [estado, f"baches: {n}", f"umbral ≥ {num(self.conf)}"]
        if self.modo != "imagen" and not args.no_show:
            partes.append(f"{num(self.fps, 1)} FPS")
        t = "   ·   ".join(partes)
        tw = d.textlength(t, font=F_HUD)
        d.rounded_rectangle([14, 14, 14 + tw + 64, 58], 22, fill=OSCURO)
        d.ellipse([32, 28, 48, 44], fill=color)
        d.text((58, 21), t, font=F_HUD, fill=CLARO)

    def _barra(self, dw, dh):
        """Barra de botones como arreglo RGB; se redibuja solo cuando cambia el estado (ahorra unos 10 ms por cuadro)."""
        clave = (dw, dh, self.conf, self.pausa, self.modo)
        if getattr(self, "_barra_cache", (None,))[0] == clave:
            return self._barra_cache[1]
        img = Image.new("RGB", (dw, BARRA), OSCURO)
        d = ImageDraw.Draw(img)
        self.botones = []
        items = [(num(p), ("conf", p), abs(self.conf - p) < 1e-6) for p in PRESETS]
        items += [("−", ("delta", -0.05), False), ("+", ("delta", 0.05), False)]
        if self.modo != "imagen":
            items.append(("Seguir" if self.pausa else "Pausa", ("pausa", None), self.pausa))
        items.append(("Captura", ("captura", None), False))
        if self.modo == "camara":
            items.append(("Cámara", ("camara", None), False))
        items.append(("Salir", ("salir", None), False))
        x, y = 16, 18
        for texto, accion, activo in items:
            w = max(56, d.textlength(texto, font=F_BOTON) + 36)
            d.rounded_rectangle([x, y, x + w, y + 52], 26, fill=NARANJA if activo else BOTON)
            d.text((x + (w - d.textlength(texto, font=F_BOTON)) / 2, y + 12), texto, font=F_BOTON, fill=CLARO)
            self.botones.append((x, dh + y, x + w, dh + y + 52, accion))  # en coordenadas de la ventana
            x += w + 10
        ayuda = "teclas: 1 2 3  + -  espacio  s  c  f  q"
        tw = d.textlength(ayuda, font=F_AYUDA)
        if x + tw + 16 < dw:
            d.text((dw - tw - 16, 34), ayuda, font=F_AYUDA, fill=GRIS)
        self._barra_cache = (clave, np.asarray(img))
        return self._barra_cache[1]

    # ---------------------------------------------------------------- acciones
    def avisar(self, texto, segundos=2.0):
        self.aviso, self.aviso_hasta = texto, time.time() + segundos
        print(texto)

    def ejecutar(self, accion):
        tipo, valor = accion
        if tipo == "conf":
            self.conf = valor
        elif tipo == "delta":
            self.conf = round(min(0.95, max(0.05, self.conf + valor)), 2)
        elif tipo == "pausa":
            self.pausa = not self.pausa
        elif tipo == "captura":
            self.capturar()
        elif tipo == "camara":
            self.siguiente_camara()
        elif tipo == "salir":
            self.salir = True

    def tecla(self, k):
        mapa = {ord("1"): ("conf", 0.25), ord("2"): ("conf", 0.35), ord("3"): ("conf", 0.50),
                ord("+"): ("delta", 0.05), ord("="): ("delta", 0.05), ord("-"): ("delta", -0.05), ord("_"): ("delta", -0.05),
                ord(" "): ("pausa", None), ord("p"): ("pausa", None), ord("s"): ("captura", None),
                ord("c"): ("camara", None), ord("q"): ("salir", None), 27: ("salir", None)}
        if k == ord("f"):
            self.pantalla_completa = not self.pantalla_completa
            cv2.setWindowProperty(WINDOW, cv2.WND_PROP_FULLSCREEN,
                                  cv2.WINDOW_FULLSCREEN if self.pantalla_completa else cv2.WINDOW_NORMAL)
        elif k in mapa and (self.modo != "imagen" or mapa[k][0] in ("conf", "delta", "captura", "salir")):
            self.ejecutar(mapa[k])

    def raton(self, evento, x, y, flags, _):
        if evento == cv2.EVENT_LBUTTONUP:
            for x1, y1, x2, y2, accion in self.botones:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    self.ejecutar(accion)
                    break

    def capturar(self):
        vista, _ = self.componer(con_barra=False)
        p = self.snap_dir / f"captura_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        cv2.imwrite(str(p), vista)
        self.avisar(f"Captura guardada: {p.name}")

    # ---------------------------------------------------------------- camara
    def abrir(self, fuente_):
        es_cam = isinstance(fuente_, int)
        cap = cv2.VideoCapture(fuente_, cv2.CAP_DSHOW) if (es_cam and sys.platform == "win32") else cv2.VideoCapture(fuente_)
        return cap if cap.isOpened() else None

    def siguiente_camara(self):
        for paso in (1, 2, 3):
            idx = (self.cam_idx + paso) % 4
            cap = self.abrir(idx)
            if cap is not None and cap.read()[0]:
                self.cap.release()
                self.cap, self.cam_idx = cap, idx
                self.avisar(f"Cámara {idx}")
                return
            if cap is not None:
                cap.release()
        self.avisar("No encontré otra cámara")

    # ---------------------------------------------------------------- ciclos
    def ventana(self):
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(WINDOW, self.raton)

    def mostrar(self, espera):
        vista, _ = self.componer()
        if not self.botones_listos:
            cv2.resizeWindow(WINDOW, vista.shape[1], vista.shape[0])
            self.botones_listos = True
        cv2.imshow(WINDOW, vista)
        k = cv2.waitKey(espera) & 0xFF
        if k != 255:
            self.tecla(k)
        if cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
            self.salir = True

    def correr_imagen(self, ruta):
        self.modo = "imagen"
        self.frame = cv2.imread(str(ruta))
        if self.frame is None:
            sys.exit(f"No pude leer la imagen '{ruta}'")
        self.detectar(self.frame)
        if args.ui_png:
            cv2.imwrite(args.ui_png, self.componer()[0])
            print("Interfaz guardada en", args.ui_png)
            return
        if args.no_show:
            vista, _ = self.componer(con_barra=False)
            out = self.snap_dir / f"{Path(ruta).stem}_conf{int(self.conf * 100)}.jpg"
            cv2.imwrite(str(out), vista)
            confs = [round(float(c), 2) for c in self.visibles()[:, 4]]
            print(f"{Path(ruta).name}: {len(confs)} bache(s) con conf>={self.conf:.2f} {confs} -> {out}")
            return
        self.ventana()
        self.botones_listos = False
        while not self.salir:
            self.mostrar(30)

    def correr_video(self, fuente_):
        self.modo = "camara" if isinstance(fuente_, int) else "video"
        self.cam_idx = fuente_ if isinstance(fuente_, int) else 0
        self.cap = self.abrir(fuente_)
        if self.cap is None:
            sys.exit(f"No pude abrir la fuente '{fuente_}'. Cierra otras apps que usen la cámara o prueba --source 1")
        escritor = None
        if args.guardar or (args.no_show and self.modo == "video"):
            destino = Path(args.guardar) if args.guardar else Path(fuente_).with_name(Path(fuente_).stem + "_anotado.mp4")
            fps_fuente = self.cap.get(cv2.CAP_PROP_FPS) or 0
            fps_salida = fps_fuente if 1 <= fps_fuente <= 120 else 15.0
        if args.no_show and self.modo == "video":
            total = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
            n = 0
            while True:
                ok, frame = self.cap.read()
                if not ok:
                    break
                self.frame = frame
                self.detectar(frame)
                vista, _ = self.componer(con_barra=False)
                if escritor is None:
                    escritor = cv2.VideoWriter(str(destino), cv2.VideoWriter_fourcc(*"mp4v"), fps_salida, (vista.shape[1], vista.shape[0]))
                escritor.write(vista)
                n += 1
                if n % 30 == 0:
                    print(f"  {n}/{total or '?'} cuadros")
            self.cap.release()
            if escritor is not None:
                escritor.release()
            print(f"Video anotado ({n} cuadros) en {destino}")
            return
        self.ventana()
        self.botones_listos = False
        t_prev = time.time()
        n, t_inicio = 0, None
        while not self.salir:
            if not self.pausa or self.frame is None:
                ok, frame = self.cap.read()
                if not ok:
                    if self.frame is None:
                        sys.exit("La fuente no envió ninguna imagen.")
                    self.pausa = True
                    self.avisar("Fin del video" if self.modo == "video" else "La cámara dejó de enviar imagen", 4)
                else:
                    self.frame = frame
                    self.detectar(frame)
                    ahora = time.time()
                    self.fps = 0.9 * self.fps + 0.1 * (1.0 / max(ahora - t_prev, 1e-6))
                    t_prev = ahora
                    n += 1
                    if n == 1:
                        t_inicio = ahora  # el primer cuadro incluye el calentamiento del modelo
            if args.guardar and not self.pausa and self.frame is not None:
                vista, _ = self.componer(con_barra=False)
                if escritor is None:
                    escritor = cv2.VideoWriter(str(destino), cv2.VideoWriter_fourcc(*"mp4v"), fps_salida if self.modo == "video" else 15.0,
                                               (vista.shape[1], vista.shape[0]))
                escritor.write(vista)
            self.mostrar(1)
        if escritor is not None:
            escritor.release()
            print(f"Video grabado en {destino}")
        if t_inicio is not None and n > 1:
            print(f"FPS promedio (sin el primer cuadro): {(n - 1) / max(time.time() - t_inicio, 1e-6):.1f} sobre {n - 1} cuadros")
        self.cap.release()


if __name__ == "__main__":
    app = App()
    ruta = Path(args.source)
    if ruta.suffix.lower() in IMG_EXT:
        app.correr_imagen(ruta)
    else:
        app.correr_video(int(args.source) if args.source.isdigit() else args.source)
    cv2.destroyAllWindows()
