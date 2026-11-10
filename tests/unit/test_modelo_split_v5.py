"""Reglas del split v5 propuesto (consolidación de grupos y partición del artículo)."""

from avocadoia_modelo import split_v5


def _f(sha, grupo, particion):
    return {"sha256": sha, "grupo": grupo, "particion": particion}


def test_grupo_repartido_va_a_su_particion_mayoritaria():
    filas = [_f("a", "g1", "train"), _f("b", "g1", "train"), _f("c", "g1", "test"), _f("d", "g2", "val")]
    movidas = split_v5.consolidar_grupos(filas)
    assert [(f["sha256"], antes, despues) for f, antes, despues in movidas] == [("c", "test", "train")]
    assert {f["particion"] for f in filas if f["grupo"] == "g1"} == {"train"}


def test_empate_va_a_train():
    filas = [_f("a", "g", "test"), _f("b", "g", "val")]
    split_v5.consolidar_grupos(filas)
    assert {f["particion"] for f in filas} == {"val"}  # val antes que test; train no está presente
    filas = [_f("a", "g", "test"), _f("b", "g", "train")]
    split_v5.consolidar_grupos(filas)
    assert {f["particion"] for f in filas} == {"train"}


def test_particion_fija_del_articulo_manda():
    filas = [_f("a", "g", "train"), _f("b", "g", "train"), _f("c", "g", "test")]
    split_v5.consolidar_grupos(filas, fijas=frozenset({"c"}))
    assert {f["particion"] for f in filas} == {"test"}


def test_comprobaciones():
    salida = [{"grupo_duplicacion_escena": "g", "conjunto": "train", "sha256": "a", "fuente": "hass"},
              {"grupo_duplicacion_escena": "g", "conjunto": "test", "sha256": "b", "fuente": "sano_web"}]
    c = split_v5.comprobaciones(salida)
    assert c["grupos_en_varias_particiones"] == 1 and c["fuentes_sin_licencia"] == ["sano_web"]


def test_reasignacion_estratificada_respeta_proporciones_y_grupos():
    filas = []
    for g in range(100):  # 100 frutos de 2 fotos, cada uno repartido entre train y test
        filas += [{"sha256": f"{g}a", "grupo": f"g{g}", "particion": "train", "clase": "sano"},
                  {"sha256": f"{g}b", "grupo": f"g{g}", "particion": "test", "clase": "sano"}]
    split_v5.reasignar_grupos_estratificado(filas)
    por_grupo = {}
    for f in filas:
        por_grupo.setdefault(f["grupo"], set()).add(f["particion"])
    assert all(len(p) == 1 for p in por_grupo.values())
    from collections import Counter
    c = Counter(f["particion"] for f in filas)
    assert c == {"train": 140, "val": 30, "test": 30}
    otra = [dict(f) for f in filas]
    assert split_v5.reasignar_grupos_estratificado(otra) == []  # idempotente
