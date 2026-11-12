"""Entrenamiento en dos fases con BatchNorm congelada, pesos de clase y reanudación (research M7, M9; T023).

Nunca abre la partición de prueba (FR-005): solo pide 'train' y 'val' a la caché.
Reanudación: una corrida `en_curso` o `incompleta` con la misma arquitectura, semilla, huella de configuración y
huella de manifiesto se retoma con el mismo id; BackupAndRestore recupera la época dentro de cada fase y los pesos
de fin de fase 1 evitan repetirla.
"""

import datetime
import glob
import os
import time

import keras
import numpy as np
import tensorflow as tf

from avocadoia_datos.es_csv import escribir_csv, leer_csv, leer_json

from avocadoia_modelo import arquitecturas, datos_tf, figuras, metricas, preparacion, registro
from avocadoia_modelo.config import canonica, es_linea_base, huella_config

COLUMNAS_HISTORIAL = ("epoca", "fase", "loss", "val_loss", "accuracy", "val_accuracy", "learning_rate")


def dir_corrida(salida, id_):
    return os.path.join(salida, "experimentos", id_)


def _buscar_reanudable(repo_datos, arquitectura, semilla, huella_c, huella_m):
    for ruta in sorted(glob.glob(os.path.join(repo_datos, "experimentos", "*", "registro.json"))):
        r = leer_json(ruta)
        if (r.get("estado") in ("en_curso", "incompleta") and r.get("arquitectura") == arquitectura
                and r.get("semilla") == semilla and r.get("huella_config") == huella_c
                and r.get("huella_manifiesto") == huella_m):
            return r
    return None


def _semillas(semilla, deterministico):
    keras.utils.set_random_seed(semilla)
    if deterministico:
        tf.config.experimental.enable_op_determinism()


def _historial(dir_drive, fase):
    """Filas del CSVLogger de una fase, sin duplicados de época tras una reanudación (gana la última)."""
    filas = {}
    for f in leer_csv(os.path.join(dir_drive, f"historial_{fase}.csv")):
        filas[int(f["epoch"])] = f
    return [filas[e] for e in sorted(filas)]


def _callbacks(cfg, dir_drive, fase, checkpoint):
    p = cfg["parada"]
    return [
        keras.callbacks.EarlyStopping(monitor="val_loss", patience=p["paciencia"], restore_best_weights=True),
        keras.callbacks.ReduceLROnPlateau(monitor="val_loss", factor=p["factor"], patience=p["paciencia_plateau"],
                                          min_lr=p["min_lr"]),
        checkpoint,
        keras.callbacks.BackupAndRestore(os.path.join(dir_drive, f"backup_{fase}")),
        keras.callbacks.CSVLogger(os.path.join(dir_drive, f"historial_{fase}.csv"), append=True),
    ]


def _compilar(modelo, tasa):
    modelo.compile(optimizer=keras.optimizers.Adam(tasa),
                   loss=keras.losses.SparseCategoricalCrossentropy(from_logits=True),
                   metrics=[keras.metrics.SparseCategoricalAccuracy(name="accuracy")])


def _experimental(verificacion):
    return (verificacion.get("estado") != "ok" or any(verificacion.get("etiquetas_provisionales", {}).values())
            or bool(verificacion.get("fuga_por_fruto", {}).get("grupos")))


def entrenar(cfg, ruta_cache, repo_datos, salida, verificacion, pesos="imagenet", ahora=None):
    """Entrena una corrida (cfg con cfg['corrida']) y devuelve su id. El estado queda `en_curso` hasta evaluar."""
    arq, semilla = cfg["corrida"]["arquitectura"], cfg["corrida"]["semilla"]
    huella_c, huella_m = huella_config(cfg), verificacion["huella_manifiesto"]
    previo = _buscar_reanudable(repo_datos, arq, semilla, huella_c, huella_m)
    if previo:
        id_ = previo["id"]
        if previo["estado"] == "incompleta":
            registro.actualizar_estado(repo_datos, id_, "en_curso")
    else:
        id_ = registro.id_corrida(ahora or datetime.datetime.now(), arq, semilla, huella_m)
        registro.actualizar_estado(
            repo_datos, id_, "en_curso", arquitectura=arq, semilla=semilla, huella_config=huella_c,
            huella_manifiesto=huella_m, huella_cache=os.path.basename(os.path.normpath(ruta_cache)),
            configuracion=canonica(cfg), experimental=_experimental(verificacion),
            verificacion={k: verificacion.get(k) for k in ("estado", "conteos", "excluidas", "fuga_por_fruto",
                                                           "etiquetas_provisionales")})
    dir_drive = dir_corrida(salida, id_)
    os.makedirs(dir_drive, exist_ok=True)
    inicio = time.time()

    _semillas(semilla, cfg["entrenamiento"]["deterministico"])
    tr = preparacion.cargar(ruta_cache, "train")
    va = preparacion.cargar(ruta_cache, "val")
    lote = cfg["entrenamiento"]["lote"]
    ds_tr = datos_tf.dataset_entrenamiento(tr["x"], tr["y"], lote, semilla, cfg["aumento"])
    ds_va = datos_tf.dataset_evaluacion(va["x"], va["y"], lote)
    pesos_clase = metricas.pesos_clase(tr["y"])

    modelo, capas_base, capa_mapa = arquitecturas.construir(arq, cfg["modelo"]["dropout"], pesos,
                                                            cfg["entrada"]["tamano"])
    checkpoint = keras.callbacks.ModelCheckpoint(os.path.join(dir_drive, "mejor.keras"), monitor="val_loss",
                                                 save_best_only=True)
    previas = _historial(dir_drive, "fase1") + _historial(dir_drive, "fase2")
    if previas:  # al reanudar, no sobrescribir el mejor modelo con uno peor
        checkpoint.best = min(float(f["val_loss"]) for f in previas)

    reg = registro.leer_registro(repo_datos, id_)
    if es_linea_base(cfg, arq):
        return _entrenar_linea_base(cfg, id_, modelo, capas_base, capa_mapa, ds_tr, ds_va, pesos_clase, checkpoint,
                                    dir_drive, repo_datos, inicio, tr, va)
    ruta_f1 = os.path.join(dir_drive, "fase1.weights.h5")
    if reg.get("fase1_completa") and os.path.exists(ruta_f1):
        modelo.load_weights(ruta_f1)
        e1 = reg["epocas_fase1"]
    else:
        arquitecturas.congelar_fase1(capas_base)
        _compilar(modelo, cfg["fase1"]["tasa"])
        modelo.fit(ds_tr, validation_data=ds_va, epochs=cfg["fase1"]["epocas"], class_weight=pesos_clase,
                   callbacks=_callbacks(cfg, dir_drive, "fase1", checkpoint), verbose=2)
        e1 = len(_historial(dir_drive, "fase1"))
        modelo.save_weights(ruta_f1)
        registro.escribir_registro(repo_datos, {**registro.leer_registro(repo_datos, id_),
                                                "fase1_completa": True, "epocas_fase1": e1})

    entrenables = arquitecturas.descongelar_fase2(capas_base, cfg["fase2"]["fraccion"])
    _compilar(modelo, cfg["fase2"]["tasa"])
    modelo.fit(ds_tr, validation_data=ds_va, initial_epoch=e1, epochs=e1 + cfg["fase2"]["epocas"],
               class_weight=pesos_clase, callbacks=_callbacks(cfg, dir_drive, "fase2", checkpoint), verbose=2)

    _cerrar(cfg, id_, dir_drive, repo_datos, ("fase1", "fase2"), inicio, tr, va, capa_mapa=capa_mapa,
            capas_base=len(capas_base), capas_entrenables_fase2=entrenables, epocas_fase1=e1,
            epocas_fase2=len(_historial(dir_drive, "fase2")), pesos_clase=pesos_clase)
    return id_


def _entrenar_linea_base(cfg, id_, modelo, capas_base, capa_mapa, ds_tr, ds_va, pesos_clase, checkpoint, dir_drive,
                         repo_datos, inicio, tr, va):
    """Una sola fase, todo entrenable desde cero (research M22). Misma parada, pesos de clase y aumento que M7–M8,
    con la tasa, las épocas máximas y la paciencia de [linea_base]."""
    lb = cfg["linea_base"]
    cfg_parada = {**cfg, "parada": {**cfg["parada"], "paciencia": lb["paciencia"]}}
    _compilar(modelo, lb["tasa"])
    # Igual que la fase 1 normal: BackupAndRestore retoma la época si Colab se desconecta.
    modelo.fit(ds_tr, validation_data=ds_va, epochs=lb["epocas"],
               class_weight=pesos_clase, callbacks=_callbacks(cfg_parada, dir_drive, "fase1", checkpoint), verbose=2)
    _cerrar(cfg, id_, dir_drive, repo_datos, ("fase1",), inicio, tr, va, capa_mapa=capa_mapa,
            capas_base=len(capas_base), capas_entrenables_fase2=0, epocas_fase1=len(_historial(dir_drive, "fase1")),
            epocas_fase2=0, pesos_clase=pesos_clase, linea_base=lb, desde_cero=True,
            parametros=int(modelo.count_params()))
    return id_


def _cerrar(cfg, id_, dir_drive, repo_datos, fases, inicio, tr, va, **campos):
    """Historial, curvas y campos finales del registro (comunes a las arquitecturas y a la línea base)."""
    arq, semilla = cfg["corrida"]["arquitectura"], cfg["corrida"]["semilla"]
    historial = [{"epoca": int(f["epoch"]) + 1, "fase": fase, "loss": f["loss"], "val_loss": f["val_loss"],
                  "accuracy": f.get("accuracy", ""), "val_accuracy": f.get("val_accuracy", ""),
                  "learning_rate": f.get("learning_rate", "")}
                 for fase in fases for f in _historial(dir_drive, fase)]
    dir_repo = os.path.dirname(registro.ruta_registro(repo_datos, id_))
    escribir_csv(os.path.join(dir_repo, "historial.csv"), COLUMNAS_HISTORIAL, historial)
    figuras.curvas_entrenamiento(historial, os.path.join(dir_repo, "curvas.png"), f"{arq} · semilla {semilla}")
    reg = registro.leer_registro(repo_datos, id_)
    reg.update(**campos, duracion_min=round(reg.get("duracion_min", 0) + (time.time() - inicio) / 60, 2),
               tamano_keras_mb=round(os.path.getsize(os.path.join(dir_drive, "mejor.keras")) / 2**20, 3),
               versiones=registro.versiones(), n_train=int(len(tr["y"])), n_val=int(len(va["y"])),
               distribucion_train=np.bincount(tr["y"].astype(int), minlength=3).tolist())
    registro.escribir_registro(repo_datos, reg)
