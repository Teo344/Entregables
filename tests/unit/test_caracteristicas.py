"""Características de imagen del EDA (spec 002, T024). Requiere numpy (.venv-ml)."""

import pytest

pytest.importorskip("numpy")

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402

from avocadoia_datos.etl import caracteristicas  # noqa: E402


def _guardar(tmp_path, nombre, im, exif=None):
    ruta = str(tmp_path / nombre)
    im.save(ruta, "PNG") if exif is None else im.save(ruta, "JPEG", quality=95, exif=exif.tobytes())
    return ruta


def test_imagen_negra_tiene_brillo_cero(tmp_path):
    m = caracteristicas.medir(_guardar(tmp_path, "negra.png", Image.new("RGB", (100, 80))))
    assert float(m["brillo"]) < 0.5 and float(m["contraste"]) < 0.5


def test_tablero_es_mas_nitido_que_su_version_desenfocada(tmp_path):
    tablero = Image.new("RGB", (128, 128), "white")
    d = ImageDraw.Draw(tablero)
    for i in range(0, 128, 8):
        for j in range(0, 128, 8):
            if (i + j) // 8 % 2:
                d.rectangle([i, j, i + 7, j + 7], fill="black")
    nitido = caracteristicas.medir(_guardar(tmp_path, "t.png", tablero))
    borroso = caracteristicas.medir(_guardar(tmp_path, "b.png", tablero.filter(ImageFilter.GaussianBlur(4))))
    assert float(nitido["nitidez"]) > 10 * float(borroso["nitidez"])


def test_fondo_blanco_es_uniforme_y_ruido_es_natural(tmp_path):
    fruto = Image.new("RGB", (200, 200), "white")
    ImageDraw.Draw(fruto).ellipse([50, 40, 150, 160], fill=(60, 120, 40))
    assert caracteristicas.medir(_guardar(tmp_path, "f.png", fruto))["fondo"] == "uniforme"
    ruido = Image.effect_noise((200, 200), 120).convert("RGB")
    assert caracteristicas.medir(_guardar(tmp_path, "r.png", ruido))["fondo"] == "natural"


def test_tono_medio_es_circular(tmp_path):
    im = Image.new("RGB", (100, 100), (255, 0, 0))            # 0°
    ImageDraw.Draw(im).rectangle([50, 0, 99, 99], fill=(255, 0, 255))  # 300°
    tono = float(caracteristicas.medir(_guardar(tmp_path, "h.png", im))["tono_medio"])
    assert abs(tono - 330) < 3  # la media lineal daría 150°


def test_proporcion_respeta_la_orientacion_exif(tmp_path):
    exif = Image.Exif()
    exif[0x0112] = 6
    m = caracteristicas.medir(_guardar(tmp_path, "o.jpg", Image.new("RGB", (120, 60), "gray"), exif))
    assert (m["ancho"], m["alto"]) == (60, 120) and m["proporcion"] == "0.5000"
