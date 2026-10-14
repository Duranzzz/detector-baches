# Detección de baches para el mantenimiento vial en Santa Cruz

Prototipo que analiza una cámara, fotografías o videos y señala posibles baches para su revisión. Busca reunir evidencia visual que podría apoyar las inspecciones de calles de la Alcaldía de Santa Cruz de la Sierra.

El desarrollo integra un **detector previamente entrenado por terceros**, una interfaz con controles, procesamiento de videos y evaluaciones propias. La aplicación municipal es una propuesta: todavía no se ha probado en recorridos reales de Santa Cruz ni con personal de la Alcaldía.

Proyecto del primer parcial de Inteligencia Artificial, cuarto semestre de Ingeniería en Inteligencia Artificial, Departamento de Ciencias Informáticas y Robótica, Universidad Católica Boliviana “San Pablo”. Autor: Leonardo Duran Cuenca ([ORCID](https://orcid.org/0009-0001-1608-5788)).

## Qué funciona actualmente

- Cámara conectada, fotografía y video como entradas.
- Recuadros sobre posibles baches y ajuste de la confianza exigida.
- Pausa, capturas y cambio de cámara desde la ventana.
- Procesamiento por lotes de videos grabados con el celular.
- Video anotado, imagen destacada cuando hay detecciones y resumen por archivo.
- Ejecución en una laptop sin tarjeta gráfica dedicada.

Una detección debe revisarse. El sistema no mide profundidad o gravedad ni asigna prioridad de reparación. El resumen cuenta cuadros con detecciones, **no baches únicos**.

## Documentación y presentación

- [Artículo del proyecto](docs/articulo_deteccion_baches.docx): funcionamiento, pruebas, dificultades y resultados.
- [Presentación HTML](docs/presentacion.html): 11 diapositivas animadas, fotografías y mapa de referencia incrustados. Se abre en un navegador sin conexión.
- [Datos de tablas y gráfico](docs/datos_graficas.xlsx): evaluación inicial y análisis de imágenes repetidas.
- [Dataset y propuesta de publicación](docs/dataset.md).
- [Inventario del conjunto de referencia](docs/dataset_manifest.csv): particiones, nombres relativos, huellas y cantidad de anotaciones; no incluye fotografías.

En las diapositivas: flechas o espacio para avanzar y `F` para pantalla completa. En el celular se puede deslizar. No hay barras flotantes de navegación ni paneles de notas. El mapa de referencia de Santa Cruz ilustra una **función futura**, con recorrido y marcadores simulados para la segunda etapa.

## Cómo ejecutarlo en Windows

Se necesita Python 3.10 o superior, internet para instalar y aproximadamente 2 GB libres. Las pruebas existentes se realizaron con Python 3.14.7. El instalador descarga el conjunto de referencia y prepara un entorno local.

```powershell
git clone https://github.com/Duranzzz/detector-baches.git
cd detector-baches
.\setup_y_correr.bat
.\abrir_camara.bat
```

Después de instalar y descargar los archivos, las entradas y el procesamiento son locales. Falta una prueba con la conexión desactivada. Volver a ejecutar el instalador usa internet para comprobar o instalar dependencias.

### Cámara e imágenes

```powershell
.\.venv\Scripts\python.exe webcam.py                         # cámara de la laptop
.\.venv\Scripts\python.exe webcam.py --source 1              # otra cámara
.\.venv\Scripts\python.exe webcam.py --source foto.jpg       # fotografía
.\.venv\Scripts\python.exe webcam.py --source video.mp4      # video con ventana
.\.venv\Scripts\python.exe webcam.py --guardar demo.mp4      # cámara y grabación
```

| Control | Tecla | Acción |
|---|---|---|
| 0,25 / 0,35 / 0,50 | `1` / `2` / `3` | Cambiar la confianza exigida |
| − / + | `-` / `+` | Ajustar la confianza |
| Pausa / Seguir | Espacio | Congelar o continuar |
| Captura | `s` | Guardar en `resultados/capturas/` |
| Cámara | `c` | Probar otra cámara conectada |
| Salir | `q` / Esc | Cerrar |
| Pantalla completa | `f` | Cambiar la vista |

### Grabar con el celular y procesar en la laptop

1. Grabar videos cortos, de día y con el teléfono horizontal. Como punto de partida, usar 1080p y 30 cuadros por segundo. En iPhone, el formato “Más compatible” evita problemas de lectura de algunos videos HEVC.
2. Copiar los archivos a `videos/`.
3. Ejecutar `procesar_videos.bat` o arrastrar los archivos sobre ese acceso.
4. Revisar `videos/anotados/`: video anotado, imagen destacada si hubo detecciones y `resumen.csv`.

```powershell
.\.venv\Scripts\python.exe procesar_videos.py
.\.venv\Scripts\python.exe procesar_videos.py calle.mp4 --cada 2
.\.venv\Scripts\python.exe procesar_videos.py --conf 0.5
```

El celular **graba**; la computadora procesa. `--cada 2` analiza uno de cada dos cuadros y conserva aproximadamente la duración del video de salida. Las grabaciones y sus salidas se excluyen de Git.

## Resultados disponibles

Las cifras provienen de `resultados/`; no son mediciones en calles cruceñas. Equipo: Intel Core i7-1355U, 7,7 GB de memoria y procesamiento en CPU.

| Evaluación | Imágenes | Precisión | Recall | mAP50 | mAP50-95 |
|---|---:|---:|---:|---:|---:|
| Validación, configuración inicial | 720 | 0,810 | 0,621 | 0,730 | 0,404 |
| Prueba, configuración inicial | 718 | 0,796 | 0,600 | 0,711 | 0,394 |
| Prueba sin casi duplicados en entrenamiento | 670 | 0,806 | 0,614 | 0,719 | 0,399 |
| Validación, filtro ajustado a 0,5 | 720 | 0,843 | 0,638 | 0,751 | 0,401 |
| Prueba, filtro ajustado a 0,5 | 718 | 0,820 | 0,640 | 0,739 | 0,390 |

La precisión y el recall de esa tabla resumen el punto seleccionado por el evaluador; no representan necesariamente la confianza fija de la ventana. Para la configuración actual, los conteos a confianza fija son:

| Confianza | Detecciones correctas | Falsas alarmas | Baches omitidos | Precisión | Recall | F1 |
|---|---:|---:|---:|---:|---:|---:|
| 0,25 | 637 | 233 | 357 | 0,732 | 0,641 | 0,683 |
| 0,35, inicial de la demo | 581 | 145 | 413 | 0,800 | 0,585 | 0,676 |
| 0,50 | 486 | 55 | 508 | 0,898 | 0,489 | 0,633 |

Entre los niveles explorados, **0,25 obtiene el mayor F1**. La ventana conserva **0,35** como una opción que reduce falsas alarmas y permite cambiarla. La exploración se hizo sobre prueba; el ajuste debe confirmarse en escenas independientes.

La webcam con la interfaz inicial registró 17,4 cuadros por segundo en 922 cuadros. La interfaz posterior con botones se describió en las pruebas de desarrollo en torno a 15–17. Un video corto de prueba tomó unos 3 segundos para 30 cuadros, incluida la carga del detector. No hay medición con recorridos reales del celular.

## Dificultades y límites

- **Omisiones:** una fotografía produce una detección de confianza 0,32; se muestra con exigencia 0,25 y desaparece con 0,35. Aumentar la confianza también oculta baches reales.
- **Falsa detección:** una posición concreta del rostro del autor fue marcada como bache. No se registraron el umbral ni la frecuencia.
- **Datos desequilibrados:** solo 22 de las 4.719 imágenes tienen etiquetas vacías. Faltan más escenas sin baches.
- **Repetición:** 48 de las 718 imágenes de prueba tienen un casi duplicado en entrenamiento según el criterio visual utilizado. Retirarlas no reduce el mAP50 observado, pero esto no demuestra ausencia de sesgo.
- **Procedencia incompleta:** el conjunto mezcla fuentes sin una licencia de imágenes completamente documentada.
- **Entrenamiento:** no se reprodujo el original y su trazabilidad es incompleta. El aporte propio es la integración y evaluación del detector recibido.
- **Prueba local pendiente:** no se comprobó la generalización a calles de Santa Cruz, noche, lluvia o diferentes recorridos.

## Segunda etapa

1. Recolectar imágenes locales, con y sin baches, y registrar aciertos y errores.
2. Separar los datos por recorrido o escena y realizar un entrenamiento propio documentado.
3. Evaluar con escenas independientes y conservar los resultados.
4. Relacionar el tiempo del video con un registro GPS del celular y mostrar ubicaciones aproximadas en un mapa de Santa Cruz.
5. Agrupar observaciones repetidas y revisar cada registro antes de confirmarlo.

El mapa de la presentación ilustra esa propuesta. Actualmente no hay captura de GPS, mapa operativo ni mediciones de beneficios municipales.

## Reproducir las pruebas

```powershell
.\.venv\Scripts\python.exe verify.py
.\.venv\Scripts\python.exe auditar_dataset.py
.\.venv\Scripts\python.exe fugas.py
.\.venv\Scripts\python.exe test_limpio.py
.\.venv\Scripts\python.exe umbrales.py
.\.venv\Scripts\python.exe umbrales.py --nms 0.5
.\.venv\Scripts\python.exe nms.py
```

Estos comandos regeneran resultados. `nms.py` requiere ejecutar primero `verify.py`. El código fija la versión del repositorio de datos, pero el instalador no fija las versiones de las dependencias: una nueva instalación podría producir diferencias. Las versiones de la evaluación conservada están en `resultados/metricas.json`.

## Fuentes y licencias

- [Repositorio externo del detector y los datos, versión consultada](https://github.com/Bisman-Singh-Dev/YOLO-Pothole-Detection-Model/tree/bd8238b0f87083a1cea658336307d15b54eb7500).
- Código y pesos de este proyecto: **AGPL-3.0**, según [LICENSE](LICENSE).
- Artículo: **CC BY 4.0**, como indica su bloque de derechos de uso.
- La licencia del código de origen no aclara por sí sola las condiciones de cada imagen. El inventario describe archivos; no incluye ni autoriza redistribuir sus fotografías.
- Las fotos de la presentación conservan sus atribuciones y no representan calles de Santa Cruz.

La bibliografía del artículo conserva fuentes sobre daños viales, evaluación, datos y limitaciones.
