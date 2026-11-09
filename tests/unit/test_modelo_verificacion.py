"""Pruebas de la verificación previa (T011, FR-003, FR-026)."""

import json
import os

from avocadoia_datos.es_csv import leer_csv

from avocadoia_modelo import verificacion as mv


def _base(esc):
    esc.agregar("AGUACATESANOS/hass_a.jpg", "AGUACATESANOS", "train", estado="ETIQUETA_RESPALDADA")
    esc.agregar("ANTRACNOSIS/rgb_antracnosis_1.jpg", "ANTRACNOSIS", "val", estado="ETIQUETA_RESPALDADA")
    esc.agregar("PEDUNCULO/DRIVE_X/r1.jpg", "PEDUNCULO", "test", estado="ETIQUETA_RESPALDADA")
    return esc


def _verificar(esc):
    esc.escribir()
    return mv.verificar(esc.cfg, esc.manifiesto, esc.raiz, esc.repo_datos, esc.salida)


def test_todo_correcto(escenario_modelo):
    inf = _verificar(_base(escenario_modelo))
    assert inf["estado"] == "ok"
    assert inf["total"] == 3
    assert inf["conteos"]["train"] == {"sano": 1, "antracnosis": 0, "pedunculo": 0}
    assert os.path.exists(inf["ruta_manifiesto_normalizado"])
    with open(os.path.join(escenario_modelo.repo_datos, "verificacion.json"), encoding="utf-8") as fh:
        assert json.load(fh)["estado"] == "ok"


def test_sin_licencia_se_excluye_y_registra(escenario_modelo):
    esc = _base(escenario_modelo)
    esc.agregar("AGUACATESANOS/sano-0972.jpeg", "AGUACATESANOS", "train", estado="ETIQUETA_RESPALDADA")
    inf = _verificar(esc)
    assert inf["conteos"]["train"] == {"sano": 1, "antracnosis": 0, "pedunculo": 0}
    assert inf["conteos_entrada"]["train"]["sano"] == 2
    assert inf["excluidas"]["por_motivo"] == {"licencia:sano_web:no": 1}
    excl = leer_csv(os.path.join(esc.repo_datos, "excluidas.csv"))
    assert [e["motivo"] for e in excl] == ["licencia:sano_web:no"]
    norm = leer_csv(inf["ruta_manifiesto_normalizado"])
    assert all(f["fuente"] != "sano_web" for f in norm)


def test_sin_licencia_y_faltante_no_falla(escenario_modelo):
    """Se filtra antes de comprobar el disco: una imagen sin licencia ausente no vuelve fallida la verificación."""
    esc = _base(escenario_modelo)
    esc.agregar("AGUACATESANOS/sano-0999.jpeg", "AGUACATESANOS", "train", crear=False,
                estado="ETIQUETA_RESPALDADA")
    assert _verificar(esc)["estado"] == "ok"


def test_faltante_con_licencia_falla(escenario_modelo):
    esc = _base(escenario_modelo)
    esc.agregar("AGUACATESANOS/hass_b.jpg", "AGUACATESANOS", "train", crear=False)
    inf = _verificar(esc)
    assert inf["estado"] == "fallida"
    assert inf["faltantes"] == ["train/AGUACATESANOS/hass_b.jpg"]
    assert "ruta_manifiesto_normalizado" not in inf


def test_ilegible_falla(escenario_modelo):
    esc = _base(escenario_modelo)
    ruta = esc.agregar("AGUACATESANOS/hass_roto.jpg", "AGUACATESANOS", "train")
    with open(ruta, "wb") as fh:
        fh.write(b"no es una imagen")
    assert _verificar(esc)["ilegibles"] == ["train/AGUACATESANOS/hass_roto.jpg"]


def test_sha_cruzado_falla(escenario_modelo):
    esc = _base(escenario_modelo)
    origen = esc.agregar("AGUACATESANOS/hass_c.jpg", "AGUACATESANOS", "train")
    esc.agregar("AGUACATESANOS/hass_d.jpg", "AGUACATESANOS", "test", contenido_de=origen)
    inf = _verificar(esc)
    assert inf["estado"] == "fallida"
    assert len(inf["sha_cruzados"]) == 1


def test_fuga_por_fruto_es_aviso(escenario_modelo):
    esc = _base(escenario_modelo)
    esc.agregar("AGUACATESANOS/hass_f1_a.jpg", "AGUACATESANOS", "train", registro_002="hass", grupo_002="hass:T:1",
                estado="ETIQUETA_RESPALDADA")
    esc.agregar("AGUACATESANOS/hass_f1_b.jpg", "AGUACATESANOS", "test", registro_002="hass", grupo_002="hass:T:1",
                estado="ETIQUETA_RESPALDADA")
    inf = _verificar(esc)
    assert inf["estado"] == "ok_con_avisos"
    assert inf["fuga_por_fruto"]["grupos"] == 1
    assert inf["fuga_por_fruto"]["imagenes_test"] == 1


def test_provisionales_es_aviso(escenario_modelo):
    esc = _base(escenario_modelo)
    esc.agregar("ANTRACNOSIS/rgb_antracnosis_2.jpg", "ANTRACNOSIS", "train")
    inf = _verificar(esc)
    assert inf["estado"] == "ok_con_avisos"
    assert inf["etiquetas_provisionales"]["train"] == 1


def test_clase_desconocida_falla_sin_excepcion(escenario_modelo):
    esc = _base(escenario_modelo)
    esc.agregar("MANZANA/x.jpg", "MANZANA", "train")
    inf = _verificar(esc)
    assert inf["estado"] == "fallida"
    assert inf["clases_desconocidas"] == ["MANZANA"]
