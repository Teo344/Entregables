"""Patrones con alternativas "|" en fuentes.csv (spec 002, research E5)."""

FILA_HM = ("herrera_marin,sano,AGUACATESANOS/sano-000[1-9].*|AGUACATESANOS/sano-001[0-7].*,"
           "Fotos propias,ref,permiso,si,no,ninguna,general\n")


def _con_herrera_marin(arbol):
    texto = open(arbol.fuentes, encoding="utf-8").read()
    # herrera_marin va antes que la fuente web: gana la primera coincidencia.
    texto = texto.replace("web,sano,", FILA_HM + "web,sano,", 1)
    with open(arbol.fuentes, "w", encoding="utf-8") as fh:
        fh.write(texto)
    return arbol.config()


def test_alternativas_separan_fotos_propias_de_descargas(arbol):
    cfg = _con_herrera_marin(arbol)
    assert cfg.fuente_de("AGUACATESANOS/sano-0001.jpg").fuente == "herrera_marin"
    assert cfg.fuente_de("AGUACATESANOS/sano-0017.jpg").fuente == "herrera_marin"
    assert cfg.fuente_de("AGUACATESANOS/sano-0018.jpg").fuente == "web"
    assert cfg.fuente_de("AGUACATESANOS/sano-0019.jpeg").fuente == "web"
    assert cfg.fuente_de("AGUACATESANOS/sano-0000.jpg").fuente == "web"


def test_patron_sin_alternativas_igual_que_en_001(arbol):
    cfg = _con_herrera_marin(arbol)
    assert cfg.fuente_de("AGUACATESANOS/hass_T10_d01_001_a_1_x.jpg").fuente == "hass"
    assert cfg.fuente_de("ANTRACNOSIS/otro.jpg") is None
