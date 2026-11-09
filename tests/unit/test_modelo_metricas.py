"""Pruebas de métricas en NumPy (T016, FR-008, FR-012)."""

import numpy as np
import pytest

from avocadoia_modelo import metricas as mt

# 0 = sano, 1 = antracnosis, 2 = pedunculo
Y = [0, 0, 0, 1, 1, 1, 1, 2, 2, 2]
P = [0, 0, 1, 1, 1, 1, 2, 2, 2, 0]


def test_matriz_confusion_orden():
    cm = mt.matriz_confusion(Y, P)
    assert cm.tolist() == [[2, 1, 0], [0, 3, 1], [1, 0, 2]]


def test_por_clase_y_macro_a_mano():
    pc = mt.por_clase(mt.matriz_confusion(Y, P))
    # sano: P=2/3, R=2/3 ; antracnosis: P=3/4, R=3/4 ; pedunculo: P=2/3, R=2/3
    assert pc["sano"]["precision"] == pytest.approx(2 / 3)
    assert pc["antracnosis"]["recall"] == pytest.approx(3 / 4)
    assert pc["pedunculo"]["soporte"] == 3
    assert mt.macro_f1(Y, P) == pytest.approx((2 / 3 + 3 / 4 + 2 / 3) / 3)
    assert mt.exactitud(Y, P) == pytest.approx(0.7)


def test_clase_sin_predicciones_no_divide_por_cero():
    pc = mt.por_clase(mt.matriz_confusion([0, 1, 2], [0, 0, 0]))
    assert pc["antracnosis"]["precision"] == 0.0
    assert pc["pedunculo"]["f1"] == 0.0


def test_bootstrap_reproducible_y_contiene_puntual():
    a = mt.bootstrap(Y, P, mt.macro_f1, n=300, semilla=42)
    b = mt.bootstrap(Y, P, mt.macro_f1, n=300, semilla=42)
    assert a == b
    assert a[0] <= mt.macro_f1(Y, P) <= a[1]


def test_por_fuente_omite_pocas():
    fuentes = ["hass"] * 10 + ["rgb"] * 3
    y = [0] * 10 + [1] * 3
    p = [0] * 9 + [1] + [1] * 3
    pf = mt.por_fuente(y, p, fuentes, minimo=10)
    assert list(pf) == ["hass"]
    assert pf["hass"]["exactitud"] == pytest.approx(0.9)
    assert pf["hass"]["recall"] == {"sano": pytest.approx(0.9)}


def test_pesos_clase():
    w = mt.pesos_clase([0] * 6 + [1] * 3 + [2] * 1)
    assert w[0] == pytest.approx(10 / (3 * 6))
    assert w[2] == pytest.approx(10 / 3)


def test_resumen_estructura():
    logits = np.eye(3)[P] * 5.0
    r = mt.resumen(Y, logits, fuentes=["x"] * 10, experimental=True, n_bootstrap=50)
    assert r["macro_f1"] == pytest.approx(mt.macro_f1(Y, P))
    assert r["matriz_confusion"] == [[2, 1, 0], [0, 3, 1], [1, 0, 2]]
    assert len(r["por_clase"]["sano"]["recall_ic95"]) == 2
    assert r["experimental"] is True and r["n"] == 10
