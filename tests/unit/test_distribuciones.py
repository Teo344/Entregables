"""Tablas descriptivas y mosaicos del EDA (spec 002, T025). Requiere numpy (.venv-ml)."""

import pytest

pytest.importorskip("numpy")

from avocadoia_datos.eda import distribuciones  # noqa: E402


def _particion():
    filas = []
    for i in range(30):
        filas.append({"id_contenido": f"s{i:03d}", "clase": "sano", "fuente": "hass" if i % 3 else "mdpi",
                      "particion": ("train", "val", "test")[i % 3]})
    for i in range(12):
        filas.append({"id_contenido": f"a{i:03d}", "clase": "antracnosis", "fuente": "rgb",
                      "particion": ("train", "train", "val", "test")[i % 4]})
    filas.append({"id_contenido": "x", "clase": "sano", "fuente": "campo", "particion": "test_campo"})
    return filas


def test_distribucion_suma_el_total_de_la_particion():
    filas = distribuciones.distribucion(_particion())
    todas = [f for f in filas if f["fuente"] == "todas"]
    assert sum(f["total"] for f in todas) == 42  # la prueba de campo no es parte del conjunto final
    sano = {f["fuente"]: f for f in filas if f["clase"] == "sano"}
    assert sano["hass"]["total"] + sano["mdpi"]["total"] == sano["todas"]["total"] == 30
    assert {f["clase"] for f in filas} == {"sano", "antracnosis", "pedunculo"}


def test_mosaico_es_reproducible_y_limitado():
    p = _particion()
    a = distribuciones.elegir_mosaico(p, 42, "sano", "hass")
    b = distribuciones.elegir_mosaico(list(reversed(p)), 42, "sano", "hass")
    assert a == b and len(a) == 16
    assert distribuciones.elegir_mosaico(p, 7, "sano", "hass") != a
