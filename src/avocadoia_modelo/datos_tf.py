"""tf.data desde la caché y aumento solo en entrenamiento (research M8; FR-009). Requiere TensorFlow.

Las imágenes entran como float32 en rango 0–255 SIN normalizar: MobileNetV3 y EfficientNet reescalan dentro del
modelo (research M6).
"""

import keras
import tensorflow as tf


def capas_aumento(aum, semilla):
    if aum.get("volteo_horizontal") and aum.get("volteo_vertical"):
        modo = "horizontal_and_vertical"
    elif aum.get("volteo_vertical"):
        modo = "vertical"
    else:
        modo = "horizontal"
    capas = [
        keras.layers.RandomFlip(modo, seed=semilla),
        keras.layers.RandomRotation(aum["rotacion_grados"] / 360.0, fill_mode="reflect", seed=semilla + 1),
        keras.layers.RandomTranslation(aum["traslacion"], aum["traslacion"], fill_mode="reflect", seed=semilla + 2),
        keras.layers.RandomZoom(aum["zoom"], fill_mode="reflect", seed=semilla + 3),
        keras.layers.RandomBrightness(aum["brillo"], value_range=(0.0, 255.0), seed=semilla + 4),
        keras.layers.RandomContrast(aum["contraste"], value_range=(0.0, 255.0), seed=semilla + 5),
    ]
    return keras.Sequential(capas, name="aumento")


def dataset_entrenamiento(x, y, lote, semilla, aumento):
    aug = capas_aumento(aumento, semilla)
    ds = tf.data.Dataset.from_tensor_slices((x, y.astype("int32")))
    ds = ds.shuffle(len(x), seed=semilla, reshuffle_each_iteration=True).batch(lote)
    ds = ds.map(lambda a, b: (aug(tf.cast(a, tf.float32), training=True), b))
    return ds.prefetch(tf.data.AUTOTUNE)


def dataset_evaluacion(x, y, lote=64):
    ds = tf.data.Dataset.from_tensor_slices((x, y.astype("int32"))).batch(lote)
    return ds.map(lambda a, b: (tf.cast(a, tf.float32), b)).prefetch(tf.data.AUTOTUNE)
