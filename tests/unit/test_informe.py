import os

from avocadoia_datos import informe, inventario, particion
from avocadoia_datos.es_csv import leer_json


def test_pesos_de_clase():
    pesos = informe.pesos_de_clase({"sano": 700, "antracnosis": 700, "pedunculo": 199})
    assert pesos == {"sano": 0.7614, "antracnosis": 0.7614, "pedunculo": 2.6784}


def test_informe_cuadra_con_la_particion(arbol_completo):
    arbol = arbol_completo
    cfg = arbol.config()
    m = inventario.ejecutar(cfg, arbol.modelo, arbol.salida, arbol.confirmados())[0]
    filas, meta = particion.ejecutar(m, cfg, arbol.salida)
    datos = informe.ejecutar(arbol.salida, cfg)
    for clase, conteo in meta["conteos"].items():
        for p, n in conteo.items():
            assert datos["conteos"][clase][p] == n
    assert datos["estado_particion"] == "provisional"
    assert datos["razon_desbalance"] == round(35 / 28, 2)
    assert datos["aumento"]["rotacion_grados"] == 45
    md = open(os.path.join(arbol.salida, "informe.md"), encoding="utf-8").read()
    assert "Síntomas compatibles con anillado del pedúnculo" in md
    assert "Partición provisional" in md
    assert "Tono / saturación" in md
    assert leer_json(os.path.join(arbol.salida, "informe.json"))["totales_particion"]["train"] == 35 + 35 + 28
