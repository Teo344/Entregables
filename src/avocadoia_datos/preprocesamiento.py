"""Preprocesamiento a Modelo/PROCESADO/<particion>/<clase>/<id>.jpg (US4, research D9)."""

import hashlib
import json
import os

from PIL import Image, ImageFilter, ImageOps, ImageStat

from avocadoia_datos.es_csv import escribir_csv

COLUMNAS_ADVERTENCIAS = ("id_contenido", "ruta", "tipo", "valor")
_HUELLA = ".configuracion"
_LAPLACIANO = ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=128)


def huella_configuracion(prepro):
    claves = ("tamano", "calidad_jpeg")
    return hashlib.sha256(json.dumps({k: prepro[k] for k in claves}, sort_keys=True).encode()).hexdigest()


def a_rgb(im):
    """Aplica la orientación EXIF y convierte a RGB, componiendo la transparencia sobre blanco."""
    im = ImageOps.exif_transpose(im)
    if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
        im = im.convert("RGBA")
        fondo = Image.new("RGBA", im.size, (255, 255, 255, 255))
        return Image.alpha_composite(fondo, im).convert("RGB")
    return im.convert("RGB")


def cargar_224(origen, tamano):
    """La misma transformación que procesar_imagen, en memoria (EXIF → RGB → tamano × tamano)."""
    with Image.open(origen) as im:
        return a_rgb(im).resize((tamano, tamano), Image.LANCZOS)


def procesar_imagen(origen, destino, tamano, calidad):
    salida = cargar_224(origen, tamano)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    salida.save(destino, "JPEG", quality=calidad)
    return salida


def medir_calidad(im):
    """(brillo medio, varianza del laplaciano) sobre la imagen procesada en escala de grises."""
    gris = im.convert("L")
    brillo = ImageStat.Stat(gris).mean[0]
    # Pillow no filtra el borde de 1 px: se recorta para que no infle la varianza.
    filtrada = gris.filter(_LAPLACIANO)
    nitidez = ImageStat.Stat(filtrada.crop((1, 1, filtrada.width - 1, filtrada.height - 1))).var[0]
    return brillo, nitidez


def ejecutar(particion, manifiesto, config, raiz_imagenes, destino, salida, forzar=False):
    prepro = config.preprocesamiento
    tamano, calidad = int(prepro["tamano"]), int(prepro["calidad_jpeg"])
    huella = huella_configuracion(prepro)
    ruta_huella = os.path.join(destino, _HUELLA)
    if os.path.exists(ruta_huella):
        with open(ruta_huella, encoding="utf-8") as fh:
            if fh.read().strip() != huella:
                forzar = True
    dims = {f["id_contenido"]: (f["ancho"], f["alto"]) for f in manifiesto if f["canonica"] == "si"}

    esperados = set()
    advertencias = []
    nuevos = 0
    for fila in particion:
        archivo = os.path.join(destino, fila["particion"], fila["clase"], f"{fila['id_contenido']}.jpg")
        esperados.add(os.path.normcase(os.path.abspath(archivo)))
        if forzar or not os.path.exists(archivo):
            im = procesar_imagen(os.path.join(raiz_imagenes, fila["ruta"]), archivo, tamano, calidad)
            nuevos += 1
        else:
            with Image.open(archivo) as abierta:
                im = abierta.convert("RGB")
        advertencias += _advertencias(fila, dims.get(fila["id_contenido"]), im, prepro)

    eliminados = 0
    for raiz, _, archivos in os.walk(destino):
        for nombre in archivos:
            ruta = os.path.join(raiz, nombre)
            if nombre.lower().endswith(".jpg") and os.path.normcase(os.path.abspath(ruta)) not in esperados:
                os.remove(ruta)
                eliminados += 1

    os.makedirs(destino, exist_ok=True)
    with open(ruta_huella, "w", encoding="utf-8") as fh:
        fh.write(huella + "\n")
    advertencias.sort(key=lambda a: (a["tipo"], a["id_contenido"]))
    escribir_csv(os.path.join(salida, "advertencias.csv"), COLUMNAS_ADVERTENCIAS, advertencias)
    return {"procesadas": nuevos, "existentes": len(particion) - nuevos, "eliminadas": eliminados,
            "advertencias": len(advertencias)}


def _advertencias(fila, dims, im, prepro):
    resultado = []

    def agregar(tipo, valor):
        resultado.append({"id_contenido": fila["id_contenido"], "ruta": fila["ruta"], "tipo": tipo, "valor": valor})

    if dims and dims[0] and dims[1]:
        ancho, alto = int(dims[0]), int(dims[1])
        if min(ancho, alto) < int(prepro.get("lado_minimo", 224)):
            agregar("pequena", f"{ancho}x{alto}")
        if max(ancho, alto) / min(ancho, alto) > float(prepro.get("aspecto_maximo", 2.0)):
            agregar("aspecto", f"{max(ancho, alto) / min(ancho, alto):.2f}")
    brillo, nitidez = medir_calidad(im)
    if brillo < float(prepro.get("umbral_brillo", 40)):
        agregar("oscura", f"{brillo:.1f}")
    if nitidez < float(prepro.get("umbral_borrosidad", 50)):
        agregar("borrosa", f"{nitidez:.1f}")
    return resultado
