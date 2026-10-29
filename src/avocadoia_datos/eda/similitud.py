"""Mapa de similitud t-SNE del conjunto final (spec 002, US5, research E8)."""

import os

import numpy as np

from avocadoia_datos.clases import CLASES, PARTICIONES
from avocadoia_datos.es_csv import escribir_csv
from avocadoia_datos.etl.sospechas import vecinos_otra_clase

COLUMNAS = ("id_contenido", "x", "y", "clase", "fuente", "conjunto", "vecinos_otra_clase", "rotulo")
N_ROTULOS = 15


def coordenadas(X, semilla=42):
    from sklearn.decomposition import PCA
    from sklearn.manifold import TSNE
    reducida = PCA(n_components=min(50, X.shape[1], len(X) - 1), random_state=semilla).fit_transform(X)
    perplejidad = min(30.0, (len(X) - 1) / 3)
    return TSNE(n_components=2, perplexity=perplejidad, init="pca", random_state=semilla).fit_transform(reducida)


def calcular(filas, X, semilla=42, n_rotulos=N_ROTULOS):
    """Filas de tsne.csv; se rotulan las n imágenes con más vecinos de otra clase."""
    y = np.array([CLASES.index(f["clase"]) for f in filas])
    vecinos = vecinos_otra_clase(X, y, np.array([f["grupo"] for f in filas]))
    xy = coordenadas(X, semilla)
    rotuladas = set(sorted(range(len(filas)), key=lambda i: (-vecinos[i], filas[i]["id_contenido"]))[:n_rotulos])
    return [{"id_contenido": f["id_contenido"], "x": f"{xy[i, 0]:.4f}", "y": f"{xy[i, 1]:.4f}", "clase": f["clase"],
             "fuente": f["fuente"], "conjunto": f["particion"], "vecinos_otra_clase": f"{vecinos[i]:.4f}",
             "rotulo": "si" if i in rotuladas else "no"} for i, f in enumerate(filas)]


def ejecutar(representaciones, particion, salida, semilla=42):
    indice = {i: n for n, i in enumerate(representaciones["ids"])}
    filas = sorted((f for f in particion if f["particion"] in PARTICIONES and f["id_contenido"] in indice),
                   key=lambda f: f["id_contenido"])
    X = representaciones["vectores"][[indice[f["id_contenido"]] for f in filas]]
    resultado = calcular(filas, X, semilla)
    escribir_csv(os.path.join(salida, "eda", "tablas", "tsne.csv"), COLUMNAS, resultado)
    return resultado
