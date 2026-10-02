"""Detector de baches en vivo, sobre un video o sobre una imagen.

  python webcam.py                      # webcam 0
  python webcam.py --source 1           # otra camara
  python webcam.py --source video.mp4   # un video
  python webcam.py --source foto.jpg    # una imagen (se puede cambiar el umbral en vivo)
  python webcam.py --source foto.jpg --no-show   # solo guarda la imagen anotada y no abre ventana
Teclas: q o ESC salir | + / - confianza | 1 / 2 / 3 umbral 0.25 / 0.35 / 0.50 | s guardar captura
"""
import argparse
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import cv2  # noqa: E402
from ultralytics import YOLO  # noqa: E402

HERE = Path(__file__).resolve().parent
IMG_EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
PRESETS = {ord("1"): 0.25, ord("2"): 0.35, ord("3"): 0.50}
ap = argparse.ArgumentParser()
ap.add_argument("--source", default="0", help="0 = webcam, o ruta a un video o a una imagen")
ap.add_argument("--weights", default=str(HERE / "modelo" / "best.pt"))
ap.add_argument("--conf", type=float, default=0.35)
ap.add_argument("--imgsz", type=int, default=640)
ap.add_argument("--no-show", action="store_true", help="con una imagen: guarda el resultado sin abrir ventana")
args = ap.parse_args()

model = YOLO(args.weights)
conf = args.conf
snap_dir = HERE / "resultados" / "capturas"
snap_dir.mkdir(parents=True, exist_ok=True)
WINDOW = "Detector de baches (q = salir)"


def anotar(frame, conf, fps=None):
    r = model.predict(frame, conf=conf, imgsz=args.imgsz, verbose=False)[0]
    view = r.plot()
    texto = f"baches: {len(r.boxes)}  conf>={conf:.2f}" + (f"  {fps:.1f} FPS" if fps is not None else "")
    cv2.putText(view, texto, (10, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2, cv2.LINE_AA)
    return view, r


def cambiar_conf(k, conf):
    if k in PRESETS:
        return PRESETS[k]
    if k in (ord("+"), ord("=")):
        return min(0.95, round(conf + 0.05, 2))
    if k in (ord("-"), ord("_")):
        return max(0.05, round(conf - 0.05, 2))
    return conf


src_path = Path(args.source)
if src_path.suffix.lower() in IMG_EXT:
    # ---- modo imagen ----
    frame = cv2.imread(str(src_path))
    if frame is None:
        sys.exit(f"No pude leer la imagen '{args.source}'")
    if args.no_show:
        view, r = anotar(frame, conf)
        out = snap_dir / f"{src_path.stem}_conf{int(conf * 100)}.jpg"
        cv2.imwrite(str(out), view)
        confs = [round(float(c), 2) for c in r.boxes.conf]
        print(f"{src_path.name}: {len(r.boxes)} bache(s) con conf>={conf:.2f} {confs} -> {out}")
        sys.exit(0)
    print("Imagen cargada. q/ESC salir, +/- o 1/2/3 cambian el umbral, s guarda.")
    while True:
        view, r = anotar(frame, conf)
        cv2.imshow(WINDOW, view)
        k = cv2.waitKey(0) & 0xFF
        if k in (ord("q"), 27):
            break
        if k == ord("s"):
            p = snap_dir / f"{src_path.stem}_conf{int(conf * 100)}.jpg"
            cv2.imwrite(str(p), view)
            print("Guardada", p)
        conf = cambiar_conf(k, conf)
    cv2.destroyAllWindows()
    sys.exit(0)

# ---- modo camara / video ----
is_cam = args.source.isdigit()
src = int(args.source) if is_cam else args.source
cap = cv2.VideoCapture(src, cv2.CAP_DSHOW) if (is_cam and sys.platform == "win32") else cv2.VideoCapture(src)
if not cap.isOpened():
    sys.exit(f"No pude abrir la fuente '{args.source}'. Cierra otras apps que usen la camara o prueba --source 1")

fps, t_prev = 0.0, time.time()
n_frames, t_start = 0, None
print("Corriendo. q/ESC salir, +/- o 1/2/3 cambian el umbral, s captura.")

while True:
    ok, frame = cap.read()
    if not ok:
        print("Fin del video o la camara dejo de enviar imagen.")
        break
    view, r = anotar(frame, conf, fps)
    now = time.time()
    fps = 0.9 * fps + 0.1 * (1.0 / max(now - t_prev, 1e-6))
    t_prev = now
    n_frames += 1
    if n_frames == 1:
        t_start = now  # el primer fotograma incluye el calentamiento del modelo
    cv2.imshow(WINDOW, view)
    k = cv2.waitKey(1) & 0xFF
    if k in (ord("q"), 27):
        break
    if k == ord("s"):
        p = snap_dir / f"captura_{int(now)}.jpg"
        cv2.imwrite(str(p), view)
        print("Guardada", p)
    conf = cambiar_conf(k, conf)

if t_start is not None and n_frames > 1:
    print(f"FPS promedio (sin el primer fotograma): {(n_frames - 1) / max(time.time() - t_start, 1e-6):.1f} "
          f"sobre {n_frames - 1} fotogramas")
cap.release()
cv2.destroyAllWindows()
