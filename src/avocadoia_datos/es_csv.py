"""Lectura y escritura deterministas de CSV y JSON (UTF-8 sin BOM, fin de línea LF)."""

import csv
import hashlib
import json
import os


def leer_csv(ruta):
    if not os.path.exists(ruta):
        return []
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def escribir_csv(ruta, campos, filas):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="") as fh:
        escritor = csv.DictWriter(fh, fieldnames=campos, lineterminator="\n", extrasaction="ignore")
        escritor.writeheader()
        for fila in filas:
            escritor.writerow({c: "" if fila.get(c) is None else fila.get(c) for c in campos})


def agregar_csv(ruta, campos, filas):
    """Añade filas al final; crea el archivo con encabezado si no existe."""
    nuevo = not os.path.exists(ruta)
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "a", encoding="utf-8", newline="") as fh:
        escritor = csv.DictWriter(fh, fieldnames=campos, lineterminator="\n", extrasaction="ignore")
        if nuevo:
            escritor.writeheader()
        escritor.writerows(filas)


def escribir_json(ruta, datos):
    os.makedirs(os.path.dirname(ruta) or ".", exist_ok=True)
    with open(ruta, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(datos, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def leer_json(ruta):
    with open(ruta, encoding="utf-8") as fh:
        return json.load(fh)


def sha256_bytes(datos):
    return hashlib.sha256(datos).hexdigest()


def sha256_archivo(ruta):
    h = hashlib.sha256()
    with open(ruta, "rb") as fh:
        for bloque in iter(lambda: fh.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()
