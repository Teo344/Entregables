"""ETL de las fotos de campo (CAMPO_SIGCHOS) con las reglas de 002."""

import os

from PIL import Image

from avocadoia_datos import config as config_002

from conftest import DATASET_MODELO_TOML, FUENTES_MODELO_CSV, imagen

from avocadoia_modelo import campo

FUENTES = FUENTES_MODELO_CSV + (
    "campo_sigchos_pedunculo,pedunculo,CAMPO_SIGCHOS/PEDUNCULO/*,Campo,GAD,propia,si,no,ninguna,test_campo\n")
PREPRO = {"tamano": 224, "lado_minimo": 224, "aspecto_maximo": 2.0, "umbral_brillo": 40, "umbral_borrosidad": 50}


def _cfg(tmp_path):
    (tmp_path / "fuentes.csv").write_text(FUENTES, encoding="utf-8")
    (tmp_path / "dataset.toml").write_text(DATASET_MODELO_TOML, encoding="utf-8")
    return config_002.cargar(str(tmp_path / "dataset.toml"), str(tmp_path / "fuentes.csv"))


def test_inventario_campo(tmp_path):
    raiz = tmp_path / "Modelo"
    ped = raiz / "CAMPO_SIGCHOS" / "PEDUNCULO"
    a = imagen(str(ped / "IMG_0001.jpg"), 1, tamano=(300, 400))
    with Image.open(a) as im:                       # casi duplicado: misma foto un poco recortada
        im.crop((5, 5, 295, 395)).save(ped / "IMG_0002.jpg", quality=90)
    imagen(str(ped / "IMG_0003.jpg"), 3, tamano=(300, 400))
    imagen(str(ped / "IMG_0004.jpg"), 4, tamano=(120, 160))        # demasiado pequeña
    dup = imagen(str(ped / "IMG_0005.jpg"), 5, tamano=(300, 400))  # ya existe en 002
    (ped / "IMG_0006.HEIC").write_bytes(b"heic original")          # se ignora (se usa su JPG)
    from avocadoia_datos.es_csv import sha256_archivo
    por_sha = {sha256_archivo(dup): {"ruta": "PEDUNCULO/DRIVE_X/r.jpg"}}

    filas = campo.inventariar(str(raiz), _cfg(tmp_path), por_sha, PREPRO)
    por_nombre = {os.path.basename(f["ruta"]): f for f in filas}
    assert set(por_nombre) == {"IMG_0001.jpg", "IMG_0002.jpg", "IMG_0003.jpg", "IMG_0004.jpg", "IMG_0005.jpg"}
    assert por_nombre["IMG_0001.jpg"]["estado"] == "test_campo"
    assert por_nombre["IMG_0001.jpg"]["fuente"] == "campo_sigchos_pedunculo"
    assert por_nombre["IMG_0001.jpg"]["licencia"] == "propia"
    assert por_nombre["IMG_0004.jpg"]["motivo"] == "calidad:lado_minimo"
    assert por_nombre["IMG_0005.jpg"]["motivo"] == "duplicada_de_002"
    assert por_nombre["IMG_0001.jpg"]["grupo_similitud"] == por_nombre["IMG_0002.jpg"]["grupo_similitud"]
    assert por_nombre["IMG_0001.jpg"]["grupo_similitud"] != por_nombre["IMG_0003.jpg"]["grupo_similitud"]
    assert all(f["validacion"] == "pendiente" for f in filas)

    res = campo.escribir(filas, str(tmp_path / "salida"))
    assert res["test_campo"] == 3 and res["rechazadas"] == {"calidad:lado_minimo": 1, "duplicada_de_002": 1}
    assert os.path.exists(tmp_path / "salida" / "manifiesto_campo.csv")


def test_tabla_comparativa():
    caract = [{"id_contenido": "a", "brillo": "50", "contraste": "10", "nitidez": "20", "saturacion": "0.2",
               "tono_medio": "90", "fondo_fraccion": "0.9", "megapixeles": "2", "fondo": "uniforme"}]
    man = [{"id_contenido": "a", "fuente": "mdpi_pedunculo"}]
    campo_f = [{**caract[0], "brillo": "70", "fondo": "natural", "estado": "test_campo"}]
    tabla, grupos = campo.tabla_comparativa(campo_f, caract, man, ("mdpi_pedunculo",))
    assert [t["grupo"] for t in tabla] == ["mdpi_pedunculo", "campo_sigchos (propias)"]
    assert tabla[1]["brillo_mediana"] == 70.0 and tabla[1]["fondo_uniforme_pct"] == 0.0


def test_metricas_campo_sensibilidad():
    import numpy as np

    y = np.array([2, 2, 2, 2])
    probs = np.array([[0.1, 0.1, 0.8], [0.7, 0.2, 0.1], [0.2, 0.75, 0.05], [0.4, 0.35, 0.25]])
    m = campo.metricas_campo(y, probs, umbral=0.6)
    assert m["predicciones"] == {"sano": 2, "antracnosis": 1, "pedunculo": 1}
    assert m["por_clase"]["pedunculo"]["sensibilidad"] == 0.25
    assert m["por_clase"]["pedunculo"]["confundida_con"] == {"sano": 2, "antracnosis": 1}
    assert m["no_concluyentes"] == 1 and list(m["por_clase"]) == ["pedunculo"]
