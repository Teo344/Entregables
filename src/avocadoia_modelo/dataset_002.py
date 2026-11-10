"""Adaptador del dataset de la especificación 002 al formato de manifiesto del modelo (research M20, T068).

Entrada: `datos/particion.csv` (qué imagen va a cada partición) y `datos/manifiesto.csv` (SHA-256 del original,
grupo y validación). Las imágenes ya procesadas a 224 × 224 están en `Modelo/PROCESADO/<particion>/<clase>/<id>.jpg`.
El manifiesto resultante usa las columnas de M2; el `sha256` es el del ORIGINAL, para que la licencia (M19), los
duplicados y la fuga se comprueben con las mismas reglas que con cualquier otro manifiesto.
"""

import os

from avocadoia_datos import config as config_002
from avocadoia_datos.es_csv import escribir_csv, escribir_json, leer_csv, sha256_archivo
from avocadoia_datos.preprocesamiento import huella_configuracion

COLUMNAS = ("ruta_destino", "clase_original", "conjunto", "sha256", "estado_etiqueta", "grupo_duplicacion_escena",
            "ruta_origen", "fuente", "id_contenido")


# Decisiones del experto en 002 (avocadoia_datos.inventario.DECISIONES_VALIDAS) que confirman la etiqueta efectiva.
VALIDADAS = ("aceptada", "reasignada")


class ErrorDataset002(ValueError):
    pass


def generar(particion_csv, manifiesto_csv, huella_esperada=None):
    """Filas del manifiesto 002 en formato M2 y un resumen de las comprobaciones."""
    huella = sha256_archivo(particion_csv)
    if huella_esperada and huella != huella_esperada:
        raise ErrorDataset002(f"la partición cambió: huella {huella[:8]} ≠ {huella_esperada[:8]}")
    por_id = {f["id_contenido"]: f for f in leer_csv(manifiesto_csv)}
    filas, sin_manifiesto = [], []
    for p in leer_csv(particion_csv):
        if p["particion"] not in ("train", "val", "test"):
            continue  # test_campo u otras reservas no entran al manifiesto de entrenamiento
        reg = por_id.get(p["id_contenido"])
        if reg is None:
            sin_manifiesto.append(p["id_contenido"])
            continue
        filas.append({
            "ruta_destino": f"{p['particion']}/{p['clase']}/{p['id_contenido']}.jpg",
            "clase_original": p["clase"], "conjunto": p["particion"], "sha256": reg["sha256"],
            "estado_etiqueta": "ETIQUETA_VALIDADA" if reg.get("validacion") in VALIDADAS else "ETIQUETA_PROVISIONAL",
            "grupo_duplicacion_escena": p.get("grupo") or reg.get("grupo", ""), "ruta_origen": p["ruta"],
            "fuente": p["fuente"], "id_contenido": p["id_contenido"],
        })
    if sin_manifiesto:
        raise ErrorDataset002(f"{len(sin_manifiesto)} imágenes de la partición no están en el manifiesto de 002")
    return filas, {"huella_particion": huella, "total": len(filas)}


def comprobar_procesado(raiz_procesado, dataset_toml, fuentes_csv):
    """La configuración con que se generó PROCESADO/ debe ser la vigente (misma huella que 002)."""
    ruta = os.path.join(raiz_procesado, ".configuracion")
    if not os.path.exists(ruta):
        return {"huella_procesado": None, "coincide": False}
    with open(ruta, encoding="utf-8") as fh:
        guardada = fh.read().strip()
    vigente = huella_configuracion(config_002.cargar(dataset_toml, fuentes_csv).preprocesamiento)
    return {"huella_procesado": guardada, "huella_vigente": vigente, "coincide": guardada == vigente}


def escribir(filas, resumen, destino):
    os.makedirs(destino, exist_ok=True)
    ruta = os.path.join(destino, "manifiesto_002.csv")
    escribir_csv(ruta, COLUMNAS, filas)
    escribir_json(os.path.join(destino, "generacion_002.json"), resumen)
    return ruta
