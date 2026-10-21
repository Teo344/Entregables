# Contrato de inferencia del modelo

**Estado**: preliminar para la integración móvil posterior. La implementación de esta iteración termina en la comparación y selección del candidato; el formato de exportación se decidirá con pruebas en el dispositivo Android objetivo.

## Propósito

Mantener coherencia entre preprocesamiento, orden de clases y salida del modelo de entrenamiento y la futura aplicación Android offline.

## Entrada

- Una imagen RGB decodificada desde cámara o galería.
- El adaptador de inferencia debe aplicar exactamente el tamaño, normalización y orden de canales definidos en el artefacto elegido; esos parámetros se exportan como metadatos junto al modelo.
- La aplicación valida que la imagen sea legible y comunica fallos de decodificación. La detección de desenfoque/iluminación y rechazo de imagen requiere umbrales evaluados antes de fijarse.

## Salida

La respuesta lógica incluye:

| Campo | Tipo | Regla |
|---|---|---|
| `class_id` | cadena | Una de las clases del artefacto/versionado. |
| `class_probabilities` | mapa de cadena a número | Probabilidades/scores en el orden documentado; su significado depende de calibración. |
| `confidence` | número o null | Si se presenta, indicar su definición. No equivale por sí sola a probabilidad de diagnóstico correcto. |
| `abstained` | booleano | Activado solo con criterio de rechazo calibrado y documentado; inicialmente pendiente. |
| `model_version` | cadena | Identificador de modelo, clases y preprocesamiento. |
| `heatmap` | objeto o null | Grad-CAM++ opcional; si existe, asociado a imagen y clase exactas. |

## Orden de clases del producto

El objetivo de producto define el siguiente orden estable:

1. `healthy` — fruto visualmente sano respecto de las condiciones cubiertas.
2. `anthracnose` — clase con etiqueta y definición de fuente verificadas.
3. `peduncle_ring_compatible` — síntomas visualmente compatibles con anillado del pedúnculo, solo cuando exista fuente y revisión técnica verificables.

El orden no obliga a entrenar una clase sin datos confiables. Un artefacto de investigación con menos de tres clases debe declarar explícitamente su orden reducido, no puede etiquetarse como modelo final del alcance de producto ni integrarse para aparentar soporte de las tres clases.

## Invariantes

- La app no cambia ni reinterpreta el orden de salida de un modelo.
- La clase predicha se presenta como orientación, no diagnóstico fitosanitario definitivo.
- No se muestra umbral de abstención hasta definirlo mediante validación/calibración sin usar el conjunto test.
- Un mapa de calor es una visualización de regiones asociadas a la salida; no demuestra causalidad, enfermedad ni precisión adicional.
- El flujo de inferencia previsto debe funcionar sin internet. Runtime, cuantización y mínimo Android se congelan después de pruebas en dispositivo.
