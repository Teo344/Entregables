import os

from avocadoia_datos import inventario
from avocadoia_datos.es_csv import escribir_csv, sha256_archivo


def _por_ruta(filas):
    return {f["ruta"]: f for f in filas}


def _ejecutar(arbol):
    return inventario.ejecutar(arbol.config(), arbol.modelo, arbol.salida, arbol.confirmados())


def test_una_fila_por_archivo_e_ignora_otros(arbol):
    arbol.agregar("AGUACATESANOS/sano-0001.jpg")
    arbol.agregar("ANTRACNOSIS/rgb_antracnosis_1.png")
    os.makedirs(os.path.join(arbol.modelo, "PEDUNCULO"), exist_ok=True)
    open(os.path.join(arbol.modelo, "PEDUNCULO", "desktop.ini"), "w").close()
    arbol.agregar("PORCLASIFICAR/x.jpg")
    filas, meta = _ejecutar(arbol)
    assert [f["ruta"] for f in filas] == ["AGUACATESANOS/sano-0001.jpg", "ANTRACNOSIS/rgb_antracnosis_1.png"]
    assert meta["total_archivos"] == 2


def test_duplicado_exacto_y_conflicto(arbol):
    arbol.agregar("AGUACATESANOS/sano-0002.jpg", semilla=7)
    arbol.copiar("AGUACATESANOS/sano-0002.jpg", "AGUACATESANOS/sano-0001.jpg")
    arbol.agregar("AGUACATESANOS/sano-0010.jpg", semilla=8)
    arbol.copiar("AGUACATESANOS/sano-0010.jpg", "ANTRACNOSIS/rgb_antracnosis_9.jpg")
    f = _por_ruta(_ejecutar(arbol)[0])
    assert f["AGUACATESANOS/sano-0001.jpg"]["canonica"] == "si"
    assert f["AGUACATESANOS/sano-0002.jpg"]["estado"] == "duplicada"
    assert f["AGUACATESANOS/sano-0002.jpg"]["duplicado_de"] == "AGUACATESANOS/sano-0001.jpg"
    assert f["AGUACATESANOS/sano-0010.jpg"]["estado"] == "excluida_conflicto"
    assert f["ANTRACNOSIS/rgb_antracnosis_9.jpg"]["estado"] == "excluida_conflicto"


def test_archivo_corrupto(arbol):
    ruta = os.path.join(arbol.modelo, "AGUACATESANOS", "sano-0001.jpg")
    os.makedirs(os.path.dirname(ruta))
    with open(ruta, "wb") as fh:
        fh.write(b"no es una imagen")
    f = _por_ruta(_ejecutar(arbol)[0])
    assert f["AGUACATESANOS/sano-0001.jpg"]["estado"] == "excluida_invalida"


def test_dimensiones_con_exif_y_modo(arbol):
    arbol.agregar("ANTRACNOSIS/rgb_antracnosis_1.jpg", tamano=(200, 100), orientacion=6)
    arbol.agregar("AGUACATESANOS/sano-0001.png", modo="RGBA")
    f = _por_ruta(_ejecutar(arbol)[0])
    rot = f["ANTRACNOSIS/rgb_antracnosis_1.jpg"]
    assert (rot["ancho"], rot["alto"]) == (100, 200)
    assert f["AGUACATESANOS/sano-0001.png"]["modo"] == "RGBA"
    assert f["AGUACATESANOS/sano-0001.png"]["formato"] == "PNG"


def test_fuente_particion_de_origen_y_estado(arbol):
    arbol.agregar("PEDUNCULO/DRIVE_PARTICIONES_ARTICULO/val/r1.jpg")
    arbol.agregar("PEDUNCULO/DRIVE_CANDIDATAS/c1.jpg")
    arbol.agregar("ANTRACNOSIS/desconocida.jpg")
    arbol.agregar("CAMPO_SIGCHOS/AGUACATESANOS/campo1.jpg")
    f = _por_ruta(_ejecutar(arbol)[0])
    assert f["PEDUNCULO/DRIVE_PARTICIONES_ARTICULO/val/r1.jpg"]["particion_origen"] == "val"
    assert f["PEDUNCULO/DRIVE_CANDIDATAS/c1.jpg"]["particion_origen"] == ""
    assert f["PEDUNCULO/DRIVE_CANDIDATAS/c1.jpg"]["estado"] == "provisional"
    assert f["ANTRACNOSIS/desconocida.jpg"]["fuente"] == "desconocida"
    assert f["CAMPO_SIGCHOS/AGUACATESANOS/campo1.jpg"]["estado"] == "test_campo"


def test_decisiones_del_experto(arbol):
    arbol.agregar("PEDUNCULO/DRIVE_CANDIDATAS/c1.jpg")
    arbol.agregar("PEDUNCULO/DRIVE_CANDIDATAS/c2.jpg")
    arbol.agregar("PEDUNCULO/DRIVE_CANDIDATAS/c3.jpg")
    f = _por_ruta(_ejecutar(arbol)[0])
    ids = [f[f"PEDUNCULO/DRIVE_CANDIDATAS/c{i}.jpg"]["id_contenido"] for i in (1, 2, 3)]
    escribir_csv(os.path.join(arbol.salida, "validacion", "decisiones.csv"),
                 ["id_contenido", "decision", "clase_nueva", "validador", "fecha"],
                 [{"id_contenido": ids[0], "decision": "rechazada", "validador": "e", "fecha": "2026-10-20"},
                  {"id_contenido": ids[0], "decision": "aceptada", "validador": "e", "fecha": "2026-10-21"},
                  {"id_contenido": ids[1], "decision": "reasignada", "clase_nueva": "antracnosis",
                   "validador": "e", "fecha": "2026-10-21"},
                  {"id_contenido": ids[2], "decision": "mixto", "validador": "e", "fecha": "2026-10-21"},
                  {"id_contenido": "ffffffffffffffff", "decision": "aceptada", "validador": "e",
                   "fecha": "2026-10-21"}])
    filas, meta = _ejecutar(arbol)
    f = _por_ruta(filas)
    assert f["PEDUNCULO/DRIVE_CANDIDATAS/c1.jpg"]["validacion"] == "aceptada"
    assert f["PEDUNCULO/DRIVE_CANDIDATAS/c1.jpg"]["estado"] == "elegible"  # licencia CC-BY en la prueba
    assert f["PEDUNCULO/DRIVE_CANDIDATAS/c2.jpg"]["clase_efectiva"] == "antracnosis"
    assert f["PEDUNCULO/DRIVE_CANDIDATAS/c2.jpg"]["clase_propuesta"] == "pedunculo"
    assert f["PEDUNCULO/DRIVE_CANDIDATAS/c3.jpg"]["estado"] == "rechazada"
    assert meta["decisiones_ausentes"] == ["ffffffffffffffff"]


def test_idempotente_y_no_modifica_originales(arbol_completo):
    arbol = arbol_completo
    antes = {}
    for raiz, _, archivos in os.walk(arbol.modelo):
        for n in archivos:
            r = os.path.join(raiz, n)
            antes[r] = (sha256_archivo(r), os.path.getmtime(r))
    _ejecutar(arbol)
    primero = open(os.path.join(arbol.salida, "manifiesto.csv"), "rb").read()
    _ejecutar(arbol)
    assert open(os.path.join(arbol.salida, "manifiesto.csv"), "rb").read() == primero
    for r, (sha, mtime) in antes.items():
        assert sha256_archivo(r) == sha and os.path.getmtime(r) == mtime
