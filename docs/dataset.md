# Conjunto de referencia y propuesta de publicación

El prototipo se evaluó con 4.719 imágenes y 7.340 anotaciones de baches, obtenidas de un [repositorio externo en una versión fijada](https://github.com/Bisman-Singh-Dev/YOLO-Pothole-Detection-Model/tree/bd8238b0f87083a1cea658336307d15b54eb7500). No es una colección recolectada por este proyecto ni una muestra de calles de Santa Cruz.

| Partición original | Imágenes | Baches anotados | Imágenes con etiqueta vacía |
|---|---:|---:|---:|
| Entrenamiento | 3.281 | 5.353 | 18 |
| Validación | 720 | 993 | 2 |
| Prueba | 718 | 994 | 2 |
| Total | 4.719 | 7.340 | 22 |

La procedencia y la licencia de cada fuente de imágenes no están completamente documentadas. Por ahora se prepara un inventario sin fotografías para una posible publicación; no se presenta esta colección como un dataset propio ni se le asigna una licencia de imágenes nueva.

## Qué contiene el inventario

[dataset_manifest.csv](dataset_manifest.csv) registra un archivo por imagen, con estas columnas:

- `split`: partición original, sin modificarla.
- `imagen`: ruta relativa dentro de `repo/dataset/`.
- `etiqueta`: ruta relativa de las anotaciones.
- `sha256_imagen` y `sha256_etiqueta`: huellas para comprobar los archivos.
- `baches_anotados`: cantidad de líneas de anotación no vacías.

El inventario no incluye rutas personales, fotografías, videos ni coordenadas. Describe una copia local de la versión consultada; permite contrastar nombres, cantidades e integridad después de obtener los archivos desde su fuente. Las particiones originales no garantizan independencia entre escenas.

## Limitaciones de los datos actuales

Solo 22 imágenes tienen etiquetas vacías. El criterio de huella visual identifica 48 de las 718 imágenes de prueba con distancia de hasta 8 a alguna imagen de entrenamiento. El método detecta casi copias y no todas las relaciones entre escenas. No se dispone de una identificación completa de los recorridos, cámaras o fuentes originales.

Los resultados no permiten afirmar el mismo desempeño en calles de Santa Cruz. Los conteos y el análisis de similitudes están en `resultados/dataset.json` y `resultados/fugas.json`.

## Dónde publicar la futura colección local

La propuesta es un repositorio en **Hugging Face Datasets**, separado del código, con nombre provisional `baches-santa-cruz`. La plataforma permite alojar imágenes, conservar versiones y presentar una ficha descriptiva. [Guía de publicación](https://huggingface.co/docs/hub/datasets-adding) y [fichas de datos](https://huggingface.co/docs/hub/datasets-cards).

Todavía no se creó ese repositorio ni se subió material. Mientras se aclaran los permisos de la colección externa, el inventario y esta documentación pueden acompañar el proyecto. La colección local necesitará sus propias imágenes, revisión de permisos y condiciones de publicación.

## Contenido de la ficha de la colección local

1. Propósito académico y evaluación de posibles baches visibles; no equivale a un inventario municipal confirmado.
2. Autoría, fuente, fechas de captura y condiciones de uso de cada grupo de archivos.
3. Dispositivo, resolución, luz, superficie y procedencia de cada recorrido.
4. Clases y criterio de anotación, incluidos ejemplos sin baches y casos ambiguos.
5. Cantidades por clase y partición; separación por recorrido o escena para evitar compartir cuadros relacionados entre entrenamiento y prueba.
6. Revisión de personas y placas antes de publicar; descripción de cualquier anonimización aplicada.
7. Errores conocidos, sesgos de cobertura y condiciones no evaluadas.
8. Versión, licencia confirmada, cita recomendada y registro de cambios.

La ubicación precisa se conservaría cuando fuera necesaria para la evaluación y su publicación estuviera justificada. Para el futuro mapa, el GPS del celular indicaría inicialmente una posición aproximada de captura, no la coordenada exacta del bache.

## Uso en el artículo y las diapositivas

El artículo identifica el conjunto utilizado, sus cantidades y limitaciones. Las diapositivas presentan la recolección local y el mapa como acciones de la segunda etapa. Hasta realizar nuevas pruebas, las fotografías de demostración siguen siendo referencias externas con sus atribuciones.
