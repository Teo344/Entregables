"""Agregación de corridas y regla de selección de arquitectura (T033, research M12)."""

import pytest

from avocadoia_modelo import seleccion as sel


def _corrida(id_, arq, semilla, val, test, estado="completa", hc="c" * 64, hm="m" * 64, rec_antr=0.95):
    return {"id": id_, "arquitectura": arq, "semilla": semilla, "estado": estado, "huella_config": hc,
            "huella_manifiesto": hm, "duracion_min": 20.0, "tamano_keras_mb": 30.0,
            "val_macro_f1": val, "test_macro_f1": test, "test_exactitud": test,
            "test_recall": {"sano": 0.99, "antracnosis": rec_antr, "pedunculo": 0.80}}


def _seis(val_a=(0.97, 0.98, 0.96), val_b=(0.97, 0.97, 0.98)):
    return ([_corrida(f"a{s}", "mobilenetv3", s, v, v - 0.03) for s, v in zip((42, 43, 44), val_a)]
            + [_corrida(f"b{s}", "efficientnetb0", s, v, v - 0.03) for s, v in zip((42, 43, 44), val_b)])


TAMANOS = {"mobilenetv3": 8.4, "efficientnetb0": 8.1}


def test_agregar_media_y_desviacion_muestral():
    tabla = sel.agregar(_seis(), TAMANOS)
    a = tabla["mobilenetv3"]
    assert a["n"] == 3
    assert a["val_macro_f1_media"] == pytest.approx(0.97)
    assert a["val_macro_f1_desv"] == pytest.approx(0.01)  # muestral (n - 1)
    assert a["tamano_fp16_mb"] == 8.4


def test_diferencia_menor_al_margen_gana_el_mas_liviano():
    d = sel.elegir(sel.agregar(_seis(), TAMANOS), margen=0.02)
    assert d["regla"] == "desempate_por_tamano_fp16"
    assert d["arquitectura"] == "efficientnetb0"  # 8,1 MB < 8,4 MB
    assert d["diferencia_val_macro_f1"] == pytest.approx(0.0033, abs=1e-4)


def test_diferencia_mayor_o_igual_al_margen_gana_el_mayor_macro_f1_de_validacion():
    d = sel.elegir(sel.agregar(_seis(val_a=(0.99, 0.99, 0.99), val_b=(0.95, 0.96, 0.97)), TAMANOS), margen=0.02)
    assert d["regla"] == "mayor_macro_f1_val"
    assert d["arquitectura"] == "mobilenetv3"


def test_huellas_distintas_invalidan():
    corridas = _seis()
    corridas[0]["huella_manifiesto"] = "x" * 64
    with pytest.raises(sel.ComparacionInvalida):
        sel.validar_igualdad(corridas)
    corridas = _seis()
    corridas[3]["huella_config"] = "y" * 64
    with pytest.raises(sel.ComparacionInvalida):
        sel.validar_igualdad(corridas)


def test_incompletas_se_excluyen_y_faltan_corridas():
    corridas = _seis()
    corridas[1]["estado"] = "incompleta"
    with pytest.raises(sel.ComparacionInvalida):
        sel.validar_igualdad(sel.seleccionar(corridas, semillas=(42, 43, 44)))


def test_repetidas_se_reducen_a_una_por_semilla():
    corridas = _seis() + [_corrida("a43bis", "mobilenetv3", 43, 0.98, 0.95)]
    elegidas = sel.seleccionar(corridas, semillas=(42, 43, 44))
    assert len(elegidas) == 6
    assert sorted(c["id"] for c in elegidas if c["arquitectura"] == "mobilenetv3") == ["a42", "a43", "a44"]
    assert sel.repetidas(corridas, elegidas) == ["a43bis"]


def test_representativa_es_la_de_mayor_val_macro_f1():
    corridas = _seis()
    assert sel.representativa(corridas, "mobilenetv3")["id"] == "a43"


def test_cumple_metas():
    metas = {"macro_f1": 0.85, "recall_antracnosis": 0.85}
    assert sel.cumple_metas({"macro_f1": 0.90, "recall_antracnosis": 0.86}, metas)["cumple"]
    r = sel.cumple_metas({"macro_f1": 0.90, "recall_antracnosis": 0.80}, metas)
    assert not r["cumple"] and r["detalle"]["recall_antracnosis"]["cumple"] is False


def test_mcnemar_exacto():
    # 10 discordantes, todos a favor de A → p = 2 · 0,5^10
    y = [0] * 20
    pred_a = [0] * 20
    pred_b = [1] * 10 + [0] * 10
    r = sel.mcnemar(y, pred_a, pred_b)
    assert (r["solo_a_acierta"], r["solo_b_acierta"]) == (10, 0)
    assert r["p_valor"] == pytest.approx(2 * 0.5 ** 10)
    assert sel.mcnemar(y, pred_a, pred_a)["p_valor"] == 1.0
