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


# --- Spec 003: escenario sintético del split v4 para avocadoia_modelo -------------------------------

FUENTES_MODELO_CSV = """fuente,clase,patron,descripcion,referencia,licencia,uso_academico,particion_origen,regla_grupo,rol
hass,sano,AGUACATESANOS/hass_*,Hass,ref,CC BY 4.0,si,no,ninguna,general
avocare_sano,sano,AGUACATESANOS/avocare_*,avocare,ref,CC BY 4.0,si,no,ninguna,general
herrera_marin,sano,AGUACATESANOS/sano-000[1-9].*|AGUACATESANOS/sano-001[0-7].*,Propias,ref,permiso,si,no,ninguna,general
sano_web,sano,AGUACATESANOS/sano-*,Web,ref,sin licencia,no,no,ninguna,general
avocare_antracnosis,antracnosis,ANTRACNOSIS/avocare_*,avocare,ref,pendiente,pendiente,no,ninguna,general
rgb_antracnosis,antracnosis,ANTRACNOSIS/rgb_*,RGB,ref,CC BY 4.0,si,no,ninguna,general
mdpi_pedunculo,pedunculo,PEDUNCULO/DRIVE_*/*,MDPI,ref,CC BY 4.0,si,si,ninguna,general
"""

DATASET_MODELO_TOML = """semilla = 42
max_por_clase = 100

[proporciones]
train = 0.70
val = 0.15
test = 0.15
"""


class EscenarioModelo:
    """Mini split v4: raíz de imágenes, manifiesto v4, manifiesto de 002, fuentes y modelo.toml."""

    COLUMNAS_V4 = ("ruta_origen", "ruta_destino", "clase_original", "conjunto", "sha256", "estado_etiqueta",
                   "procedencia", "grupo_duplicacion_escena")
    COLUMNAS_002 = ("ruta", "sha256", "fuente", "grupo", "canonica", "estado")

    def __init__(self, base):
        import tomllib
        from avocadoia_datos.es_csv import escribir_csv, sha256_archivo
        self._escribir_csv, self._sha = escribir_csv, sha256_archivo
        self.base = str(base)
        self.raiz = os.path.join(self.base, "v4")
        self.fuentes = os.path.join(self.base, "fuentes.csv")
        self.dataset = os.path.join(self.base, "dataset.toml")
        self.manifiesto_002 = os.path.join(self.base, "manifiesto_002.csv")
        self.manifiesto = os.path.join(self.raiz, "reportes", "manifiesto_split.csv")
        self.repo_datos = os.path.join(self.base, "repo_datos")
        self.salida = os.path.join(self.base, "drive")
        with open(self.fuentes, "w", encoding="utf-8") as fh:
            fh.write(FUENTES_MODELO_CSV)
        with open(self.dataset, "w", encoding="utf-8") as fh:
            fh.write(DATASET_MODELO_TOML)
        with open("config/modelo.toml", "rb") as fh:
            self.cfg = tomllib.load(fh)
        self.cfg["filtros"].update(dataset_002=self.dataset, fuentes_002=self.fuentes,
                                   manifiesto_002=self.manifiesto_002)
        self.cfg["_entorno"] = "pc"
        self.cfg["_rutas"] = {"repo_datos": self.repo_datos, "raiz_imagenes": self.raiz,
                              "manifiesto": self.manifiesto, "salida": self.salida}
        self.filas_v4, self.filas_002 = [], []
        self._semilla = 0

    def agregar(self, ruta_origen, clase, particion, registro_002=None, grupo_002=None, crear=True,
                estado="ETIQUETA_PROVISIONAL", contenido_de=None):
        """Agrega una imagen al v4. registro_002 = fuente con que figura en el manifiesto de 002 (o None)."""
        self._semilla += 1
        nombre = os.path.basename(ruta_origen)
        destino = f"{particion}/{clase}/{nombre}"
        ruta_abs = os.path.join(self.raiz, destino)
        if contenido_de is not None:
            os.makedirs(os.path.dirname(ruta_abs), exist_ok=True)
            with open(contenido_de, "rb") as src, open(ruta_abs, "wb") as dst:
                dst.write(src.read())
        else:
            imagen(ruta_abs, self._semilla, tamano=(96, 64))
        sha = self._sha(ruta_abs)
        if not crear:
            os.remove(ruta_abs)
        self.filas_v4.append({"ruta_origen": ruta_origen, "ruta_destino": destino, "clase_original": clase,
                              "conjunto": particion, "sha256": sha, "estado_etiqueta": estado,
                              "procedencia": "reporte_x.csv", "grupo_duplicacion_escena": f"sha256:{sha}"})
        if registro_002:
            self.filas_002.append({"ruta": ruta_origen, "sha256": sha, "fuente": registro_002,
                                   "grupo": grupo_002 or sha[:16], "canonica": "si", "estado": "provisional"})
        return ruta_abs

    def escribir(self):
        self._escribir_csv(self.manifiesto, self.COLUMNAS_V4, self.filas_v4)
        self._escribir_csv(self.manifiesto_002, self.COLUMNAS_002, self.filas_002)
        return self


@pytest.fixture
def escenario_modelo(tmp_path):
    return EscenarioModelo(tmp_path)
