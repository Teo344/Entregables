"""Pruebas del manifiesto normalizado y de los filtros de licencia y calidad (T009, FR-001/002/026/027)."""

import pytest

from avocadoia_modelo import manifiesto as mm


def _preparar(esc):
    esc.agregar("AGUACATESANOS/hass_T10_d01_001_a_1_x.jpg", "AGUACATESANOS", "train")          # nombre → hass
    esc.agregar("AGUACATESANOS/sano-0005.jpg", "AGUACATESANOS", "train")                       # nombre → herrera
    esc.agregar("AGUACATESANOS/sano-0707.jpg", "AGUACATESANOS", "val", registro_002="herrera_marin")  # renombrada
    esc.agregar("AGUACATESANOS/sano-0972.jpeg", "AGUACATESANOS", "train")                      # web, sin registro
    esc.agregar("AGUACATESANOS/avocare_ab.jpg", "AGUACATESANOS", "train")                      # calidad
    esc.agregar("ANTRACNOSIS/avocare_cd.jpg", "ANTRACNOSIS", "test")                           # licencia pendiente
    esc.agregar("ANTRACNOSIS/rgb_antracnosis_1.jpg", "ANTRACNOSIS", "test")
    esc.agregar("PEDUNCULO/ring_1.jpg", "PEDUNCULO", "train", registro_002="mdpi_pedunculo")   # solo por SHA
    esc.agregar("PEDUNCULO/desconocida.jpg", "PEDUNCULO", "train")                            # sin fuente
    return esc.escribir()


def _filtrar(esc):
    norm = mm.normalizar(mm.leer_entrada(esc.manifiesto), esc.cfg)
    cfg002, por_sha = mm.contexto_002(esc.cfg)
    cons, excl = mm.filtrar(norm, esc.cfg, cfg002, por_sha)
    return {f["ruta_origen"].split("/")[-1]: f for f in cons}, {f["ruta_origen"].split("/")[-1]: f for f in excl}


def test_mapeo_y_equivalencias(escenario_modelo):
    esc = _preparar(escenario_modelo)
    norm = mm.normalizar(mm.leer_entrada(esc.manifiesto), esc.cfg)
    assert set(norm[0]) == set(mm.COLUMNAS)
    assert {f["clase"] for f in norm} == {"sano", "antracnosis", "pedunculo"}
    assert norm[0]["ruta"].startswith("train/AGUACATESANOS/")
    assert all(f["fuente"] == "" for f in norm)  # procedencia nunca se usa como fuente


def test_clase_desconocida(escenario_modelo):
    esc = escenario_modelo
    esc.agregar("MANZANA/x.jpg", "MANZANA", "train")
    esc.escribir()
    with pytest.raises(mm.ClaseDesconocida):
        mm.normalizar(mm.leer_entrada(esc.manifiesto), esc.cfg)


def test_particion_invalida(escenario_modelo):
    esc = escenario_modelo
    esc.agregar("ANTRACNOSIS/rgb_1.jpg", "ANTRACNOSIS", "train")
    esc.filas_v4[-1]["conjunto"] = ""
    esc.escribir()
    with pytest.raises(mm.ErrorManifiesto):
        mm.normalizar(mm.leer_entrada(esc.manifiesto), esc.cfg)


def test_filtro_licencias_y_calidad(escenario_modelo):
    cons, excl = _filtrar(_preparar(escenario_modelo))
    assert cons["hass_T10_d01_001_a_1_x.jpg"]["fuente"] == "hass"
    assert cons["sano-0005.jpg"]["fuente"] == "herrera_marin"
    assert cons["rgb_antracnosis_1.jpg"]["fuente"] == "rgb_antracnosis"
    assert excl["sano-0972.jpeg"]["motivo"] == "licencia:sano_web:no"
    assert excl["avocare_ab.jpg"]["motivo"] == "calidad:copias_aumentadas_roboflow_v4"
    assert excl["avocare_cd.jpg"]["motivo"] == "licencia:avocare_antracnosis:pendiente"
    assert excl["desconocida.jpg"]["motivo"] == "sin_fuente"


def test_sha_manda_sobre_el_nombre(escenario_modelo):
    """Caso real del v4: sano-0707 es la foto propia sano-0001 renumerada; el nombre diría sano_web."""
    cons, excl = _filtrar(_preparar(escenario_modelo))
    assert "sano-0707.jpg" not in excl
    assert cons["sano-0707.jpg"]["fuente"] == "herrera_marin"


def test_pedunculo_resuelto_por_sha(escenario_modelo):
    cons, _ = _filtrar(_preparar(escenario_modelo))
    assert cons["ring_1.jpg"]["fuente"] == "mdpi_pedunculo"
    assert cons["ring_1.jpg"]["licencia"] == "CC BY 4.0"


def test_quitar_avocare_de_excluidas_lo_conserva(escenario_modelo):
    esc = _preparar(escenario_modelo)
    esc.cfg["filtros"]["fuentes_excluidas"] = []
    cons, excl = _filtrar(esc)
    assert cons["avocare_ab.jpg"]["fuente"] == "avocare_sano"
    assert excl["avocare_cd.jpg"]["motivo"].startswith("licencia:")  # su licencia sigue pendiente


def test_huella_estable(escenario_modelo):
    esc = _preparar(escenario_modelo)
    assert mm.huella_manifiesto(esc.manifiesto) == mm.huella_manifiesto(esc.manifiesto)
    assert len(mm.huella_manifiesto(esc.manifiesto)) == 64
