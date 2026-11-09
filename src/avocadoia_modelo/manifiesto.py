"""Manifiesto normalizado, equivalencias de clase y filtros de licencia y calidad (research M2, M3, M19).

Sin TensorFlow. La fuente de cada imagen se determina PRIMERO por SHA-256 en el manifiesto de la
especificación 002 (asignación auditada) y, si el contenido no está registrado, por las reglas de nombre de
config/fuentes.csv: el split v4 renombra archivos (p. ej. las fotos propias sano-0001… aparecen como sano-0707…).
"""

import os

from avocadoia_datos import config as config_002
from avocadoia_datos.es_csv import escribir_csv, leer_csv, sha256_archivo

from avocadoia_modelo import CLASES, PARTICIONES

COLUMNAS = ("ruta", "clase", "particion", "sha256", "fuente", "licencia", "estado_etiqueta", "grupo", "ruta_origen")
COLUMNAS_EXCLUIDAS = ("sha256", "ruta", "particion", "clase", "fuente", "licencia", "uso_academico", "motivo")


class ErrorManifiesto(ValueError):
    pass


class ClaseDesconocida(ErrorManifiesto):
    pass


def leer_entrada(ruta):
    if not os.path.exists(ruta):
        raise ErrorManifiesto(f"no existe el manifiesto {ruta}")
    return leer_csv(ruta)


def huella_manifiesto(ruta):
    return sha256_archivo(ruta)


def clases_desconocidas(filas, cfg):
    col = cfg["datos"]["columnas"]["clase"]
    eq = cfg["datos"]["equivalencias"]
    return sorted({f.get(col, "") for f in filas if f.get(col, "") not in eq})


def normalizar(filas, cfg):
    """Mapea columnas y traduce clases; aborta ante clase desconocida o partición inválida (FR-001, FR-002)."""
    col = cfg["datos"]["columnas"]
    eq = cfg["datos"]["equivalencias"]
    desconocidas = clases_desconocidas(filas, cfg)
    if desconocidas:
        raise ClaseDesconocida(f"clases sin equivalencia: {desconocidas}")
    salida = []
    for n, f in enumerate(filas, start=2):
        particion = f.get(col["particion"], "").strip()
        if particion not in PARTICIONES:
            raise ErrorManifiesto(f"fila {n}: partición '{particion}' no está en {PARTICIONES}")
        ruta = f.get(col["ruta"], "").strip().replace("\\", "/")
        if not ruta:
            raise ErrorManifiesto(f"fila {n}: ruta vacía")
        salida.append({
            "ruta": ruta,
            "clase": eq[f[col["clase"]]],
            "particion": particion,
            "sha256": f.get(col.get("sha256", ""), "").strip().lower(),
            "fuente": "",
            "licencia": "",
            "estado_etiqueta": f.get(col.get("estado_etiqueta", ""), ""),
            "grupo": f.get(col.get("grupo", ""), ""),
            "ruta_origen": f.get(col.get("ruta_origen", ""), "").replace("\\", "/"),
        })
    assert all(x["clase"] in CLASES for x in salida)
    return salida


def contexto_002(cfg):
    """(Config de fuentes de 002, mapa sha256 → fila del manifiesto de 002)."""
    filtros = cfg["filtros"]
    cfg002 = config_002.cargar(filtros["dataset_002"], filtros["fuentes_002"])
    por_sha = {}
    for fila in leer_csv(filtros["manifiesto_002"]):
        sha = fila.get("sha256", "")
        # Entre copias exactas se prefiere la canónica; todas comparten fuente y grupo.
        if sha and (sha not in por_sha or fila.get("canonica") == "si"):
            por_sha[sha] = fila
    return cfg002, por_sha


def asignar_fuente(fila, cfg002, por_sha):
    registrada = por_sha.get(fila["sha256"])
    if registrada:
        fuente = cfg002.fuente_por_nombre(registrada.get("fuente", ""))
        if fuente is not None:
            return fuente
    if fila.get("ruta_origen"):
        return cfg002.fuente_de(fila["ruta_origen"])
    return None


def filtrar(filas, cfg, cfg002, por_sha):
    """Separa conservadas y excluidas: licencia (FR-026, sin opción de desactivarlo) y calidad (FR-027)."""
    excluidas_calidad = set(cfg["filtros"].get("fuentes_excluidas", []))
    motivo_calidad = cfg["filtros"].get("motivo_exclusion", "calidad")
    conservadas, excluidas = [], []
    for fila in filas:
        fuente = asignar_fuente(fila, cfg002, por_sha)
        if fuente is None:
            excluidas.append({**fila, "uso_academico": "", "motivo": "sin_fuente"})
            continue
        fila = {**fila, "fuente": fuente.fuente, "licencia": fuente.licencia}
        if fuente.uso_academico != "si":
            excluidas.append({**fila, "uso_academico": fuente.uso_academico,
                              "motivo": f"licencia:{fuente.fuente}:{fuente.uso_academico}"})
        elif fuente.fuente in excluidas_calidad:
            excluidas.append({**fila, "uso_academico": fuente.uso_academico, "motivo": motivo_calidad})
        else:
            conservadas.append(fila)
    return conservadas, excluidas


def escribir_normalizado(ruta, filas):
    escribir_csv(ruta, COLUMNAS, filas)


def escribir_excluidas(ruta, filas):
    escribir_csv(ruta, COLUMNAS_EXCLUIDAS, filas)
