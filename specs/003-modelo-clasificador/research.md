# Research: Construcción, calibración y exportación del modelo clasificador

**Feature**: 003-modelo-clasificador | **Fecha**: 2026-11-09

Cada decisión se identifica como **M<n>** para citarla desde el plan, las tareas y el código.

---

## M1. Paquete nuevo `avocadoia_modelo` dentro de la misma distribución

- **Decision**: crear `src/avocadoia_modelo/` como segundo paquete de la distribución existente
  (`pyproject.toml`), con un grupo opcional `[modelo]`. TensorFlow se importa solo en los módulos de
  entrenamiento, explicación y exportación; manifiesto, métricas, calibración, selección y registro son
  NumPy puro.
- **Rationale**: separa el código del modelo del pipeline de datos sin crear otro repositorio ni otro
  `pyproject`. Las pruebas de lógica determinista corren sin TensorFlow (FR-024).
- **Alternatives considered**: subpaquete `avocadoia_datos.modelo` (mezcla responsabilidades: el paquete se
  llama "datos"); repositorio aparte (rompe la trazabilidad con el manifiesto y duplica la configuración).

## M2. Manifiesto normalizado con adaptador configurable

- **Decision**: el entrenamiento consume un **manifiesto normalizado** con las columnas `ruta, clase,
  particion, sha256, fuente, estado_etiqueta, grupo`. Un adaptador lo construye a partir de cualquier CSV
  de entrada mediante un mapeo de columnas declarado en `config/modelo.toml`. Para el split v4:
  `ruta_destino → ruta`, `clase_original → clase`, `conjunto → particion`, `sha256 → sha256`,
  `estado_etiqueta → estado_etiqueta`, `grupo_duplicacion_escena → grupo`. La `fuente` **no** se toma
  de `procedencia` (en el v4 contiene nombres de reportes CSV, no de fuentes): se determina con M19.
- **Rationale**: cumple FR-001/FR-002 y permite sustituir el v4 por su versión corregida (o por
  `datos/particion.csv`) sin tocar código.
- **Alternatives considered**: leer el v4 tal cual (acopla el código a un formato provisional); recorrer
  carpetas (pierde trazabilidad, principio II).

## M3. Equivalencia de clases explícita

- **Decision**: tabla en `config/modelo.toml`:
  `AGUACATESANOS|sano → sano`, `ANTRACNOSIS|antracnosis → antracnosis`,
  `PEDUNCULO|pedunculo → pedunculo`. El orden de salida del modelo es fijo:
  `[sano, antracnosis, pedunculo]`; la etiqueta visible de la tercera clase es "síntomas compatibles con
  anillado del pedúnculo". Un nombre fuera de la tabla aborta (FR-002).
- **Rationale**: evita errores silenciosos de orden de clases entre entrenamiento, exportación y app.

## M4. Verificación previa y aviso de fuga por fruto

- **Decision**: el comando `verificar` comprueba (a) existencia y legibilidad de cada imagen, (b) que
  ningún SHA-256 aparece en dos particiones (aborta), (c) clases conocidas (aborta) y (d) **avisa** —sin
  abortar— de frutos que cruzan particiones usando los grupos de `datos/manifiesto.csv` (spec 001/002)
  cruzados por SHA-256. Hoy detecta 89 grupos / 76 imágenes de prueba en el v4. El resultado queda en
  `datos/modelo/verificacion.json` y su resumen entra en cada registro de experimento.
- **Rationale**: FR-003 exige abortar por duplicados exactos; la fuga por fruto es una observación abierta
  del compañero (spec, Supuestos) y debe ser visible en cada métrica que se reporte.

## M5. Redimensionado único a 224 × 224 y caché de tensores

- **Decision**: las imágenes del v4 están en su tamaño original (300–3072 px, algunas no cuadradas). El
  comando `preparar` las convierte **una vez** a RGB 224 × 224 con `Pillow LANCZOS` **sin recorte ni
  relleno** (el mismo criterio que `preprocesamiento.cargar_224` de 001/002) y guarda un `.npz` por
  partición (`uint8`, ~110 MB en total) con la huella `sha256(manifiesto) + tamaño + método`. El
  entrenamiento lee solo la caché.
- **Rationale**: decodificar fotos de 3 072 px desde Drive en cada época haría las corridas lentas e
  irreproducibles por tiempos de E/S. Mantener el mismo redimensionado que la etapa de datos evita una
  segunda convención. La app debe aplicar el mismo redimensionado (se documenta en el contrato TFLite).
- **Alternatives considered**: `tf.image.resize_with_pad` (agrega bordes negros que la app tendría que
  imitar); recorte central (puede cortar la lesión o el pedúnculo en el borde); `tf.data` desde JPEG con
  `cache()` (depende de la sesión de Colab y se pierde al reiniciar).

## M6. Arquitecturas: MobileNetV3Large y EfficientNetB0 sin anidar

- **Decision**: `keras.applications.MobileNetV3Large(include_top=False, include_preprocessing=True,
  minimalistic=False)` y `keras.applications.EfficientNetB0(include_top=False)`, pesos ImageNet,
  entrada `224×224×3` en rango **0–255** (ambos reescalan internamente). La cabeza se construye sobre
  `base.output` en un único modelo funcional (sin anidar el modelo base como capa):
  `GlobalAveragePooling2D → Dropout(0.3) → Dense(3)` **sin activación** (logits).
- **Rationale**: (1) no normalizar por fuera evita el doble reescalado; (2) un modelo plano permite leer
  el mapa de características final para Grad-CAM++ sin trucos con submodelos de Keras 3; (3) emitir logits
  es necesario para Temperature Scaling (M10).
- **Alternatives considered**: MobileNetV3Small (menor exactitud; la diferencia de tamaño no es
  necesaria con cuantización); modelo base anidado (complica Grad-CAM++ y la congelación de BN).

## M7. Entrenamiento en dos fases y congelación de BatchNorm

- **Decision**: fase 1 con todas las capas del modelo base congeladas (Adam 1e-3, 15 épocas); fase 2
  descongela el 30 % final de las capas del modelo base **excepto** las `BatchNormalization`, que siguen
  con `trainable=False` (en Keras 3 eso las fija en modo inferencia), Adam 1e-5, hasta 30 épocas.
  Pérdida `SparseCategoricalCrossentropy(from_logits=True)` con `class_weight = n / (k · n_c)` calculado
  sobre entrenamiento. Callbacks: `EarlyStopping(val_loss, patience=5, restore_best_weights=True)`,
  `ReduceLROnPlateau(val_loss, factor=0.5, patience=2, min_lr=1e-7)`, `ModelCheckpoint` del mejor
  modelo y `BackupAndRestore` para reanudar si Colab se desconecta (FR-011). Lote 32.
- **Rationale**: receta estándar de transferencia de aprendizaje; descongelar BN con lotes pequeños
  degrada las estadísticas de ImageNet. `BackupAndRestore` resuelve el caso borde de la sesión
  interrumpida sin código propio.

## M8. Aumento de datos fuera del modelo exportado

- **Decision**: capas de aumento de Keras (`RandomFlip("horizontal_and_vertical")`,
  `RandomRotation(45°)`, `RandomTranslation(0.2)`, `RandomZoom(0.2)`, `RandomBrightness(0.2,
  value_range=(0,255))`, `RandomContrast(0.2)`) aplicadas en el `tf.data` **solo de entrenamiento**, con
  la semilla de la corrida. Los valores repiten la sección `[aumento]` de `config/dataset.toml` (002) más
  contraste.
- **Rationale**: cumple FR-009 y deja el modelo exportado libre de capas de aumento. Se mantiene la rotación
  de 45° (no los ±20° sugeridos en la conversación inicial) por coherencia con la 002 y porque los frutos se
  fotografían en cualquier orientación; la traslación de 0,2 compensa encuadres descentrados. Ambos valores son
  iguales para las dos arquitecturas (principio III) y pueden ajustarse en `config/modelo.toml` antes de la
  comparación, nunca entre corridas de una misma comparación (hallazgo I2).

## M9. Reproducibilidad y semillas

- **Decision**: `keras.utils.set_random_seed(semilla)` y
  `tf.config.experimental.enable_op_determinism()` (configurable: `deterministico = true` por defecto);
  el orden de los datos y el aumento derivan de la semilla. Cada corrida registra: configuración
  completa, huella del manifiesto, huella de la caché, versiones (Python, TF, Keras, NumPy, CUDA/cuDNN),
  GPU y resultado de `verificar`. Identificador:
  `AAAAMMDD-HHMM_<arquitectura>_s<semilla>_<huella8>`.
- **Rationale**: SC-006 admite ≤ 1 punto de macro-F1 de variación; el determinismo de operaciones en GPU
  reduce la variación a casi cero a costa de ~10–20 % de velocidad, aceptable con 998 imágenes de entrenamiento.

## M10. Calibración: Temperature Scaling en NumPy

- **Decision**: se guardan los logits de validación y prueba de cada corrida (`.npz`). La temperatura
  `T` minimiza la NLL en **validación** con búsqueda de sección áurea sobre `log T ∈ [log 0.05, log 20]`
  (determinista, sin SciPy). ECE con 15 intervalos de igual ancho sobre la confianza máxima; se reporta
  antes y después en validación y prueba, junto con el diagrama de fiabilidad y la NLL y Brier.
- **Rationale**: un solo parámetro no cambia el argmax (la exactitud no varía) y es fácil de embeber en
  el modelo exportado. Implementarlo en NumPy permite pruebas unitarias sin TensorFlow.
- **Alternatives considered**: Platt/vector scaling (más parámetros con solo ~330 imágenes de
  validación); `tfp` (otra dependencia).

## M11. Umbral de "no concluyente" con curva cobertura–exactitud

- **Decision**: sobre validación calibrada se calcula, para umbrales 0,34–0,99, la cobertura (fracción
  con confianza ≥ umbral) y la exactitud de las aceptadas. Se reporta el punto 0,60 y el umbral mínimo
  que alcanza exactitud ≥ 95 % en las aceptadas, como alternativa justificada. El umbral elegido se
  registra y viaja en los metadatos del modelo exportado.

## M12. Métricas, intervalos y regla de selección

- **Decision**: métricas en NumPy: matriz de confusión, precisión/recall/F1 por clase, macro-F1,
  exactitud, y desglose por fuente cuando hay ≥ 10 imágenes de esa fuente en la partición. Intervalo de
  confianza del 95 % por **bootstrap** (1 000 remuestreos, semilla 42) para macro-F1 y recall por clase
  (relevante para pedúnculo con ~31 imágenes de prueba). Las métricas sobre etiquetas provisionales se
  rotulan "experimentales". Selección: mayor macro-F1 **medio de validación** de las 3 semillas; si la
  diferencia es < 0,02, gana la arquitectura con menor tamaño del modelo exportado en media precisión. El
  conjunto de prueba solo se lee en `evaluar`, `calibrar` (para reportar, no para ajustar) y `exportar`.
- **Rationale**: FR-012–FR-015; separar selección (validación) de reporte (prueba) cumple FR-005.

## M13. Explicabilidad: Grad-CAM++ de referencia y CAM exportable

- **Decision**: Grad-CAM++ se calcula en TensorFlow con `GradientTape` sobre `base.output` (el último
  mapa de características). Muestra con semilla 42: hasta 10 aciertos y 10 errores por clase en prueba.
  Salidas: mosaico PNG por clase (imagen, mapa, superposición) y `planilla_explicaciones.csv` con
  columnas de valoración (`lesion_fruto | fondo_ajeno | ambiguo`, revisor, fecha). El resumen calcula el
  % de aciertos con foco en fondo/ajeno por clase y marca "posible atajo" si supera el 20 %.
- **Rationale**: FR-018, SC-005 y principio IV.

## M14. Spike de la firma `explain` (FR-022) y plan B

- **Decision**: probar dos variantes:
  1. **Grad-CAM++ con gradientes dentro de TFLite**: un `tf.Module` con firmas `clasificar` y `explain`
     que llama a `GradientTape`. Riesgo alto: el conversor de TFLite no garantiza soportar operaciones de
     gradiente.
  2. **Plan B: CAM sin gradientes**. Como la cabeza es `GAP → Dense`, el mapa de activación de clase
     `CAM_c = Σ_k w_k^c · A_k` es exacto y solo usa operaciones de inferencia (multiplicación y suma), por
     lo que convierte sin problemas. Se mide su correlación (Pearson y IoU del 20 % superior) frente a
     Grad-CAM++ calculado en Python.
  El spike se hace **temprano**, con un modelo de 1 época, y documenta tamaño extra, latencia y
  concordancia. Si la variante 1 falla, la firma `explain` del modelo de producción usa la variante 2.
- **Rationale**: elimina el riesgo técnico más incierto de la constitución con un plan B que no requiere
  servidor (principio I).

### M14.1 Resultado del spike (2026-11-09, corrida `20261109-2246_mobilenetv3_s42_6691b967`)

- **Grad-CAM++ con gradientes dentro del grafo SÍ convierte** a TFLite usando solo `TFLITE_BUILTINS`
  (sin operaciones de TensorFlow seleccionadas): +0,058 MB sobre el modelo base de 11,3 MB (fp32); el mapa de
  la firma `explain` coincide con el calculado en Python (Pearson 1,0; IoU del 20 % superior 1,0) en 20
  imágenes de validación. Conversión ≈ 10 s en CPU.
- CAM también convierte (+0,055 MB) pero concuerda menos con Grad-CAM++ (Pearson 0,88; IoU 0,75).
- **Decisión**: la firma `explain` del modelo de producción usa **Grad-CAM++** (`metadatos.json →
  explicacion.metodo = "gradcam++"`); el plan B no se aplica. Evidencia en `datos/modelo/spike_explain/`.

## M15. Exportación a TFLite con calibración embebida

- **Decision**: se construye un modelo de inferencia `entrada float32 [1,224,224,3] (0–255) →
  softmax(logits / T)`, se exporta como SavedModel (`model.export`) y se convierte con
  `tf.lite.TFLiteConverter.from_saved_model` en tres variantes: `fp32`, `fp16`
  (`optimizations=[DEFAULT]`, `supported_types=[float16]`) e `int8-dinamico`
  (`optimizations=[DEFAULT]`). Cada variante se evalúa con `tf.lite.Interpreter` sobre prueba (macro-F1,
  exactitud, diferencia frente a Keras) y se mide su tamaño. Producción: la más liviana con pérdida ≤ 1
  punto y ≤ 10 MB. Junto al `.tflite` se escribe `metadatos.json` (contrato
  [contracts/modelo-tflite.md](contracts/modelo-tflite.md)).
- **Rationale**: embeber `T` y el softmax evita que la app tenga que replicar la calibración. `tf.lite`
  sigue disponible en TF 2.20 (con aviso de migración a LiteRT); el intérprete de la app es independiente.
- **Alternatives considered**: cuantización entera completa (requiere conjunto representativo y suele
  costar exactitud en MobileNetV3 por hard-swish; se difiere a trabajo futuro si fp16/int8 dinámico no
  cumplen).

## M16. Latencia en teléfono real

- **Decision**: usar la herramienta oficial `benchmark_model` (binario Android aarch64 de TFLite) por
  `adb` con `--num_threads=4 --num_runs=50 --warmup_runs=5`, CPU sin delegados. Se registra el modelo del
  teléfono, RAM, versión de Android y la latencia media y p90 en `datos/modelo/exportacion/latencia.csv`.
- **Rationale**: FR-021 exige medir en un dispositivo real antes de que exista la app.

## M17. Entorno: Colab para entrenar, `.venv-ml` local para pruebas

- **Decision**: el entrenamiento corre en Google Colab con GPU. El notebook
  `notebooks/entrenar_colab.ipynb` solo monta Drive, clona la rama, instala `.[modelo]` con versiones
  fijadas y llama al CLI. **Lectura** de imágenes:
  `/content/drive/Othercomputers/Mi portátil/Modelo/...` (la carpeta respaldada del portátil);
  **escritura** de caché, checkpoints, modelos y registros: `/content/drive/MyDrive/AvocadoIA/modelo/`.
  En el PC, `importar` copia desde `G:\Mi unidad\AvocadoIA\modelo\` al repositorio solo los archivos
  livianos versionables (registros, métricas, figuras, metadatos). Localmente se recrea `.venv-ml`
  (Python 3.12, se perdió con el cambio de computadora) para las pruebas y para `verificar`.
- **Rationale**: Windows nativo no usa GPU con TF ≥ 2.11; la PC solo tiene Python 3.15, sin ruedas de
  TensorFlow. Separar lectura (respaldo del portátil) y escritura (Mi unidad) evita modificar la carpeta
  respaldada desde Colab.
- **Alternatives considered**: Kaggle (subir el dataset a otro servicio); WSL2 (sin GPU NVIDIA confirmada
  para esto).

## M18. Qué se versiona

- **Decision**: en Git: `src/avocadoia_modelo/`, `config/modelo.toml`, `notebooks/entrenar_colab.ipynb`
  (sin salidas), `datos/modelo/` (verificación, bitácora, registros JSON/CSV, figuras PNG, planillas de
  explicación, metadatos del modelo, informe). Fuera de Git (Drive): cachés `.npz`, logits, checkpoints,
  `.keras`, SavedModel y `.tflite`. El `.tflite` de producción se copiará a la app en su propia
  funcionalidad.
- **Rationale**: principio II/III y restricción técnica "las imágenes no se versionan"; los modelos
  binarios pesan decenas de MB y son regenerables desde el registro.

## M19. Fuente y filtro de licencias con las reglas de la especificación 002

- **Decision**: la fuente de cada imagen se determina **primero por SHA-256** en `datos/manifiesto.csv`
  (columna `fuente`, la asignación auditada de 002) y, si el contenido no está registrado, con
  `avocadoia_datos.config.cargar("config/dataset.toml", "config/fuentes.csv").fuente_de(ruta_origen)`
  (patrones glob con `|`, primera coincidencia). El contenido manda sobre el nombre porque el v4 renombra
  archivos. Se
  conserva solo la imagen cuya fuente tiene `uso_academico = si`; `no`, `pendiente` o fuente indeterminable
  → excluida con motivo `licencia:<fuente>:<uso_academico>` o `sin_fuente`. El filtro se aplica en el
  adaptador, antes de verificar, preparar o entrenar, y no tiene opción para desactivarlo.
- **Medición sobre el v4 (2026-11-09)**: 0 imágenes sin fuente (el pedúnculo, cuya ruta `PEDUNCULO/ring*`
  no coincide con los patrones, se resuelve por SHA como `mdpi_pedunculo`, CC BY 4.0). Excluidas: 412
  `sano_web` (`no`; 209 ya registradas en 002 y 203 nombres `sano-0295`…`sano-0999` que no estaban en el
  manifiesto de 002 pero coinciden con el patrón `AGUACATESANOS/sano-*`) y 373 `avocare` (`pendiente`,
  licencia "no verificada"; luego excluidas por calidad, M19.1). Las 16 fotos `sano-0707`…`sano-0723` del v4
  son, por SHA-256, las `sano-0001`…`sano-0017` de Herrera y Marín (Google Pixel 8, 22-05-2026) renumeradas:
  se conservan como `herrera_marin`. Quedan 1 426: train 998 (277/573/148), val 220 (61/127/32), test 208
  (54/123/31) en el orden sano/antracnosis/pedúnculo.
- **Rationale**: el principio II dice "Solo se usan fuentes cuya licencia permita uso académico; las demás se
  excluyen", sin excepción para experimentos. Un filtro solo por SHA dejaría pasar las 203 `sano-*` que no
  estaban registradas; las reglas por nombre las capturan. Un filtro solo por nombre (primera versión de esta
  decisión) habría excluido por error las 16 fotos propias renumeradas; por eso el SHA va primero.
- **Evidencia de que las 412 `sano_web` son descargas de internet** (EXIF de las 428 `sano-*` del v4,
  2026-11-09): 404 sin datos de cámara; 342 de lado mayor ≤ 400 px y mediana de 13 KB (miniaturas); las que
  tienen cámara son de terceros (Nikon D3400, Kodak DX6440, Canon IXUS 100 IS, Olympus); solo las 16 de
  Pixel 8 son de Herrera y Marín. El permiso de los tesistas previos cubre sus propias fotos, no imágenes
  de terceros que descargaron, aunque el uso sea educativo. Leer `config/fuentes.csv` (y no una lista fija)
  permite que `avocare` vuelva a entrar si se verifica su licencia, sin cambiar código. Resuelve además el
  hallazgo U1: el desglose por fuente usa nombres reales (`hass`, `rgb_antracnosis`, ...).
- **Alternatives considered**: excluir solo los SHA `excluida_licencia` de 002 (deja pasar 203 sin
  licencia); pedir al compañero que filtre antes de empezar (bloquea el trabajo; se le pide igualmente para
  su versión corregida); tratar `pendiente` como permitido (contradice "permita uso académico": una licencia
  no verificada no lo demuestra). La consulta automática a Roboflow devolvió HTTP 403: la verificación de
  `avocare` queda como tarea manual.

### M19.1 Verificación de avocare (2026-11-09) y exclusión por calidad

- **Evidencia** (página de Roboflow Universe revisada por los autores): licencia **CC BY 4.0** → se registra en
  `config/fuentes.csv` con `uso_academico = si`. La versión 4 tiene 2 488 imágenes generadas desde 1 134
  originales, con **"Outputs per training example: 3"** y aumentos: flip horizontal y vertical; rotación de 90°
  (horaria, antihoraria, invertida); rotación entre −15° y +15°; tono ±11°; saturación ±20 %; brillo ±15 %;
  exposición ±10 %.
- **Decision**: `avocare_sano` y `avocare_antracnosis` se excluyen **por calidad**, no por licencia, mediante
  `[datos].fuentes_excluidas` en `config/modelo.toml`, con motivo
  `calidad:copias_aumentadas_roboflow_v4`. Las exclusiones se registran en
  `datos/modelo/excluidas.csv` (columna `motivo`
  distingue `licencia:*`, `sin_fuente` y `calidad:*`).
- **Rationale**: variantes del mismo original repartidas entre train y test son fuga de datos que infla las
  métricas; coincide con la exclusión por revisión de la especificación 002 (`excluida_revision`). El conjunto
  vuelve a 1 426 imágenes.
- **Para reincorporar avocare**: el compañero debe entregar solo los originales (una imagen por ejemplo de
  origen) o agruparlas por original para que no crucen particiones; entonces se quita de
  `fuentes_excluidas`.

## M20. Dataset de entrada: partición de la especificación 002 (decisión del 2026-11-10)

- **Decision**: el modelo se entrena y evalúa con `datos/particion.csv` de la especificación 002 (2 188 imágenes,
  huella `096faf72d19f…`) y sus imágenes procesadas `Modelo/PROCESADO/<particion>/<clase>/<id_contenido>.jpg`
  (224 × 224, LANCZOS, JPEG calidad 95). Un adaptador (`avocadoia_modelo.dataset_002`) genera
  `datos/modelo/dataset_002/manifiesto_002.csv` con las columnas de M2 (`ruta_destino`, `clase_original`,
  `conjunto`, `sha256` del original, `estado_etiqueta`, `grupo_duplicacion_escena`, `ruta_origen`); el SHA-256 es el
  del original para que licencia (M19), duplicados y fuga se comprueben igual que antes. `preparar` no altera las
  imágenes (ya están a 224 × 224). El v4 queda como experimento descartado.
- **Comparación medida** (mismo criterio de fuente por SHA-256):

  | Criterio | v4 | 002 |
  | --- | --- | --- |
  | Imágenes | 2 211 | 2 188 |
  | Sin licencia académica | 412 | 0 |
  | Ya descartadas por la revisión de 002 (avocare, Kaggle sin lesión visible, dudosas) | 568 | 0 |
  | Frutos en varias particiones (imágenes de test afectadas) | 89 (76) | 0 (0) |
  | Pedúnculos sanos del artículo (`mdpi_pedunculo_sano`) | 0 | 338 |
  | Partición oficial del artículo | no | sí (578 imágenes) |
  | Revisión manual de etiquetas | no | sí (393 decisiones) |
  | Imágenes en común | 880 | 880 |

- **Rationale**: la 002 cumple FR-026/FR-027 y el principio II sin filtros adicionales, no tiene fuga entre
  particiones e incluye los pedúnculos sanos cuya ausencia explica el 0/40 de la prueba de campo con el v4.
- **Limitaciones heredadas (requisitos de viabilidad)**: auditoría de etiquetas de 002 con 6 % de error (IC 95 %
  2,8–12,5 %; criterio ≤ 2 %), sonda de fondo 0,95 (alerta de atajo), sondas de fuente 0,996–1,0, etiquetas sin
  validación del agrónomo y 76 originales de 002 ausentes en el PC actual (sus versiones procesadas sí están; no
  afecta al entrenamiento).
- **Alternatives considered**: v4 tal cual (incumple licencias y tiene fuga); v4 filtrado (1 426, sin pedúnculos
  sanos: 0/40 en campo); v5 propuesto (v4 corregido con las reglas de 002: 1 828 imágenes, sin la revisión manual de
  002; se conserva solo como diagnóstico del v4, ver `datos/modelo/v5/informe_v5.md`).
