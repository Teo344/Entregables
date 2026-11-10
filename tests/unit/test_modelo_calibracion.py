"""Pruebas de calibración en NumPy (T038, FR-016, FR-017)."""

import numpy as np
import pytest

from avocadoia_modelo import calibracion as cal


def _datos_calibrados(n=20000, semilla=0):
    """Logits cuyas probabilidades softmax SON las verdaderas: y se muestrea de ellas."""
    rng = np.random.default_rng(semilla)
    logits = rng.normal(0, 2.0, (n, 3))
    p = cal.softmax(logits)
    y = np.array([rng.choice(3, p=fila) for fila in p])
    return logits, y


def test_recupera_temperatura():
    logits, y = _datos_calibrados()
    t = cal.ajustar_temperatura(logits * 3.0, y)  # sobreconfiado ×3
    assert t == pytest.approx(3.0, abs=0.1)


def test_temperatura_no_cambia_argmax():
    logits, _ = _datos_calibrados(500)
    assert np.array_equal(cal.softmax(logits, 2.5).argmax(1), logits.argmax(1))


def test_ece_calibrado_casi_cero():
    logits, y = _datos_calibrados()
    assert cal.ece(cal.softmax(logits), y) < 0.02
    assert cal.ece(cal.softmax(logits * 3.0), y) > 0.05


def test_ece_a_mano():
    # confianzas 0.95, 0.95, 0.65, 0.65, 0.45, 0.45 ; aciertos 1,1,1,0,0,1
    probs = np.array([[0.95, 0.03, 0.02], [0.95, 0.03, 0.02], [0.65, 0.2, 0.15],
                      [0.65, 0.2, 0.15], [0.45, 0.35, 0.2], [0.45, 0.35, 0.2]])
    y = np.array([0, 0, 0, 1, 1, 0])
    # bins: {0.95: acc 1, conf .95}, {0.65: acc .5, conf .65}, {0.45: acc .5, conf .45}
    esperado = (2 * 0.05 + 2 * 0.15 + 2 * 0.05) / 6
    assert cal.ece(probs, y, 15) == pytest.approx(esperado)


def test_nll_y_brier():
    probs = np.array([[1.0, 0.0, 0.0]])
    assert cal.brier(probs, np.array([0])) == pytest.approx(0.0)
    assert cal.brier(probs, np.array([1])) == pytest.approx(2.0)
    assert cal.nll(np.log(np.array([[0.5, 0.25, 0.25]])), np.array([0])) == pytest.approx(np.log(2))


def test_curva_cobertura_monotona_y_umbral():
    logits, y = _datos_calibrados(3000)
    curva = cal.curva_cobertura(cal.softmax(logits), y)
    coberturas = [c["cobertura"] for c in curva]
    assert all(a >= b for a, b in zip(coberturas, coberturas[1:]))
    assert curva[0]["umbral"] == pytest.approx(0.34) and curva[-1]["umbral"] == pytest.approx(0.99)
    u = cal.umbral_para_exactitud(curva, 0.95)
    assert u is not None
    fila = next(c for c in curva if c["umbral"] == u)
    assert fila["exactitud"] >= 0.95
    assert all(c["exactitud"] is None or c["exactitud"] < 0.95 for c in curva if c["umbral"] < u)
    assert cal.umbral_para_exactitud(curva, 1.01) is None


def test_calibrar_usa_solo_validacion():
    lv, yv = _datos_calibrados(4000, 1)
    lt, yt = _datos_calibrados(4000, 2)
    a = cal.calibrar(lv * 2, yv, lt * 2, yt, intervalos=15, umbral=0.6)
    b = cal.calibrar(lv * 2, yv, lt * 50, yt[::-1], intervalos=15, umbral=0.6)  # otro test, misma T
    assert a["temperatura"] == b["temperatura"]
    assert a["ece_test_despues"] < a["ece_test_antes"]
    assert 0 <= a["no_concluyentes_test"] <= 1
