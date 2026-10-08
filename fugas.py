"""Busca imagenes de val/test casi identicas a imagenes de train (fuga de datos).

Si el dataset tiene versiones aumentadas de una misma foto repartidas entre train y test,
el mAP medido en test sale inflado. Usa un hash perceptual dHash de 64 bits.
Uso (dentro del venv):  python fugas.py
"""
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import cv2  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
IMGS = HERE / "repo" / "dataset" / "images"
EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
POP = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)


def dhash(path):
    im = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None
    im = cv2.resize(im, (9, 8), interpolation=cv2.INTER_AREA)
    return np.packbits((im[:, 1:] > im[:, :-1]).flatten())  # 8 bytes


def load(split):
    files = [p for p in sorted((IMGS / split).iterdir()) if p.suffix.lower() in EXT]
    pairs = [(p, dhash(p)) for p in files]
    pairs = [(p, h) for p, h in pairs if h is not None]
    return [p for p, _ in pairs], np.stack([h for _, h in pairs])


def nearest(query, ref, skip_self=False):
    out = np.empty(len(query), dtype=np.int32)
    for i, h in enumerate(query):
        d = POP[np.bitwise_xor(ref, h)].sum(axis=1)
        if skip_self:
            d[i] = 255
        out[i] = d.min()
    return out


if not (IMGS / "train").exists():
    sys.exit("No encuentro repo/dataset. Ejecuta setup_y_correr.bat")

print("Calculando hashes...")
files = {}
hashes = {}
for s in ("train", "val", "test"):
    files[s], hashes[s] = load(s)
    print(f"  {s}: {len(files[s])} imagenes")

print("\nDistancia Hamming al vecino mas cercano de train (0 = misma imagen visual, maximo 64):")
rows = {}
for q in ("val", "test"):
    d = nearest(hashes[q], hashes["train"])
    rows[q] = d
    n = len(d)
    print(f"  {q:4s}: d==0 {np.mean(d == 0):6.1%} | d<=4 {np.mean(d <= 4):6.1%} | "
          f"d<=8 {np.mean(d <= 8):6.1%} | mediana {int(np.median(d))}  (n={n})")

rng = np.random.default_rng(0)
idx = rng.choice(len(hashes["train"]), min(500, len(hashes["train"])), replace=False)
tr = hashes["train"]
ref_d = np.array([POP[np.bitwise_xor(np.delete(tr, i, axis=0), tr[i])].sum(axis=1).min() for i in idx])
print(f"  ref. train contra el resto de train (muestra {len(idx)}): d<=4 {np.mean(ref_d <= 4):6.1%} | "
      f"d<=8 {np.mean(ref_d <= 8):6.1%} | mediana {int(np.median(ref_d))}")

t = rows["test"]
print("\nLectura:")
frac = float(np.mean(t <= 4))
if frac >= 0.10:
    print(f"  {frac:.0%} de test tiene una copia casi identica en train: el mAP de test esta inflado.")
    print("  Para una medida honesta hay que rehacer los splits agrupando por foto original.")
elif frac >= 0.02:
    print(f"  {frac:.0%} de test tiene un casi-duplicado en train: fuga leve, tomar el mAP como optimista.")
else:
    print(f"  Solo {frac:.1%} de test tiene un casi-duplicado en train: no se ve fuga relevante.")

worst = np.argsort(t)[:10]
print("\nLos 10 pares test -> train mas parecidos (nombre en test, distancia):")
for i in worst:
    print(f"  {files['test'][i].name}  d={int(t[i])}")

# ---- duplicados exactos (mismo contenido byte a byte) ----
import collections  # noqa: E402
import hashlib  # noqa: E402

por_contenido = collections.defaultdict(list)
for s in ("train", "val", "test"):
    for p in files[s]:
        por_contenido[hashlib.sha256(p.read_bytes()).hexdigest()].append((s, p.name))
grupos = [v for v in por_contenido.values() if len(v) > 1]
dentro = sum(len(v) - 1 for v in grupos if len({s for s, _ in v}) == 1)
cruzan = [v for v in grupos if len({s for s, _ in v}) > 1]
print(f"\nDuplicados exactos: {len(grupos)} grupos; {dentro} copias sobrantes dentro de un mismo split; "
      f"{len(cruzan)} grupos que cruzan splits")
for v in cruzan:
    print("  cruza splits:", v)

# ---- salida en JSON para el articulo ----
import json  # noqa: E402

resumen = {
    "umbral_casi_duplicado": 8,
    "vecino_mas_cercano_en_train": {
        q: {"n": int(len(rows[q])), "d0": float(np.mean(rows[q] == 0)), "d_le4": float(np.mean(rows[q] <= 4)),
            "d_le8": float(np.mean(rows[q] <= 8)), "mediana": float(np.median(rows[q]))}
        for q in ("val", "test")
    },
    "train_contra_train_muestra": {"n": int(len(ref_d)), "d_le4": float(np.mean(ref_d <= 4)),
                                   "d_le8": float(np.mean(ref_d <= 8)), "mediana": float(np.median(ref_d))},
    "histograma_distancias": {q: np.bincount(rows[q], minlength=65).tolist() for q in ("val", "test")},
    "duplicados_exactos": {"grupos": len(grupos), "copias_dentro_de_un_split": int(dentro),
                           "grupos_que_cruzan_splits": len(cruzan)},
}
(HERE / "resultados").mkdir(exist_ok=True)
(HERE / "resultados" / "fugas.json").write_text(json.dumps(resumen, indent=2), encoding="utf-8")
