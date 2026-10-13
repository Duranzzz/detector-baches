"""Procesa los videos grabados con el celular: dibuja las cajas de los baches y guarda un video anotado por cada uno.

  python procesar_videos.py                    # todos los videos de la carpeta videos/
  python procesar_videos.py clip1.mp4 clip2.mov  # solo esos
  python procesar_videos.py --cada 2           # 1 de cada 2 cuadros: el doble de rapido

Salida en videos/anotados/: <nombre>_anotado.mp4, <nombre>_anotado_mejor.jpg (el cuadro con la deteccion
mas confiable) y resumen.csv. Funciona sin internet; usa webcam.py con el filtro de duplicados al 50 %.
"""
import argparse
import csv
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
VIDEOS = HERE / "videos"
SALIDA = VIDEOS / "anotados"
EXT = {".mp4", ".mov", ".avi", ".mkv", ".3gp", ".m4v", ".webm"}

ap = argparse.ArgumentParser(description="Procesa videos del celular con el detector de baches")
ap.add_argument("videos", nargs="*", help="archivos de video; si no se da ninguno, se usa la carpeta videos/")
ap.add_argument("--conf", type=float, default=0.35, help="umbral de confianza")
ap.add_argument("--cada", type=int, default=1, help="procesa 1 de cada N cuadros")
args = ap.parse_args()

VIDEOS.mkdir(exist_ok=True)
SALIDA.mkdir(exist_ok=True)
lista = [Path(v) for v in args.videos] if args.videos else sorted(p for p in VIDEOS.iterdir() if p.suffix.lower() in EXT)
if not lista:
    sys.exit(f"No hay videos. Copia los del celular en {VIDEOS} o arrástralos sobre procesar_videos.bat")

filas = []
for i, v in enumerate(lista, 1):
    if not v.exists():
        print(f"[{i}/{len(lista)}] No existe: {v}")
        continue
    destino = SALIDA / (v.stem + "_anotado.mp4")
    print(f"\n[{i}/{len(lista)}] {v.name} -> {destino.name}")
    r = subprocess.run([sys.executable, str(HERE / "webcam.py"), "--source", str(v), "--no-show", "--guardar", str(destino),
                        "--conf", str(args.conf), "--cada", str(args.cada)], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    resumen = [l for l in r.stdout.splitlines() if l.startswith("RESUMEN|")]
    if r.returncode or not resumen:
        print("  [ERROR] no se pudo procesar. Si el video es HEVC/H.265 (iPhone), grábalo en formato 'Más compatible' (H.264).")
        print("  " + (r.stderr or r.stdout).strip().splitlines()[-1] if (r.stderr or r.stdout).strip() else "")
        continue
    _, nombre, n, con, mejor, seg = resumen[0].split("|")
    print(f"  {n} cuadros en {seg} s; {con} con baches; confianza maxima {mejor}")
    filas.append({"video": nombre, "cuadros_procesados": n, "cuadros_con_baches": con,
                  "porcentaje": f"{100 * int(con) / max(int(n), 1):.0f}", "confianza_maxima": mejor,
                  "segundos": seg, "salida": destino.name})

if filas:
    with open(SALIDA / "resumen.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]), delimiter=";")
        w.writeheader()
        w.writerows(filas)
    print(f"\nListo: {len(filas)} video(s) en {SALIDA} (resumen en resumen.csv)")
