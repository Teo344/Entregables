"""Pruebas de config/modelo.toml y huella_config (T007)."""

import copy

import pytest

from avocadoia_modelo import config as mc


def test_carga_toml_real():
    cfg = mc.cargar("config/modelo.toml", entorno_="pc")
    assert cfg["_entorno"] == "pc"
    assert cfg["_rutas"]["salida"].startswith("G:/")
    assert cfg["_rutas"]["repo_datos"] == "datos/modelo"
    assert cfg["entrenamiento"]["semillas"] == [42, 43, 44]
    assert cfg["filtros"]["fuentes_excluidas"] == ["avocare_sano", "avocare_antracnosis"]


def test_huella_ignora_arquitectura_y_semilla():
    cfg = mc.cargar("config/modelo.toml", entorno_="pc")
    a = mc.con_corrida(cfg, "mobilenetv3", 42)
    b = mc.con_corrida(cfg, "efficientnetb0", 44)
    assert mc.huella_config(a) == mc.huella_config(b) == mc.huella_config(cfg)


def test_huella_ignora_rutas_de_entorno():
    pc = mc.cargar("config/modelo.toml", entorno_="pc")
    colab = mc.cargar("config/modelo.toml", entorno_="colab")
    assert mc.huella_config(pc) == mc.huella_config(colab)


def test_huella_cambia_con_hiperparametro():
    cfg = mc.cargar("config/modelo.toml", entorno_="pc")
    otra = copy.deepcopy(cfg)
    otra["fase2"]["tasa"] = 2e-5
    assert mc.huella_config(otra) != mc.huella_config(cfg)


def test_arquitectura_desconocida():
    cfg = mc.cargar("config/modelo.toml", entorno_="pc")
    with pytest.raises(mc.ErrorConfig):
        mc.con_corrida(cfg, "resnet50", 42)


def test_seccion_faltante(tmp_path):
    ruta = tmp_path / "m.toml"
    ruta.write_text("[datos]\n", encoding="utf-8")
    with pytest.raises(mc.ErrorConfig):
        mc.cargar(str(ruta), entorno_="pc")
