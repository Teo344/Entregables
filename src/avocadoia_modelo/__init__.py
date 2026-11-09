"""Modelo clasificador de AvocadoIA (spec 003): entrenamiento, calibración, explicación y exportación.

TensorFlow NO se importa aquí: solo en datos_tf, arquitecturas, entrenamiento, evaluacion, explicacion y
exportacion, para que la lógica determinista y sus pruebas funcionen sin él (plan, Structure Decision).
"""

# Orden fijo de las salidas del modelo (research M3); no cambiarlo sin versionar el contrato TFLite.
CLASES = ("sano", "antracnosis", "pedunculo")

# Etiquetas para toda salida visible (figuras, tablas, informes); término obligatorio de la constitución.
ETIQUETAS_VISIBLES = ("Sano", "Antracnosis", "Síntomas compatibles con anillado del pedúnculo")

PARTICIONES = ("train", "val", "test")
