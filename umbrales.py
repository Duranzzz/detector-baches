"""Precision, recall y F1 del detector en test para varios umbrales de confianza (IoU 0.5).

`model.val` reporta P y R en el punto de mejor F1, no en el umbral que uno elige para la camara;
este script mide P y R justo en cada umbral. Una caja predicha es acierto (TP) si su IoU con una caja
real aun no emparejada es >= 0.5 (emparejado voraz por confianza descendente); si no, es falso positivo.
Una caja real sin emparejar es falso negativo.
Uso (dentro del venv):  python umbrales.py [--split test]
Escribe resultados/umbrales.md y .json.
"""
import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import numpy as np  # noqa: E402
import torch  # noqa: E402
from ultralytics import YOLO  # noqa: E402

HERE = Path(__file__).resolve().parent
DATASET = HERE / "repo" / "dataset"
OUT = HERE / "resultados"
UMBRALES = [0.10, 0.25, 0.35, 0.50, 0.65]
IOU_MIN = 0.5
EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

ap = argparse.ArgumentParser()
ap.add_argument("--split", default="test", choices=["val", "test"])
args = ap.parse_args()


def leer_gt(label_path, w, h):
    if not label_path.exists():
        return np.zeros((0, 4))
    filas = [list(map(float, l.split()[1:5])) for l in label_path.read_text().splitlines() if l.strip()]
    if not filas:
        return np.zeros((0, 4))
    a = np.array(filas)
    x, y, bw, bh = a[:, 0] * w, a[:, 1] * h, a[:, 2] * w, a[:, 3] * h
    return np.stack([x - bw / 2, y - bh / 2, x + bw / 2, y + bh / 2], axis=1)


def iou(a, b):
    """IoU de una caja a (4,) contra varias b (n,4)."""
    x1 = np.maximum(a[0], b[:, 0]); y1 = np.maximum(a[1], b[:, 1])
    x2 = np.minimum(a[2], b[:, 2]); y2 = np.minimum(a[3], b[:, 3])
    inter = np.clip(x2 - x1, 0, None) * np.clip(y2 - y1, 0, None)
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[:, 2] - b[:, 0]) * (b[:, 3] - b[:, 1])
    return inter / np.maximum(area_a + area_b - inter, 1e-9)


files = sorted(p for p in (DATASET / "images" / args.split).iterdir() if p.suffix.lower() in EXT)
device = 0 if torch.cuda.is_available() else "cpu"
model = YOLO(str(HERE / "modelo" / "best.pt"))
print(f"Prediciendo {len(files)} imagenes de {args.split} con conf>={min(UMBRALES)} ...")

preds = []  # por imagen: (boxes xyxy, conf), gt
for r, p in zip(model.predict(source=[str(f) for f in files], conf=min(UMBRALES), imgsz=640,
                              device=device, batch=16, stream=True, verbose=False), files):
    h, w = r.orig_shape
    gt = leer_gt(DATASET / "labels" / args.split / (p.stem + ".txt"), w, h)
    preds.append((r.boxes.xyxy.cpu().numpy(), r.boxes.conf.cpu().numpy(), gt))

total_gt = sum(len(g) for _, _, g in preds)
res = {}
for u in UMBRALES:
    tp = fp = 0
    for boxes, confs, gt in preds:
        orden = np.argsort(-confs)
        usado = np.zeros(len(gt), dtype=bool)
        for i in orden:
            if confs[i] < u:
                break
            if len(gt):
                ious = iou(boxes[i], gt)
                ious[usado] = -1
                j = int(np.argmax(ious))
                if ious[j] >= IOU_MIN:
                    usado[j] = True
                    tp += 1
                    continue
            fp += 1
    fn = total_gt - tp
    prec = tp / max(tp + fp, 1)
    rec = tp / max(total_gt, 1)
    f1 = 2 * prec * rec / max(prec + rec, 1e-9)
    res[f"{u:.2f}"] = {"TP": tp, "FP": fp, "FN": fn, "precision": prec, "recall": rec, "f1": f1}
    print(f"conf>={u:.2f}  TP={tp:4d} FP={fp:4d} FN={fn:4d}  P={prec:.3f}  R={rec:.3f}  F1={f1:.3f}")

(OUT / "umbrales.json").write_text(json.dumps({"split": args.split, "imagenes": len(files), "cajas_reales": total_gt,
                                               "iou_min": IOU_MIN, "umbrales": res}, indent=2), encoding="utf-8")
lines = [
    f"# Precision y recall por umbral de confianza (split {args.split}, IoU >= {IOU_MIN})\n",
    f"{len(files)} imagenes, {total_gt} cajas reales. Mismo modelo, sin reentrenar.\n",
    "| conf >= | TP | FP | FN | Precision | Recall | F1 |",
    "|---|---|---|---|---|---|---|",
]
for u, r in res.items():
    lines.append(f"| {u} | {r['TP']} | {r['FP']} | {r['FN']} | {r['precision']:.3f} | {r['recall']:.3f} | {r['f1']:.3f} |")
(OUT / "umbrales.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"Resumen en {OUT / 'umbrales.md'}")
