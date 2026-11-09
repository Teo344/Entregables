# Contrato del modelo exportado (para la app)

**Feature**: 003-modelo-clasificador | Consumidor: funcionalidad de la app Flutter (futura)

## Archivos

- `avocadoia_<variante>.tflite`
- `metadatos.json`: viaja siempre junto al `.tflite`.

## Firma `clasificar` (obligatoria)

| | Tensor | Tipo | Forma | Contenido |
| --- | --- | --- | --- | --- |
| Entrada | `imagen` | float32 | `[1, 224, 224, 3]` | RGB **0–255**, sin normalizar |
| Salida | `probabilidades` | float32 | `[1, 3]` | Probabilidades **ya calibradas** (`softmax(logits / T)`) en el orden de `clases` |

**Preprocesamiento que DEBE hacer la app**: decodificar la foto, aplicar la orientación EXIF, convertir
a RGB y redimensionar a 224 × 224 **estirando, sin recorte ni relleno** (filtro bilineal o superior). No
dividir entre 255 ni restar medias: el modelo lo hace internamente.

**Regla de decisión**: si `max(probabilidades) < umbral`, la app muestra "resultado no concluyente"; si
no, la clase del máximo con su porcentaje.

## Firma `explain` (opcional; depende del spike M14)

| | Tensor | Tipo | Forma | Contenido |
| --- | --- | --- | --- | --- |
| Entrada | `imagen` | float32 | `[1, 224, 224, 3]` | Igual que `clasificar` |
| Salida | `probabilidades` | float32 | `[1, 3]` | Igual que `clasificar` |
| Salida | `mapa` | float32 | `[1, 7, 7]` | Mapa de la clase predicha, normalizado a 0–1; la app lo escala a 224 × 224 y lo superpone |

`metadatos.json → explicacion.metodo` indica `gradcam++` o `cam`.

## `metadatos.json`

```json
{
  "version_contrato": "1.0",
  "corrida": "20261110-0930_mobilenetv3_s42_ab12cd34",
  "arquitectura": "mobilenetv3",
  "variante": "fp16",
  "clases": ["sano", "antracnosis", "pedunculo"],
  "etiquetas_visibles": ["Sano", "Antracnosis", "Síntomas compatibles con anillado del pedúnculo"],
  "entrada": {"tamano": 224, "rango": [0, 255], "redimensionado": "estirar", "canales": "RGB"},
  "calibracion": {"metodo": "temperature_scaling", "temperatura": 1.37, "embebida": true},
  "umbral_no_concluyente": 0.60,
  "explicacion": {"firma": "explain", "metodo": "cam"},
  "metricas_test": {"macro_f1": 0.0, "ece_calibrado": 0.0, "experimental": true},
  "huella_manifiesto": "…",
  "fecha": "2026-11-10"
}
```

Cambios incompatibles en firmas o metadatos incrementan `version_contrato` en su número mayor.
