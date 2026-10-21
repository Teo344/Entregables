# Modelo de datos de la iteración

Este artefacto describe registros del pipeline de datos/modelo. No prescribe una base de datos concreta.

## Entidades

### Fuente de datos

Representa un dataset, repositorio o recolección propia.

| Campo | Tipo lógico | Regla |
|---|---|---|
| `source_id` | cadena | Obligatorio, estable y único. |
| `name` | cadena | Obligatorio. |
| `origin_uri` | cadena/URI | Enlace, referencia compartida o descripción reproducible del origen; no incluir credenciales. |
| `license` | cadena/null | Registrar licencia o `unknown`; no asumir permiso de redistribución. |
| `usage_conditions` | cadena | Condiciones y limitaciones conocidas. |
| `acquired_at` | fecha/null | Fecha de adquisición si se conoce. |
| `notes` | cadena | Contexto y evidencia de procedencia. |

### Imagen del conjunto

Cada archivo original y su copia derivada se vinculan por una fila de manifiesto. El identificador debe ser estable; el hash detecta duplicados o modificaciones.

| Campo | Tipo lógico | Regla |
|---|---|---|
| `image_id` | cadena | Obligatorio y único. |
| `source_id` | cadena | Referencia a Fuente de datos. |
| `original_path` | cadena | Ruta relativa dentro de la fuente preservada. |
| `original_filename` | cadena | Nombre original sin renombrar la fuente. |
| `working_path` | cadena/null | Ruta a copia derivada; null si está excluida o en cuarentena. |
| `sha256` | hexadecimal | Hash de bytes del archivo original. |
| `specimen_group_id` | cadena/null | Identificador de fruto/lote de captura si se conoce; se usa para prevenir fuga. |
| `capture_session_id` | cadena/null | Sesión de captura si se conoce. |
| `source_label` | cadena/null | Etiqueta original literalmente preservada. |
| `project_class` | enum/null | `healthy`, `anthracnose`, `peduncle_ring_compatible`; null si no validada. |
| `review_status` | enum | `pending`, `accepted`, `excluded`, `quarantined`. |
| `reviewer_role` | cadena/null | Rol de persona revisora; nombres solo si se autorizan y son necesarios. |
| `review_criteria_version` | cadena/null | Versión de criterios aplicados. |
| `review_note` | cadena/null | Evidencia/razón legible de aceptación, exclusión o discrepancia. |
| `split` | enum/null | `train`, `validation`, `test`; solo para aceptadas. |
| `created_at` | fecha/hora | Alta del registro. |

### Configuración de partición

| Campo | Tipo lógico | Regla |
|---|---|---|
| `split_id` | cadena | Identifica una ejecución de particionado. |
| `manifest_version` | cadena/hash | Identifica entradas aceptadas. |
| `ratios` | objeto | Inicialmente train 0.70, validation 0.15, test 0.15; suma 1.0. |
| `seed` | entero | 42 inicialmente. |
| `grouping_key` | cadena | Llave usada para agrupar por espécimen/sesión, o motivo si no estaba disponible. |
| `class_counts` | objeto | Conteos reales por clase y split luego de redondeo/agrupación. |
| `created_at` | fecha/hora | Momento de la ejecución. |

### Experimento de modelo

| Campo | Tipo lógico | Regla |
|---|---|---|
| `experiment_id` | cadena | Identificador único. |
| `architecture` | enum | `MobileNetV3` o `EfficientNet-B0`. |
| `config` | objeto | Preprocesamiento, resolución, pesos iniciales, aumentos, hiperparámetros. |
| `software_environment` | objeto | Python, TensorFlow/Keras, librerías y runtime/accelerator. |
| `dataset_manifest_version` | cadena/hash | Manifiesto y partición evaluados. |
| `class_order` | lista | Orden fijo de salida y métricas. |
| `artifact_uri` | cadena/null | Ubicación del modelo/checkpoint. |
| `selected_by_validation` | booleano | Selección usa validación; no test. |

### Informe de evaluación

| Campo | Tipo lógico | Regla |
|---|---|---|
| `experiment_id` | cadena | Referencia al experimento. |
| `evaluated_split` | enum | `validation` o `test`; test se ejecuta para evaluación final. |
| `accuracy` | número | Reportar junto con conteo y protocolo. |
| `precision_per_class`, `recall_per_class`, `f1_per_class` | mapas | Una entrada por clase y soporte. |
| `macro_precision`, `macro_recall`, `macro_f1` | número | Métricas agregadas requeridas. |
| `confusion_matrix` | matriz | Orden de clases declarado. |
| `roc_auc_ovr_macro` | número/null | Nulo si no es calculable; registrar motivo. |
| `calibration` | objeto | Medidas/método y limitaciones. |
| `generalization_notes` | cadena | Errores, dominios y límites. |
| `mobile_efficiency` | objeto/null | Tamaño, latencia y dispositivo/runtime; null si aún no medido. |

## Relaciones y estados

- Una Fuente de datos contiene muchas Imágenes del conjunto.
- Una Imagen aceptada pertenece a exactamente una partición en una versión del split; las imágenes pendientes, excluidas o en cuarentena no tienen split.
- Una imagen relacionada con un grupo de espécimen/sesión comparte una partición con todas las imágenes del grupo.
- Un Experimento usa una versión concreta del manifiesto y de la partición. Varios experimentos comparables comparten ambas.
- Un Informe de evaluación corresponde a un Experimento y a un split.

Flujo de revisión: `pending` → `accepted`, `excluded` o `quarantined`. Solo `accepted` con clase validada participa en particionado. La clase `peduncle_ring_compatible` permanece ausente hasta contar con fuente y criterio documentados; no se crea a partir de `Scab`.

## Invariantes

1. Ningún archivo de origen se renombra, edita o sobrescribe durante este flujo.
2. `project_class` es nulo mientras la asignación no esté verificada.
3. Solo imágenes `accepted` con hash, fuente y clase admitida pueden entrar a los splits.
4. No se distribuyen grupos de espécimen/sesión entre splits.
5. La lista ordenada de clases y el mapeo de salida se registran con cada experimento.
6. El conjunto test no se utiliza para escoger arquitectura, umbral ni hiperparámetros.
