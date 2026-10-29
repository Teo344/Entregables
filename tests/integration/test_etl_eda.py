"""Cadena ETL + EDA sobre un árbol sintético, con TensorFlow (spec 002, T048)."""

import os

import pytest

pytestmark = pytest.mark.ml
pytest.importorskip("tensorflow")

from avocadoia_datos import cli  # noqa: E402
from avocadoia_datos.es_csv import escribir_csv, leer_json  # noqa: E402
from avocadoia_datos.etl.embudo import ruta_linea_base  # noqa: E402

PASOS = ("etl-extraer", "todo", "etl-representaciones", "etl-sospechas", "etl-embudo", "eda", "informe-etl-eda")
TABLAS = ("etl/sospechas.csv", "etl/embudo.csv", "etl/comparacion_001.csv", "eda/tablas/caracteristicas.csv",
          "eda/tablas/sondas.csv", "eda/tablas/tsne.csv", "eda/tablas/distribucion_clase_fuente_conjunto.csv")


def _leer(ruta):
    with open(ruta, "rb") as fh:
        return fh.read()


def test_cadena_completa_y_reproducible(arbol_completo):
    a = arbol_completo
    # Sin repositorio Git en el árbol temporal: línea base vacía.
    escribir_csv(ruta_linea_base(a.salida), ("id_contenido", "clase", "fuente", "grupo", "particion"), [])
    for paso in PASOS:
        assert cli.main(a.args(paso)) == 0, paso
    for t in TABLAS:
        assert os.path.exists(os.path.join(a.salida, t)), t
    assert os.path.exists(os.path.join(a.salida, "eda", "figuras", "tsne_por_clase.png"))
    assert os.path.exists(os.path.join(a.salida, "eda", "informe_etl_eda.md"))
    primero = {t: _leer(os.path.join(a.salida, t)) for t in TABLAS}
    json1 = leer_json(os.path.join(a.salida, "eda", "informe_etl_eda.json"))
    assert all(c["evidencia"] for c in json1["conclusiones"])
    assert all(s["conjuntos"] == "train+val" for s in json1["sondas"])

    for paso in ("etl-representaciones", "etl-sospechas", "etl-embudo", "eda", "informe-etl-eda"):
        assert cli.main(a.args(paso)) == 0, paso
    assert {t: _leer(os.path.join(a.salida, t)) for t in TABLAS} == primero
    assert leer_json(os.path.join(a.salida, "eda", "informe_etl_eda.json")) == json1


def test_subcomandos_ml_sin_cache_fallan_con_precondicion(arbol_completo):
    a = arbol_completo
    assert cli.main(a.args("etl-extraer")) in (0, 2)
    assert cli.main(a.args("inventario")) == 0
    assert cli.main(a.args("etl-sospechas")) == 2
