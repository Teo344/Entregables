"""Calibración con Temperature Scaling en NumPy puro (research M10, M11; data-model.md §8).

La temperatura se ajusta SOLO con validación (FR-005); la prueba solo se usa para reportar.
Un único parámetro T no cambia el argmax: la exactitud no varía, solo la honestidad de la confianza.
"""

import math

import numpy as np

UMBRALES = tuple(round(0.34 + 0.01 * i, 2) for i in range(66))  # 0.34 … 0.99


def softmax(logits, temperatura=1.0):
    z = np.asarray(logits, float) / float(temperatura)
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


def nll(logits, y, temperatura=1.0):
    z = np.asarray(logits, float) / float(temperatura)
    z = z - z.max(axis=1, keepdims=True)
    log_p = z - np.log(np.exp(z).sum(axis=1, keepdims=True))
    return float(-log_p[np.arange(len(y)), np.asarray(y, int)].mean())


def ajustar_temperatura(logits_val, y_val, minimo=0.05, maximo=20.0, iteraciones=100):
    """T que minimiza la NLL en validación, por sección áurea sobre log T (determinista, sin SciPy)."""
    a, b = math.log(minimo), math.log(maximo)
    r = (math.sqrt(5) - 1) / 2
    c, d = b - r * (b - a), a + r * (b - a)
    fc, fd = nll(logits_val, y_val, math.exp(c)), nll(logits_val, y_val, math.exp(d))
    for _ in range(iteraciones):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - r * (b - a)
            fc = nll(logits_val, y_val, math.exp(c))
        else:
            a, c, fc = c, d, fd
            d = a + r * (b - a)
            fd = nll(logits_val, y_val, math.exp(d))
    return round(math.exp((a + b) / 2), 6)


def fiabilidad(probs, y, intervalos=15):
    """Por intervalo de confianza (igual ancho en (0, 1]): n, confianza media y exactitud."""
    probs, y = np.asarray(probs, float), np.asarray(y, int)
    conf = probs.max(axis=1)
    acierto = probs.argmax(axis=1) == y
    bordes = np.linspace(0, 1, intervalos + 1)
    salida = []
    for i in range(intervalos):
        m = (conf > bordes[i]) & (conf <= bordes[i + 1])
        salida.append({"desde": float(bordes[i]), "hasta": float(bordes[i + 1]), "n": int(m.sum()),
                       "confianza": float(conf[m].mean()) if m.any() else None,
                       "exactitud": float(acierto[m].mean()) if m.any() else None})
    return salida


def ece(probs, y, intervalos=15):
    total = len(y)
    return float(sum(b["n"] / total * abs(b["exactitud"] - b["confianza"])
                     for b in fiabilidad(probs, y, intervalos) if b["n"])) if total else 0.0


def brier(probs, y):
    probs = np.asarray(probs, float)
    uno = np.eye(probs.shape[1])[np.asarray(y, int)]
    return float(((probs - uno) ** 2).sum(axis=1).mean())


def curva_cobertura(probs, y, umbrales=UMBRALES):
    """Para cada umbral: fracción aceptada (confianza ≥ umbral) y exactitud de las aceptadas."""
    probs, y = np.asarray(probs, float), np.asarray(y, int)
    conf = probs.max(axis=1)
    acierto = probs.argmax(axis=1) == y
    curva = []
    for u in umbrales:
        m = conf >= u
        curva.append({"umbral": float(u), "cobertura": float(m.mean()) if len(y) else 0.0,
                      "exactitud": float(acierto[m].mean()) if m.any() else None, "aceptadas": int(m.sum())})
    return curva


def umbral_para_exactitud(curva, objetivo):
    for fila in curva:
        if fila["exactitud"] is not None and fila["exactitud"] >= objetivo:
            return fila["umbral"]
    return None


def calibrar(logits_val, y_val, logits_test, y_test, intervalos=15, umbral=0.60, objetivo=0.95):
    t = ajustar_temperatura(logits_val, y_val)
    res = {"temperatura": t, "intervalos": intervalos, "umbral": umbral, "exactitud_objetivo": objetivo,
           "nll_antes": nll(logits_val, y_val), "nll_despues": nll(logits_val, y_val, t)}
    for nombre, lg, y in (("val", logits_val, y_val), ("test", logits_test, y_test)):
        antes, despues = softmax(lg), softmax(lg, t)
        res[f"ece_{nombre}_antes"] = ece(antes, y, intervalos)
        res[f"ece_{nombre}_despues"] = ece(despues, y, intervalos)
        res[f"brier_{nombre}_antes"] = brier(antes, y)
        res[f"brier_{nombre}_despues"] = brier(despues, y)
        res[f"confianza_media_{nombre}_antes"] = float(antes.max(axis=1).mean())
        res[f"confianza_media_{nombre}_despues"] = float(despues.max(axis=1).mean())
    curva_val = curva_cobertura(softmax(logits_val, t), y_val)
    res["umbral_exactitud_95"] = umbral_para_exactitud(curva_val, objetivo)
    p_test = softmax(logits_test, t)
    aceptadas = p_test.max(axis=1) >= umbral
    res["cobertura_test_umbral"] = float(aceptadas.mean())
    res["no_concluyentes_test"] = float(1 - aceptadas.mean())
    res["exactitud_test_aceptadas"] = (float((p_test.argmax(1) == np.asarray(y_test))[aceptadas].mean())
                                       if aceptadas.any() else None)
    res["_curva_val"] = curva_val
    return res
