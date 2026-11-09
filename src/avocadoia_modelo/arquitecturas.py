"""MobileNetV3Large / EfficientNetB0 + cabeza de logits en un modelo funcional plano (research M6).

El modelo base se construye sobre el mismo tensor de entrada (input_tensor), de modo que sus capas quedan en
el grafo del modelo final sin anidar: así Grad-CAM++ puede leer el último mapa de características y la
congelación de BatchNorm se controla capa a capa. La salida son LOGITS (sin softmax) para Temperature Scaling.
"""

import keras

from avocadoia_modelo import CLASES

ARQUITECTURAS = ("mobilenetv3", "efficientnetb0")


def _base(arquitectura, entrada, pesos):
    if arquitectura == "mobilenetv3":
        return keras.applications.MobileNetV3Large(input_tensor=entrada, include_top=False, weights=pesos,
                                                   include_preprocessing=True, minimalistic=False)
    if arquitectura == "efficientnetb0":
        return keras.applications.EfficientNetB0(input_tensor=entrada, include_top=False, weights=pesos)
    raise ValueError(f"arquitectura desconocida: {arquitectura}")


def construir(arquitectura, dropout=0.3, pesos="imagenet", tamano=224):
    """Devuelve (modelo, capas_base, nombre_capa_mapa)."""
    entrada = keras.Input((tamano, tamano, 3), name="imagen")
    base = _base(arquitectura, entrada, pesos)
    mapa = base.output
    x = keras.layers.GlobalAveragePooling2D(name="gap")(mapa)
    x = keras.layers.Dropout(dropout, name="dropout")(x)
    logits = keras.layers.Dense(len(CLASES), name="logits")(x)
    modelo = keras.Model(entrada, logits, name=arquitectura)
    capas_base = [c for c in base.layers if not isinstance(c, keras.layers.InputLayer)]
    return modelo, capas_base, capas_base[-1].name


def capas_del_modelo_base(modelo):
    """Capas del modelo base dentro de un modelo ya construido o cargado (todas menos entrada y cabeza)."""
    return [c for c in modelo.layers
            if not isinstance(c, keras.layers.InputLayer) and c.name not in ("gap", "dropout", "logits")]


def nombre_capa_mapa(modelo):
    return capas_del_modelo_base(modelo)[-1].name


def congelar_fase1(capas_base):
    for c in capas_base:
        c.trainable = False


def descongelar_fase2(capas_base, fraccion):
    """Descongela el `fraccion` final de capas del modelo base salvo BatchNormalization (research M7)."""
    corte = int(round(len(capas_base) * (1.0 - fraccion)))
    for i, c in enumerate(capas_base):
        c.trainable = i >= corte and not isinstance(c, keras.layers.BatchNormalization)
    return sum(c.trainable for c in capas_base)
