"""Pruebas de la caché 224 × 224 (T017, research M5)."""

import os

import numpy as np

from avocadoia_datos.preprocesamiento import cargar_224

from conftest import imagen

from avocadoia_modelo import preparacion as mp


def _filas(tmp_path):
    raiz = tmp_path / "v4"
    imagen(str(raiz / "train/a.jpg"), 1, tamano=(1536, 2048))
    imagen(str(raiz / "train/b.jpg"), 2, tamano=(300, 300))
    imagen(str(raiz / "val/c.jpg"), 3, tamano=(400, 300))
    imagen(str(raiz / "test/d.jpg"), 4, tamano=(250, 250))
    filas = [
        {"ruta": "train/a.jpg", "clase": "sano", "particion": "train", "sha256": "aa", "fuente": "hass"},
        {"ruta": "train/b.jpg", "clase": "pedunculo", "particion": "train", "sha256": "bb", "fuente": "mdpi"},
        {"ruta": "val/c.jpg", "clase": "antracnosis", "particion": "val", "sha256": "cc", "fuente": "rgb"},
        {"ruta": "test/d.jpg", "clase": "sano", "particion": "test", "sha256": "dd", "fuente": "hass"},
    ]
    return str(raiz), filas


def test_forma_tipo_y_mismo_resultado_que_002(tmp_path):
    raiz, filas = _filas(tmp_path)
    r = mp.preparar(filas, raiz, str(tmp_path / "drive"), "h" * 64)
    d = mp.cargar(r["ruta"], "train")
    assert d["x"].shape == (2, 224, 224, 3) and d["x"].dtype == np.uint8
    assert d["y"].tolist() == [0, 2]
    assert d["sha256"].tolist() == ["aa", "bb"] and d["fuente"].tolist() == ["hass", "mdpi"]
    esperado = np.asarray(cargar_224(os.path.join(raiz, "train/a.jpg"), 224), dtype=np.uint8)
    assert np.array_equal(d["x"][0], esperado)
    assert r["conteos"]["val"] == {"sano": 0, "antracnosis": 1, "pedunculo": 0}


def test_reutiliza_y_forzar(tmp_path):
    raiz, filas = _filas(tmp_path)
    salida = str(tmp_path / "drive")
    r1 = mp.preparar(filas, raiz, salida, "h" * 64)
    r2 = mp.preparar(filas, raiz, salida, "h" * 64)
    assert r2["reutilizada"] and r2["huella_cache"] == r1["huella_cache"]
    r3 = mp.preparar(filas, raiz, salida, "h" * 64, forzar=True)
    assert not r3["reutilizada"]


def test_huella_depende_del_manifiesto():
    assert mp.huella_cache("a" * 64) != mp.huella_cache("b" * 64)
    assert mp.huella_cache("a" * 64, 224) != mp.huella_cache("a" * 64, 192)
