"""Métricas de clasificación en NumPy puro (research M12; data-model.md §5 `metricas.json`).

Orden de clases fijo: CLASES = (sano, antracnosis, pedunculo). Sin TensorFlow ni scikit-learn.
"""

import numpy as np

from avocadoia_modelo import CLASES

K = len(CLASES)


def matriz_confusion(y, pred, k=K):
    """cm[real, predicha]."""
    cm = np.zeros((k, k), dtype=np.int64)
    np.add.at(cm, (np.asarray(y, dtype=np.int64), np.asarray(pred, dtype=np.int64)), 1)
    return cm


def _div(a, b):
    return float(a) / float(b) if b else 0.0


def por_clase(cm):
    salida = {}
    for i, c in enumerate(CLASES[: cm.shape[0]]):
        tp = cm[i, i]
        precision = _div(tp, cm[:, i].sum())
        recall = _div(tp, cm[i, :].sum())
        f1 = _div(2 * precision * recall, precision + recall)
        salida[c] = {"precision": precision, "recall": recall, "f1": f1, "soporte": int(cm[i, :].sum())}
    return salida


def macro_f1(y, pred, k=K):
    return float(np.mean([v["f1"] for v in por_clase(matriz_confusion(y, pred, k)).values()]))


def exactitud(y, pred):
    y, pred = np.asarray(y), np.asarray(pred)
    return float(np.mean(y == pred)) if len(y) else 0.0


def recall_de(clase):
    i = CLASES.index(clase)

    def f(y, pred):
        return por_clase(matriz_confusion(y, pred))[CLASES[i]]["recall"]
    return f


def bootstrap(y, pred, metrica, n=1000, semilla=42, alfa=0.05):
    """Intervalo de confianza percentil (1 − alfa) por remuestreo con reemplazo."""
    y, pred = np.asarray(y), np.asarray(pred)
    if len(y) == 0:
        return (0.0, 0.0)
    rng = np.random.default_rng(semilla)
    valores = np.empty(n)
    for b in range(n):
        idx = rng.integers(0, len(y), len(y))
        valores[b] = metrica(y[idx], pred[idx])
    return (float(np.percentile(valores, 100 * alfa / 2)), float(np.percentile(valores, 100 * (1 - alfa / 2))))


def por_fuente(y, pred, fuentes, minimo=10):
    """Exactitud y recall de las clases presentes, por fuente con al menos `minimo` imágenes."""
    y, pred, fuentes = np.asarray(y), np.asarray(pred), np.asarray(fuentes)
    salida = {}
    for f in sorted(set(fuentes.tolist())):
        m = fuentes == f
        if m.sum() < minimo:
            continue
        cm = matriz_confusion(y[m], pred[m])
        clases = por_clase(cm)
        salida[f] = {"n": int(m.sum()), "exactitud": exactitud(y[m], pred[m]),
                     "recall": {c: v["recall"] for c, v in clases.items() if v["soporte"]}}
    return salida


def pesos_clase(y_train, k=K):
    """n / (k · n_c), calculado solo sobre entrenamiento (FR-008)."""
    conteos = np.bincount(np.asarray(y_train, dtype=np.int64), minlength=k)
    n = conteos.sum()
    return {i: float(n / (k * c)) if c else 0.0 for i, c in enumerate(conteos)}


def resumen(y, logits, fuentes=None, experimental=False, n_bootstrap=1000, semilla=42, minimo_fuente=10):
    y = np.asarray(y, dtype=np.int64)
    pred = np.asarray(logits).argmax(axis=1)
    cm = matriz_confusion(y, pred)
    clases = por_clase(cm)
    for c in CLASES:
        clases[c]["recall_ic95"] = list(bootstrap(y, pred, recall_de(c), n_bootstrap, semilla))
    return {
        "n": int(len(y)),
        "exactitud": exactitud(y, pred),
        "macro_f1": macro_f1(y, pred),
        "macro_f1_ic95": list(bootstrap(y, pred, macro_f1, n_bootstrap, semilla)),
        "por_clase": clases,
        "matriz_confusion": cm.tolist(),
        "por_fuente": por_fuente(y, pred, fuentes, minimo_fuente) if fuentes is not None else {},
        "experimental": bool(experimental),
    }
