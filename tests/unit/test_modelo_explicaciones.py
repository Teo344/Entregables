"""Lógica de explicaciones sin TensorFlow (T043): muestra, resumen y concordancia."""

import numpy as np
import pytest

from avocadoia_modelo import explicacion as me


def test_muestra_reproducible_y_limitada():
    y = np.array([0] * 30 + [1] * 30 + [2] * 5)
    pred = y.copy()
    pred[[0, 1, 2]] = 1  # 3 errores en sano
    a = me.seleccionar_muestra(y, pred, semilla=42, n=10)
    assert a == me.seleccionar_muestra(y, pred, semilla=42, n=10)
    tipos = [(int(y[i]), t) for i, t in a]
    assert tipos.count((0, "acierto")) == 10 and tipos.count((0, "error")) == 3
    assert tipos.count((1, "acierto")) == 10 and tipos.count((1, "error")) == 0
    assert tipos.count((2, "acierto")) == 5   # menos de n: todos


def _fila(clase, tipo, valoracion):
    return {"clase_real": clase, "tipo": tipo, "valoracion": valoracion}


def test_resumen_y_atajo():
    planilla = ([_fila("sano", "acierto", "lesion_fruto")] * 7 + [_fila("sano", "acierto", "fondo_ajeno")] * 3
                + [_fila("antracnosis", "acierto", "lesion_fruto")] * 9 + [_fila("antracnosis", "acierto", "ambiguo")]
                + [_fila("pedunculo", "acierto", "")] * 4 + [_fila("sano", "error", "fondo_ajeno")] * 5)
    r = me.resumir(planilla, umbral_atajo=0.20)
    assert r["por_clase"]["sano"]["fondo_ajeno"] == pytest.approx(0.3)
    assert r["por_clase"]["sano"]["valoradas"] == 10       # los errores no cuentan
    assert r["posibles_atajos"] == ["sano"]
    assert r["sin_valorar"] == 4
    assert r["por_clase"]["pedunculo"]["valoradas"] == 0
    assert r["cumple_sc005"] is False                      # sano 0.7 < 0.8


def test_concordancia():
    a = np.arange(49).reshape(7, 7)
    assert me.concordancia(a, a) == {"pearson": pytest.approx(1.0), "iou_top": 1.0}
    assert me.concordancia(a, -a)["pearson"] == pytest.approx(-1.0)
    assert me.concordancia(a, -a)["iou_top"] == 0.0


def test_softmax_temperatura():
    lg = np.array([[2.0, 0.0, 0.0]])
    assert me.softmax(lg, 2.0)[0, 0] < me.softmax(lg, 1.0)[0, 0]
    assert me.softmax(lg).sum() == pytest.approx(1.0)


def test_planilla_xlsx_ida_y_vuelta(tmp_path):
    """El .xlsx tiene columnas separadas, lista desplegable y miniaturas; resumir lo lee."""
    from openpyxl import load_workbook

    filas = [{"n": i + 1, "clase_real": "sano", "tipo": "acierto", "valoracion": "", "sha256": f"s{i}"} for i in range(3)]
    vistas = [np.zeros((224, 224, 3), np.uint8)] * 3
    ruta = tmp_path / "planilla_explicaciones.xlsx"
    me.escribir_planilla_xlsx(str(ruta), filas, vistas)
    libro = load_workbook(ruta)
    hoja = libro["valoracion"]
    assert hoja["A1"].value == "vista" and hoja.max_row == 4
    assert len(hoja.data_validations.dataValidation) == 1 and len(hoja._images) == 3
    col = [c.value for c in hoja[1]].index("valoracion") + 1
    for k, v in zip((2, 3, 4), ("lesion_fruto", "fondo_ajeno", "lesion_fruto")):
        hoja.cell(k, col).value = v
    libro.save(ruta)
    leidas = me.leer_planilla(str(tmp_path))
    assert [f["valoracion"] for f in leidas] == ["lesion_fruto", "fondo_ajeno", "lesion_fruto"]
    assert me.resumir(leidas)["por_clase"]["sano"]["fondo_ajeno"] == pytest.approx(1 / 3)
