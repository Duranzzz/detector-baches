# Precision y recall por umbral de confianza (split test, IoU >= 0.5)

718 imagenes, 994 cajas reales. Mismo modelo, sin reentrenar.

| conf >= | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| 0.10 | 729 | 921 | 265 | 0.442 | 0.733 | 0.551 |
| 0.25 | 638 | 345 | 356 | 0.649 | 0.642 | 0.645 |
| 0.35 | 583 | 207 | 411 | 0.738 | 0.587 | 0.654 |
| 0.50 | 486 | 79 | 508 | 0.860 | 0.489 | 0.623 |
| 0.65 | 334 | 23 | 660 | 0.936 | 0.336 | 0.494 |
