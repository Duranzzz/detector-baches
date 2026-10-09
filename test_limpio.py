"""Fase 5a: evalua el modelo en el test "limpio" (sin casi-duplicado en train) y en el "contaminado".

Casi-duplicado = distancia dHash de 64 bits <= 8 respecto a alguna imagen de train (mismo criterio que fugas.py).
No reentrena nada. Escribe resultados/test_limpio.json.
Uso (dentro del venv):  python test_limpio.py
"""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import cv2  # noqa: E402
import numpy as np  # noqa: E402
import torch  # noqa: E402
from ultralytics import YOLO  # noqa: E402

HERE = Path(__file__).resolve().parent
DATASET = HERE / "repo" / "dataset"
IMGS = DATASET / "images"
OUT = HERE / "resultados"
WEIGHTS = HERE / "modelo" / "best.pt"
EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
UMBRAL = 8
POP = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def dhash(path):
    im = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None
    im = cv2.resize(im, (9, 8), interpolation=cv2.INTER_AREA)
    return np.packbits((im[:, 1:] > im[:, :-1]).flatten())


def load(split):
    files = [p for p in sorted((IMGS / split).iterdir()) if p.suffix.lower() in EXT]
    pairs = [(p, dhash(p)) for p in files]
    pairs = [(p, h) for p, h in pairs if h is not None]
    return [p for p, _ in pairs], np.stack([h for _, h in pairs])


def evaluar(model, nombre, rutas, device):
    lista = OUT / f"test_{nombre}.txt"
    lista.write_text("\n".join(p.as_posix() for p in rutas) + "\n", encoding="utf-8")
    yaml = OUT / f"data_test_{nombre}.yaml"
    yaml.write_text(
        f"path: {DATASET.as_posix()}\ntrain: images/train\nval: {lista.as_posix()}\n"
        f"test: {lista.as_posix()}\nnc: 1\nnames:\n  0: pothole\n",
        encoding="utf-8",
    )
    m = model.val(data=str(yaml), split="val", imgsz=640, batch=16, device=device, workers=0,
                  plots=False, project=str(OUT), name=f"val_test_{nombre}", exist_ok=True, verbose=False)
    return {
        "imagenes": len(rutas),
        "precision": float(m.box.mp), "recall": float(m.box.mr),
        "map50": float(m.box.map50), "map50_95": float(m.box.map),
    }


if not (IMGS / "train").exists():
    sys.exit("No encuentro repo/dataset. Ejecuta setup_y_correr.bat")

print("Calculando hashes...")
f_train, h_train = load("train")
f_test, h_test = load("test")
d = np.array([POP[np.bitwise_xor(h_train, h)].sum(axis=1).min() for h in h_test])
limpias = [p for p, di in zip(f_test, d) if di > UMBRAL]
sucias = [p for p, di in zip(f_test, d) if di <= UMBRAL]
print(f"test total {len(f_test)} | limpio (d>{UMBRAL}) {len(limpias)} | con casi-duplicado en train (d<={UMBRAL}) {len(sucias)}")

device = 0 if torch.cuda.is_available() else "cpu"
model = YOLO(str(WEIGHTS))
res = {}
for nombre, rutas in (("completo", f_test), ("limpio", limpias), ("contaminado", sucias)):
    print(f"\n--- test {nombre} ---")
    res[nombre] = evaluar(model, nombre, rutas, device)
    r = res[nombre]
    print(f"n={r['imagenes']}  P={r['precision']:.3f}  R={r['recall']:.3f}  "
          f"mAP50={r['map50']:.3f}  mAP50-95={r['map50_95']:.3f}")

(OUT / "test_limpio.json").write_text(json.dumps({"umbral_dhash": UMBRAL, "resultados": res}, indent=2), encoding="utf-8")
print(f"\nDetalle en {OUT / 'test_limpio.json'}")
