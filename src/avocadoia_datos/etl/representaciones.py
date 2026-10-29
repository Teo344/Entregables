"""Representaciones EfficientNet-B0 de las imágenes candidatas (spec 002, research E2).

Es el único módulo que importa TensorFlow. Vectores de 1 280 valores normalizados (L2), con y sin
el 60 % central tapado (sonda de fondo), en caché con huella.
"""

import hashlib
import os

from avocadoia_datos.config import ErrorDependencia, ErrorPrecondicion
from avocadoia_datos.es_csv import sha256_archivo

TAMANO = 224
GRIS = 128
FRACCION_CENTRO = 0.60
LOTE = 32
ARCHIVO_PESOS = "efficientnetb0_notop.h5"


def ruta_cache(salida):
    return os.path.join(salida, "eda", "cache", "representaciones.npz")


def _preparar_entorno():
    os.environ.setdefault("TF_DETERMINISTIC_OPS", "1")
    os.environ.setdefault("TF_ENABLE_ONEDNN_OPTS", "0")
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
    try:
        import keras
        import tensorflow as tf
    except ImportError as e:
        raise ErrorDependencia("Este subcomando requiere el entorno .venv-ml (TensorFlow)") from e
    keras.utils.set_random_seed(42)
    return tf, keras


def _ruta_pesos():
    return os.path.join(os.path.expanduser(os.environ.get("KERAS_HOME", "~/.keras")), "models", ARCHIVO_PESOS)


def _modelo(keras):
    if os.environ.get("AVOCADOIA_SIN_RED") == "1" and not os.path.exists(_ruta_pesos()):
        raise ErrorPrecondicion(f"AVOCADOIA_SIN_RED=1 y los pesos no están en caché ({_ruta_pesos()})")
    return keras.applications.EfficientNetB0(include_top=False, weights="imagenet", pooling="avg",
                                             input_shape=(TAMANO, TAMANO, 3))


def tapar_centro(lote, fraccion=FRACCION_CENTRO, valor=GRIS):
    """Copia del lote (N × H × W × 3) con el cuadrado central de lado `fraccion` tapado."""
    salida = lote.copy()
    h, w = lote.shape[1:3]
    y0, x0 = round(h * (1 - fraccion) / 2), round(w * (1 - fraccion) / 2)
    salida[:, y0:h - y0, x0:w - x0, :] = valor
    return salida


def huella(sha_pesos, version_tf, pares):
    texto = "\n".join([sha_pesos, version_tf, *(f"{i}:{s}" for i, s in sorted(pares))])
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def cargar_cache(salida):
    """{'ids', 'sha256', 'vectores', 'vectores_borde', 'huella', ...} o None si no hay caché."""
    import numpy as np
    ruta = ruta_cache(salida)
    if not os.path.exists(ruta):
        return None
    with np.load(ruta, allow_pickle=False) as datos:
        return {k: datos[k] for k in datos.files}


def calcular(manifiesto, raiz_imagenes, salida, forzar=False):
    """Calcula (o completa) la caché para todas las candidatas; devuelve un resumen."""
    tf, keras = _preparar_entorno()
    import numpy as np

    from avocadoia_datos.preprocesamiento import cargar_224

    from avocadoia_datos.etl.sospechas import poblacion
    filas = sorted(poblacion(manifiesto), key=lambda f: f["id_contenido"])
    previa = None if forzar else cargar_cache(salida)
    conocidas = {}
    if previa is not None:
        for n, (i, s) in enumerate(zip(previa["ids"], previa["sha256"])):
            conocidas[(str(i), str(s))] = n
    faltan = [f for f in filas if (f["id_contenido"], f["sha256"]) not in conocidas]

    nuevas_v, nuevas_b = np.zeros((0, 1280), np.float32), np.zeros((0, 1280), np.float32)
    if faltan:
        modelo = _modelo(keras)
        partes_v, partes_b = [], []
        for inicio in range(0, len(faltan), LOTE):
            lote = np.stack([np.asarray(cargar_224(os.path.join(raiz_imagenes, f["ruta"]), TAMANO), np.float32)
                             for f in faltan[inicio:inicio + LOTE]])
            partes_v.append(modelo(lote, training=False).numpy())
            partes_b.append(modelo(tapar_centro(lote), training=False).numpy())
        # Solo se normalizan los vectores nuevos: renormalizar los de la caché cambia cifras del
        # orden de 1e-8 que t-SNE amplifica (SC-006).
        nuevas_v, nuevas_b = _normalizar(np.concatenate(partes_v)), _normalizar(np.concatenate(partes_b))

    nuevas = {(f["id_contenido"], f["sha256"]): n for n, f in enumerate(faltan)}
    vectores, bordes = [], []
    for f in filas:
        clave = (f["id_contenido"], f["sha256"])
        if clave in nuevas:
            vectores.append(nuevas_v[nuevas[clave]])
            bordes.append(nuevas_b[nuevas[clave]])
        else:
            vectores.append(previa["vectores"][conocidas[clave]])
            bordes.append(previa["vectores_borde"][conocidas[clave]])
    vectores, bordes = np.array(vectores, np.float32), np.array(bordes, np.float32)

    sha_pesos = sha256_archivo(_ruta_pesos()) if os.path.exists(_ruta_pesos()) else str(previa["sha_pesos"])
    pares = [(f["id_contenido"], f["sha256"]) for f in filas]
    datos = {"ids": np.array([f["id_contenido"] for f in filas]), "sha256": np.array([f["sha256"] for f in filas]),
             "vectores": vectores, "vectores_borde": bordes, "sha_pesos": np.array(sha_pesos),
             "version_tf": np.array(tf.__version__), "huella": np.array(huella(sha_pesos, tf.__version__, pares))}
    os.makedirs(os.path.dirname(ruta_cache(salida)), exist_ok=True)
    np.savez_compressed(ruta_cache(salida), **datos)
    return {"imagenes": len(filas), "calculadas": len(faltan), "reutilizadas": len(filas) - len(faltan),
            "huella": str(datos["huella"]), "version_tf": tf.__version__}


def _normalizar(m):
    import numpy as np
    return (m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-12)).astype(np.float32)
