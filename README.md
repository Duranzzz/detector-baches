# Detector de baches (YOLO11n): verificación reproducible

Verificación de un detector de baches ya entrenado (YOLO11n, una clase) y demo con webcam, video o imagen que corre en una laptop sin GPU.
No entrenamos el modelo: tomamos los pesos publicados por un tercero, comprobamos que son los que dicen ser, **reproducimos sus métricas ejecutándolas**, medimos la fuga de datos entre train y test, y documentamos lo que no se pudo verificar.

Proyecto del primer parcial de Inteligencia Artificial (4.º semestre, Ingeniería en Inteligencia Artificial, Departamento de Ciencias Informáticas y Robótica, Universidad Católica Boliviana "San Pablo"). Autor: Leonardo Duran Cuenca ([ORCID](https://orcid.org/0009-0001-1608-5788)).

> **Origen del modelo y del dataset:** [Bisman-Singh-Dev/YOLO-Pothole-Detection-Model](https://github.com/Bisman-Singh-Dev/YOLO-Pothole-Detection-Model), fijado al commit `bd8238b0f87083a1cea658336307d15b54eb7500`. El repo del autor cambia seguido; este proyecto no modifica ni sustituye su trabajo.

## Resultados medidos (CPU, sin GPU)

Equipo: Intel Core i7-1355U, 7.7 GB de RAM, Python 3.14.7, ultralytics 8.4.171, torch 2.14.1+cpu. Todo con `conf=0.001`, `imgsz=640`.

| Conjunto | Imágenes | Precisión | Recall | mAP50 | mAP50-95 |
|---|---|---|---|---|---|
| val, guardado por el autor en el checkpoint | 720 | 0.811 | 0.619 | 0.730 | 0.404 |
| **val, medido aquí** | 720 | 0.810 | 0.621 | 0.730 | 0.404 |
| test, declarado en el README del autor (mismo commit) | 718 | 0.797 | 0.600 | 0.711 | 0.394 |
| **test, medido aquí** | 718 | 0.796 | 0.600 | 0.711 | 0.394 |
| test limpio (sin casi-duplicado en train) | 670 | 0.806 | 0.614 | 0.719 | 0.399 |
| test con casi-duplicado en train | 48 | 0.696 | 0.601 | 0.680 | 0.366 |

- **Fuga train → test:** 6.7% de test tiene un casi-duplicado en train (distancia dHash de 64 bits ≤ 8). El mAP no se infla por eso: el test limpio sale igual o ligeramente mejor. El subconjunto contaminado es pequeño (48 imágenes), su cifra es ruidosa.
- **Velocidad:** ~62 ms por imagen en CPU durante la validación; 17.4 FPS promedio con la webcam y la ventana abierta (922 fotogramas). El autor declara 5.21 ms (~192 FPS) en una GPU NVIDIA RTX 4050: otro hardware, no comparable.
- **Duplicados exactos (byte a byte):** 13 grupos; 11 copias sobrantes dentro de un mismo split y 2 grupos que cruzan train y test.
- **Umbral de confianza en test** (IoU ≥ 0.5, medido en `umbrales.py`):

| conf ≥ | Precisión | Recall | F1 |
|---|---|---|---|
| 0.25 | 0.649 | 0.642 | 0.645 |
| **0.35** | 0.738 | 0.587 | **0.654** |
| 0.50 | 0.860 | 0.489 | 0.623 |
| 0.65 | 0.936 | 0.336 | 0.494 |

  0.35 da el mejor F1; 0.50 reduce las falsas alarmas a costa de perder casi la mitad de los baches.
- **Seguridad de los pesos:** `picklescan` no encontró nada malicioso en `best.pt` (0 archivos infectados, 0 globals peligrosos; de `__builtin__` solo pide `set`). Es una revisión heurística, ver `resultados/picklescan.txt`.

Detalle en [`resultados/`](resultados/) y en el artículo [`docs/articulo_deteccion_baches.docx`](docs/articulo_deteccion_baches.docx), que todavía tiene un campo marcado en rojo por completar: la fecha de envío.

## Cómo correrlo (Windows)

Necesitas Python 3.10 o superior (probado con 3.14), Git opcional, internet y ~2 GB libres.

```powershell
git clone https://github.com/Duranzzz/detector-baches.git
cd detector-baches
.\setup_y_correr.bat        # descarga el dataset (~640 MB), crea .venv, instala ultralytics y verifica
.\abrir_camara.bat          # abre la webcam
```

> `setup_y_correr.bat` no se probó de punta a punta como "doble clic": sus pasos se ejecutaron a mano y funcionaron.

Pasos a mano, desde esta carpeta:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install ultralytics
.\.venv\Scripts\python.exe verify.py          # SHA-256 de los pesos + métricas en val y test -> resultados\metricas.json
.\.venv\Scripts\python.exe fugas.py           # casi-duplicados train -> val/test
.\.venv\Scripts\python.exe test_limpio.py     # test completo vs limpio vs contaminado
.\.venv\Scripts\python.exe umbrales.py        # precisión/recall por umbral de confianza
```

(`verify.py` espera el dataset en `repo\dataset`; lo descarga `setup_y_correr.bat`.)

### Demo: webcam, video o imagen

```powershell
.\.venv\Scripts\python.exe webcam.py                          # webcam 0
.\.venv\Scripts\python.exe webcam.py --source video.mp4       # video
.\.venv\Scripts\python.exe webcam.py --source foto.jpg        # imagen
.\.venv\Scripts\python.exe webcam.py --source foto.jpg --no-show   # sin ventana, guarda en resultados\capturas
```

Teclas: `q`/ESC salir · `+`/`-` umbral ±0.05 · `1`/`2`/`3` umbral 0.25/0.35/0.50 · `s` guardar captura.

## Contenido

| Ruta | Qué es |
|---|---|
| `modelo/best.pt` | Pesos (5.5 MB). SHA-256 `f3490f953b4ac2aa0205c206c151be8f2da281da99708713b182492a43c7751c` |
| `verify.py` | Comprueba el hash y mide P, R, mAP50, mAP50-95 en val y test |
| `auditar_dataset.py` | Conteos por split, etiquetas mal formadas, cajas fuera de rango, etiquetas vacías |
| `fugas.py` | Distancia dHash de cada imagen de val/test a su vecino más cercano de train, y duplicados exactos |
| `test_limpio.py` | Evalúa el test completo, el limpio y el contaminado |
| `umbrales.py` | Precisión, recall y F1 por umbral de confianza |
| `webcam.py` | Detección en vivo, sobre video o sobre una imagen |
| `setup_y_correr.bat`, `abrir_camara.bat` | Instalación y atajo a la cámara |
| `resultados/` | Salidas medidas en JSON: `metricas`, `dataset`, `fugas`, `test_limpio`, `umbrales`, y `picklescan.txt` |
| `docs/articulo_deteccion_baches.docx` | Artículo (12 páginas) en el formato de la Revista 3i, con los resultados de este repo |
| `docs/datos_graficas.xlsx` | Datos de las tablas y gráfico editable de la figura 1 (la revista pide las gráficas en un Excel aparte) |

## Limitaciones (lo que no se verificó o no se puede afirmar)

- **No se entrenó nada.** Las métricas son del modelo de un tercero; el entrenamiento (15 épocas, desde unos pesos propios del autor anteriores) no se reprodujo.
- **El dataset no tiene procedencia ni licencia documentadas.** Es una mezcla de varias fuentes; no sabemos con qué licencia se puede redistribuir cada imagen. Por eso este repo **no incluye imágenes del dataset** (se descargan del repo del autor).
- **La fuga se midió con un hash perceptual** (dHash de 64 bits, umbral 8), que detecta copias casi idénticas, no cualquier parecido entre escenas. Medir generalización real requiere un test externo (por ejemplo RDD2022 o HRP4K), no hecho.
- **Falso positivo observado a mano:** con la webcam apuntando a una cara, en una posición muy concreta de la cara el modelo la marcó como bache. Una prueba de 60 fotogramas de un escritorio sin baches dio 0 detecciones a 0.25, 0.35 y 0.50, así que no es un problema general, pero la cara a esa distancia y ángulo sí es un contraejemplo. No se midió su frecuencia.
- **Dominio:** el modelo se entrenó con imágenes de calle (cámara de vehículo, dron, fotos). Una webcam de escritorio solo sirve apuntando a fotos o video de baches.
- **Un solo equipo, CPU:** los tiempos no se compararon con GPU ni con otros equipos.

## Licencias

- **Código y pesos de este repo: AGPL-3.0** (archivo [`LICENSE`](LICENSE)). Se eligió porque Ultralytics y el checkpoint de `best.pt` declaran AGPL-3.0 y este repo redistribuye los pesos. Si el proyecto pasara a uso comercial, esto hay que revisarlo.
- **Artículo (`docs/`): CC BY 4.0**, como indica la plantilla de la revista (https://creativecommons.org/licenses/by/4.0/deed.es).
- El repo de origen del modelo y del dataset declara MIT; la licencia de las imágenes del dataset no está documentada, por eso no se incluyen aquí.

## Referencias

Ver la lista completa en el artículo ([`docs/`](docs/)). Principales:

- Arya, D., et al. (2022). RDD2022: A multi-national image dataset for automatic road damage detection. https://doi.org/10.48550/arXiv.2209.08538
- Khanam, R., & Hussain, M. (2024). YOLOv11: An overview of the key architectural enhancements. https://doi.org/10.48550/arXiv.2410.17725
- Barz, B., & Denzler, J. (2020). Do we train on test data? Purging CIFAR of near-duplicates. *Journal of Imaging, 6*(6), 41. https://doi.org/10.3390/jimaging6060041
