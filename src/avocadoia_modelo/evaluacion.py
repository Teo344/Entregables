"""Evaluación de una corrida: logits de val y test, metricas.json, matrices y bitácora (T024).

Es la única función del flujo de entrenamiento que abre la partición de prueba, y solo para reportar.
"""

import os

import keras
import numpy as np

from avocadoia_datos.es_csv import escribir_csv, escribir_json

from avocadoia_modelo import ETIQUETAS_VISIBLES, metricas, preparacion, registro
from avocadoia_modelo.entrenamiento import dir_corrida


def logits_de(modelo, x, lote=64):
    return modelo.predict(x.astype("float32"), batch_size=lote, verbose=0)


def evaluar(cfg, id_, ruta_cache, repo_datos, salida):
    reg = registro.leer_registro(repo_datos, id_)
    dir_drive = dir_corrida(salida, id_)
    modelo = keras.models.load_model(os.path.join(dir_drive, "mejor.keras"))
    ev = cfg["evaluacion"]
    resultado, guardar = {}, {}
    dir_repo = os.path.dirname(registro.ruta_registro(repo_datos, id_))
    for p in ("val", "test"):
        d = preparacion.cargar(ruta_cache, p)
        lg = logits_de(modelo, d["x"])
        guardar.update({f"logits_{p}": lg, f"y_{p}": d["y"], f"sha256_{p}": d["sha256"], f"fuente_{p}": d["fuente"]})
        resultado[p] = metricas.resumen(d["y"], lg, d["fuente"], reg.get("experimental", True), ev["bootstrap"],
                                        ev["semilla"], ev["min_por_fuente"])
        cm = resultado[p]["matriz_confusion"]
        escribir_csv(os.path.join(dir_repo, f"matriz_confusion_{p}.csv"), ("real",) + ETIQUETAS_VISIBLES,
                     [{"real": ETIQUETAS_VISIBLES[i], **dict(zip(ETIQUETAS_VISIBLES, fila))}
                      for i, fila in enumerate(cm)])
    np.savez(os.path.join(dir_drive, "logits.npz"), **guardar)
    escribir_json(os.path.join(dir_repo, "metricas.json"), resultado)
    registro.agregar_a_bitacora(repo_datos, {
        "id": id_, "fecha": id_[:13], "arquitectura": reg["arquitectura"], "semilla": reg["semilla"],
        "huella_config": reg["huella_config"][:12], "huella_manifiesto": reg["huella_manifiesto"][:12],
        "estado": "completa", "val_macro_f1": round(resultado["val"]["macro_f1"], 4),
        "test_macro_f1": round(resultado["test"]["macro_f1"], 4),
        "test_recall_antracnosis": round(resultado["test"]["por_clase"]["antracnosis"]["recall"], 4),
        "tamano_keras_mb": reg.get("tamano_keras_mb", ""), "duracion_min": reg.get("duracion_min", ""),
        "experimental": "si" if reg.get("experimental", True) else "no"})
    return resultado
