import pytest

from avocadoia_datos import config as mod_config


def test_carga_valida(arbol):
    cfg = arbol.config()
    assert cfg.semilla == 42
    assert cfg.proporciones == {"train": 0.70, "val": 0.15, "test": 0.15}
    assert cfg.cuotas["antracnosis"] == {"kaggle": 25, "rgb": 25}
    assert len(cfg.version_config) == 64


def test_fuente_de_primera_coincidencia(arbol):
    cfg = arbol.config()
    assert cfg.fuente_de("AGUACATESANOS/DRIVE_PARTICIONES_ARTICULO/train/a.jpg").fuente == "mdpi_sano"
    assert cfg.fuente_de("AGUACATESANOS/hass_T10_d01_001_a_1_x.jpg").fuente == "hass"
    assert cfg.fuente_de("ANTRACNOSIS/Avocado 0001.jpg").fuente == "kaggle"
    assert cfg.fuente_de("ANTRACNOSIS/otro.jpg") is None


def _reescribir(ruta, viejo, nuevo):
    texto = open(ruta, encoding="utf-8").read()
    with open(ruta, "w", encoding="utf-8") as fh:
        fh.write(texto.replace(viejo, nuevo))


def test_proporciones_invalidas(arbol):
    _reescribir(arbol.toml, "test = 0.15", "test = 0.25")
    with pytest.raises(mod_config.ErrorConfig, match="sumar 1"):
        arbol.config()


def test_cuota_con_fuente_inexistente(arbol):
    _reescribir(arbol.toml, "kaggle = 25", "inexistente = 25")
    with pytest.raises(mod_config.ErrorConfig, match="inexistente"):
        arbol.config()


def test_cuotas_mayores_que_el_tope(arbol):
    _reescribir(arbol.toml, "web = 10", "web = 90")
    with pytest.raises(mod_config.ErrorConfig, match="max_por_clase"):
        arbol.config()


def test_enum_invalido(arbol):
    _reescribir(arbol.fuentes, "pendiente,pendiente,no,hass", "pendiente,quizas,no,hass")
    with pytest.raises(mod_config.ErrorConfig, match="uso_academico"):
        arbol.config()
