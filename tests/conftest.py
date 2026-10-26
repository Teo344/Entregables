"""Fábrica de árboles Modelo/ sintéticos para las pruebas."""

import os
import random

import pytest
from PIL import Image

from avocadoia_datos import config as mod_config

FUENTES_CSV = """fuente,clase,patron,descripcion,referencia,licencia,uso_academico,particion_origen,regla_grupo,rol
mdpi_sano,sano,AGUACATESANOS/DRIVE_*/*,MDPI sano,ref,CC-BY-4.0,si,si,ninguna,general
hass,sano,AGUACATESANOS/hass_*,Hass,ref,pendiente,pendiente,no,hass,general
web,sano,AGUACATESANOS/sano-*,Web,ref,pendiente,pendiente,no,ninguna,general
kaggle,antracnosis,ANTRACNOSIS/Avocado *,Kaggle,ref,pendiente,pendiente,no,ninguna,general
rgb,antracnosis,ANTRACNOSIS/rgb_*,RGB,ref,CC-BY-4.0,si,no,ninguna,general
mdpi_ped,pedunculo,PEDUNCULO/DRIVE_*/*,MDPI pedunculo,ref,CC-BY-4.0,si,si,ninguna,general
campo,sano,CAMPO_SIGCHOS/AGUACATESANOS/*,Campo,GAD,propia,si,no,ninguna,test_campo
"""

DATASET_TOML = """semilla = 42
max_por_clase = 100

[proporciones]
train = 0.70
val = 0.15
test = 0.15

[cuotas.sano]
mdpi_sano = 20
hass = 20
web = 10

[cuotas.antracnosis]
kaggle = 25
rgb = 25

[cuotas.pedunculo]
mdpi_ped = 40

[preprocesamiento]
tamano = 32
calidad_jpeg = 90
umbral_brillo = 40
umbral_borrosidad = 50
lado_minimo = 64
aspecto_maximo = 2.0

[aumento]
rotacion_grados = 45
desplazamiento = 0.2
zoom = 0.2
volteo_horizontal = true
volteo_vertical = true
brillo = [0.8, 1.2]

[planilla]
lote = 10
"""


def imagen(ruta, semilla, tamano=(80, 60), modo="RGB", orientacion=None):
    """Imagen con ruido determinista (contenido distinto por semilla)."""
    rng = random.Random(semilla)
    canales = len(modo)
    datos = bytes(rng.randrange(256) for _ in range(tamano[0] * tamano[1] * canales))
    im = Image.frombytes(modo, tamano, datos)
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    if ruta.lower().endswith(".png"):
        im.save(ruta, "PNG")
    else:
        exif = Image.Exif()
        if orientacion:
            exif[0x0112] = orientacion
        im.convert("RGB").save(ruta, "JPEG", quality=90, exif=exif.tobytes())
    return ruta


class Arbol:
    def __init__(self, base):
        self.base = str(base)
        self.modelo = os.path.join(self.base, "Modelo")
        self.salida = os.path.join(self.base, "datos")
        self.config_dir = os.path.join(self.base, "config")
        os.makedirs(self.config_dir, exist_ok=True)
        self.toml = os.path.join(self.config_dir, "dataset.toml")
        self.fuentes = os.path.join(self.config_dir, "fuentes.csv")
        with open(self.toml, "w", encoding="utf-8") as fh:
            fh.write(DATASET_TOML)
        with open(self.fuentes, "w", encoding="utf-8") as fh:
            fh.write(FUENTES_CSV)
        self._semilla = 0

    def agregar(self, relativa, **kw):
        self._semilla += 1
        return imagen(os.path.join(self.modelo, relativa), kw.pop("semilla", self._semilla), **kw)

    def copiar(self, origen_rel, destino_rel):
        destino = os.path.join(self.modelo, destino_rel)
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(os.path.join(self.modelo, origen_rel), "rb") as a, open(destino, "wb") as b:
            b.write(a.read())

    def config(self):
        return mod_config.cargar(self.toml, self.fuentes)

    def args(self, *extra):
        return [*extra, "--config", self.toml, "--fuentes", self.fuentes,
                "--raiz-imagenes", self.modelo, "--salida", self.salida]

    def confirmados(self):
        return os.path.join(self.salida, "curacion", "casi_duplicados_confirmados.csv")


@pytest.fixture
def arbol(tmp_path):
    return Arbol(tmp_path)


@pytest.fixture
def arbol_completo(arbol):
    """Árbol con las tres clases, particiones de origen, grupos hass y una fuente web."""
    for i, p in enumerate(["train"] * 14 + ["val"] * 3 + ["test"] * 3):
        arbol.agregar(f"AGUACATESANOS/DRIVE_PARTICIONES_ARTICULO/{p}/s{i:03d}.jpg")
    for fruto in range(15):
        for dia in (1, 2):
            arbol.agregar(f"AGUACATESANOS/hass_T10_d{dia:02d}_{fruto:03d}_a_1_x{fruto}{dia}.jpg")
    for i in range(12):
        arbol.agregar(f"AGUACATESANOS/sano-{i:04d}.jpg")
    for i in range(30):
        arbol.agregar(f"ANTRACNOSIS/Avocado {i:04d}.jpg")
    for i in range(30):
        arbol.agregar(f"ANTRACNOSIS/rgb_antracnosis_{i:04d}.jpg")
    for i, p in enumerate(["train"] * 26 + ["val"] * 5 + ["test"] * 5):
        arbol.agregar(f"PEDUNCULO/DRIVE_PARTICIONES_ARTICULO/{p}/r{i:03d}.jpg")
    for i in range(4):
        arbol.agregar(f"PEDUNCULO/DRIVE_CANDIDATAS/c{i:03d}.jpg")
    return arbol
