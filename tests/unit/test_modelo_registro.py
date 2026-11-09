"""Pruebas del registro de corridas, la bitácora y la importación (T013)."""

import datetime
import os

import pytest

from avocadoia_datos.es_csv import leer_csv

from avocadoia_modelo import registro as mr


def test_formato_id():
    f = datetime.datetime(2026, 11, 10, 9, 30)
    assert mr.id_corrida(f, "mobilenetv3", 42, "ab12cd34ef") == "20261110-0930_mobilenetv3_s42_ab12cd34"


def test_transiciones(tmp_path):
    repo = str(tmp_path)
    mr.actualizar_estado(repo, "x", "en_curso", arquitectura="mobilenetv3")
    mr.actualizar_estado(repo, "x", "incompleta")
    mr.actualizar_estado(repo, "x", "en_curso")  # reanudación
    reg = mr.actualizar_estado(repo, "x", "completa")
    assert reg["estado"] == "completa" and reg["arquitectura"] == "mobilenetv3"
    with pytest.raises(mr.TransicionInvalida):
        mr.actualizar_estado(repo, "x", "en_curso")


def test_no_se_puede_completar_sin_empezar(tmp_path):
    with pytest.raises(mr.TransicionInvalida):
        mr.actualizar_estado(str(tmp_path), "y", "completa")


def test_bitacora_sin_duplicados(tmp_path):
    repo = str(tmp_path)
    mr.agregar_a_bitacora(repo, {"id": "b", "estado": "en_curso"})
    mr.agregar_a_bitacora(repo, {"id": "a", "estado": "completa"})
    mr.agregar_a_bitacora(repo, {"id": "b", "estado": "completa", "test_macro_f1": "0.9"})
    filas = leer_csv(os.path.join(repo, "bitacora.csv"))
    assert [f["id"] for f in filas] == ["a", "b"]
    assert filas[1]["test_macro_f1"] == "0.9"
    assert list(filas[0]) == list(mr.COLUMNAS_BITACORA)


def test_importar_solo_livianos(tmp_path):
    origen, destino = tmp_path / "drive", tmp_path / "repo"
    for nombre in ("experimentos/x/registro.json", "experimentos/x/metricas.csv", "experimentos/x/curvas.png",
                   "experimentos/x/mejor.keras", "cache/h/train.npz", "exportacion/x/avocadoia_fp16.tflite"):
        ruta = origen / nombre
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_bytes(b"x")
    copiados = mr.importar(str(origen), str(destino))
    assert copiados == ["experimentos/x/curvas.png", "experimentos/x/metricas.csv", "experimentos/x/registro.json"]


def test_versiones_sin_tensorflow():
    v = mr.versiones()
    assert v["python"]
    assert set(v) >= {"tensorflow", "keras", "numpy", "gpu"}
