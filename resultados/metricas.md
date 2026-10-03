# Metricas del modelo (medidas en este equipo)

- Pesos SHA-256: `f3490f953b4ac2aa0205c206c151be8f2da281da99708713b182492a43c7751c` (coinciden con los revisados)
- ultralytics 8.4.171, torch 2.14.1+cpu, dispositivo cpu

| Split | Precision | Recall | mAP50 | mAP50-95 | ms/img (inferencia) |
|---|---|---|---|---|---|
| val | 0.810 | 0.621 | 0.730 | 0.404 | 62.09 |
| test | 0.796 | 0.600 | 0.711 | 0.394 | 62.28 |

Referencia, guardada por el autor dentro del checkpoint (val): P=0.811, R=0.619, mAP50=0.730, mAP50-95=0.404.
Las metricas se calculan con conf=0.001, el valor por defecto de ultralytics para validar. Con la camara se usa un umbral mayor (0.35).
