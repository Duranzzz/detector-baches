"""Audita el formato del dataset: conteos por split, etiquetas mal formadas, cajas fuera de rango,
imagenes sin etiqueta, etiquetas sin imagen y archivos de etiqueta vacios.

Uso (dentro del venv):  python auditar_dataset.py
Escribe resultados/dataset.json.
"""
import collections
import json
import sys
from pathlib import Path

import cv2

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
DS = HERE / "repo" / "dataset"
EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
if not (DS / "images").exists():
    sys.exit("No encuentro repo/dataset. Ejecuta setup_y_correr.bat")

res = {}
for split in ("train", "val", "test"):
    imgs = {p.stem for p in (DS / "images" / split).iterdir() if p.suffix.lower() in EXT}
    labs = {p.stem: p for p in (DS / "labels" / split).glob("*.txt")}
    cajas = malformadas = fuera = vacios = 0
    clases = set()
    for p in labs.values():
        lineas = [l for l in p.read_text().splitlines() if l.strip()]
        if not lineas:
            vacios += 1
        for l in lineas:
            partes = l.split()
            try:
                c, x, y, w, h = int(partes[0]), *map(float, partes[1:5])
                if len(partes) != 5:
                    raise ValueError
            except (ValueError, IndexError):
                malformadas += 1
                continue
            cajas += 1
            clases.add(c)
            if not (0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1):
                fuera += 1
    tamanos = collections.Counter()
    for p_ in (DS / "images" / split).iterdir():
        if p_.suffix.lower() in EXT:
            h_, w_ = cv2.imread(str(p_)).shape[:2]
            tamanos[f"{w_}x{h_}"] += 1
    res[split] = {"tamanos_imagen": dict(tamanos.most_common()), "imagenes": len(imgs), "cajas": cajas, "etiquetas_vacias": vacios,
                  "lineas_malformadas": malformadas, "cajas_fuera_de_rango": fuera,
                  "imagenes_sin_etiqueta": len(imgs - labs.keys()), "etiquetas_sin_imagen": len(labs.keys() - imgs),
                  "clases": sorted(clases)}
    print(split, res[split])
(HERE / "resultados").mkdir(exist_ok=True)
(HERE / "resultados" / "dataset.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
