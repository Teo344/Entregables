"""Detección de etiquetas dudosas (spec 002, T013). Requiere numpy y scikit-learn (.venv-ml)."""

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("sklearn")

from avocadoia_datos.etl import sospechas  # noqa: E402


def _nubes(n_por_clase=60, dim=16, semilla=0):
    """Tres nubes gaussianas separadas, en pares de vistas del mismo fruto (grupos de 2)."""
    rng = np.random.default_rng(semilla)
    centros = rng.normal(0, 8, (3, dim))
    X, y, grupos = [], [], []
    for c in range(3):
        for i in range(n_por_clase):
            X.append(centros[c] + rng.normal(0, 1, dim))
            y.append(c)
            grupos.append(f"g{c}_{i // 2}")
    return np.array(X), np.array(y), np.array(grupos)


def test_etiquetas_cambiadas_aparecen_como_conflicto():
    X, y, grupos = _nubes()
    clases = ("sano", "antracnosis", "pedunculo")
    etiquetas = [clases[c] for c in y]
    cambiadas = list(range(0, 180, 20))  # 9 imágenes = 5 %
    for i in cambiadas:
        etiquetas[i] = clases[(y[i] + 1) % 3]
    ids = [f"id{i:04d}" for i in range(len(y))]
    filas, _ = sospechas.calcular(ids, X, etiquetas, grupos, ["f"] * len(y))
    por_id = {f["id_contenido"]: f for f in filas}
    # Todas las cambiadas quedan para revisión; las del límite entre nubes pueden no superar el
    # umbral de su clase verdadera y entran solo por el 10 % superior de puntaje.
    assert all(por_id[ids[i]]["a_revisar"] == "si" for i in cambiadas)
    detectadas = [i for i in cambiadas if por_id[ids[i]]["conflicto"] == "si"]
    assert len(detectadas) >= len(cambiadas) - 1
    assert all(por_id[ids[i]]["clase_sugerida"] == clases[y[i]] for i in detectadas)
    assert sum(f["conflicto"] == "si" for f in filas) <= len(cambiadas) + 3


def test_umbral_es_la_media_de_la_propia_clase():
    p = np.array([[0.9, 0.1, 0.0], [0.7, 0.2, 0.1], [0.2, 0.8, 0.0], [0.1, 0.1, 0.8]])
    y = np.array([0, 0, 1, 2])
    assert np.allclose(sospechas.umbrales(p, y), [0.8, 0.8, 0.8])
    # Ninguna clase supera su umbral: sin sugerencia.
    assert list(sospechas.clase_sugerida(np.array([[0.5, 0.3, 0.2]]), np.array([0.8, 0.8, 0.8]))) == [-1]


def test_pliegues_no_reparten_grupos():
    X, y, grupos = _nubes()
    pliegue = sospechas.pliegues(y, grupos)
    for g in set(grupos):
        assert len(set(pliegue[grupos == g])) == 1


def test_vecinos_excluyen_su_propio_grupo():
    # La imagen 0 tiene una vista idéntica (1) con otra etiqueta; al excluir su grupo, sus vecinos
    # son de su misma clase.
    X = np.array([[1.0, 0.0], [1.0, 0.0], [0.9, 0.1], [0.95, 0.05], [0.0, 1.0]])
    y = np.array([0, 1, 0, 0, 1])
    grupos = np.array(["a", "a", "b", "c", "d"])
    assert sospechas.vecinos_otra_clase(X, y, grupos, k=2)[0] == 0.0


def test_top10_por_clase_y_orden_estable():
    X, y, grupos = _nubes()
    clases = ("sano", "antracnosis", "pedunculo")
    ids = [f"id{i:04d}" for i in range(len(y))]
    filas, _ = sospechas.calcular(ids, X, [clases[c] for c in y], grupos, ["f"] * len(y))
    for c in clases:
        assert sum(1 for f in filas if f["clase_asignada"] == c and "top10" in f["motivo_marca"]) == 6
    claves = [(-float(f["puntaje"]), f["id_contenido"]) for f in filas]
    assert claves == sorted(claves)
    filas2, _ = sospechas.calcular(ids, X, [clases[c] for c in y], grupos, ["f"] * len(y))
    assert filas == filas2


def test_poblacion_conserva_las_excluidas_por_los_autores():
    manifiesto = [
        {"id_contenido": "a", "canonica": "si", "estado": "provisional", "revision_autores": ""},
        {"id_contenido": "b", "canonica": "si", "estado": "excluida_revision", "revision_autores": "excluir"},
        {"id_contenido": "c", "canonica": "si", "estado": "excluida_revision", "revision_autores": ""},
        {"id_contenido": "d", "canonica": "si", "estado": "excluida_licencia", "revision_autores": ""},
    ]
    assert [f["id_contenido"] for f in sospechas.poblacion(manifiesto)] == ["a", "b"]
