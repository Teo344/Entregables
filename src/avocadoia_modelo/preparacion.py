"""Redimensionado único a 224 × 224 y caché .npz por partición (research M5; data-model.md §3). Sin TF.

Reutiliza avocadoia_datos.preprocesamiento.cargar_224 (EXIF → RGB → LANCZOS, estirar sin recorte): el mismo
criterio de 001/002 y el que debe replicar la app (contracts/modelo-tflite.md).
"""

import hashlib
import os

import numpy as np

from avocadoia_datos.es_csv import escribir_json, leer_csv, leer_json
from avocadoia_datos.preprocesamiento import cargar_224

from avocadoia_modelo import CLASES, PARTICIONES

METODO = "LANCZOS-estirar"


def huella_cache(huella_manifiesto, tamano=224, metodo=METODO):
    return hashlib.sha256(f"{huella_manifiesto}|tamano={tamano}|metodo={metodo}".encode()).hexdigest()


def directorio(salida, huella):
    return os.path.join(salida, "cache", huella)


def _completa(ruta, huella):
    meta = os.path.join(ruta, "meta.json")
    if not os.path.exists(meta) or leer_json(meta).get("huella_cache") != huella:
        return False
    return all(os.path.exists(os.path.join(ruta, f"{p}.npz")) for p in PARTICIONES)


def preparar(filas, raiz, salida, huella_manifiesto, tamano=224, forzar=False, progreso=None):
    """filas: manifiesto normalizado (dicts con ruta, clase, particion, sha256, fuente)."""
    huella = huella_cache(huella_manifiesto, tamano)
    ruta = directorio(salida, huella)
    if not forzar and _completa(ruta, huella):
        return {"huella_cache": huella, "ruta": ruta, "reutilizada": True, **leer_json(os.path.join(ruta, "meta.json"))}
    os.makedirs(ruta, exist_ok=True)
    conteos = {}
    for p in PARTICIONES:
        sel = sorted((f for f in filas if f["particion"] == p), key=lambda f: f["sha256"] or f["ruta"])
        x = np.zeros((len(sel), tamano, tamano, 3), dtype=np.uint8)
        for i, f in enumerate(sel):
            x[i] = np.asarray(cargar_224(os.path.join(raiz, f["ruta"]), tamano), dtype=np.uint8)
            if progreso:
                progreso(p, i + 1, len(sel))
        y = np.array([CLASES.index(f["clase"]) for f in sel], dtype=np.int8)
        np.savez(os.path.join(ruta, f"{p}.npz"), x=x, y=y,
                 sha256=np.array([f["sha256"] for f in sel], dtype=str),
                 fuente=np.array([f.get("fuente", "") for f in sel], dtype=str))
        conteos[p] = {c: int((y == i).sum()) for i, c in enumerate(CLASES)}
    meta = {"huella_cache": huella, "huella_manifiesto": huella_manifiesto, "tamano": tamano, "metodo": METODO,
            "conteos": conteos}
    escribir_json(os.path.join(ruta, "meta.json"), meta)
    return {"ruta": ruta, "reutilizada": False, **meta}


def preparar_desde_verificacion(verificacion, raiz, salida, forzar=False, progreso=None):
    if verificacion.get("estado") == "fallida":
        raise ValueError("la verificación está fallida: corrija los datos y vuelva a ejecutar `verificar`")
    ruta = verificacion.get("ruta_manifiesto_normalizado", "")
    if not os.path.exists(ruta):  # verificado en otro entorno (p. ej. G:/ en la PC): misma carpeta de Drive
        ruta = os.path.join(salida, "manifiestos", f"{verificacion['huella_manifiesto'][:8]}.csv")
    filas = leer_csv(ruta)
    if not filas:
        raise ValueError(f"no se encontró el manifiesto normalizado ({ruta}): ejecute `verificar`")
    return preparar(filas, raiz, salida, verificacion["huella_manifiesto"], forzar=forzar, progreso=progreso)


def cargar(ruta_cache, particion):
    """Arrays de una partición. Entrenamiento solo debe pedir 'train' y 'val' (FR-005)."""
    if particion not in PARTICIONES:
        raise ValueError(particion)
    with np.load(os.path.join(ruta_cache, f"{particion}.npz"), allow_pickle=False) as d:
        return {k: d[k] for k in d.files}
