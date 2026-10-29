"""Estado excluida_licencia para fuentes con uso_academico = no (spec 002, T007)."""

from avocadoia_datos import inventario, muestra


def _sin_licencia(arbol):
    texto = open(arbol.fuentes, encoding="utf-8").read()
    texto = texto.replace("web,sano,AGUACATESANOS/sano-*,Web,ref,pendiente,pendiente",
                          "web,sano,AGUACATESANOS/sano-*,Web,ref,ninguna,no")
    with open(arbol.fuentes, "w", encoding="utf-8") as fh:
        fh.write(texto)


def test_fuente_sin_uso_academico_queda_excluida_y_fuera_de_la_muestra(arbol):
    _sin_licencia(arbol)
    arbol.agregar("AGUACATESANOS/sano-0001.jpg")
    arbol.agregar("AGUACATESANOS/hass_T10_d01_001_a_1_x.jpg")
    filas, meta = inventario.ejecutar(arbol.config(), arbol.modelo, arbol.salida, arbol.confirmados())
    f = {x["ruta"]: x for x in filas}
    assert f["AGUACATESANOS/sano-0001.jpg"]["estado"] == "excluida_licencia"
    assert f["AGUACATESANOS/sano-0001.jpg"]["motivo"] == "La fuente no permite uso académico"
    assert meta["por_estado"]["excluida_licencia"] == 1
    assert all(c["fuente"] != "web" for c in muestra.candidatas(filas))


def test_copia_exacta_sigue_siendo_duplicada(arbol):
    _sin_licencia(arbol)
    arbol.agregar("AGUACATESANOS/sano-0001.jpg", semilla=7)
    arbol.agregar("AGUACATESANOS/sano-0002.jpg", semilla=7)
    filas, _ = inventario.ejecutar(arbol.config(), arbol.modelo, arbol.salida, arbol.confirmados())
    f = {x["ruta"]: x for x in filas}
    assert f["AGUACATESANOS/sano-0001.jpg"]["estado"] == "excluida_licencia"
    assert f["AGUACATESANOS/sano-0002.jpg"]["estado"] == "duplicada"
