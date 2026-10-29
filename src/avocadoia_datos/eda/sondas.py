"""Sondas de atajo: ¿se puede adivinar la clase sin mirar la lesión? (spec 002, US4, research E7).

Todas usan solo train + val (FR-020) y validación cruzada por grupos.
"""

import os

import numpy as np

from avocadoia_datos.clases import CLASES
from avocadoia_datos.es_csv import escribir_csv
from avocadoia_datos.eda.distribuciones import MEDIDAS

COLUMNAS = ("sonda", "descripcion", "exactitud_balanceada", "azar", "alerta", "n", "conjuntos")
UMBRAL_ALERTA = 0.80
CONJUNTOS = ("train", "val")


def exactitud_balanceada_cv(X, y, grupos, semilla=42, n=5):
    """Exactitud balanceada fuera de muestra de una regresión logística estandarizada."""
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import balanced_accuracy_score
    from sklearn.model_selection import StratifiedGroupKFold
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    y = np.asarray(y)
    n = min(n, min(np.unique(y, return_counts=True)[1]))
    prediccion = np.empty(len(y), dtype=y.dtype)
    for entrena, prueba in StratifiedGroupKFold(n_splits=n, shuffle=True, random_state=semilla).split(X, y, grupos):
        modelo = make_pipeline(StandardScaler(), LogisticRegression(max_iter=3000, random_state=semilla))
        prediccion[prueba] = modelo.fit(X[entrena], y[entrena]).predict(X[prueba])
    return float(balanced_accuracy_score(y, prediccion))


def filas_entrenamiento(particion):
    """Solo train y val: el conjunto de prueba nunca entra a una sonda (FR-020)."""
    return sorted((f for f in particion if f["particion"] in CONJUNTOS), key=lambda f: f["id_contenido"])


def ejecutar(caracteristicas, representaciones, particion, salida, semilla=42):
    filas = filas_entrenamiento(particion)
    medidas = {f["id_contenido"]: [float(f[m]) for m in MEDIDAS] for f in caracteristicas}
    indice = {i: n for n, i in enumerate(representaciones["ids"])}
    filas = [f for f in filas if f["id_contenido"] in medidas and f["id_contenido"] in indice]
    y = np.array([f["clase"] for f in filas])
    grupos = np.array([f["grupo"] for f in filas])
    posiciones = [indice[f["id_contenido"]] for f in filas]
    azar = 1 / len(set(y))

    resultados = []

    def agregar(sonda, descripcion, X, etiquetas, g, azar_sonda, con_alerta):
        ba = exactitud_balanceada_cv(X, etiquetas, g, semilla)
        alerta = ("si" if ba > UMBRAL_ALERTA else "no") if con_alerta else ""
        resultados.append({"sonda": sonda, "descripcion": descripcion, "exactitud_balanceada": f"{ba:.4f}",
                           "azar": f"{azar_sonda:.4f}", "alerta": alerta, "n": len(etiquetas),
                           "conjuntos": "+".join(CONJUNTOS)})

    agregar("bajo_nivel", "Clase desde brillo, contraste, nitidez, color, tamaño y fondo (sin la fuente)",
            np.array([medidas[f["id_contenido"]] for f in filas]), y, grupos, azar, True)
    agregar("fondo", "Clase desde la imagen con el 60 % central tapado (solo el borde)",
            representaciones["vectores_borde"][posiciones], y, grupos, azar, True)
    agregar("imagen_completa", "Referencia: clase desde la imagen completa (clasificador lineal)",
            representaciones["vectores"][posiciones], y, grupos, azar, False)
    for clase in CLASES:
        mascara = y == clase
        fuentes = np.array([f["fuente"] for f in filas])[mascara]
        if len(set(fuentes)) > 1:
            agregar(f"fuente_{clase}", f"Fuente dentro de la clase {clase} desde la imagen completa",
                    representaciones["vectores"][np.array(posiciones)[mascara]], fuentes, grupos[mascara],
                    1 / len(set(fuentes)), False)
    escribir_csv(os.path.join(salida, "eda", "tablas", "sondas.csv"), COLUMNAS, resultados)
    return resultados
