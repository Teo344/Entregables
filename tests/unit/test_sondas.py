"""Sondas de atajo y mapa de similitud (spec 002, T030 y T034). Requiere scikit-learn (.venv-ml)."""

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("sklearn")

from avocadoia_datos.eda import similitud, sondas  # noqa: E402
from avocadoia_datos.eda.distribuciones import MEDIDAS  # noqa: E402

CLASES = ("sano", "antracnosis", "pedunculo")


def test_caracteristica_que_codifica_la_clase_genera_alerta():
    rng = np.random.default_rng(1)
    y = np.repeat(CLASES, 40)
    grupos = np.array([f"g{i // 2}" for i in range(120)])
    codifica = np.c_[np.repeat([0.0, 5.0, 10.0], 40) + rng.normal(0, 0.3, 120), rng.normal(size=(120, 3))]
    assert sondas.exactitud_balanceada_cv(codifica, y, grupos) > sondas.UMBRAL_ALERTA
    ruido = rng.normal(size=(120, 4))
    assert abs(sondas.exactitud_balanceada_cv(ruido, y, grupos) - 1 / 3) < 0.15


def _datos(tmp_path):
    rng = np.random.default_rng(2)
    particion, caracteristicas = [], []
    for i in range(90):
        conjunto = ("train", "train", "val", "test")[i % 4]
        particion.append({"id_contenido": f"i{i:03d}", "clase": CLASES[i % 3], "fuente": f"f{i % 3}",
                          "grupo": f"g{i // 3}", "particion": conjunto})
        caracteristicas.append({"id_contenido": f"i{i:03d}", **{m: str(rng.normal()) for m in MEDIDAS}})
    rep = {"ids": np.array([f["id_contenido"] for f in particion]),
           "vectores": rng.normal(size=(90, 8)), "vectores_borde": rng.normal(size=(90, 8))}
    return particion, caracteristicas, rep


def test_sondas_nunca_usan_el_conjunto_de_prueba(tmp_path):
    particion, caracteristicas, rep = _datos(tmp_path)
    resultados = sondas.ejecutar(caracteristicas, rep, particion, str(tmp_path))
    n_sin_test = sum(f["particion"] != "test" for f in particion)
    principales = {r["sonda"]: r for r in resultados}
    assert principales["bajo_nivel"]["n"] == principales["fondo"]["n"] == n_sin_test
    assert all(r["conjuntos"] == "train+val" for r in resultados)
    assert principales["bajo_nivel"]["alerta"] in ("si", "no")
    assert (tmp_path / "eda" / "tablas" / "sondas.csv").exists()


def test_tsne_reproducible_con_rotulos_y_una_fila_por_imagen(tmp_path):
    particion, _, rep = _datos(tmp_path)
    a = similitud.ejecutar(rep, particion, str(tmp_path))
    b = similitud.ejecutar(rep, particion, str(tmp_path))
    assert a == b and len(a) == 90
    rotuladas = [f for f in a if f["rotulo"] == "si"]
    assert len(rotuladas) == similitud.N_ROTULOS
    umbral = min(float(f["vecinos_otra_clase"]) for f in rotuladas)
    assert all(float(f["vecinos_otra_clase"]) <= umbral for f in a if f["rotulo"] == "no")
