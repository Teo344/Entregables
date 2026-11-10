"""Adaptador del dataset 002 (T068)."""

import pytest

from avocadoia_datos.es_csv import escribir_csv, sha256_archivo

from avocadoia_modelo import dataset_002 as d2
from avocadoia_modelo import manifiesto as mm


def _archivos(tmp_path):
    particion = tmp_path / "particion.csv"
    manifiesto = tmp_path / "manifiesto.csv"
    escribir_csv(str(particion), ("id_contenido", "clase", "fuente", "grupo", "particion", "origen_asignacion", "ruta"), [
        {"id_contenido": "aaaa", "clase": "sano", "fuente": "hass", "grupo": "hass:T:1", "particion": "train",
         "origen_asignacion": "estratificada", "ruta": "AGUACATESANOS/hass_1.jpg"},
        {"id_contenido": "bbbb", "clase": "pedunculo", "fuente": "mdpi_pedunculo", "grupo": "bbbb", "particion": "test",
         "origen_asignacion": "fuente", "ruta": "PEDUNCULO/DRIVE_X/test/r.jpg"},
        {"id_contenido": "cccc", "clase": "pedunculo", "fuente": "campo", "grupo": "cccc", "particion": "test_campo",
         "origen_asignacion": "test_campo", "ruta": "CAMPO_SIGCHOS/PEDUNCULO/x.jpg"},
    ])
    escribir_csv(str(manifiesto), ("id_contenido", "sha256", "grupo", "validacion"), [
        {"id_contenido": "aaaa", "sha256": "a" * 64, "grupo": "hass:T:1", "validacion": "pendiente"},
        {"id_contenido": "bbbb", "sha256": "b" * 64, "grupo": "bbbb", "validacion": "aceptada"},
        {"id_contenido": "cccc", "sha256": "c" * 64, "grupo": "cccc", "validacion": "pendiente"},
    ])
    return str(particion), str(manifiesto)


def test_genera_formato_m2(tmp_path):
    particion, manifiesto = _archivos(tmp_path)
    filas, res = d2.generar(particion, manifiesto)
    assert res["total"] == 2  # test_campo no entra
    assert filas[0]["ruta_destino"] == "train/sano/aaaa.jpg"
    assert filas[0]["sha256"] == "a" * 64 and filas[0]["grupo_duplicacion_escena"] == "hass:T:1"
    assert filas[0]["estado_etiqueta"] == "ETIQUETA_PROVISIONAL"
    assert filas[1]["estado_etiqueta"] == "ETIQUETA_VALIDADA"
    assert res["huella_particion"] == sha256_archivo(particion)


def test_compatible_con_el_adaptador_del_modelo(tmp_path):
    import tomllib
    particion, manifiesto = _archivos(tmp_path)
    filas, res = d2.generar(particion, manifiesto)
    ruta = d2.escribir(filas, res, str(tmp_path / "salida"))
    with open("config/modelo.toml", "rb") as fh:
        cfg = tomllib.load(fh)
    norm = mm.normalizar(mm.leer_entrada(ruta), cfg)
    assert [f["clase"] for f in norm] == ["sano", "pedunculo"]
    assert [f["particion"] for f in norm] == ["train", "test"]


def test_huella_distinta_aborta(tmp_path):
    particion, manifiesto = _archivos(tmp_path)
    with pytest.raises(d2.ErrorDataset002):
        d2.generar(particion, manifiesto, huella_esperada="0" * 64)


def test_imagen_sin_manifiesto_aborta(tmp_path):
    particion, manifiesto = _archivos(tmp_path)
    escribir_csv(manifiesto, ("id_contenido", "sha256", "grupo", "validacion"),
                 [{"id_contenido": "aaaa", "sha256": "a" * 64, "grupo": "g", "validacion": "pendiente"}])
    with pytest.raises(d2.ErrorDataset002):
        d2.generar(particion, manifiesto)
