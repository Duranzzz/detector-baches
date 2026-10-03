# Test completo vs test limpio (Fase 5a)

Casi-duplicado = distancia dHash <= 8 contra alguna imagen de train. Mismo modelo, sin reentrenar.

| Subconjunto de test | Imagenes | Precision | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|---|
| completo | 718 | 0.796 | 0.600 | 0.711 | 0.394 |
| limpio | 670 | 0.806 | 0.614 | 0.719 | 0.399 |
| contaminado | 48 | 0.696 | 0.601 | 0.680 | 0.366 |

Nota: 'contaminado' son las imagenes de test con un casi-duplicado en train; 'limpio' son las demas. Si la fuga inflara el mAP, 'limpio' saldria claramente por debajo de 'completo'. 'contaminado' es un subconjunto chico (decenas de imagenes), asi que su cifra es ruidosa.
