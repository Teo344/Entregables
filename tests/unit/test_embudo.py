"""Embudo de calidad y comparación con 001 (spec 002, T037)."""

from avocadoia_datos.etl import embudo


def _fila(i, estado, clase="sano", fuente="hass", en_muestra="no", propuesta=None):
    return {"id_contenido": i, "estado": estado, "clase_efectiva": clase, "clase_propuesta": propuesta or clase,
            "fuente": fuente, "en_muestra": en_muestra}


def test_cada_imagen_cae_en_un_solo_paso_y_el_embudo_cuadra():
    manifiesto = [
        _fila("a", "excluida_invalida"), _fila("b", "duplicada"), _fila("c", "excluida_conflicto"),
        _fila("d", "excluida_licencia", fuente="sano_web"), _fila("e", "excluida_revision"), _fila("f", "rechazada"),
        _fila("g", "test_campo", fuente="campo"), _fila("h", "provisional"), _fila("i", "provisional", en_muestra="si"),
        _fila("j", "elegible", en_muestra="si"),
    ]
    assert [embudo.paso_de(f) for f in manifiesto] == [
        "invalida", "duplicada", "conflicto_clase", "excluida_licencia", "excluida_revision", "rechazada",
        "test_campo", "fuera_de_cuota", "conjunto_final", "conjunto_final"]
    filas = embudo.calcular_embudo(manifiesto)
    assert embudo.verificar_embudo(filas) == []
    hass = {f["paso"]: f["imagenes"] for f in filas if f["fuente"] == "hass"}
    assert hass["inventariadas"] == 8 and hass["conjunto_final"] == 2


def test_descuadre_detectado():
    filas = [{"paso": "inventariadas", "clase": "sano", "fuente": "hass", "imagenes": 5},
             {"paso": "conjunto_final", "clase": "sano", "fuente": "hass", "imagenes": 4}]
    assert embudo.verificar_embudo(filas) == [("sano", "hass")]


def test_reasignada_cuenta_en_su_clase_final():
    filas = embudo.calcular_embudo([_fila("a", "provisional", clase="sano", propuesta="antracnosis", en_muestra="si")])
    assert {(f["paso"], f["clase"]) for f in filas} == {("inventariadas", "sano"), ("conjunto_final", "sano")}


def test_comparacion_con_001_detecta_las_cinco_categorias():
    antes = [{"id_contenido": "sale", "clase": "sano", "particion": "train"},
             {"id_contenido": "clase", "clase": "antracnosis", "particion": "val"},
             {"id_contenido": "conj", "clase": "sano", "particion": "val"},
             {"id_contenido": "igual", "clase": "pedunculo", "particion": "test"}]
    despues = [{"id_contenido": "entra", "clase": "sano", "particion": "train"},
               {"id_contenido": "clase", "clase": "sano", "particion": "val"},
               {"id_contenido": "conj", "clase": "sano", "particion": "test"},
               {"id_contenido": "igual", "clase": "pedunculo", "particion": "test"}]
    cambios = {f["id_contenido"]: f["cambio"] for f in embudo.comparar_con_001(antes, despues)}
    assert cambios == {"sale": "sale", "entra": "entra", "clase": "cambia_clase", "conj": "cambia_conjunto",
                       "igual": "igual"}
