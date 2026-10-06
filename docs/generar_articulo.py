"""Genera el articulo en el formato de la Revista 3i a partir de la plantilla .docx y de los resultados medidos.

Uso (dentro del venv, desde la raiz del proyecto):
    python docs/generar_articulo.py "ruta/a/Articulo Cientifico-Revista 3i formato.docx"
Requiere: python-docx, y haber corrido antes docs/figuras.py y los scripts que escriben resultados/*.json.
Los numeros de las tablas se leen de resultados/*.json (no se teclean a mano).
Escribe docs/articulo_deteccion_baches.docx. Convencion numerica de la plantilla: coma decimal y punto de miles.
"""
import json
import re
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "resultados"
FIG = ROOT / "docs" / "figuras"
OUT = ROOT / "docs" / "articulo_deteccion_baches.docx"
TEMPLATE = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "Artículo Científico-Revista 3i formato.docx"
if not TEMPLATE.exists():
    sys.exit(f"No encuentro la plantilla: {TEMPLATE}")

J = lambda n: json.loads((RES / n).read_text(encoding="utf-8"))  # noqa: E731
M = J("metricas.json")
TL = J("test_limpio.json")["resultados"]
UM = J("umbrales.json")
FU = J("fugas.json")
DS = J("dataset.json")


def n(x, d=3):
    """Numero con coma decimal."""
    return f"{x:.{d}f}".replace(".", ",")


def pct(x, d=1):
    return f"{n(100 * x, d)} %"


def miles(x):
    return f"{x:,}".replace(",", ".")


# ------------------------------------------------------------------ documento base
doc = Document(str(TEMPLATE))
body = doc.element.body
for el in list(body):
    if el.tag != qn("w:sectPr"):
        body.remove(el)
doc.core_properties.title = "Verificación reproducible de un detector de baches con inteligencia artificial"
doc.core_properties.author = "Leonardo Duran Cuenca"
doc.core_properties.subject = "Artículo en el formato de la Revista 3i"

TOKEN = re.compile(r"(\*\*.+?\*\*|\*.+?\*)")
RED = RGBColor(0xFF, 0x00, 0x00)


def add_run(p, text, bold=False, italic=False, size=12, color=None, font="Arial"):
    r = p.add_run(text)
    r.bold = bold or None
    r.italic = italic or None
    r.font.size = Pt(size)
    r.font.name = font
    rpr = r._r.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    for a in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(a), font)
    if color is not None:
        r.font.color.rgb = color
    return r


def add_marked(p, text, size=12, bold=False, italic=False, color=None):
    """Texto con **negrita** y *cursiva*; [[texto]] = marcador rojo de pendiente."""
    for part in re.split(r"(\[\[.+?\]\])", text):
        if part.startswith("[[") and part.endswith("]]"):
            add_run(p, part[2:-2], size=size, bold=bold, italic=italic, color=RED)
            continue
        for tok in TOKEN.split(part):
            if not tok:
                continue
            if tok.startswith("**"):
                add_run(p, tok[2:-2], size=size, bold=True, italic=italic, color=color)
            elif tok.startswith("*"):
                add_run(p, tok[1:-1], size=size, bold=bold, italic=True, color=color)
            else:
                add_run(p, tok, size=size, bold=bold, italic=italic, color=color)


def para(text="", style="Body Text", align=WD_ALIGN_PARAGRAPH.JUSTIFY, before=3, after=6, line=1.5,
         left=None, right=None, size=12, bold=False, italic=False, keep_next=False, color=None):
    p = doc.add_paragraph(style=style)
    pf = p.paragraph_format
    pf.alignment = align
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    pf.line_spacing = line
    if left is not None:
        pf.left_indent = Inches(left)
    if right is not None:
        pf.right_indent = Inches(right)
    pf.keep_with_next = keep_next
    if text:
        add_marked(p, text, size=size, bold=bold, italic=italic, color=color)
    return p


def heading(text, align=None):
    p = doc.add_paragraph(text, style="Heading 1")
    if align is not None:
        p.paragraph_format.alignment = align
    return p


def sub(text):
    return para(text, align=WD_ALIGN_PARAGRAPH.LEFT, bold=True, keep_next=True, before=10, after=2)


# ------------------------------------------------------------------ tablas, figuras, ecuaciones
tab_n = fig_n = 0


def caption_tabla(titulo):
    global tab_n
    tab_n += 1
    p = doc.add_paragraph(style="Caption")
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(0)
    p.paragraph_format.line_spacing = 1.5
    add_run(p, f"Tabla {tab_n}", bold=True, italic=False, color=RGBColor(0, 0, 0))
    p.add_run().add_break(WD_BREAK.LINE)
    add_run(p, titulo, italic=False, color=RGBColor(0, 0, 0))
    return tab_n


def borders_xml(tag, top=True, bottom=True):
    parts = []
    if top:
        parts.append('<w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>')
    if bottom:
        parts.append('<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>')
    return parse_xml(f'<w:{tag} xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">{"".join(parts)}</w:{tag}>')


def tabla(encabezado, filas, anchos, nota=None, alinear_primera="left"):
    """Tabla APA: solo lineas horizontales, Arial 11, encabezado en negrita. anchos en twips (suman <= 9360)."""
    t = doc.add_table(rows=1 + len(filas), cols=len(encabezado))
    t.autofit = False
    tblPr = t._tbl.tblPr
    for ch in list(tblPr):
        tblPr.remove(ch)
    W_ = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    tblPr.append(parse_xml(f'<w:tblW xmlns:w="{W_}" w:w="{sum(anchos)}" w:type="dxa"/>'))
    tblPr.append(borders_xml("tblBorders"))
    tblPr.append(parse_xml(f'<w:tblLayout xmlns:w="{W_}" w:type="fixed"/>'))
    tblPr.append(parse_xml(f'<w:tblCellMar xmlns:w="{W_}"><w:left w:w="70" w:type="dxa"/><w:right w:w="70" w:type="dxa"/></w:tblCellMar>'))
    tblPr.append(parse_xml(f'<w:tblLook xmlns:w="{W_}" w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/>'))
    grid = t._tbl.tblGrid
    for gc, w in zip(grid.findall(qn("w:gridCol")), anchos):
        gc.set(qn("w:w"), str(w))
    todas = [encabezado] + filas
    for ri, fila in enumerate(todas):
        for ci, val in enumerate(fila):
            c = t.cell(ri, ci)
            c.width = Inches(anchos[ci] / 1440)
            tcPr = c._tc.get_or_add_tcPr()
            tcPr.append(borders_xml("tcBorders"))
            tcPr.append(parse_xml('<w:vAlign xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" w:val="center"/>'))
            p = c.paragraphs[0]
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.line_spacing = 1.0
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT if (ci == 0 and alinear_primera == "left") else WD_ALIGN_PARAGRAPH.CENTER
            add_marked(p, str(val), size=11, bold=(ri == 0))
    for ri in range(len(t.rows) - (0 if nota else 1)):
        for c in t.rows[ri].cells:
            for pp in c.paragraphs:
                pp.paragraph_format.keep_with_next = True
    # no partir filas y repetir el encabezado (cantSplit va antes que tblHeader en el esquema)
    for i, r in enumerate(t.rows):
        trPr = r._tr.get_or_add_trPr()
        trPr.append(parse_xml('<w:cantSplit xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'))
        if i == 0:
            trPr.append(parse_xml('<w:tblHeader xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>'))
    if nota:
        p = para(align=WD_ALIGN_PARAGRAPH.LEFT, before=4, after=10, line=1.0)
        add_run(p, "Nota.", bold=True, italic=True, size=10)
        add_marked(p, " " + nota, size=10)
    return t


def figura(archivo, titulo, nota, ancho=5.3):
    global fig_n
    fig_n += 1
    para(f"**Figura {fig_n}.**", align=WD_ALIGN_PARAGRAPH.LEFT, keep_next=True, before=8, after=0, line=1.0)
    para(titulo, align=WD_ALIGN_PARAGRAPH.LEFT, italic=True, keep_next=True, before=0, after=4, line=1.0)
    p = para(align=WD_ALIGN_PARAGRAPH.CENTER, keep_next=True, before=0, after=2, line=1.0)
    p.add_run().add_picture(str(FIG / archivo), width=Inches(ancho))
    q = para(align=WD_ALIGN_PARAGRAPH.LEFT, before=2, after=10, line=1.0)
    add_run(q, "Nota.", bold=True, italic=True, size=10)
    add_marked(q, " " + nota, size=10)
    return fig_n


MNS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def mt(t, plain=False):
    sty = '<m:rPr><m:sty m:val="p"/></m:rPr>' if plain else ""
    return f'<m:r>{sty}<m:t xml:space="preserve">{t}</m:t></m:r>'


def frac(a, b):
    return f"<m:f><m:num>{a}</m:num><m:den>{b}</m:den></m:f>"


def ssub(base, sub_):
    return f"<m:sSub><m:e>{mt(base)}</m:e><m:sub>{mt(sub_, True)}</m:sub></m:sSub>"


def ecuacion(omml, numero):
    """Ecuacion centrada, nativa de Word (OMML), numerada entre corchetes."""
    xml = (f'<w:p xmlns:w="{WNS}" xmlns:m="{MNS}"><w:pPr><w:tabs><w:tab w:val="center" w:pos="4680"/>'
           f'<w:tab w:val="right" w:pos="9360"/></w:tabs><w:spacing w:before="120" w:after="120"/></w:pPr>'
           f'<w:r><w:tab/></w:r><m:oMath>{omml}</m:oMath>'
           f'<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:cs="Arial"/><w:sz w:val="24"/></w:rPr><w:tab/><w:t>[{numero}]</w:t></w:r></w:p>')
    body.insert(len(body) - 1, parse_xml(xml))


def referencia(partes):
    """Referencia APA 7 con sangria francesa. partes: lista de (texto, cursiva)."""
    p = para(align=WD_ALIGN_PARAGRAPH.LEFT, before=0, after=3, line=1.5)
    p.paragraph_format.left_indent = Inches(0.5)
    p.paragraph_format.first_line_indent = Inches(-0.5)
    for texto, cur in partes:
        add_run(p, texto, italic=cur)
    return p


# ------------------------------------------------------------------ cifras
mv, mt_ = M["metricas_en_este_equipo"]["val"], M["metricas_en_este_equipo"]["test"]
ck = M["metricas_guardadas_en_el_checkpoint_split_val_del_autor"]
README_TEST = {"precision": 0.7968, "recall": 0.6000, "map50": 0.7110, "map50_95": 0.3937}
um = UM["umbrales"]
mejor_u, mejor = max(um.items(), key=lambda kv: kv[1]["f1"])
d_val, d_test = FU["vecino_mas_cercano_en_train"]["val"], FU["vecino_mas_cercano_en_train"]["test"]
d_tr = FU["train_contra_train_muestra"]
dup = FU["duplicados_exactos"]
n_lim, n_con = TL["limpio"]["imagenes"], TL["contaminado"]["imagenes"]
tot_img = sum(DS[s]["imagenes"] for s in DS)
tot_box = sum(DS[s]["cajas"] for s in DS)

# ================================================================== PORTADA
ES_TITULO = "Verificación reproducible de un detector de baches con inteligencia artificial"
EN_TITULO = "Reproducible verification of a pothole detector using artificial intelligence"
PT_TITULO = "Verificação reprodutível de um detector de buracos com inteligência artificial"
assert len(ES_TITULO.split()) <= 12

para(ES_TITULO, align=WD_ALIGN_PARAGRAPH.CENTER, bold=True, size=14, before=8, after=6, line=1.15)
para(EN_TITULO, align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, before=6, after=0)
para(PT_TITULO, align=WD_ALIGN_PARAGRAPH.CENTER, italic=True, before=6, after=10)

para("**Leonardo Duran Cuenca**", align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=0, line=1.15)
para("Facultad de [[por definir]]", align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=0, line=1.15)
para("Universidad Católica Boliviana “San Pablo”", align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=0, line=1.15)
para("https://orcid.org/0009-0001-1608-5788", align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=0, line=1.15)
para("leonardo.duran.c1@ucb.edu.bo", align=WD_ALIGN_PARAGRAPH.CENTER, before=0, after=12, line=1.15)
para("Recibido: [[fecha de envío por definir]]", align=WD_ALIGN_PARAGRAPH.LEFT, before=0, after=10, line=1.15)

# ------------------------------------------------------------------ resumen / abstract / resumo
RESUMEN = (
    "El objetivo de la investigación fue verificar, mediante ejecución propia, un detector de baches YOLO11n de una sola "
    "clase publicado por un tercero, en relación con la reproducibilidad de sus métricas, la calidad de su conjunto de "
    "datos y su uso en un equipo sin GPU. Para ello se desarrolló una investigación con enfoque cuantitativo y diseño de "
    f"replicación, aplicada a {miles(tot_img)} imágenes; la recolección de datos se realizó ejecutando el modelo en CPU y "
    "registrando sus salidas, y el análisis se llevó a cabo con mAP, precisión, recall, F1 por umbral de confianza y un "
    "hash perceptual para medir casi-duplicados. Los resultados evidenciaron que las métricas se reproducen "
    f"(mAP50 de {n(mv['map50'])} en validación y {n(mt_['map50'])} en prueba), que {pct(d_test['d_le8'])} de la prueba "
    f"tiene un casi-duplicado en entrenamiento sin inflar el mAP, que el mejor F1 ({n(mejor['f1'])}) aparece con un "
    f"umbral de {n(float(mejor_u), 2)} y que el sistema procesa 17,4 cuadros por segundo con una webcam. En conclusión, "
    "el reconocimiento de formas del modelo es consistente con lo declarado dentro del dominio de sus datos, pero la "
    "procedencia del conjunto de datos y su desempeño con otras cámaras siguen sin verificarse."
)
ABSTRACT = (
    "The objective of the research was to verify, through our own execution, a single-class YOLO11n pothole detector "
    "published by a third party, in relation to the reproducibility of its metrics, the quality of its dataset, and its use "
    "on a machine without a GPU. To this end, a study with a quantitative approach and a replication design was conducted, "
    f"applied to {tot_img:,} images; data collection was carried out by running the model on a CPU and recording its "
    "outputs, and analysis was performed through mAP, precision, recall, F1 by confidence threshold, and a perceptual hash "
    "to measure near-duplicates. The results showed that the metrics are reproduced "
    f"(mAP50 of {mv['map50']:.3f} on validation and {mt_['map50']:.3f} on test), that {100 * d_test['d_le8']:.1f}% of the test "
    f"set has a near-duplicate in the training set without inflating the mAP, that the best F1 ({mejor['f1']:.3f}) appears "
    f"at a threshold of {float(mejor_u):.2f}, and that the system processes 17.4 frames per second with a webcam. In "
    "conclusion, the pattern recognition performed by the model is consistent with what is reported within the domain of "
    "its data, but the provenance of the dataset and the performance with other cameras remain unverified."
)
RESUMO = (
    "O objetivo desta pesquisa foi verificar, por meio de execução própria, um detector de buracos YOLO11n de uma única "
    "classe publicado por terceiros, em relação à reprodutibilidade de suas métricas, à qualidade de seu conjunto de dados "
    "e ao seu uso em um equipamento sem GPU. Para tanto, foi desenvolvida uma pesquisa com abordagem quantitativa e "
    f"delineamento de replicação, aplicada a {miles(tot_img)} imagens. A coleta de dados foi realizada executando o modelo "
    "em CPU e registrando suas saídas, e a análise foi conduzida por meio de mAP, precisão, recall, F1 por limiar de "
    "confiança e um hash perceptual para medir quase duplicatas. Os resultados revelaram que as métricas são reproduzidas "
    f"(mAP50 de {n(mv['map50'])} na validação e {n(mt_['map50'])} no teste), que {pct(d_test['d_le8'])} do teste tem uma "
    f"quase duplicata no treinamento sem inflar o mAP, que o melhor F1 ({n(mejor['f1'])}) ocorre com um limiar de "
    f"{n(float(mejor_u), 2)} e que o sistema processa 17,4 quadros por segundo com uma webcam. Em conclusão, o "
    "reconhecimento de padrões do modelo é consistente com o declarado dentro do domínio de seus dados, mas a procedência "
    "do conjunto de dados e o desempenho com outras câmeras continuam sem verificação."
)
for nombre, txt in (("Resumen", RESUMEN), ("Abstract", ABSTRACT), ("Resumo", RESUMO)):
    assert len(txt.split()) <= 200, (nombre, len(txt.split()))

para("Resumen", align=WD_ALIGN_PARAGRAPH.LEFT, bold=True, before=6, after=2, line=1.0, keep_next=True)
para(RESUMEN, left=0.5, before=2, after=6, line=1.15)
para("**Palabras clave:** inteligencia artificial, reconocimiento de formas, baches. "
     "[[Pendiente: confirmar los términos en el Tesauro de la UNESCO (en inglés se confirmaron “Artificial intelligence” y “Pattern recognition”) y elegir un tercero.]]",
     left=0.5, right=0.08, before=2, after=14, line=1.15)
heading("Abstract", align=WD_ALIGN_PARAGRAPH.LEFT)
para(ABSTRACT, left=0.5, before=6, after=6, line=1.15)
para("**Keywords:** artificial intelligence, pattern recognition, potholes", left=0.5, before=2, after=14, line=1.15)
para("Resumo", align=WD_ALIGN_PARAGRAPH.LEFT, bold=True, before=6, after=2, line=1.15, keep_next=True)
para(RESUMO, left=0.5, before=2, after=6, line=1.15)
para("**Palavras-chave:** inteligência artificial, reconhecimento de padrões, buracos", left=0.5, before=2, after=10, line=1.15)

# ================================================================== INTRODUCCIÓN
heading("Introducción")
para("Los baches deterioran la seguridad vial y elevan los costos de mantenimiento, y detectarlos de forma automática con "
     "visión por computador es una línea de trabajo consolidada (Ma et al., 2022). La familia YOLO, que parte de los "
     "detectores de una sola etapa (Redmon et al., 2015), es la base de buena parte de los sistemas de detección en tiempo "
     "real; su versión 11 incorpora bloques C3k2 y de atención espacial C2PSA (Khanam & Hussain, 2024). Para esta tarea "
     "existen conjuntos de datos públicos como RDD2022, con 47.420 imágenes de seis países y más de 55.000 instancias de "
     "daño en cuatro categorías (Arya et al., 2022), y HRP4K, de imágenes de alta resolución en perspectiva (Chen et al., "
     "2026), y sistemas que combinan YOLO con georreferenciación (Sahoo et al., 2025).")
para("Sin embargo, muchos modelos se publican con métricas autodeclaradas que nadie volvió a ejecutar y con conjuntos de "
     "datos cuya procedencia y licencia no están documentadas, algo que las prácticas de documentación de datos buscan evitar "
     "(Gebru et al., 2021). Además, si hay imágenes casi idénticas entre entrenamiento y prueba, la métrica de prueba se "
     "vuelve optimista: en CIFAR, el 3,3 % y el 10 % de las imágenes de prueba de CIFAR-10 y CIFAR-100 tenían duplicados "
     "en el conjunto de entrenamiento (Barz & Denzler, 2020). Por último, se han documentado modelos con código malicioso "
     "en repositorios públicos (Zhao et al., 2024), lo que obliga a revisar los archivos de pesos antes de cargarlos.")
para("Este manuscrito es resultado de la materia de Inteligencia Artificial (cuarto semestre, primer parcial) de la carrera de "
     "[[carrera por definir]], a nivel de licenciatura, en la Universidad Católica Boliviana “San Pablo”. El objetivo fue "
     "verificar, con ejecución propia, un detector de baches YOLO11n ya entrenado y publicado por un tercero (Bisman-Singh-Dev, "
     "2026): comprobar la integridad de sus pesos, reproducir sus métricas, medir la fuga de datos entre entrenamiento y "
     "prueba, elegir con datos un umbral de confianza y medir su velocidad en un equipo sin GPU. No se entrenó ningún modelo.")

# ================================================================== METODOLOGÍA
heading("Metodología")
para("Se realizó un estudio cuantitativo de replicación: sobre un modelo y un conjunto de datos de un tercero se ejecutaron las "
     "evaluaciones que el autor declara y otras adicionales, y se compararon las cifras. El código y las salidas están en el "
     "repositorio del proyecto [[enlace por definir]].")
para(f"El modelo es un YOLO11n de una clase (*pothole*) con 2.582.347 parámetros una vez fusionadas sus capas y 6,4 GFLOPs, "
     "guardado en un archivo de 5.467.546 bytes cuyo SHA-256 es f3490f95…c7751c. El *checkpoint* registra ultralytics 8.4.108 "
     "y un entrenamiento de 15 épocas a 640 píxeles que partió de pesos anteriores del propio autor y no de COCO. "
     f"El conjunto de datos, del mismo repositorio (commit bd8238b), tiene {miles(tot_img)} imágenes y "
     f"{miles(tot_box)} cajas de una sola clase: {miles(DS['train']['imagenes'])} imágenes de entrenamiento "
     f"({miles(DS['train']['cajas'])} cajas), {DS['val']['imagenes']} de validación ({DS['val']['cajas']}) y "
     f"{DS['test']['imagenes']} de prueba ({DS['test']['cajas']}). Se comprobó que no hay líneas de etiqueta malformadas, "
     "cajas fuera de rango, imágenes sin etiqueta ni etiquetas sin imagen. Solo "
     f"{sum(DS[k]['etiquetas_vacias'] for k in DS)} archivos de etiqueta están vacíos (imágenes sin baches), "
     "menos del 1 % de las imágenes, de modo que casi no hay ejemplos negativos.")
para("Todo se ejecutó en un equipo con procesador Intel Core i7-1355U (10 núcleos), 7,7 GB de RAM, sin GPU NVIDIA, Windows 11, "
     "Python 3.14.7, ultralytics 8.4.171 (Jocher et al., 2023), PyTorch 2.14.1 en su versión para CPU (Paszke et al., 2019), "
     "OpenCV 5.0.0 y una webcam de 640 × 480 píxeles.")
para("**Integridad y seguridad.** Se calculó el SHA-256 de los pesos y se comparó con el del archivo auditado; después se "
     "escaneó el pickle con picklescan para listar las funciones y clases que importa. **Métricas estándar.** Con la función "
     "de validación de ultralytics (tamaño de imagen 640, lote de 16, umbral de confianza 0,001 y el resto de parámetros por "
     "defecto) se midieron precisión, recall, mAP50 y mAP50-95 en validación y prueba (Padilla et al., 2021).")
para("**Fuga de datos.** Cada imagen se redujo a 9 × 8 píxeles en escala de grises y se codificó con el hash de diferencias "
     "dHash (Krawetz, 2013), que genera 64 bits comparando píxeles adyacentes. La distancia entre dos imágenes es la "
     "distancia de Hamming entre sus hashes (ecuación 1). Para cada imagen de validación y de prueba se halló la distancia a "
     "su vecino más cercano en entrenamiento y se consideró casi-duplicado una distancia menor o igual que 8. También se "
     "buscaron duplicados exactos comparando el SHA-256 del contenido de cada archivo. Luego se evaluó por separado el "
     "subconjunto de prueba sin casi-duplicados (“limpio”) y el que sí los tiene (“contaminado”).")
ecuacion(
    f'{mt("d")}<m:d><m:e>{ssub("h", "1")}{mt(",")}{ssub("h", "2")}</m:e></m:d>{mt("=")}'
    f'<m:nary><m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/></m:naryPr><m:sub>{mt("i=1", True)}</m:sub>'
    f'<m:sup>{mt("64", True)}</m:sup><m:e>{ssub("h", "1,i")}{mt("⊕")}{ssub("h", "2,i")}</m:e></m:nary>', 1)
para("**Umbral de confianza.** Se predijo sobre la prueba con confianza mínima de 0,10 y se calcularon la precisión, el recall y "
     "la F1 en cada umbral entre 0,10 y 0,65. Una caja predicha cuenta como acierto (TP) si su intersección sobre unión (IoU, "
     "ecuación 2) con una caja real aún no emparejada es al menos 0,5, con emparejamiento voraz por confianza descendente; "
     "si no, es un falso positivo (FP), y una caja real sin emparejar es un falso negativo (FN). Con esos conteos se "
     "calcularon las ecuaciones 3 a 5.")
ecuacion(f'{mt("IoU", True)}{mt("=")}{frac(mt("|A∩B|", True), mt("|A∪B|", True))}', 2)
ecuacion(f'{mt("P")}{mt("=")}{frac(mt("TP", True), mt("TP+FP", True))}', 3)
ecuacion(f'{mt("R")}{mt("=")}{frac(mt("TP", True), mt("TP+FN", True))}', 4)
ecuacion(f'{mt("F1", True)}{mt("=")}{frac(mt("2PR", True), mt("P+R", True))}', 5)
para("**Velocidad y demostración.** Se registró el tiempo de inferencia por imagen durante la validación y los cuadros por "
     "segundo con la webcam: primero sin ventana (60 cuadros, captura más inferencia) y luego con la ventana de demostración "
     "abierta (922 cuadros, umbral inicial 0,35). Las pruebas con cámara las hizo el propio autor, apuntando la webcam a "
     "su rostro y a una escena de escritorio sin baches, sin conservar imágenes. Además se probó el modo de imagen con "
     "dos imágenes de prueba.")

# ================================================================== RESULTADOS
heading("Resultados")
sub("Integridad y seguridad de los pesos")
para("El SHA-256 del archivo de pesos coincide con el del archivo auditado. El escaneo con picklescan examinó un archivo "
     "(data.pkl, dentro del contenedor zip del *checkpoint*) y no marcó archivos infectados ni funciones peligrosas. De las 29 "
     "funciones o clases que importa el pickle, marcó 24 como sospechosas (clases de torch y de ultralytics como Conv2d, "
     "BatchNorm2d, SiLU, DetectionModel, C3k2, SPPF o C2PSA, y la función set de __builtin__, que no están en su lista "
     "blanca) y 5 como inocuas (almacenamientos de tensores, la reconstrucción de tensores y OrderedDict). Esa etiqueta de "
     "“sospechosa” no implica peligro; la revisión es heurística y descarta los patrones conocidos de ejecución de código, "
     "pero no demuestra que el archivo sea inocuo.")

sub("Reproducción de las métricas")
dv = {k: mv[k] - ck[k] for k in ("precision", "recall", "map50", "map50_95")}
dt = {k: mt_[k] - README_TEST[k] for k in README_TEST}
para(f"En validación, las cifras medidas coinciden con las que el autor dejó guardadas en el *checkpoint*, con diferencias "
     f"de {n(max(abs(v) for v in dv.values()), 3)} como máximo (tabla 1). El *checkpoint* no trae métricas de "
     "prueba, pero el README del autor, en el mismo commit, declara para la partición de prueba una precisión de 79,68 %, "
     "un recall de 60,00 %, un mAP50 de 71,10 % y un mAP50-95 de 39,37 %, y las cifras medidas aquí coinciden con esas hasta "
     f"la tercera cifra decimal (diferencia máxima {n(max(abs(v) for v in dt.values()), 4)}). Por tanto, las métricas "
     "declaradas se reproducen en un equipo distinto, con otra versión de ultralytics y sin GPU.")
caption_tabla("Métricas declaradas y métricas medidas")
filas = [
    ["Validación, declarada (checkpoint)", n(ck["precision"]), n(ck["recall"]), n(ck["map50"]), n(ck["map50_95"])],
    ["Validación, medida", n(mv["precision"]), n(mv["recall"]), n(mv["map50"]), n(mv["map50_95"])],
    ["Prueba, declarada (README)", n(README_TEST["precision"]), n(README_TEST["recall"]), n(README_TEST["map50"]), n(README_TEST["map50_95"])],
    ["Prueba, medida", n(mt_["precision"]), n(mt_["recall"]), n(mt_["map50"]), n(mt_["map50_95"])],
]
tabla(["Conjunto", "Precisión", "Recall", "mAP50", "mAP50-95"], filas, [3360, 1500, 1500, 1500, 1500],
      "Umbral de confianza 0,001, tamaño de imagen 640. Las cifras del README se convirtieron de porcentaje a proporción.")

sub("Fuga de datos entre entrenamiento y prueba")
para(f"La distancia dHash al vecino más cercano de entrenamiento tiene dos grupos bien separados (figura 1): una masa "
     f"pequeña de imágenes con distancia entre 0 y 8, y el resto con distancias que se concentran entre 12 y 21, con una mediana de "
     f"{int(d_test['mediana'])}. Con el umbral de 8, {pct(d_val['d_le8'])} de la validación y {pct(d_test['d_le8'])} de la "
     f"prueba tienen un casi-duplicado en entrenamiento, y {pct(d_test['d0'])} de la prueba tiene una distancia de 0, es "
     f"decir, una imagen visualmente idéntica (tabla 2). Dentro del propio entrenamiento la proporción es mayor "
     f"({pct(d_tr['d_le8'])} con distancia menor o igual que 8 en una muestra de {d_tr['n']} imágenes), lo que indica que el "
     f"conjunto contiene versiones repetidas o derivadas de las mismas fotos. Además hay {dup['grupos']} grupos de archivos con "
     f"contenido idéntico: {dup['copias_dentro_de_un_split']} copias sobrantes dentro de una misma partición y "
     f"{dup['grupos_que_cruzan_splits']} grupos que cruzan entrenamiento y prueba.")
caption_tabla("Distancia al vecino más cercano en el conjunto de entrenamiento")
tabla(["Conjunto", "n", "d = 0", "d ≤ 4", "d ≤ 8", "Mediana de d"],
      [["Validación", d_val["n"], pct(d_val["d0"]), pct(d_val["d_le4"]), pct(d_val["d_le8"]), int(d_val["mediana"])],
       ["Prueba", d_test["n"], pct(d_test["d0"]), pct(d_test["d_le4"]), pct(d_test["d_le8"]), int(d_test["mediana"])],
       ["Entrenamiento (muestra, sin sí misma)", d_tr["n"], "-", pct(d_tr["d_le4"]), pct(d_tr["d_le8"]), int(d_tr["mediana"])]],
      [3000, 900, 1200, 1200, 1200, 1860],
      "d es la distancia de Hamming entre hashes dHash de 64 bits (ecuación 1). El guion indica que no se calculó.")
figura("fig1_fuga.png", "Distribución de la distancia al vecino más cercano de entrenamiento",
       "Elaboración propia con 720 imágenes de validación y 718 de prueba; la línea discontinua marca el umbral de 8.")
sub("Prueba limpia frente a prueba contaminada")
para(f"De las {TL['completo']['imagenes']} imágenes de prueba, {n_lim} no tienen casi-duplicado en entrenamiento (prueba "
     f"limpia) y {n_con} sí lo tienen (prueba contaminada). Si la fuga inflara el desempeño, la prueba limpia debería "
     f"quedar claramente por debajo de la completa; ocurre lo contrario (tabla 3): el mAP50 de la limpia es "
     f"{n(TL['limpio']['map50'])} frente a {n(TL['completo']['map50'])} de la completa, y el de la contaminada, "
     f"{n(TL['contaminado']['map50'])}, es el más bajo. La contaminada tiene solo {n_con} imágenes, por lo que su cifra es "
     "ruidosa y no debe interpretarse como un efecto real.")
caption_tabla("Desempeño en la prueba completa, limpia y contaminada")
tabla(["Subconjunto de prueba", "Imágenes", "Precisión", "Recall", "mAP50", "mAP50-95"],
      [[nm, TL[k]["imagenes"], n(TL[k]["precision"]), n(TL[k]["recall"]), n(TL[k]["map50"]), n(TL[k]["map50_95"])]
       for nm, k in (("Completa", "completo"), ("Limpia (d > 8)", "limpio"), ("Contaminada (d ≤ 8)", "contaminado"))],
      [2760, 1200, 1350, 1350, 1350, 1350], "Mismo modelo, sin reentrenar; d es la distancia dHash a entrenamiento.")

sub("Umbral de confianza")
r35, r50, r25 = um["0.35"], um["0.50"], um["0.25"]
para(f"La precisión sube y el recall baja al aumentar el umbral (tabla 4 y figura 2). La F1 es máxima ({n(mejor['f1'])}) "
     f"con un umbral de {n(float(mejor_u), 2)}, donde la precisión es {n(r35['precision'])} y el recall {n(r35['recall'])}. "
     f"Con 0,50 hay menos falsas alarmas ({r50['FP']} contra {r35['FP']}), pero se pierden más baches reales ({r50['FN']} "
     f"contra {r35['FN']}). El valor de 0,35 que usa la demostración por defecto coincide con el mejor compromiso medido.")
caption_tabla("Precisión, recall y F1 por umbral de confianza en la prueba")
tabla(["Umbral", "TP", "FP", "FN", "Precisión", "Recall", "F1"],
      [[k.replace(".", ","), v["TP"], v["FP"], v["FN"], n(v["precision"]), n(v["recall"]), n(v["f1"])] for k, v in um.items()],
      [1260, 1100, 1100, 1100, 1600, 1600, 1600],
      f"{UM['imagenes']} imágenes y {UM['cajas_reales']} cajas reales; un acierto exige IoU ≥ 0,5.",
      alinear_primera="center")
figura("fig2_umbrales.png", "Precisión, recall y F1 según el umbral de confianza",
       "Elaboración propia a partir de la prueba (718 imágenes).")

sub("Velocidad y demostración con cámara")
para(f"En CPU, el tiempo de inferencia fue de {n(mv['ms_por_imagen']['inference'], 1)} ms por imagen en validación y "
     f"{n(mt_['ms_por_imagen']['inference'], 1)} ms en prueba. Con la webcam, la captura más la inferencia, sin "
     "ventana, dio 17,8 cuadros por segundo (53,6 ms de inferencia por cuadro), y con la ventana de demostración abierta el "
     "promedio fue de 17,4 cuadros por segundo en 922 cuadros. El README del autor declara 5,21 ms por imagen en una GPU "
     "NVIDIA RTX 4050; es otro hardware y no se compara con las cifras de CPU.")
para("En las pruebas cualitativas, una escena de escritorio sin baches no produjo ninguna detección en 60 cuadros con los "
     "umbrales de 0,25, 0,35 y 0,50. En cambio, durante la sesión de demostración el propio autor observó que, con la "
     "webcam apuntando a su rostro, en una posición muy concreta el modelo marcaba el rostro como un bache; no se registró "
     "con qué umbral ni con qué frecuencia. Con dos imágenes de prueba, una se detectó con confianza 0,75 en los tres "
     "umbrales y otra se detectó con confianza 0,32 solo en el umbral de 0,25.")

# ================================================================== DISCUSIÓN
heading("Discusión")
para("Las cifras que declara el autor se reproducen con una diferencia de milésimas, en un equipo y con versiones distintas de las "
     "que él usó. Esa reproducibilidad no equivale a validez externa: validación y prueba salen del mismo conjunto de datos que "
     "entrenamiento, y este contiene repeticiones, por lo que las métricas describen qué tan bien se comporta el modelo en "
     "imágenes parecidas a las que vio, no en cualquier calle.")
para(f"La fuga medida es mayor que la que Barz y Denzler (2020) hallaron en CIFAR-10 ({pct(d_test['d_le8'])} frente a 3,3 %), "
     "pero no inflaría el mAP: la prueba limpia rinde igual o ligeramente mejor. Pudo deberse a que la muestra contaminada es "
     "pequeña y ruidosa o a que el modelo no memoriza las repeticiones lo bastante como para mejorar en ellas; con estos "
     "datos no puede distinguirse. Además, el hash perceptual solo detecta copias casi idénticas y no el parecido entre "
     "escenas de una misma fuente, así que la medida es un piso de la contaminación y no un techo.")
para("El umbral de 0,35 maximiza la F1, pero la elección depende del uso: para alertar a un conductor puede preferirse un umbral "
     "alto que reduzca las falsas alarmas, aceptando perder cerca de la mitad de los baches, y para un inventario de pavimento "
     "revisado por una persona conviene un umbral bajo con mayor recall. El rostro marcado como bache es un contraejemplo "
     "anecdótico, coherente con un conjunto de una sola clase y casi sin ejemplos negativos: sin ejemplos de lo que no es un "
     "bache, el modelo pudo no aprender a rechazar objetos fuera de su dominio. Esto es una hipótesis, no una medición.")
para("La procedencia del conjunto de datos sigue sin documentarse: el repositorio lo describe como una mezcla de datos sintéticos "
     "y reales sin indicar fuente ni licencia, justo lo que una hoja de datos (Gebru et al., 2021) debería contener; por eso este "
     "trabajo no redistribuye imágenes del conjunto. La revisión con picklescan no halló patrones maliciosos, pero es heurística "
     "(Zhao et al., 2024). Las cifras no son comparables con las de trabajos sobre RDD2022 o HRP4K, que usan otros datos y, en "
     "RDD2022, varias clases de daño. Las limitaciones son un solo modelo de un solo autor, un solo equipo sin GPU, el "
     "entrenamiento no reproducido, la ausencia de una prueba externa a las fuentes del conjunto y una observación del rostro "
     "basada en una sesión corta y sin registro del umbral.")

# ================================================================== CONCLUSIONES
heading("Conclusiones")
para(f"El detector YOLO11n verificado cumple lo que declara su autor en las métricas: en validación y prueba se obtuvo un mAP50 de "
     f"{n(mv['map50'])} y {n(mt_['map50'])}, con diferencias de milésimas respecto de las cifras publicadas. La fuga de datos "
     f"entre entrenamiento y prueba existe ({pct(d_test['d_le8'])} de la prueba), pero no inflaría el mAP de forma apreciable. El mejor "
     f"compromiso entre precisión y recall en la prueba se logra con un umbral de confianza de {n(float(mejor_u), 2)}, y el "
     "modelo corre a unos 17 cuadros por segundo con una webcam en un equipo sin GPU.")
para("Quedan fuera de lo verificado la procedencia y la licencia de las imágenes, el comportamiento con cámaras y escenas distintas "
     "de las del conjunto de datos, la frecuencia de falsos positivos como el del rostro y el entrenamiento del modelo. "
     "Un siguiente paso es evaluarlo con un conjunto externo etiquetado de la misma forma.")

# ================================================================== REFERENCIAS
heading("Referencias")
REFS = [
    [("Arya, D., Maeda, H., Ghosh, S. K., Toshniwal, D., & Sekimoto, Y. (2022). RDD2022: A multi-national image dataset for automatic road damage detection. ", False), ("arXiv", True), (". https://doi.org/10.48550/arXiv.2209.08538", False)],
    [("Barz, B., & Denzler, J. (2020). Do we train on test data? Purging CIFAR of near-duplicates. ", False), ("Journal of Imaging, 6", True), ("(6), 41. https://doi.org/10.3390/jimaging6060041", False)],
    [("Bisman-Singh-Dev. (2026). ", False), ("YOLO-Pothole-Detection-Model", True), (" [Software, commit bd8238b]. GitHub. https://github.com/Bisman-Singh-Dev/YOLO-Pothole-Detection-Model", False)],
    [("Chen, H., Tu, Z., Zhao, Y., & Ye, J. (2026). A high-resolution perspective-view road image dataset for pothole detection. ", False), ("Scientific Data, 13", True), (", Artículo 961. https://doi.org/10.1038/s41597-026-07317-w", False)],
    [("Gebru, T., Morgenstern, J., Vecchione, B., Vaughan, J. W., Wallach, H., Daumé III, H., & Crawford, K. (2021). Datasheets for datasets. ", False), ("Communications of the ACM, 64", True), ("(12), 86-92. https://doi.org/10.1145/3458723", False)],
    [("Jocher, G., Qiu, J., & Chaurasia, A. (2023). ", False), ("Ultralytics YOLO", True), (" (Versión 8.0.0) [Software]. Ultralytics. https://github.com/ultralytics/ultralytics", False)],
    [("Khanam, R., & Hussain, M. (2024). YOLOv11: An overview of the key architectural enhancements. ", False), ("arXiv", True), (". https://doi.org/10.48550/arXiv.2410.17725", False)],
    [("Krawetz, N. (2013, 21 de enero). Kind of like that. ", False), ("The Hacker Factor Blog", True), (". https://www.hackerfactor.com/blog/index.php?/archives/529-Kind-of-Like-That.html", False)],
    [("Ma, N., Fan, J., Wang, W., Wu, J., Jiang, Y., Xie, L., & Fan, R. (2022). Computer vision for road imaging and pothole detection: A state-of-the-art review of systems and algorithms. ", False), ("Transportation Safety and Environment, 4", True), ("(4), Artículo tdac026. https://doi.org/10.1093/tse/tdac026", False)],
    [("Padilla, R., Passos, W. L., Dias, T. L. B., Netto, S. L., & da Silva, E. A. B. (2021). A comparative analysis of object detection metrics with a companion open-source toolkit. ", False), ("Electronics, 10", True), ("(3), 279. https://doi.org/10.3390/electronics10030279", False)],
    [("Paszke, A., Gross, S., Massa, F., Lerer, A., Bradbury, J., Chanan, G., Killeen, T., Lin, Z., Gimelshein, N., Antiga, L., Desmaison, A., Köpf, A., Yang, E., DeVito, Z., Raison, M., Tejani, A., Chilamkurthy, S., Steiner, B., Fang, L., … Chintala, S. (2019). PyTorch: An imperative style, high-performance deep learning library. ", False), ("arXiv", True), (". https://doi.org/10.48550/arXiv.1912.01703", False)],
    [("Redmon, J., Divvala, S., Girshick, R., & Farhadi, A. (2015). You only look once: Unified, real-time object detection. ", False), ("arXiv", True), (". https://doi.org/10.48550/arXiv.1506.02640", False)],
    [("Sahoo, R. R., Mohanty, S. S., & Mishra, S. (2025). iWatchRoad: Scalable detection and geospatial visualization of potholes for smart cities. ", False), ("arXiv", True), (". https://doi.org/10.48550/arXiv.2508.10945", False)],
    [("Zhao, J., Wang, S., Zhao, Y., Hou, X., Wang, K., Gao, P., Zhang, Y., Wei, C., & Wang, H. (2024). Models are codes: Towards measuring malicious code poisoning attacks on pre-trained model hubs. ", False), ("arXiv", True), (". https://doi.org/10.48550/arXiv.2409.09368", False)],
]
for ref in sorted(REFS, key=lambda r: r[0][0].lower()):
    referencia(ref)

# ================================================================== CIERRE
heading("Sobre el autor")
para("Leonardo Duran Cuenca es estudiante de [[carrera por definir]] en la Universidad Católica Boliviana “San Pablo” y cursa "
     "el cuarto semestre. Este manuscrito es su trabajo del primer parcial de la materia de Inteligencia Artificial. "
     "[[Completar con formación y experiencia en investigación, si corresponde.]]")
heading("Financiamiento de la investigación")
para("Con recursos propios.")
heading("Declaración de intereses")
para("Declara no tener ningún conflicto de intereses, que puedan haber influido en los resultados obtenidos o las interpretaciones propuestas.")
heading("Declaración de consentimiento informado")
para("El estudio se realizó respetando el Código de ética y buenas prácticas editoriales de publicación. No participaron terceros: "
     "las pruebas con cámara se hicieron solo con el rostro del autor y no se conservaron imágenes de la cámara.")
heading("Derechos de uso")
para("Copyright© 2026 por Leonardo Duran Cuenca. Este texto está protegido por la Licencia Creative Commons Atribución 4.0 Internacional.")
para("Usted es libre para compartir, copiar y redistribuir el material en cualquier medio o formato y adaptar el documento, remezclar, "
     "transformar y crear a partir del material para cualquier propósito, incluso comercialmente, siempre que cumpla la condición de "
     "atribución: usted debe reconocer el crédito de una obra de manera adecuada, proporcionar un enlace a la licencia, e indicar si se "
     "han realizado cambios. Puede hacerlo en cualquier forma razonable, pero no de forma tal que sugiera que tiene el apoyo del "
     "licenciante o lo recibe por el uso que hace.")

doc.save(str(OUT))
print("Escrito", OUT, "| tablas:", tab_n, "| figuras:", fig_n)
