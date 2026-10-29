"""Informe de ETL y EDA (spec 002, T040)."""

import os

import pytest

from avocadoia_datos.config import ErrorPrecondicion
from avocadoia_datos.eda import informe
from avocadoia_datos.es_csv import escribir_csv


def test_pesos_por_clase_sobre_train():
    particion = ([{"clase": "sano", "particion": "train"}] * 70 + [{"clase": "antracnosis", "particion": "train"}] * 70
                 + [{"clase": "pedunculo", "particion": "train"}] * 20 + [{"clase": "sano", "particion": "test"}] * 50)
    assert informe.pesos_por_clase(particion) == {"sano": round(160 / 210, 4), "antracnosis": round(160 / 210, 4),
                                                  "pedunculo": 2.6667}


def test_wilson_para_2_de_100():
    bajo, alto = informe.wilson(2, 100)
    assert bajo == pytest.approx(0.0055, abs=1e-3) and alto == pytest.approx(0.0700, abs=1e-3)
    assert informe.resumen_auditoria([
        {"id_contenido": "a", "decision": "mantener", "tipo": "auditoria"},
        {"id_contenido": "b", "decision": "excluir", "tipo": "auditoria"},
        {"id_contenido": "c", "decision": "excluir", "tipo": "sospecha"}])["errores"] == 1


def test_toda_conclusion_tiene_evidencia_existente():
    datos = {"pesos_clase": {"sano": 0.76, "antracnosis": 0.76, "pedunculo": 2.68},
             "aumento": {"rotacion_grados": 45, "desplazamiento": 0.2, "zoom": 0.2, "brillo": [0.8, 1.2]},
             "sondas": [{"sonda": "bajo_nivel", "exactitud_balanceada": "0.9100", "alerta": "si"},
                        {"sonda": "fondo", "exactitud_balanceada": "0.6000", "alerta": "no"},
                        {"sonda": "fuente_sano", "exactitud_balanceada": "0.9500", "alerta": ""}],
             "fondo": [{"clase": "sano", "fuente": "todas", "fraccion_uniforme": "0.1000"},
                       {"clase": "antracnosis", "fuente": "todas", "fraccion_uniforme": "0.6000"}]}
    conclusiones = informe.conclusiones(datos)
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    assert all(c["evidencia"] for c in conclusiones)
    for c in conclusiones:
        for e in c["evidencia"]:
            if e.startswith("config/"):
                assert os.path.exists(os.path.join(raiz, e))
    textos = " ".join(c["conclusion"] for c in conclusiones)
    assert "Riesgo de atajo" in textos and "estilo propio" in textos and "fondo uniforme" in textos


def test_precondiciones_embudo_descuadrado_y_auditoria_pendiente(tmp_path):
    salida = str(tmp_path)
    escribir_csv(os.path.join(salida, "etl", "embudo.csv"), ("paso", "clase", "fuente", "imagenes"),
                 [{"paso": "inventariadas", "clase": "sano", "fuente": "hass", "imagenes": 3},
                  {"paso": "conjunto_final", "clase": "sano", "fuente": "hass", "imagenes": 2}])
    with pytest.raises(ErrorPrecondicion, match="no cuadra"):
        informe.verificar_precondiciones(salida)
    escribir_csv(os.path.join(salida, "etl", "embudo.csv"), ("paso", "clase", "fuente", "imagenes"),
                 [{"paso": "inventariadas", "clase": "sano", "fuente": "hass", "imagenes": 2},
                  {"paso": "conjunto_final", "clase": "sano", "fuente": "hass", "imagenes": 2}])
    os.makedirs(os.path.join(salida, "revision"))
    open(os.path.join(salida, "revision", "auditoria_01.xlsx"), "wb").close()
    with pytest.raises(ErrorPrecondicion, match="auditoría sin incorporar"):
        informe.verificar_precondiciones(salida)
