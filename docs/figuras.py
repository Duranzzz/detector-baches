"""Genera las figuras del articulo a partir de los numeros medidos (resultados/*.json) y del dataset.

Uso (dentro del venv, desde la raiz del proyecto):  python docs/figuras.py
Escribe docs/figuras/fig1_metricas.png, fig1_fuga.png y fig2_umbrales.png (300 dpi).
Fig. 1 recalcula los hashes dHash del dataset (repo/dataset), ~15 s.
"""
import json
import sys
from pathlib import Path

import cv2
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "resultados"
OUT = ROOT / "docs" / "figuras"
OUT.mkdir(parents=True, exist_ok=True)
IMGS = ROOT / "repo" / "dataset" / "images"
EXT = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
POP = np.array([bin(i).count("1") for i in range(256)], dtype=np.uint8)

plt.rcParams.update({"font.family": "Arial", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
COL = ["#8da0cb", "#1b4f9c", "#e08214", "#4daf4a"]  # paleta apta para daltonismo


def dhash(p):
    im = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
    im = cv2.resize(im, (9, 8), interpolation=cv2.INTER_AREA)
    return np.packbits((im[:, 1:] > im[:, :-1]).flatten())


def hashes(split):
    return np.stack([dhash(p) for p in sorted((IMGS / split).iterdir()) if p.suffix.lower() in EXT])


def fig_fuga():
    tr = hashes("train")
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    bins = np.arange(0, 33, 1)
    for nombre, split, c in (("Val", "val", COL[1]), ("Test", "test", COL[2])):
        h = hashes(split)
        d = np.array([POP[np.bitwise_xor(tr, x)].sum(axis=1).min() for x in h])
        ax.hist(d, bins=bins, histtype="step", linewidth=1.8, color=c, label=f"{nombre} (n={len(d)}; ≤ 8: {np.mean(d <= 8):.1%})")
    ax.axvline(8, color="gray", linestyle="--", linewidth=1)
    ax.text(8.8, ax.get_ylim()[1] * 0.92, "umbral = 8", fontsize=8, color="gray")
    ax.set_xlim(-0.5, 30)
    ax.set_xlabel("Distancia de Hamming (dHash de 64 bits) al vecino más cercano en train")
    ax.set_ylabel("Número de imágenes")
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(OUT / "fig1_fuga.png", dpi=300)
    plt.close(fig)


def fig_umbrales():
    u = json.loads((RES / "umbrales.json").read_text(encoding="utf-8"))["umbrales"]
    xs = [float(k) for k in u]
    fig, ax = plt.subplots(figsize=(6.5, 3.4))
    for clave, nombre, c in (("precision", "Precisión", COL[1]), ("recall", "Recall", COL[2]), ("f1", "F1", COL[3])):
        ys = [v[clave] for v in u.values()]
        ax.plot(xs, ys, marker="o", color=c, label=nombre)
    mejor = max(u.items(), key=lambda kv: kv[1]["f1"])
    ax.annotate(f"mejor F1 = {mejor[1]['f1']:.3f}\n(conf ≥ {mejor[0]})", (float(mejor[0]), mejor[1]["f1"]),
                textcoords="offset points", xytext=(12, -42), fontsize=8,
                arrowprops={"arrowstyle": "-", "color": "gray"})
    ax.set_xlabel("Umbral de confianza")
    ax.set_ylabel("Valor (IoU ≥ 0.5)")
    ax.set_ylim(0, 1.0)
    ax.legend(fontsize=8, frameon=False, loc="lower left")
    fig.tight_layout()
    fig.savefig(OUT / "fig2_umbrales.png", dpi=300)
    plt.close(fig)


if __name__ == "__main__":
    fig_umbrales()
    if (IMGS / "train").exists():
        fig_fuga()
    else:
        sys.exit("Falta repo/dataset: fig1_fuga.png no se genero")
    print("Figuras en", OUT)
