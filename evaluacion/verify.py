"""Verifica el modelo: integridad de los pesos, metricas en val/test y ejemplos anotados.

Uso (dentro del venv):  python evaluacion/verify.py
Escribe todo en resultados/ (metricas.json, ejemplos/).
"""
import hashlib
import json
import random
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent.parent  # raiz del proyecto
REPO = HERE / "repo"
WEIGHTS = HERE / "modelo" / "best.pt"
OUT = HERE / "resultados"
OUT.mkdir(exist_ok=True)

EXPECTED_SHA256 = "f3490f953b4ac2aa0205c206c151be8f2da281da99708713b182492a43c7751c"
# Metricas guardadas dentro del checkpoint por el autor (split val, al terminar su entrenamiento)
CHECKPOINT_METRICS = {"precision": 0.8113, "recall": 0.6191, "map50": 0.7302, "map50_95": 0.4040}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


if not WEIGHTS.exists():
    sys.exit(f"No encuentro los pesos en {WEIGHTS}")
if not (REPO / "dataset" / "images" / "test").exists():
    sys.exit(f"No encuentro el dataset en {REPO / 'dataset'}. Ejecuta setup_y_correr.bat")

digest = sha256(WEIGHTS)
print(f"Pesos: {WEIGHTS}")
print(f"SHA-256: {digest}")
print("Integridad:", "OK, coincide con la revisada" if digest == EXPECTED_SHA256
      else "DISTINTO al archivo que se reviso, no son los mismos pesos")

import torch  # noqa: E402
import ultralytics  # noqa: E402
from ultralytics import YOLO  # noqa: E402

device = 0 if torch.cuda.is_available() else "cpu"
print(f"ultralytics {ultralytics.__version__} | torch {torch.__version__} | dispositivo: "
      f"{'GPU ' + torch.cuda.get_device_name(0) if device == 0 else 'CPU'}")

# yaml con ruta absoluta para no depender del directorio de trabajo
data_yaml = OUT / "data_abs.yaml"
data_yaml.write_text(
    f"path: {(REPO / 'dataset').as_posix()}\n"
    "train: images/train\nval: images/val\ntest: images/test\n"
    "nc: 1\nnames:\n  0: pothole\n",
    encoding="utf-8",
)

model = YOLO(str(WEIGHTS))
print("Clases del modelo:", model.names)

results = {}
for split in ("val", "test"):
    print(f"\n--- Evaluando split '{split}' ---")
    m = model.val(data=str(data_yaml), split=split, imgsz=640, batch=16, device=device,
                  workers=0, plots=False, project=str(OUT), name=f"val_{split}",
                  exist_ok=True, verbose=False)
    results[split] = {
        "precision": float(m.box.mp),
        "recall": float(m.box.mr),
        "map50": float(m.box.map50),
        "map50_95": float(m.box.map),
        "ms_por_imagen": {k: round(float(v), 2) for k, v in m.speed.items()},
    }
    r = results[split]
    print(f"P={r['precision']:.3f}  R={r['recall']:.3f}  mAP50={r['map50']:.3f}  "
          f"mAP50-95={r['map50_95']:.3f}  inferencia={r['ms_por_imagen'].get('inference')} ms/img")

# ejemplos anotados (muestra fija, semilla 0)
test_imgs = sorted((REPO / "dataset" / "images" / "test").glob("*.jpg")) + \
            sorted((REPO / "dataset" / "images" / "test").glob("*.png"))
random.Random(0).shuffle(test_imgs)
sample = [str(p) for p in test_imgs[:12]]
model.predict(source=sample, conf=0.35, imgsz=640, device=device, save=True,
              project=str(OUT), name="ejemplos", exist_ok=True, verbose=False)
print(f"\nEjemplos anotados en {OUT / 'ejemplos'}")

payload = {
    "pesos_sha256": digest,
    "pesos_coinciden_con_los_revisados": digest == EXPECTED_SHA256,
    "ultralytics": ultralytics.__version__,
    "torch": torch.__version__,
    "dispositivo": "cuda" if device == 0 else "cpu",
    "metricas_en_este_equipo": results,
    "metricas_guardadas_en_el_checkpoint_split_val_del_autor": CHECKPOINT_METRICS,
}
(OUT / "metricas.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

c = CHECKPOINT_METRICS
print(f"\nEn este equipo ({payload['dispositivo']}), conf=0.001:")
for split, r in results.items():
    print(f"  {split:4s} P={r['precision']:.3f} R={r['recall']:.3f} mAP50={r['map50']:.3f} mAP50-95={r['map50_95']:.3f} "
          f"({r['ms_por_imagen'].get('inference')} ms/img)")
print(f"Guardado por el autor en el checkpoint (val): P={c['precision']:.3f} R={c['recall']:.3f} "
      f"mAP50={c['map50']:.3f} mAP50-95={c['map50_95']:.3f}")
print(f"Detalle en {OUT / 'metricas.json'}")
