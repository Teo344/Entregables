import os
import random
from collections import Counter, defaultdict

import pytest

from avocadoia_datos import inventario, particion
from avocadoia_datos.config import ErrorPrecondicion


def _manifiesto(arbol):
    return inventario.ejecutar(arbol.config(), arbol.modelo, arbol.salida, arbol.confirmados())[0]


def _filas(n_por_fuente, clase="antracnosis", fijas=None):
    filas = []
    for fuente, n in n_por_fuente.items():
        for i in range(n):
            filas.append({"id_contenido": f"{fuente}{i:04d}", "clase_efectiva": clase, "fuente": fuente,
                          "grupo": f"{fuente}{i:04d}", "particion_origen": ""})
    for p, n in (fijas or {}).items():
        for i in range(n):
            filas.append({"id_contenido": f"fijo{p}{i:04d}", "clase_efectiva": clase, "fuente": "mdpi",
                          "grupo": f"fijo{p}{i:04d}", "particion_origen": p})
    return filas


def test_mayor_resto():
    assert particion.mayor_resto(284, {"train": .7, "val": .15, "test": .15}) == {"train": 199, "val": 43, "test": 42}
    assert particion.mayor_resto(1000, {"train": .7, "val": .15, "test": .15}) == {"train": 700, "val": 150, "test": 150}


def test_caso_pedunculo_real(arbol):
    cfg = arbol.config()
    filas = _filas({"mdpi_libre": 29}, "pedunculo", {"train": 182, "val": 36, "test": 37})
    a = particion.asignar(filas, cfg)
    assert Counter(p for p, _ in a.values()) == {"train": 199, "val": 43, "test": 42}
    assert all(a[f["id_contenido"]][0] == f["particion_origen"] for f in filas if f["particion_origen"])


def test_estratifica_por_fuente_y_cumple_tolerancia(arbol):
    cfg = arbol.config()
    filas = _filas({"a": 183, "b": 367, "c": 450})
    a = particion.asignar(filas, cfg)
    total = Counter(p for p, _ in a.values())
    assert total == {"train": 700, "val": 150, "test": 150}
    por_fuente = defaultdict(Counter)
    for f in filas:
        por_fuente[f["fuente"]][a[f["id_contenido"]][0]] += 1
    for fuente, n in {"a": 183, "b": 367, "c": 450}.items():
        assert abs(por_fuente[fuente]["train"] / n - 0.70) < 0.01


def test_grupos_no_se_reparten_y_orden_irrelevante(arbol):
    cfg = arbol.config()
    filas = _filas({"a": 60})
    for i, f in enumerate(filas):
        f["grupo"] = f"g{i // 3}"  # grupos de 3
    a1 = particion.asignar(filas, cfg)
    mezcladas = filas[:]
    random.Random(1).shuffle(mezcladas)
    assert particion.asignar(mezcladas, cfg) == a1
    por_grupo = defaultdict(set)
    for f in filas:
        por_grupo[f["grupo"]].add(a1[f["id_contenido"]][0])
    assert all(len(v) == 1 for v in por_grupo.values())


def test_semilla_cambia_resultado(arbol):
    cfg = arbol.config()
    filas = _filas({"a": 100})
    a1 = particion.asignar(filas, cfg)
    cfg.semilla = 7
    assert particion.asignar(filas, cfg) != a1


def test_ejecutar_reproducible_sin_fugas(arbol_completo):
    arbol = arbol_completo
    cfg = arbol.config()
    filas, meta = particion.ejecutar(_manifiesto(arbol), cfg, arbol.salida)
    csv1 = open(os.path.join(arbol.salida, "particion.csv"), "rb").read()
    particion.ejecutar(_manifiesto(arbol), cfg, arbol.salida)
    assert open(os.path.join(arbol.salida, "particion.csv"), "rb").read() == csv1
    assert meta["estado"] == "provisional"
    por_id = Counter(f["id_contenido"] for f in filas)
    assert max(por_id.values()) == 1
    por_grupo = defaultdict(set)
    for f in filas:
        por_grupo[f["grupo"]].add(f["particion"])
    assert all(len(v) == 1 for v in por_grupo.values())
    assert meta["conteos"]["sano"] == {"train": 35, "val": 8, "test": 7}
    m = inventario.leer_manifiesto(arbol.salida)
    assert sum(f["en_muestra"] == "si" for f in m) == 140


def test_definitiva_falla_con_provisionales(arbol_completo):
    with pytest.raises(ErrorPrecondicion, match="provisional"):
        particion.ejecutar(_manifiesto(arbol_completo), arbol_completo.config(), arbol_completo.salida, True)


def test_test_campo_aparte(arbol_completo):
    arbol_completo.agregar("CAMPO_SIGCHOS/AGUACATESANOS/campo1.jpg")
    filas, meta = particion.ejecutar(_manifiesto(arbol_completo), arbol_completo.config(), arbol_completo.salida)
    campo = [f for f in filas if f["particion"] == "test_campo"]
    assert len(campo) == 1 and campo[0]["origen_asignacion"] == "test_campo"


def test_sin_manifiesto():
    with pytest.raises(ErrorPrecondicion):
        particion.ejecutar([], None, "x")
