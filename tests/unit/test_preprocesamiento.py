import os

from PIL import Image

from avocadoia_datos import inventario, particion, preprocesamiento
from avocadoia_datos.es_csv import leer_csv, sha256_archivo


def _preparar(arbol):
    cfg = arbol.config()
    m = inventario.ejecutar(cfg, arbol.modelo, arbol.salida, arbol.confirmados())[0]
    filas, _ = particion.ejecutar(m, cfg, arbol.salida)
    return cfg, filas, inventario.leer_manifiesto(arbol.salida)


def _destino(arbol):
    return os.path.join(arbol.modelo, "PROCESADO")


def test_salida_rgb_tamano_y_originales_intactos(arbol):
    arbol.agregar("ANTRACNOSIS/rgb_antracnosis_1.jpg", tamano=(200, 100), orientacion=6)
    arbol.agregar("AGUACATESANOS/sano-0001.png", modo="RGBA", tamano=(90, 90))
    original = os.path.join(arbol.modelo, "ANTRACNOSIS/rgb_antracnosis_1.jpg")
    sha, mtime = sha256_archivo(original), os.path.getmtime(original)
    cfg, filas, m = _preparar(arbol)
    r = preprocesamiento.ejecutar(filas, m, cfg, arbol.modelo, _destino(arbol), arbol.salida)
    assert r["procesadas"] == 2
    for f in filas:
        with Image.open(os.path.join(_destino(arbol), f["particion"], f["clase"], f"{f['id_contenido']}.jpg")) as im:
            assert im.size == (32, 32) and im.mode == "RGB" and im.format == "JPEG"
    assert sha256_archivo(original) == sha and os.path.getmtime(original) == mtime


def test_orientacion_exif_aplicada():
    im = Image.new("RGB", (40, 20), (255, 0, 0))
    exif = Image.Exif()
    exif[0x0112] = 6
    im.info["exif"] = exif.tobytes()
    im.getexif()[0x0112] = 6
    assert preprocesamiento.a_rgb(im).size == (20, 40)


def test_transparencia_sobre_blanco():
    im = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    assert preprocesamiento.a_rgb(im).getpixel((0, 0)) == (255, 255, 255)


def test_omite_existentes_forzar_y_limpieza(arbol):
    arbol.agregar("ANTRACNOSIS/rgb_antracnosis_1.jpg")
    cfg, filas, m = _preparar(arbol)
    destino = _destino(arbol)
    preprocesamiento.ejecutar(filas, m, cfg, arbol.modelo, destino, arbol.salida)
    sobrante = os.path.join(destino, "train", "sano", "viejo.jpg")
    os.makedirs(os.path.dirname(sobrante), exist_ok=True)
    Image.new("RGB", (8, 8)).save(sobrante)
    r = preprocesamiento.ejecutar(filas, m, cfg, arbol.modelo, destino, arbol.salida)
    assert r["procesadas"] == 0 and r["existentes"] == 1 and r["eliminadas"] == 1
    assert not os.path.exists(sobrante)
    r = preprocesamiento.ejecutar(filas, m, cfg, arbol.modelo, destino, arbol.salida, forzar=True)
    assert r["procesadas"] == 1


def test_advertencias(arbol):
    arbol.agregar("ANTRACNOSIS/rgb_antracnosis_1.jpg", tamano=(40, 20))  # pequeña y aspecto 2:1 justo
    arbol.agregar("ANTRACNOSIS/rgb_antracnosis_2.jpg", tamano=(150, 50))  # aspecto 3:1
    oscura = os.path.join(arbol.modelo, "ANTRACNOSIS", "rgb_antracnosis_3.jpg")
    Image.new("RGB", (100, 100), (5, 5, 5)).save(oscura)  # oscura y sin bordes (borrosa)
    cfg, filas, m = _preparar(arbol)
    preprocesamiento.ejecutar(filas, m, cfg, arbol.modelo, _destino(arbol), arbol.salida)
    adv = leer_csv(os.path.join(arbol.salida, "advertencias.csv"))
    tipos = {(a["ruta"].split("/")[-1], a["tipo"]) for a in adv}
    assert ("rgb_antracnosis_1.jpg", "pequena") in tipos
    assert ("rgb_antracnosis_2.jpg", "aspecto") in tipos
    assert ("rgb_antracnosis_3.jpg", "oscura") in tipos
    assert ("rgb_antracnosis_3.jpg", "borrosa") in tipos
    assert ("rgb_antracnosis_1.jpg", "aspecto") not in tipos
