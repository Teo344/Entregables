from avocadoia_datos import grupos


def _fila(ruta, id_, regla="ninguna"):
    return {"ruta": ruta, "id_contenido": id_, "regla_grupo": regla}


def test_regla_hass_ignora_dia_y_lado():
    assert grupos.grupo_por_regla("hass_T10_d01_041_a_1_abc.jpg", "hass") == "hass:T10:041"
    assert grupos.grupo_por_regla("hass_T10_d05_041_b_3_def.jpg", "hass") == "hass:T10:041"
    assert grupos.grupo_por_regla("hass_T20_d01_041_a_1_abc.jpg", "hass") == "hass:T20:041"
    assert grupos.grupo_por_regla("hass_Tam_d02_019_a_1_abc.jpg", "hass") == "hass:Tam:019"
    assert grupos.grupo_por_regla("sano-0001.jpg", "hass") is None
    assert grupos.grupo_por_regla("hass_T10_d01_041_a_1_abc.jpg", "ninguna") is None


def test_union_con_confirmados_transitiva():
    filas = [_fila("A/a.jpg", "aaa"), _fila("A/b.jpg", "bbb"), _fila("A/c.jpg", "ccc"), _fila("A/d.jpg", "ddd")]
    confirmados = {"G001": ["A/a.jpg", "A/b.jpg"], "G002": ["A/b.jpg", "A/c.jpg"], "G003": ["A/x.jpg", "A/d.jpg"]}
    g = grupos.asignar_grupos(filas, confirmados)
    assert g["A/a.jpg"] == g["A/b.jpg"] == g["A/c.jpg"] == "aaa"
    assert g["A/d.jpg"] == "ddd"  # la otra ruta del grupo ya no existe


def test_hass_y_sin_regla():
    filas = [_fila("S/hass_T10_d01_041_a_1_x.jpg", "i1", "hass"),
             _fila("S/hass_T10_d07_041_b_2_y.jpg", "i2", "hass"),
             _fila("S/hass_T20_d01_041_a_1_z.jpg", "i3", "hass"),
             _fila("S/sano-0001.jpg", "i4")]
    g = grupos.asignar_grupos(filas, {})
    assert g["S/hass_T10_d01_041_a_1_x.jpg"] == g["S/hass_T10_d07_041_b_2_y.jpg"] == "hass:T10:041"
    assert g["S/hass_T20_d01_041_a_1_z.jpg"] == "hass:T20:041"
    assert g["S/sano-0001.jpg"] == "i4"


def test_inventario_une_grupos_de_similitud(arbol):
    import os
    from avocadoia_datos import inventario
    from avocadoia_datos.es_csv import escribir_csv
    for i in range(3):
        arbol.agregar(f"ANTRACNOSIS/Avocado {i:04d}.jpg")
    escribir_csv(os.path.join(arbol.salida, "curacion", "grupos_similitud.csv"), ["grupo", "ruta"],
                 [{"grupo": "S0001", "ruta": "ANTRACNOSIS/Avocado 0000.jpg"},
                  {"grupo": "S0001", "ruta": "ANTRACNOSIS/Avocado 0002.jpg"}])
    filas, _ = inventario.ejecutar(arbol.config(), arbol.modelo, arbol.salida, arbol.confirmados())
    g = {f["ruta"]: f["grupo"] for f in filas}
    assert g["ANTRACNOSIS/Avocado 0000.jpg"] == g["ANTRACNOSIS/Avocado 0002.jpg"]
    assert g["ANTRACNOSIS/Avocado 0001.jpg"] != g["ANTRACNOSIS/Avocado 0000.jpg"]


def test_copias_exactas_comparten_grupo():
    filas = [_fila("S/a.jpg", "mismo"), _fila("S/b.jpg", "mismo")]
    g = grupos.asignar_grupos(filas, {})
    assert g["S/a.jpg"] == g["S/b.jpg"]
