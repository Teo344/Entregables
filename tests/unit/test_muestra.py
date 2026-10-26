from collections import Counter

from avocadoia_datos import inventario, muestra


def _manifiesto(arbol):
    return inventario.ejecutar(arbol.config(), arbol.modelo, arbol.salida, arbol.confirmados())[0]


def test_cuotas_y_particion_de_origen_completa(arbol_completo):
    m = _manifiesto(arbol_completo)
    ids, faltantes, reserva = muestra.seleccionar(m, arbol_completo.config())
    por = Counter((f["clase_efectiva"], f["fuente"]) for f in m if f["id_contenido"] in ids)
    assert por[("sano", "mdpi_sano")] == 20
    assert por[("sano", "hass")] == 20
    assert por[("sano", "web")] == 10
    assert por[("antracnosis", "kaggle")] == 25
    assert por[("antracnosis", "rgb")] == 25
    assert por[("pedunculo", "mdpi_ped")] == 40  # cuota 40 = todas (36 con partición + 4 candidatas)
    assert reserva["sano"] == {"hass": 10, "web": 2}
    assert reserva["antracnosis"] == {"kaggle": 5, "rgb": 5}
    assert faltantes == {}


def test_una_foto_por_grupo_antes_de_repetir(arbol_completo):
    m = _manifiesto(arbol_completo)
    ids, _, _ = muestra.seleccionar(m, arbol_completo.config())
    grupos_hass = Counter(f["grupo"] for f in m if f["id_contenido"] in ids and f["fuente"] == "hass")
    # 15 frutos con 2 fotos y cuota 20: primero 15 frutos distintos, luego 5 segundas fotos.
    assert len(grupos_hass) == 15
    assert sorted(grupos_hass.values()) == [1] * 10 + [2] * 5


def test_fuente_corta_informa_faltante(arbol_completo):
    cfg = arbol_completo.config()
    cfg.cuotas["sano"]["web"] = 30
    cfg.cuotas["sano"]["hass"] = 10
    ids, faltantes, _ = muestra.seleccionar(_manifiesto(arbol_completo), cfg)
    assert faltantes == {"sano": {"web": 18}}


def test_reposicion_estable(arbol_completo):
    cfg = arbol_completo.config()
    m = _manifiesto(arbol_completo)
    ids, _, _ = muestra.seleccionar(m, cfg)
    elegida = sorted(f["id_contenido"] for f in m if f["id_contenido"] in ids and f["fuente"] == "kaggle")[0]
    for f in m:
        if f["id_contenido"] == elegida:
            f["estado"] = "rechazada"
    ids2, _, _ = muestra.seleccionar(m, cfg)
    assert elegida not in ids2
    assert len(ids2) == len(ids)
    assert len(ids - ids2) == 1 and len(ids2 - ids) == 1  # solo cambia la imagen repuesta


def test_nunca_entran_excluidas(arbol):
    arbol.agregar("ANTRACNOSIS/rgb_antracnosis_1.jpg", semilla=5)
    arbol.copiar("ANTRACNOSIS/rgb_antracnosis_1.jpg", "ANTRACNOSIS/rgb_antracnosis_2.jpg")
    arbol.agregar("CAMPO_SIGCHOS/AGUACATESANOS/c.jpg")
    m = _manifiesto(arbol)
    ids, _, _ = muestra.seleccionar(m, arbol.config())
    assert len(ids) == 1  # la copia duplicada no cuenta y el campo no entra
