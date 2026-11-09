"""Registro de corridas, bitácora e importación desde Drive (data-model.md §5–§6, research M9, M18).

Sin TensorFlow obligatorio: `versiones()` lo describe solo si ya está importado.
"""

import datetime
import os
import platform
import shutil
import sys

from avocadoia_datos.es_csv import escribir_csv, escribir_json, leer_csv, leer_json

ESTADOS = ("en_curso", "completa", "incompleta")
TRANSICIONES = {None: {"en_curso"}, "en_curso": {"completa", "incompleta"}, "incompleta": {"en_curso"},
                "completa": set()}
COLUMNAS_BITACORA = ("id", "fecha", "arquitectura", "semilla", "huella_config", "huella_manifiesto", "estado",
                     "val_macro_f1", "test_macro_f1", "test_recall_antracnosis", "tamano_keras_mb", "duracion_min",
                     "experimental")
EXTENSIONES_LIVIANAS = (".json", ".csv", ".png", ".md")


class TransicionInvalida(ValueError):
    pass


def id_corrida(fecha, arquitectura, semilla, huella_manifiesto):
    """AAAAMMDD-HHMM_<arquitectura>_s<semilla>_<huella8>."""
    return f"{fecha:%Y%m%d-%H%M}_{arquitectura}_s{int(semilla)}_{huella_manifiesto[:8]}"


def versiones():
    v = {"python": platform.python_version(), "plataforma": platform.platform(), "tensorflow": None,
         "keras": None, "numpy": None, "cuda": None, "cudnn": None, "gpu": []}
    if "numpy" in sys.modules:
        v["numpy"] = sys.modules["numpy"].__version__
    tf = sys.modules.get("tensorflow")
    if tf is not None:
        v["tensorflow"] = tf.__version__
        v["keras"] = sys.modules["keras"].__version__ if "keras" in sys.modules else None
        info = tf.sysconfig.get_build_info()
        v["cuda"], v["cudnn"] = info.get("cuda_version"), info.get("cudnn_version")
        v["gpu"] = [d.name for d in tf.config.list_physical_devices("GPU")]
    return v


def ruta_registro(repo_datos, id_):
    return os.path.join(repo_datos, "experimentos", id_, "registro.json")


def leer_registro(repo_datos, id_):
    return leer_json(ruta_registro(repo_datos, id_))


def escribir_registro(repo_datos, registro):
    escribir_json(ruta_registro(repo_datos, registro["id"]), registro)
    return registro


def actualizar_estado(repo_datos, id_, nuevo, **campos):
    ruta = ruta_registro(repo_datos, id_)
    registro = leer_json(ruta) if os.path.exists(ruta) else {"id": id_, "estado": None}
    actual = registro.get("estado")
    if nuevo not in TRANSICIONES.get(actual, set()):
        raise TransicionInvalida(f"{id_}: {actual} → {nuevo} no permitido")
    registro.update(campos, estado=nuevo,
                    **{f"fecha_{nuevo}": datetime.datetime.now().isoformat(timespec="seconds")})
    return escribir_registro(repo_datos, registro)


def agregar_a_bitacora(repo_datos, fila):
    """Inserta o reemplaza la fila del id (nunca duplica)."""
    ruta = os.path.join(repo_datos, "bitacora.csv")
    filas = [f for f in leer_csv(ruta) if f["id"] != fila["id"]]
    filas.append({c: fila.get(c, "") for c in COLUMNAS_BITACORA})
    filas.sort(key=lambda f: f["id"])
    escribir_csv(ruta, COLUMNAS_BITACORA, filas)


def importar(origen, destino):
    """Copia desde Drive solo artefactos livianos versionables (research M18); devuelve las rutas copiadas."""
    copiados = []
    for base, _, archivos in os.walk(origen):
        for nombre in archivos:
            if not nombre.lower().endswith(EXTENSIONES_LIVIANAS):
                continue
            src = os.path.join(base, nombre)
            dst = os.path.join(destino, os.path.relpath(src, origen))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(src, dst)
            copiados.append(os.path.relpath(dst, destino).replace("\\", "/"))
    return sorted(copiados)
