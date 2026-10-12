"""Compara el filtro de cajas duplicadas (NMS) por defecto, IoU 0.7, con el adoptado, IoU 0.5, en val y test.

El IoU se eligio mirando validacion y se confirma en prueba. No reentrena nada.
Uso (dentro del venv):  python nms.py      -> resultados/nms.json
"""
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import torch  # noqa: E402
from ultralytics import YOLO  # noqa: E402

HERE = Path(__file__).resolve().parent
OUT = HERE / "resultados"
DATA = OUT / "data_abs.yaml"  # lo escribe verify.py
if not DATA.exists():
    sys.exit("Falta resultados/data_abs.yaml: corre antes verify.py")

device = 0 if torch.cuda.is_available() else "cpu"
model = YOLO(str(HERE / "modelo" / "best.pt"))
res = {}
for iou in (0.7, 0.5):
    for split in ("val", "test"):
        m = model.val(data=str(DATA), split=split, imgsz=640, batch=16, device=device, workers=0, iou=iou,
                      plots=False, project=str(OUT), name=f"val_nms_{split}_{int(iou * 100)}", exist_ok=True, verbose=False)
        res[f"{split}_nms{iou}"] = {"precision": float(m.box.mp), "recall": float(m.box.mr),
                                    "map50": float(m.box.map50), "map50_95": float(m.box.map)}
        r = res[f"{split}_nms{iou}"]
        print(f"{split:4s} NMS IoU {iou}: P={r['precision']:.3f} R={r['recall']:.3f} mAP50={r['map50']:.3f} mAP50-95={r['map50_95']:.3f}")
(OUT / "nms.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
print(f"Detalle en {OUT / 'nms.json'}")
