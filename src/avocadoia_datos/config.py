"""Carga y validación de config/dataset.toml y config/fuentes.csv."""

import hashlib
import tomllib
from dataclasses import dataclass, field
from fnmatch import fnmatchcase

from avocadoia_datos.clases import CLASES, PARTICIONES
from avocadoia_datos.es_csv import leer_csv

USO_ACADEMICO = ("si", "no", "pendiente")
SI_NO = ("si", "no")
REGLAS_GRUPO = ("ninguna", "hass")
ROLES = ("general", "test_campo")

COLUMNAS_FUENTES = ("fuente", "clase", "patron", "descripcion", "referencia", "licencia",
                    "uso_academico", "particion_origen", "regla_grupo", "rol")


class ErrorConfig(Exception):
    """Configuración o registro de fuentes inválido (código de salida 1)."""


class ErrorPrecondicion(Exception):
    """Precondición incumplida, p. ej. falta el manifiesto (código de salida 2)."""


@dataclass(frozen=True)
class Fuente:
    fuente: str
    clase: str
    patron: str
    descripcion: str
    referencia: str
    licencia: str
    uso_academico: str
    particion_origen: str
    regla_grupo: str
    rol: str


@dataclass
class Config:
    semilla: int
    max_por_clase: int
    proporciones: dict
    cuotas: dict
    preprocesamiento: dict
    aumento: dict
    planilla: dict
    fuentes: list = field(default_factory=list)
    version_config: str = ""

    def fuente_de(self, ruta_relativa):
        """Primera fuente cuyo patrón coincide con la ruta relativa a Modelo/ (o None)."""
        for fuente in self.fuentes:
            if fnmatchcase(ruta_relativa, fuente.patron):
                return fuente
        return None

    def fuente_por_nombre(self, nombre):
        for fuente in self.fuentes:
            if fuente.fuente == nombre:
                return fuente
        return None


def cargar(ruta_toml, ruta_fuentes):
    try:
        with open(ruta_toml, "rb") as fh:
            bruto_toml = fh.read()
        datos = tomllib.loads(bruto_toml.decode("utf-8"))
    except FileNotFoundError as e:
        raise ErrorConfig(f"No existe {ruta_toml}") from e
    except tomllib.TOMLDecodeError as e:
        raise ErrorConfig(f"{ruta_toml}: {e}") from e
    try:
        with open(ruta_fuentes, "rb") as fh:
            bruto_fuentes = fh.read()
    except FileNotFoundError as e:
        raise ErrorConfig(f"No existe {ruta_fuentes}") from e

    fuentes = _cargar_fuentes(ruta_fuentes)
    config = Config(
        semilla=int(datos.get("semilla", 42)),
        max_por_clase=int(datos.get("max_por_clase", 1000)),
        proporciones={p: float(datos.get("proporciones", {}).get(p, 0)) for p in PARTICIONES},
        cuotas={c: {k: int(v) for k, v in datos.get("cuotas", {}).get(c, {}).items()} for c in CLASES},
        preprocesamiento=dict(datos.get("preprocesamiento", {})),
        aumento=dict(datos.get("aumento", {})),
        planilla=dict(datos.get("planilla", {})),
        fuentes=fuentes,
        version_config=hashlib.sha256(bruto_toml + b"\0" + bruto_fuentes).hexdigest(),
    )
    _validar(config)
    return config


def _cargar_fuentes(ruta):
    filas = leer_csv(ruta)
    if filas and set(COLUMNAS_FUENTES) - set(filas[0].keys()):
        faltan = sorted(set(COLUMNAS_FUENTES) - set(filas[0].keys()))
        raise ErrorConfig(f"{ruta}: faltan columnas {faltan}")
    fuentes = []
    for n, fila in enumerate(filas, start=2):
        valores = {c: (fila.get(c) or "").strip() for c in COLUMNAS_FUENTES}
        for columna, permitidos in (("uso_academico", USO_ACADEMICO), ("particion_origen", SI_NO),
                                    ("regla_grupo", REGLAS_GRUPO), ("rol", ROLES), ("clase", CLASES)):
            if valores[columna] not in permitidos:
                raise ErrorConfig(f"{ruta}:{n}: {columna}='{valores[columna]}' no está en {list(permitidos)}")
        if not valores["fuente"] or not valores["patron"]:
            raise ErrorConfig(f"{ruta}:{n}: fuente y patron son obligatorios")
        fuentes.append(Fuente(**valores))
    nombres = [f.fuente for f in fuentes]
    repetidas = sorted({n for n in nombres if nombres.count(n) > 1})
    if repetidas:
        raise ErrorConfig(f"{ruta}: fuentes repetidas {repetidas}")
    return fuentes


def _validar(config):
    if abs(sum(config.proporciones.values()) - 1.0) > 1e-9:
        raise ErrorConfig(f"Las proporciones deben sumar 1 (suman {sum(config.proporciones.values())})")
    if any(v < 0 for v in config.proporciones.values()):
        raise ErrorConfig("Las proporciones no pueden ser negativas")
    for clase, cuotas in config.cuotas.items():
        for nombre, cuota in cuotas.items():
            fuente = config.fuente_por_nombre(nombre)
            if fuente is None:
                raise ErrorConfig(f"La cuota '{clase}.{nombre}' no corresponde a ninguna fuente de fuentes.csv")
            if fuente.clase != clase:
                raise ErrorConfig(f"La fuente '{nombre}' es de la clase '{fuente.clase}', no de '{clase}'")
            if cuota < 0:
                raise ErrorConfig(f"La cuota '{clase}.{nombre}' es negativa")
        if sum(cuotas.values()) > config.max_por_clase:
            raise ErrorConfig(f"Las cuotas de '{clase}' suman {sum(cuotas.values())}, "
                              f"más que max_por_clase={config.max_por_clase}")
