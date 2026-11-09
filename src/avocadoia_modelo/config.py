"""Carga de config/modelo.toml, rutas por entorno y huella de configuración (data-model.md §4)."""

import copy
import hashlib
import json
import os
import tomllib

SECCIONES = ("datos", "filtros", "entrada", "modelo", "fase1", "fase2", "parada", "aumento", "entrenamiento",
             "evaluacion", "seleccion", "calibracion", "explicacion", "exportacion", "metas", "rutas")
# Claves que nunca entran en la huella: rutas (cambian entre Colab y PC) y lo propio de cada corrida.
_FUERA_DE_HUELLA = ("rutas", "corrida")


class ErrorConfig(ValueError):
    pass


def entorno():
    """'colab' si Google Drive está montado en Colab; si no, 'pc' (research M17)."""
    return "colab" if os.path.isdir("/content/drive") else "pc"


def cargar(ruta="config/modelo.toml", entorno_=None):
    with open(ruta, "rb") as fh:
        cfg = tomllib.load(fh)
    faltan = [s for s in SECCIONES if s not in cfg]
    if faltan:
        raise ErrorConfig(f"{ruta}: faltan secciones {faltan}")
    env = entorno_ or entorno()
    if env not in cfg["rutas"]:
        raise ErrorConfig(f"{ruta}: no hay [rutas.{env}]")
    cfg["_entorno"] = env
    cfg["_rutas"] = {"repo_datos": cfg["rutas"].get("repo_datos", "datos/modelo"), **cfg["rutas"][env]}
    return cfg


def con_corrida(cfg, arquitectura, semilla):
    """Copia de la configuración con los dos únicos valores que varían entre corridas comparables."""
    if arquitectura not in cfg["modelo"]["arquitecturas"]:
        raise ErrorConfig(f"arquitectura desconocida: {arquitectura}")
    nueva = copy.deepcopy(cfg)
    nueva["corrida"] = {"arquitectura": arquitectura, "semilla": int(semilla)}
    return nueva


def canonica(cfg):
    """Configuración sin rutas, sin datos de corrida y sin claves internas, para la huella."""
    return {k: v for k, v in cfg.items() if k not in _FUERA_DE_HUELLA and not k.startswith("_")}


def huella_config(cfg):
    texto = json.dumps(canonica(cfg), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()
