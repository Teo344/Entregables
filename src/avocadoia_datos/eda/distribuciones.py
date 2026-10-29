"""Tablas descriptivas del EDA (spec 002, US3)."""

import os
from collections import Counter, defaultdict

import numpy as np

from avocadoia_datos.clases import CLASES, PARTICIONES
from avocadoia_datos.es_csv import escribir_csv
from avocadoia_datos.muestra import clave_estable

MEDIDAS = ("megapixeles", "proporcion", "brillo", "contraste", "nitidez", "tono_medio", "saturacion", "valor",
           "fondo_fraccion")
TAMANO_MOSAICO = 16


def conjunto_final(particion):
    return [f for f in particion if f["particion"] in PARTICIONES]


def distribucion(particion):
    """Filas (clase, fuente, train, val, test, total) del conjunto final, más totales por clase."""
    conteo = Counter((f["clase"], f["fuente"], f["particion"]) for f in conjunto_final(particion))
    filas = []
    for clase in CLASES:
        fuentes = sorted({fu for (c, fu, _) in conteo if c == clase})
        for fuente in fuentes + ["todas"]:
            n = {p: sum(v for (c, fu, q), v in conteo.items() if c == clase and q == p and fuente in (fu, "todas"))
                 for p in PARTICIONES}
            filas.append({"clase": clase, "fuente": fuente, **n, "total": sum(n.values())})
    return filas


def _grupo_de(particion, manifiesto):
    """{id: (clase, fuente, grupo_eda)}: conjunto final por su partición; prueba de campo aparte."""
    destino = {f["id_contenido"]: (f["clase"], f["fuente"], "final") for f in conjunto_final(particion)}
    for f in manifiesto:
        if f["canonica"] == "si" and f["estado"] == "test_campo":
            destino[f["id_contenido"]] = (f["clase_efectiva"], f["fuente"], "campo")
    return destino


def resumen_caracteristicas(caracteristicas, particion, manifiesto):
    """Mediana y cuartiles por clase × fuente (y por clase con fuente 'todas')."""
    destino = _grupo_de(particion, manifiesto)
    valores = defaultdict(lambda: defaultdict(list))
    for f in caracteristicas:
        if f["id_contenido"] not in destino:
            continue
        clase, fuente, grupo = destino[f["id_contenido"]]
        for clave in ((grupo, clase, fuente), (grupo, clase, "todas")):
            for m in MEDIDAS:
                valores[clave][m].append(float(f[m]))
    filas = []
    for (grupo, clase, fuente) in sorted(valores, key=lambda k: (k[0], CLASES.index(k[1]), k[2] == "todas", k[2])):
        for m in MEDIDAS:
            v = np.array(valores[(grupo, clase, fuente)][m])
            q1, med, q3 = np.percentile(v, [25, 50, 75])
            filas.append({"grupo": grupo, "clase": clase, "fuente": fuente, "medida": m, "n": len(v),
                          "q1": f"{q1:.4f}", "mediana": f"{med:.4f}", "q3": f"{q3:.4f}"})
    return filas


def fondo_por_clase(caracteristicas, particion):
    fondo = {f["id_contenido"]: f["fondo"] for f in caracteristicas}
    conteo = Counter((f["clase"], f["fuente"], fondo.get(f["id_contenido"], "sin_medir"))
                     for f in conjunto_final(particion))
    filas = []
    for clase in CLASES:
        for fuente in sorted({fu for (c, fu, _) in conteo if c == clase}) + ["todas"]:
            u = sum(v for (c, fu, t), v in conteo.items() if c == clase and fuente in (fu, "todas") and t == "uniforme")
            n = sum(v for (c, fu, t), v in conteo.items() if c == clase and fuente in (fu, "todas"))
            filas.append({"clase": clase, "fuente": fuente, "uniforme": u, "natural": n - u,
                          "fraccion_uniforme": f"{u / n:.4f}" if n else ""})
    return filas


def elegir_mosaico(filas, semilla, clase, fuente, n=TAMANO_MOSAICO):
    """Hasta n imágenes de clase × fuente en orden estable (misma semilla → mismas imágenes)."""
    candidatas = [f for f in filas if f["clase"] == clase and f["fuente"] == fuente]
    candidatas.sort(key=lambda f: (clave_estable(semilla, "mosaico", f["id_contenido"]), f["id_contenido"]))
    return candidatas[:n]


def ejecutar(caracteristicas, particion, manifiesto, salida):
    tablas = os.path.join(salida, "eda", "tablas")
    d = distribucion(particion)
    escribir_csv(os.path.join(tablas, "distribucion_clase_fuente_conjunto.csv"),
                 ("clase", "fuente") + PARTICIONES + ("total",), d)
    escribir_csv(os.path.join(tablas, "resumen_caracteristicas.csv"),
                 ("grupo", "clase", "fuente", "medida", "n", "q1", "mediana", "q3"),
                 resumen_caracteristicas(caracteristicas, particion, manifiesto))
    escribir_csv(os.path.join(tablas, "fondo_por_clase.csv"),
                 ("clase", "fuente", "uniforme", "natural", "fraccion_uniforme"), fondo_por_clase(caracteristicas, particion))
    return {"distribucion": d}
