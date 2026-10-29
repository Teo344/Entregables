"""Detección de etiquetas dudosas con confident learning (spec 002, US1, research E3).

El clasificador es una herramienta de curación: se entrena con validación cruzada por grupos,
juzga cada imagen con un modelo que no vio su fruto y se descarta. Trata igual a train, val y test.
"""

import math
import os

import numpy as np

from avocadoia_datos.clases import CLASES
from avocadoia_datos.es_csv import escribir_csv

COLUMNAS = ("id_contenido", "fuente", "grupo", "clase_asignada", "p_sano", "p_antracnosis", "p_pedunculo",
            "clase_sugerida", "conflicto", "puntaje", "vecinos_otra_clase", "a_revisar", "motivo_marca")


def pliegues(y, grupos, n=5, semilla=42):
    """Índice de pliegue por muestra; los grupos nunca se reparten entre pliegues."""
    from sklearn.model_selection import StratifiedGroupKFold
    pliegue = np.empty(len(y), dtype=int)
    for k, (_, prueba) in enumerate(StratifiedGroupKFold(n_splits=n, shuffle=True, random_state=semilla)
                                    .split(np.zeros(len(y)), y, grupos)):
        pliegue[prueba] = k
    return pliegue


def probabilidades_fuera_de_muestra(X, y, grupos, n=5, semilla=42):
    """Probabilidades (N × 3) con regresión logística, cada fila predicha por un modelo que no la vio."""
    from sklearn.linear_model import LogisticRegression
    pliegue = pliegues(y, grupos, n, semilla)
    p = np.zeros((len(y), len(CLASES)))
    for k in range(n):
        entrena = pliegue != k
        modelo = LogisticRegression(max_iter=3000, C=1.0, random_state=semilla).fit(X[entrena], y[entrena])
        p[np.ix_(pliegue == k, modelo.classes_)] = modelo.predict_proba(X[pliegue == k])
    return p


def umbrales(p, y):
    """t_j = media de p_j sobre las imágenes etiquetadas j (Northcutt et al., 2021)."""
    return np.array([p[y == j, j].mean() if np.any(y == j) else 1.0 for j in range(p.shape[1])])


def clase_sugerida(p, t):
    """Por fila: la clase de mayor probabilidad entre las que superan su umbral, o -1 si ninguna."""
    candidatas = np.where(p >= t, p, -np.inf)
    sugerida = candidatas.argmax(axis=1)
    sugerida[~np.isfinite(candidatas.max(axis=1))] = -1
    return sugerida


def vecinos_otra_clase(X, y, grupos, k=10):
    """Fracción de los k vecinos más cercanos (coseno) con otra clase, excluido el propio grupo."""
    Xn = X / np.maximum(np.linalg.norm(X, axis=1, keepdims=True), 1e-12)
    grupos = np.asarray(grupos)
    fraccion = np.zeros(len(y))
    for inicio in range(0, len(y), 512):
        bloque = slice(inicio, min(inicio + 512, len(y)))
        sim = Xn[bloque] @ Xn.T
        sim[grupos[bloque, None] == grupos[None, :]] = -np.inf
        vecinos = np.argsort(-sim, axis=1, kind="stable")[:, :k]
        fraccion[bloque] = (y[vecinos] != y[bloque, None]).mean(axis=1)
    return fraccion


def calcular(ids, X, etiquetas, grupos, fuentes, semilla=42, k=10, fraccion_top=0.10):
    """Filas de sospechas.csv ordenadas por puntaje descendente y luego por id_contenido."""
    y = np.array([CLASES.index(e) for e in etiquetas])
    grupos = np.asarray(grupos)
    p = probabilidades_fuera_de_muestra(X, y, grupos, semilla=semilla)
    t = umbrales(p, y)
    sugerida = clase_sugerida(p, t)
    puntaje = 1.0 - p[np.arange(len(y)), y]
    vecinos = vecinos_otra_clase(X, y, grupos, k)

    top = np.zeros(len(y), dtype=bool)
    for j in range(len(CLASES)):
        miembros = np.flatnonzero(y == j)
        n_top = math.ceil(fraccion_top * len(miembros))
        orden = sorted(miembros, key=lambda i: (-round(puntaje[i], 4), ids[i]))
        top[orden[:n_top]] = True

    filas = []
    for i in range(len(y)):
        conflicto = sugerida[i] >= 0 and sugerida[i] != y[i]
        motivo = "+".join(m for m, v in (("conflicto", conflicto), ("top10", top[i])) if v)
        filas.append({
            "id_contenido": ids[i], "fuente": fuentes[i], "grupo": grupos[i], "clase_asignada": etiquetas[i],
            **{f"p_{c}": f"{p[i, j]:.4f}" for j, c in enumerate(CLASES)},
            "clase_sugerida": CLASES[sugerida[i]] if sugerida[i] >= 0 else "",
            "conflicto": "si" if conflicto else "no",
            "puntaje": f"{puntaje[i]:.4f}", "vecinos_otra_clase": f"{vecinos[i]:.4f}",
            "a_revisar": "si" if motivo else "no", "motivo_marca": motivo,
        })
    filas.sort(key=lambda f: (-float(f["puntaje"]), f["id_contenido"]))
    return filas, {"umbrales": {c: round(float(t[j]), 4) for j, c in enumerate(CLASES)}}


def poblacion(manifiesto):
    """Candidatas más las imágenes que ya tienen decisión de los autores.

    Las excluidas por los autores siguen en el análisis: así el 10 % superior de cada clase no se
    desplaza hacia imágenes nuevas en cada ejecución y las ya revisadas siguen contando (SC-002).
    """
    from avocadoia_datos import muestra
    ids = {f["id_contenido"] for f in muestra.candidatas(manifiesto)}
    return [f for f in manifiesto if f["canonica"] == "si"
            and (f["id_contenido"] in ids or (f.get("revision_autores") and f["estado"] == "excluida_revision"))]


def ejecutar(manifiesto, representaciones, salida, semilla=42):
    """Escribe datos/etl/sospechas.csv para la población con representación; devuelve un resumen."""
    indice = {i: n for n, i in enumerate(representaciones["ids"])}
    candidatas = [f for f in poblacion(manifiesto) if f["id_contenido"] in indice]
    candidatas.sort(key=lambda f: f["id_contenido"])
    X = representaciones["vectores"][[indice[f["id_contenido"]] for f in candidatas]]
    filas, extra = calcular([f["id_contenido"] for f in candidatas], X, [f["clase_efectiva"] for f in candidatas],
                            [f["grupo"] for f in candidatas], [f["fuente"] for f in candidatas], semilla)
    escribir_csv(os.path.join(salida, "etl", "sospechas.csv"), COLUMNAS, filas)
    resumen = {c: {"candidatas": 0, "a_revisar": 0, "conflictos": 0} for c in CLASES}
    for f in filas:
        r = resumen[f["clase_asignada"]]
        r["candidatas"] += 1
        r["a_revisar"] += f["a_revisar"] == "si"
        r["conflictos"] += f["conflicto"] == "si"
    return {"por_clase": resumen, **extra}
