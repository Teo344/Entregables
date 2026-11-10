"""Convierte fotos HEIC (iPhone) a JPG junto al original, sin modificarlo, y registra cada conversión.

Constitución, principio II: los originales se conservan intactos y toda transformación produce archivos nuevos con
registro. El inventario de la especificación 002 solo admite JPG/JPEG/PNG; los .heic quedan en su carpeta y el
inventario los ignora.

Uso:
    .venv-ml\\Scripts\\python scripts/convertir_heic.py "G:/Otros ordenadores/Mi portátil/Modelo/CAMPO_SIGCHOS/PEDUNCULO"
"""

import argparse
import datetime
import os
import sys

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

from avocadoia_datos.es_csv import escribir_csv, leer_csv, sha256_archivo

COLUMNAS = ("carpeta", "original", "sha256_original", "jpg", "sha256_jpg", "ancho", "alto", "fabricante", "modelo",
            "fecha_captura", "calidad", "fecha_conversion")
TAG_FABRICANTE, TAG_MODELO, TAG_FECHA, IFD_EXIF, TAG_FECHA_ORIGINAL = 271, 272, 306, 0x8769, 36867


def convertir(carpeta, registro, calidad=95, forzar=False):
    register_heif_opener()
    previas = {(f["carpeta"], f["original"]): f for f in leer_csv(registro)}
    nuevas = []
    for nombre in sorted(os.listdir(carpeta)):
        if not nombre.lower().endswith((".heic", ".heif")):
            continue
        origen = os.path.join(carpeta, nombre)
        destino = os.path.splitext(origen)[0] + ".jpg"
        clave = (os.path.basename(os.path.normpath(carpeta)), nombre)
        if os.path.exists(destino) and not forzar:
            if clave in previas:
                nuevas.append(previas[clave])
                continue
            print(f"  aviso: {os.path.basename(destino)} ya existe y no está registrado; use --forzar", file=sys.stderr)
            continue
        with Image.open(origen) as im:
            exif = im.getexif()
            fecha = exif.get_ifd(IFD_EXIF).get(TAG_FECHA_ORIGINAL) or exif.get(TAG_FECHA, "")
            fabricante, modelo = exif.get(TAG_FABRICANTE, ""), exif.get(TAG_MODELO, "")
            salida = ImageOps.exif_transpose(im).convert("RGB")  # orientación aplicada; la etiqueta se normaliza
            exif_salida = salida.getexif() if salida.getexif() else exif
            salida.save(destino, "JPEG", quality=calidad, exif=exif_salida.tobytes())
        nuevas.append({"carpeta": clave[0], "original": nombre, "sha256_original": sha256_archivo(origen),
                       "jpg": os.path.basename(destino), "sha256_jpg": sha256_archivo(destino),
                       "ancho": salida.width, "alto": salida.height, "fabricante": fabricante, "modelo": modelo,
                       "fecha_captura": fecha, "calidad": calidad,
                       "fecha_conversion": datetime.date.today().isoformat()})
    conservadas = [f for k, f in previas.items() if k[0] != os.path.basename(os.path.normpath(carpeta))]
    escribir_csv(registro, COLUMNAS, sorted(conservadas + nuevas, key=lambda f: (f["carpeta"], f["original"])))
    return nuevas


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("carpetas", nargs="+")
    p.add_argument("--registro", default="datos/etl/conversion_heic.csv")
    p.add_argument("--calidad", type=int, default=95)
    p.add_argument("--forzar", action="store_true")
    a = p.parse_args(argv)
    for carpeta in a.carpetas:
        filas = convertir(carpeta, a.registro, a.calidad, a.forzar)
        print(f"{carpeta}: {len(filas)} fotos convertidas/registradas en {a.registro}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
