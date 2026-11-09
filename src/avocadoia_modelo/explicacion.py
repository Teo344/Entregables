"""Explicabilidad: Grad-CAM++, CAM sin gradientes, mosaicos y planilla de valoración (research M13, M14).

La selección de muestras, el resumen de la planilla y la concordancia son NumPy puro (probables sin TF);
TensorFlow se importa solo dentro de las funciones que lo necesitan.
"""

import datetime
import os
from collections import Counter

import numpy as np

from avocadoia_datos.es_csv import escribir_csv, escribir_json, leer_csv, leer_json

from avocadoia_modelo import CLASES, ETIQUETAS_VISIBLES

VALORACIONES = ("lesion_fruto", "fondo_ajeno", "ambiguo")
COLUMNAS_PLANILLA = ("n", "sha256", "ruta", "fuente", "clase_real", "clase_predicha", "confianza", "tipo", "mosaico",
                     "fila_mosaico", "valoracion", "revisor", "fecha", "notas")


# --- Lógica sin TensorFlow -------------------------------------------------------------------------------------

def seleccionar_muestra(y, pred, semilla=42, n=10):
    """Hasta n aciertos y n errores por clase real (todos los errores si hay menos), reproducible."""
    y, pred = np.asarray(y), np.asarray(pred)
    rng = np.random.default_rng(semilla)
    muestra = []
    for c in range(len(CLASES)):
        for tipo, mascara in (("acierto", (y == c) & (pred == c)), ("error", (y == c) & (pred != c))):
            idx = np.flatnonzero(mascara)
            if len(idx) > n:
                idx = np.sort(rng.choice(idx, n, replace=False))
            muestra += [(int(i), tipo) for i in idx]
    return muestra


def resumir(planilla, umbral_atajo=0.20):
    """% de valoraciones por clase sobre los aciertos valorados; posible atajo si fondo_ajeno > umbral."""
    por_clase, atajos = {}, []
    for c in CLASES:
        filas = [f for f in planilla if f["clase_real"] == c and f["tipo"] == "acierto" and f.get("valoracion")]
        cuenta = Counter(f["valoracion"] for f in filas)
        total = len(filas)
        por_clase[c] = {"valoradas": total, **{v: (cuenta[v] / total if total else 0.0) for v in VALORACIONES}}
        if total and por_clase[c]["fondo_ajeno"] > umbral_atajo:
            atajos.append(c)
    sin_valorar = sum(1 for f in planilla if not f.get("valoracion"))
    return {"por_clase": por_clase, "posibles_atajos": atajos, "sin_valorar": sin_valorar,
            "umbral_atajo": umbral_atajo, "cumple_sc005": all(por_clase[c]["lesion_fruto"] >= 0.80
                                                               for c in CLASES if por_clase[c]["valoradas"])}


def concordancia(a, b, fraccion=0.20):
    """Pearson y IoU del `fraccion` superior entre dos mapas de igual forma."""
    a, b = np.asarray(a, float).ravel(), np.asarray(b, float).ravel()
    pearson = float(np.corrcoef(a, b)[0, 1]) if a.std() > 0 and b.std() > 0 else 0.0
    k = max(1, int(round(len(a) * fraccion)))
    ta, tb = set(np.argsort(a)[-k:]), set(np.argsort(b)[-k:])
    return {"pearson": pearson, "iou_top": len(ta & tb) / len(ta | tb)}


def _normalizar(mapas):
    mapas = np.maximum(np.asarray(mapas, float), 0)
    maximo = mapas.reshape(len(mapas), -1).max(axis=1).reshape(-1, 1, 1)
    return np.divide(mapas, maximo, out=np.zeros_like(mapas), where=maximo > 0)


def softmax(logits, temperatura=1.0):
    z = np.asarray(logits, float) / temperatura
    z = z - z.max(axis=1, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=1, keepdims=True)


# --- TensorFlow ------------------------------------------------------------------------------------------------

def modelo_mapa(modelo):
    """Modelo auxiliar que devuelve [mapa final de características, logits]."""
    import keras

    from avocadoia_modelo.arquitecturas import nombre_capa_mapa

    return keras.Model(modelo.inputs, [modelo.get_layer(nombre_capa_mapa(modelo)).output, modelo.output])


def gradcam_pp(modelo, x, clases, aux=None, lote=16):
    """Grad-CAM++ (Chattopadhay et al., 2018) sobre el último mapa; devuelve mapas (n, h, w) normalizados 0–1."""
    import tensorflow as tf

    aux = aux or modelo_mapa(modelo)
    salida = []
    for i in range(0, len(x), lote):
        xb = tf.convert_to_tensor(np.asarray(x[i:i + lote], np.float32))
        cb = tf.convert_to_tensor(np.asarray(clases[i:i + lote], np.int32))
        with tf.GradientTape() as cinta:
            a, logits = aux(xb, training=False)
            score = tf.gather(logits, cb, batch_dims=1)
        g = cinta.gradient(score, a)
        g2, g3 = g ** 2, g ** 3
        suma_a = tf.reduce_sum(a, axis=(1, 2), keepdims=True)
        denom = 2.0 * g2 + suma_a * g3
        alfa = tf.math.divide_no_nan(g2, tf.where(tf.abs(denom) > 1e-12, denom, tf.ones_like(denom)))
        pesos = tf.reduce_sum(alfa * tf.nn.relu(g), axis=(1, 2))
        mapa = tf.nn.relu(tf.reduce_sum(pesos[:, None, None, :] * a, axis=-1))
        salida.append(mapa.numpy())
    return _normalizar(np.concatenate(salida))


def cam(modelo, x, clases, aux=None, normalizar=True, lote=32):
    """CAM exacto para cabeza GAP → Dense, sin gradientes: Σ_k w_k^c · A_k (research M14, plan B)."""
    aux = aux or modelo_mapa(modelo)
    w = modelo.get_layer("logits").get_weights()[0]  # (k, 3)
    salida = []
    for i in range(0, len(x), lote):
        a, _ = aux(np.asarray(x[i:i + lote], np.float32), training=False)
        a = np.asarray(a)
        wc = w[:, np.asarray(clases[i:i + lote])].T  # (n, k)
        salida.append(np.einsum("nhwk,nk->nhw", a, wc))
    mapas = np.concatenate(salida)
    return _normalizar(mapas) if normalizar else mapas


def _superponer(img, mapa):
    from PIL import Image
    import matplotlib

    grande = np.asarray(Image.fromarray((mapa * 255).astype(np.uint8)).resize(img.shape[:2][::-1], Image.BILINEAR))
    color = (matplotlib.colormaps["jet"](grande / 255.0)[..., :3] * 255).astype(np.uint8)
    return (0.55 * img + 0.45 * color).astype(np.uint8), grande


def mosaico(imgs, mapas, titulos, ruta_png, titulo):
    from avocadoia_modelo.figuras import plt

    n = len(imgs)
    fig, ejes = plt.subplots(max(n, 1), 3, figsize=(7.5, 2.5 * max(n, 1)), squeeze=False)
    for i in range(n):
        sup, grande = _superponer(imgs[i], mapas[i])
        for j, (im, t) in enumerate(((imgs[i], titulos[i]), (grande, "Grad-CAM++"), (sup, "Superposición"))):
            ejes[i][j].imshow(im, cmap="jet" if j == 1 else None, vmin=0, vmax=255)
            ejes[i][j].set_title(t if j == 0 else f"{t}", fontsize=7)
            ejes[i][j].axis("off")
    if n == 0:
        ejes[0][0].text(0.5, 0.5, "sin casos", ha="center")
        for e in ejes[0]:
            e.axis("off")
    fig.suptitle(titulo, fontsize=9)
    fig.tight_layout()
    os.makedirs(os.path.dirname(ruta_png), exist_ok=True)
    fig.savefig(ruta_png, dpi=110)
    plt.close(fig)


def generar(cfg, id_, ruta_cache, repo_datos, salida, verificacion=None):
    """Mapas Grad-CAM++ sobre prueba, mosaicos por clase y planilla de valoración (T044)."""
    import keras

    from avocadoia_modelo import preparacion

    modelo = keras.models.load_model(os.path.join(salida, "experimentos", id_, "mejor.keras"))
    d = preparacion.cargar(ruta_cache, "test")
    x = d["x"]
    logits = modelo.predict(x.astype(np.float32), batch_size=64, verbose=0)
    ruta_cal = os.path.join(repo_datos, "calibracion", id_, "calibracion.json")
    temperatura = leer_json(ruta_cal)["temperatura"] if os.path.exists(ruta_cal) else 1.0
    probs = softmax(logits, temperatura)
    pred = probs.argmax(axis=1)
    ex = cfg["explicacion"]
    muestra = seleccionar_muestra(d["y"], pred, cfg["evaluacion"]["semilla"], ex["n"])
    idx = [i for i, _ in muestra]
    aux = modelo_mapa(modelo)
    mapas = gradcam_pp(modelo, x[idx], pred[idx], aux) if idx else np.zeros((0, 7, 7))

    rutas = {}
    if verificacion and verificacion.get("huella_manifiesto"):
        norm = os.path.join(salida, "manifiestos", f"{verificacion['huella_manifiesto'][:8]}.csv")
        rutas = {f["sha256"]: f["ruta"] for f in leer_csv(norm)}
    destino = os.path.join(repo_datos, "explicaciones", id_)
    planilla, n = [], 0
    for c, clase in enumerate(CLASES):
        for tipo in ("acierto", "error"):
            sel = [(k, i) for k, (i, t) in enumerate(muestra) if t == tipo and d["y"][i] == c]
            nombre = f"mosaico_{clase}_{tipo}s.png"
            titulos = [f"real {ETIQUETAS_VISIBLES[c][:30]} · pred {ETIQUETAS_VISIBLES[pred[i]][:30]} · "
                       f"{probs[i].max():.2f}" for _, i in sel]
            mosaico(x[[i for _, i in sel]], mapas[[k for k, _ in sel]], titulos, os.path.join(destino, nombre),
                    f"{ETIQUETAS_VISIBLES[c]} — {tipo}s ({len(sel)})")
            for fila, (_, i) in enumerate(sel, start=1):
                n += 1
                sha = str(d["sha256"][i])
                planilla.append({"n": n, "sha256": sha, "ruta": rutas.get(sha, ""), "fuente": str(d["fuente"][i]),
                                 "clase_real": clase, "clase_predicha": CLASES[pred[i]],
                                 "confianza": round(float(probs[i].max()), 4), "tipo": tipo, "mosaico": nombre,
                                 "fila_mosaico": fila, "valoracion": "", "revisor": "", "fecha": "", "notas": ""})
    escribir_csv(os.path.join(destino, "planilla_explicaciones.csv"), COLUMNAS_PLANILLA, planilla)
    info = {"corrida": id_, "temperatura": temperatura, "confianza_calibrada": os.path.exists(ruta_cal),
            "n_mapas": len(planilla), "fecha": datetime.date.today().isoformat(),
            "instrucciones": "Valorar cada fila: lesion_fruto | fondo_ajeno | ambiguo; luego resumir-explicaciones"}
    escribir_json(os.path.join(destino, "generacion.json"), info)
    return info


def resumir_corrida(repo_datos, id_, umbral):
    destino = os.path.join(repo_datos, "explicaciones", id_)
    planilla = leer_csv(os.path.join(destino, "planilla_explicaciones.csv"))
    invalidas = sorted({f["valoracion"] for f in planilla if f["valoracion"] and f["valoracion"] not in VALORACIONES})
    if invalidas:
        raise ValueError(f"valoraciones no válidas {invalidas}; use {VALORACIONES}")
    res = resumir(planilla, umbral)
    escribir_json(os.path.join(destino, "resumen.json"), res)
    return res
