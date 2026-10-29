"""Línea base de 001, embudo de calidad y comparación (spec 002, research E9 y E10)."""

import os
import subprocess
from collections import Counter

from avocadoia_datos.config import ErrorPrecondicion
from avocadoia_datos.es_csv import escribir_csv, leer_csv

COMMIT_001 = "f43575e"

# Orden fijo: cada imagen se cuenta en el primer paso que la retira (research E9).
PASOS = ("invalida", "duplicada", "conflicto_clase", "excluida_licencia", "excluida_revision", "rechazada",
         "test_campo", "fuera_de_cuota", "conjunto_final")
_PASO_DE_ESTADO = {"excluida_invalida": "invalida", "excluida_conflicto": "conflicto_clase",
                   "duplicada": "duplicada", "excluida_licencia": "excluida_licencia",
                   "excluida_revision": "excluida_revision", "rechazada": "rechazada", "test_campo": "test_campo"}

COLUMNAS_EMBUDO = ("paso", "clase", "fuente", "imagenes")
COLUMNAS_COMPARACION = ("id_contenido", "clase_001", "conjunto_001", "clase_002", "conjunto_002", "cambio")


def ruta_linea_base(salida):
    return os.path.join(salida, "etl", "particion_001.csv")


def guardar_linea_base(salida, repo="."):
    """Guarda la partición de 001 (commit f43575e) si aún no existe; devuelve su ruta."""
    destino = ruta_linea_base(salida)
    if os.path.exists(destino):
        return destino
    try:
        contenido = subprocess.run(["git", "show", f"{COMMIT_001}:datos/particion.csv"], cwd=repo,
                                   capture_output=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        raise ErrorPrecondicion(f"No se pudo leer la partición de 001 desde Git ({COMMIT_001}): {e}") from e
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "wb") as fh:
        fh.write(contenido.replace(b"\r\n", b"\n"))
    return destino


def paso_de(fila):
    """Paso del embudo en el que termina una fila del manifiesto."""
    if fila["estado"] in _PASO_DE_ESTADO:
        return _PASO_DE_ESTADO[fila["estado"]]
    return "conjunto_final" if fila.get("en_muestra") == "si" else "fuera_de_cuota"


def calcular_embudo(manifiesto):
    """Filas (paso, clase, fuente, imagenes); la clase es la efectiva (una reasignada cuenta en la nueva)."""
    pasos = Counter()
    inventariadas = Counter()
    for fila in manifiesto:
        clave = (fila["clase_efectiva"], fila["fuente"])
        inventariadas[clave] += 1
        pasos[(paso_de(fila),) + clave] += 1
    filas = []
    for clase, fuente in sorted(inventariadas):
        filas.append({"paso": "inventariadas", "clase": clase, "fuente": fuente,
                      "imagenes": inventariadas[(clase, fuente)]})
        for paso in PASOS:
            n = pasos.get((paso, clase, fuente), 0)
            if n:
                filas.append({"paso": paso, "clase": clase, "fuente": fuente, "imagenes": n})
    return filas


def verificar_embudo(filas):
    """Lista de (clase, fuente) donde inventariadas no es la suma de los pasos (vacía si cuadra)."""
    total, suma = Counter(), Counter()
    for f in filas:
        clave = (f["clase"], f["fuente"])
        if f["paso"] == "inventariadas":
            total[clave] += int(f["imagenes"])
        else:
            suma[clave] += int(f["imagenes"])
    return sorted(k for k in set(total) | set(suma) if total[k] != suma[k])


def comparar_con_001(particion_001, particion_002):
    """Clasifica cada imagen: sale, entra, cambia_clase, cambia_conjunto o igual."""
    antes = {f["id_contenido"]: f for f in particion_001}
    despues = {f["id_contenido"]: f for f in particion_002}
    filas = []
    for i in sorted(set(antes) | set(despues)):
        a, d = antes.get(i), despues.get(i)
        if a is None:
            cambio = "entra"
        elif d is None:
            cambio = "sale"
        elif a["clase"] != d["clase"]:
            cambio = "cambia_clase"
        elif a["particion"] != d["particion"]:
            cambio = "cambia_conjunto"
        else:
            cambio = "igual"
        filas.append({"id_contenido": i,
                      "clase_001": a["clase"] if a else "", "conjunto_001": a["particion"] if a else "",
                      "clase_002": d["clase"] if d else "", "conjunto_002": d["particion"] if d else "",
                      "cambio": cambio})
    return filas


def ejecutar(manifiesto, salida):
    """Escribe datos/etl/embudo.csv y comparacion_001.csv; devuelve un resumen."""
    filas = calcular_embudo(manifiesto)
    escribir_csv(os.path.join(salida, "etl", "embudo.csv"), COLUMNAS_EMBUDO, filas)
    actual = [f for f in leer_csv(os.path.join(salida, "particion.csv")) if f["particion"] in ("train", "val", "test")]
    base = [f for f in leer_csv(ruta_linea_base(salida)) if f["particion"] in ("train", "val", "test")]
    comparacion = comparar_con_001(base, actual)
    escribir_csv(os.path.join(salida, "etl", "comparacion_001.csv"), COLUMNAS_COMPARACION, comparacion)
    return {"descuadres": verificar_embudo(filas), "cambios": dict(Counter(f["cambio"] for f in comparacion)),
            "linea_base": bool(base)}
