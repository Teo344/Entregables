"""Exportación a TensorFlow Lite y spike de la firma `explain` (research M14, M15; contracts/modelo-tflite.md).

El modelo de inferencia recibe float32 [1, 224, 224, 3] en 0–255 y devuelve probabilidades calibradas
softmax(logits / T). La firma `explain` añade el mapa [1, 7, 7] de la clase predicha, con Grad-CAM++
(gradientes dentro del grafo) o con CAM (plan B, solo operaciones de inferencia).
"""

import datetime
import os
import shutil
import tempfile
import time

import numpy as np

from avocadoia_datos.es_csv import escribir_json

FIRMA = ("imagen", (1, 224, 224, 3))


def _funciones(modelo, temperatura, metodo):
    import tensorflow as tf

    from avocadoia_modelo.explicacion import modelo_mapa

    aux = modelo_mapa(modelo)
    kernel = modelo.get_layer("logits").kernel  # (k, 3)
    t = tf.constant(float(temperatura))

    def clasificar(imagen):
        _, logits = aux(imagen, training=False)
        return {"probabilidades": tf.nn.softmax(logits / t)}

    def _normalizar(m):
        return m / (tf.reduce_max(m, axis=(1, 2), keepdims=True) + 1e-12)

    def explain(imagen):
        if metodo == "gradientes":
            with tf.GradientTape() as cinta:
                cinta.watch(imagen)
                a, logits = aux(imagen, training=False)
                clase = tf.argmax(logits, axis=1, output_type=tf.int32)
                score = tf.gather(logits, clase, batch_dims=1)
            g = cinta.gradient(score, a)
            g2, g3 = g ** 2, g ** 3
            denom = 2.0 * g2 + tf.reduce_sum(a, axis=(1, 2), keepdims=True) * g3
            alfa = tf.math.divide_no_nan(g2, denom)
            pesos = tf.reduce_sum(alfa * tf.nn.relu(g), axis=(1, 2))
            mapa = tf.nn.relu(tf.reduce_sum(pesos[:, None, None, :] * a, axis=-1))
        else:
            a, logits = aux(imagen, training=False)
            clase = tf.argmax(logits, axis=1, output_type=tf.int32)
            wc = tf.transpose(tf.gather(kernel, clase, axis=1))  # (n, k)
            mapa = tf.nn.relu(tf.einsum("nhwk,nk->nhw", a, wc))
        return {"probabilidades": tf.nn.softmax(logits / t), "mapa": _normalizar(mapa)}

    return aux, clasificar, explain


def exportar_saved_model(modelo, destino, temperatura=1.0, explain=None):
    """SavedModel con firma `clasificar` y, si explain ∈ {gradientes, cam}, también `explain`."""
    import keras
    import tensorflow as tf

    aux, clasificar, fn_explain = _funciones(modelo, temperatura, explain or "cam")
    firma = [tf.TensorSpec(FIRMA[1], tf.float32, name=FIRMA[0])]
    archivo = keras.export.ExportArchive()
    archivo.track(modelo)
    archivo.track(aux)
    archivo.add_endpoint("clasificar", tf.function(clasificar), input_signature=firma)
    if explain:
        archivo.add_endpoint("explain", tf.function(fn_explain), input_signature=firma)
    archivo.write_out(destino, verbose=False)
    return destino


def convertir(ruta_saved_model, variante="fp32", firmas=("clasificar",)):
    """bytes del .tflite; solo operaciones nativas de TFLite (las que trae el intérprete de la app)."""
    import tensorflow as tf

    conv = tf.lite.TFLiteConverter.from_saved_model(ruta_saved_model, signature_keys=list(firmas))
    conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS]
    if variante in ("fp16", "int8-dinamico"):
        conv.optimizations = [tf.lite.Optimize.DEFAULT]
    if variante == "fp16":
        conv.target_spec.supported_types = [tf.float16]
    return conv.convert()


def ejecutar_firma(tflite, firma, imagen):
    import tensorflow as tf

    interprete = tf.lite.Interpreter(model_content=tflite)
    return interprete.get_signature_runner(firma)(imagen=np.asarray(imagen, np.float32))


def spike_explain(cfg, ruta_cache, repo_datos, salida, id_=None, pesos="imagenet", n_comparar=20):
    """Prueba la firma `explain` con gradientes y con CAM; documenta conversión, tamaño y concordancia (T030)."""
    import keras

    from avocadoia_modelo import arquitecturas, preparacion
    from avocadoia_modelo.explicacion import concordancia, gradcam_pp, modelo_mapa

    va = preparacion.cargar(ruta_cache, "val")
    if id_:
        modelo = keras.models.load_model(os.path.join(salida, "experimentos", id_, "mejor.keras"))
        origen = f"corrida {id_}"
    else:  # modelo de 1 época solo para probar la conversión
        tr = preparacion.cargar(ruta_cache, "train")
        keras.utils.set_random_seed(42)
        modelo, capas, _ = arquitecturas.construir("mobilenetv3", cfg["modelo"]["dropout"], pesos)
        arquitecturas.congelar_fase1(capas)
        modelo.compile(optimizer=keras.optimizers.Adam(1e-3),
                       loss=keras.losses.SparseCategoricalCrossentropy(from_logits=True))
        modelo.fit(tr["x"].astype(np.float32), tr["y"].astype(np.int32), epochs=1, batch_size=8, verbose=0)
        origen = "modelo de 1 época (mobilenetv3)"

    tmp = tempfile.mkdtemp(prefix="spike_explain_")
    resultado = {"origen": origen, "fecha": datetime.date.today().isoformat()}
    try:
        base = convertir(exportar_saved_model(modelo, os.path.join(tmp, "base")))
        resultado["tamano_base_mb"] = round(len(base) / 2**20, 3)
        idx = np.arange(min(n_comparar, len(va["y"])))
        x = va["x"][idx].astype(np.float32)
        aux = modelo_mapa(modelo)
        pred = modelo.predict(x, verbose=0).argmax(axis=1)
        referencia = gradcam_pp(modelo, x, pred, aux)
        mapas_tflite = {}
        for metodo, clave in (("gradientes", "variante_gradientes"), ("cam", "variante_cam")):
            info = {"convierte": False, "error": "", "tamano_extra_mb": None}
            try:
                inicio = time.time()
                tfl = convertir(exportar_saved_model(modelo, os.path.join(tmp, metodo), 1.0, metodo),
                                firmas=("clasificar", "explain"))
                info.update(convierte=True, tamano_extra_mb=round((len(tfl) - len(base)) / 2**20, 3),
                            segundos_conversion=round(time.time() - inicio, 1))
                mapas = np.concatenate([ejecutar_firma(tfl, "explain", x[i:i + 1])["mapa"] for i in range(len(x))])
                mapas_tflite[metodo] = mapas
                conc = [concordancia(referencia[i], mapas[i]) for i in range(len(x))]
                info.update(pearson_medio=round(float(np.mean([c["pearson"] for c in conc])), 4),
                            iou_top20_medio=round(float(np.mean([c["iou_top"] for c in conc])), 4))
            except Exception as e:  # noqa: BLE001 - el fallo de conversión ES el resultado del spike
                info["error"] = f"{type(e).__name__}: {str(e)[:600]}"
            resultado[clave] = info
        g, c = resultado["variante_gradientes"], resultado["variante_cam"]
        if g["convierte"] and g.get("pearson_medio", 0) >= 0.9:
            resultado.update(decision="gradcam++", plan_b_aplicado=False)
        elif c["convierte"]:
            resultado.update(decision="cam", plan_b_aplicado=True)
        else:
            resultado.update(decision="sin_explain", plan_b_aplicado=True)
        destino = os.path.join(repo_datos, "spike_explain")
        _figura_spike(va["x"][idx][:6], referencia[:6], {k: v[:6] for k, v in mapas_tflite.items()},
                      os.path.join(destino, "comparacion.png"))
        escribir_json(os.path.join(destino, "resultado.json"), resultado)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return resultado


def _figura_spike(imgs, referencia, mapas, ruta):
    from avocadoia_modelo.explicacion import _superponer
    from avocadoia_modelo.figuras import plt

    columnas = [("Imagen", None), ("Grad-CAM++ (Python)", referencia)] + [(f"TFLite {k}", v) for k, v in mapas.items()]
    fig, ejes = plt.subplots(len(imgs), len(columnas), figsize=(2.4 * len(columnas), 2.4 * len(imgs)), squeeze=False)
    for i, img in enumerate(imgs):
        for j, (titulo, m) in enumerate(columnas):
            ejes[i][j].imshow(img if m is None else _superponer(img, m[i])[0])
            ejes[i][j].set_title(titulo, fontsize=7)
            ejes[i][j].axis("off")
    fig.tight_layout()
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    fig.savefig(ruta, dpi=110)
    plt.close(fig)
