"""Características de las imágenes originales para el EDA (spec 002, US3, research E6)."""

import math
import os

import numpy as np
from PIL import Image

from avocadoia_datos import muestra
from avocadoia_datos.es_csv import escribir_csv, leer_csv
from avocadoia_datos.preprocesamiento import a_rgb, medir_calidad

COLUMNAS = ("id_contenido", "ancho", "alto", "megapixeles", "proporcion", "brillo", "contraste", "nitidez",
            "tono_medio", "tono_dispersion", "saturacion", "valor", "fondo_fraccion", "fondo")
LADO_ANALISIS = 512
BORDE = 0.08
UMBRAL_FONDO = 0.6
_ROTADAS = (5, 6, 7, 8)


def _l_estrella(rgb):
    """L* (CIELAB, iluminante D65) de un arreglo sRGB 0–255."""
    c = rgb / 255.0
    lineal = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    y = lineal @ np.array([0.2126, 0.7152, 0.0722])
    f = np.where(y > (6 / 29) ** 3, np.cbrt(y), y / (3 * (6 / 29) ** 2) + 4 / 29)
    return 116 * f - 16


def fraccion_fondo(rgb, hsv):
    """Fracción del borde exterior (8 %) que es blanco o de un color uniforme."""
    h, w = rgb.shape[:2]
    by, bx = max(1, round(h * BORDE)), max(1, round(w * BORDE))
    mascara = np.zeros((h, w), dtype=bool)
    mascara[:by], mascara[-by:], mascara[:, :bx], mascara[:, -bx:] = True, True, True, True
    s, v = hsv[..., 1][mascara] / 255.0, hsv[..., 2][mascara] / 255.0
    blanco = (s < 0.12) & (v > 0.85)
    borde = rgb[mascara].astype(float)
    uniforme = np.abs(borde - np.median(borde, axis=0)).max(axis=1) < 20
    return float((blanco | uniforme).mean())


def medir(ruta):
    with Image.open(ruta) as im:
        orientacion = im.getexif().get(0x0112, 1)
        ancho, alto = im.size if orientacion not in _ROTADAS else im.size[::-1]
        im.draft("RGB", (LADO_ANALISIS * 2, LADO_ANALISIS * 2))
        rgb_im = a_rgb(im)
    rgb_im.thumbnail((LADO_ANALISIS, LADO_ANALISIS), Image.LANCZOS)
    rgb = np.asarray(rgb_im, dtype=float)
    hsv = np.asarray(rgb_im.convert("HSV"), dtype=float)
    l = _l_estrella(rgb)
    angulos = hsv[..., 0] / 256.0 * 2 * math.pi
    seno, coseno = np.sin(angulos).mean(), np.cos(angulos).mean()
    tono = math.degrees(math.atan2(seno, coseno)) % 360
    fondo = fraccion_fondo(rgb, hsv)
    return {
        "ancho": ancho, "alto": alto, "megapixeles": f"{ancho * alto / 1e6:.4f}", "proporcion": f"{ancho / alto:.4f}",
        "brillo": f"{l.mean():.4f}", "contraste": f"{l.std():.4f}", "nitidez": f"{medir_calidad(rgb_im)[1]:.4f}",
        "tono_medio": f"{tono:.4f}", "tono_dispersion": f"{1 - math.hypot(seno, coseno):.4f}",
        "saturacion": f"{hsv[..., 1].mean() / 255:.4f}", "valor": f"{hsv[..., 2].mean() / 255:.4f}",
        "fondo_fraccion": f"{fondo:.4f}", "fondo": "uniforme" if fondo >= UMBRAL_FONDO else "natural",
    }


def objetivo(manifiesto):
    """Imágenes a medir: las candidatas y las de la prueba de campo."""
    filas = muestra.candidatas(manifiesto) + [f for f in manifiesto if f["canonica"] == "si" and f["estado"] == "test_campo"]
    return sorted(filas, key=lambda f: f["id_contenido"])


def ejecutar(manifiesto, raiz_imagenes, salida):
    """Escribe datos/eda/tablas/caracteristicas.csv reutilizando las filas ya medidas."""
    ruta = os.path.join(salida, "eda", "tablas", "caracteristicas.csv")
    previas = {f["id_contenido"]: f for f in leer_csv(ruta)}
    filas, nuevas = [], 0
    for f in objetivo(manifiesto):
        if f["id_contenido"] in previas:
            filas.append(previas[f["id_contenido"]])
        else:
            filas.append({"id_contenido": f["id_contenido"], **medir(os.path.join(raiz_imagenes, f["ruta"]))})
            nuevas += 1
    escribir_csv(ruta, COLUMNAS, filas)
    return {"imagenes": len(filas), "medidas": nuevas}
