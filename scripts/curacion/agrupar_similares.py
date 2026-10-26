"""Grupos por similitud visual (2026-10-26) → datos/curacion/grupos_similitud.csv.

El dataset de Kaggle fotografía cada fruto desde 5 a 7 lados, con números de archivo lejanos y sin
identificador de fruto: 734 fotos de antracnosis corresponden a unos 150 frutos. Para que un mismo
fruto no quede en entrenamiento y en prueba, se agrupan las imágenes casi idénticas comparando un
dHash 16 × 16 del fruto recortado, también girado 90/180/270° y volteado (distancia de Hamming
<= 10). Agrupar de más solo forma grupos mayores; agrupar de menos deja fugas.

Se aplica a las fuentes sin partición de origen ni regla de grupo propia, sobre las imágenes que no
están excluidas. El pipeline une estos grupos a los demás (ver avocadoia_datos.grupos).

Uso (desde la raíz de Entregables, después de `python -m avocadoia_datos inventario`):
    python scripts/curacion/agrupar_similares.py
"""
import csv
import os
from collections import defaultdict

from PIL import Image, ImageOps

MODELO = "Modelo"
MANIFIESTO = "datos/manifiesto.csv"
SALIDA = "datos/curacion/grupos_similitud.csv"
FUENTES = ("kaggle_antracnosis", "rgb_antracnosis", "rgb_sano", "sano_web")
UMBRAL = 10
_TRANSFORMACIONES = (Image.ROTATE_90, Image.ROTATE_180, Image.ROTATE_270, Image.FLIP_LEFT_RIGHT,
                     Image.FLIP_TOP_BOTTOM)


def fruto(ruta):
    """Escala de grises recortada al objeto (sin el fondo claro), con la orientación EXIF aplicada."""
    im = ImageOps.exif_transpose(Image.open(ruta)).convert("L")
    caja = im.point(lambda v: 255 if v < 235 else 0).getbbox()
    if caja and (caja[2] - caja[0]) * (caja[3] - caja[1]) > 0.02 * im.size[0] * im.size[1]:
        im = im.crop(caja)
    return im


def dhash(im, n=16):
    px = im.resize((n + 1, n), Image.LANCZOS).tobytes()
    bits = 0
    for r in range(n):
        for c in range(n):
            bits = (bits << 1) | (px[r * (n + 1) + c] > px[r * (n + 1) + c + 1])
    return bits


def main():
    with open(MANIFIESTO, encoding="utf-8") as fh:
        filas = [f for f in csv.DictReader(fh)
                 if f["fuente"] in FUENTES and f["canonica"] == "si" and f["estado"] in ("elegible", "provisional")]
    filas.sort(key=lambda f: f["ruta"])
    hashes = []
    for f in filas:
        im = fruto(os.path.join(MODELO, f["ruta"]))
        hashes.append([dhash(im)] + [dhash(im.transpose(t)) for t in _TRANSFORMACIONES])

    padre = list(range(len(filas)))

    def raiz(x):
        while padre[x] != x:
            padre[x] = padre[padre[x]]
            x = padre[x]
        return x

    for i in range(len(filas)):
        for j in range(i + 1, len(filas)):
            if filas[i]["fuente"] != filas[j]["fuente"]:
                continue
            if min(bin(h ^ hashes[j][0]).count("1") for h in hashes[i]) <= UMBRAL:
                a, b = sorted((raiz(i), raiz(j)))
                padre[b] = a

    grupos = defaultdict(list)
    for i, f in enumerate(filas):
        grupos[raiz(i)].append(f["ruta"])
    multiples = sorted((sorted(g) for g in grupos.values() if len(g) > 1), key=lambda g: g[0])
    with open(SALIDA, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["grupo", "ruta"])
        for k, g in enumerate(multiples, start=1):
            for ruta in g:
                w.writerow([f"S{k:04d}", ruta])
    fuente_de = {f["ruta"]: f["fuente"] for f in filas}
    print(f"{SALIDA}: {len(multiples)} grupos con {sum(map(len, multiples))} imágenes")
    for fuente in FUENTES:
        gs = [g for g in multiples if fuente_de[g[0]] == fuente]
        print(f"  {fuente}: {len(gs)} grupos, {sum(map(len, gs))} imágenes")


if __name__ == "__main__":
    main()
