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

## M21. Proceso de construcción y sustento bibliográfico (agregado el 2026-11-11)

- **Decision**: la construcción del modelo se declara bajo tres marcos complementarios, cada uno en su nivel:
  1. **Metodología de investigación**: Design Science Research (DSR), en la que el artefacto (clasificador más app)
     se construye y se evalúa contra el problema.
  2. **Proceso de aprendizaje automático**: **CRISP-ML(Q)** (Studer et al., 2021), que extiende CRISP-DM con
     aseguramiento de calidad en cada fase.
  3. **Proceso de ingeniería de software**: desarrollo guiado por especificaciones (Spec Kit:
     especificación → plan → tareas → implementación), que deja trazabilidad entre requisito, decisión y código.

  Correspondencia de las fases de CRISP-ML(Q) con este trabajo:

  | Fase de CRISP-ML(Q) | Artefactos de AvocadoIA | Control de calidad aplicado |
  | --- | --- | --- |
  | 1. Comprensión del negocio y de los datos | constitución, `spec.md` (FR, SC), metas macro-F1 ≥ 0,85 y recall de antracnosis ≥ 0,85 | criterios de éxito medibles antes de entrenar |
  | 2. Preparación de datos | especificación 002 (ETL, EDA, revisión manual), M19–M20, `verificar`, caché 224 × 224 | licencias, SHA-256, fuga por fruto = 0, huellas del manifiesto y de la partición |
  | 3. Ingeniería del modelo | M6–M9: transferencia ImageNet, dos fases, aumento solo en train, 2 arquitecturas × 3 semillas | determinismo, registro y bitácora por corrida, reanudación |
  | 4. Evaluación | M10–M14 y M12: macro-F1 con IC 95 %, calibración, Grad-CAM++ valorado, McNemar, prueba de campo (FR-028) | selección solo con validación; prueba solo para reportar; campo nunca usado para ajustar |
  | 5. Despliegue | M15–M16: TFLite con temperatura embebida, latencia en teléfono | pérdida máxima 0,01 y tamaño máximo 10 MB |
  | 6. Monitoreo y mantenimiento | bitácora, huellas de configuración y manifiesto, `importar` | reproducibilidad SC-006 (repetición con diferencia ≤ 0,01) |

- **Sustento por decisión**:

  | Decisión (sección) | Respaldo |
  | --- | --- |
  | CNN como familia de modelos | Mohanty et al. (2016); Upadhyay et al. (2025); Ismail et al. (2026); Nalwanga et al. (2025) para dispositivos con recursos limitados |
  | MobileNetV3-Large (M6) | Howard et al. (2019) |
  | EfficientNet-B0 (M6) | Tan y Le (2019) |
  | Transferencia desde ImageNet (M6) | Yosinski et al. (2014); Kornblith et al. (2019) |
  | Dos fases, BatchNorm congelada, tasa baja en la fase 2 (M7) | Guía oficial de Keras «Transfer learning & fine-tuning» (Chollet); Ioffe y Szegedy (2015) para el papel de BatchNorm |
  | Temperature Scaling, ECE y diagrama de fiabilidad (M10) | Guo et al. (2017) |
  | Umbral de «no concluyente» con curva cobertura–exactitud (M11) | Geifman y El-Yaniv (2017), clasificación selectiva |
  | Intervalos por bootstrap (M12) | Efron y Tibshirani (1993) |
  | McNemar para comparar dos clasificadores (M12) | Dietterich (1998); usado también por Flores et al. (2026b) |
  | Grad-CAM++ (M13) y CAM exportable (M14) | Chattopadhay et al. (2018); Zhou et al. (2016) |
  | Revisión de atajos con mapas de calor y prueba de campo | Geirhos et al. (2020); Ismail et al. (2026) señala que pocos estudios validan en campo |
  | Antecedentes en aguacate | Flores et al. (2026a), antracnosis; Flores et al. (2026b), anillado del pedúnculo (fuente de `mdpi_pedunculo`) |

- **Resultado de la regla M12 (2026-11-11)**: con el dataset 002, MobileNetV3 obtuvo 0,976 ± 0,009 de macro-F1
  medio en val y EfficientNet-B0 0,972 ± 0,003. La diferencia (0,0036) es menor que el margen de 0,02, así que el
  desempate por tamaño fp16 (≈ 5,7 frente a ≈ 7,7 MB) elige MobileNetV3. McNemar en prueba entre las corridas
  representativas: p = 0,23 (informativo). Detalle en `datos/modelo/comparacion/bde6ad25/`.
- **Rationale**: declarar el proceso responde a «¿qué estándar se siguió?», y la tabla de respaldo permite citar cada
  decisión sin reescribir el diseño.
- **Pendiente**: (a) agregar a Zotero las referencias que faltan y verificar sus datos completos en la fuente (DOI,
  volumen y páginas); (b) los dos artículos de Flores et al. (2026) informan que CNN propias y poco profundas
  superaron a MobileNetV2/V3 en aguacate. Sin una línea base de ese tipo, la elección de transferencia de
  aprendizaje queda sin contraste experimental (ver la propuesta de línea base, pendiente de decisión).

### Referencias de M21

- Chattopadhay, A., Sarkar, A., Howlader, P. y Balasubramanian, V. N. (2018). Grad-CAM++: Generalized gradient-based
  visual explanations for deep convolutional networks. *WACV 2018*.
- Chollet, F. (s. f.). *Transfer learning & fine-tuning*. Guías de Keras. https://keras.io/guides/transfer_learning/
- Dietterich, T. G. (1998). Approximate statistical tests for comparing supervised classification learning
  algorithms. *Neural Computation, 10*(7).
- Efron, B. y Tibshirani, R. J. (1993). *An Introduction to the Bootstrap*. Chapman & Hall.
- Flores et al. (2026a). A weighted ensemble of convolutional neural networks for anthracnose detection in avocado
  fruit. *Computers*. https://doi.org/10.3390/computers15060378
- Flores et al. (2026b). A lightweight shallow CNN-based approach for ring-neck disease detection in avocado fruits.
  *Computers*. https://doi.org/10.3390/computers15080513
- Geifman, Y. y El-Yaniv, R. (2017). Selective classification for deep neural networks. *NeurIPS 2017*.
- Geirhos, R. et al. (2020). Shortcut learning in deep neural networks. *Nature Machine Intelligence, 2*.
- Guo, C., Pleiss, G., Sun, Y. y Weinberger, K. Q. (2017). On calibration of modern neural networks. *ICML 2017*.
- Howard, A. et al. (2019). Searching for MobileNetV3. *ICCV 2019*.
- Ioffe, S. y Szegedy, C. (2015). Batch normalization: Accelerating deep network training by reducing internal
  covariate shift. *ICML 2015*.
- Ismail et al. (2026). Explainable artificial intelligence for plant disease detection: a scoping review.
  *Computers and Electronics in Agriculture*. https://doi.org/10.1016/j.compag.2026.112338
- Kornblith, S., Shlens, J. y Le, Q. V. (2019). Do better ImageNet models transfer better? *CVPR 2019*.
- Mohanty, S. P., Hughes, D. P. y Salathé, M. (2016). Using deep learning for image-based plant disease detection.
  *Frontiers in Plant Science*. https://doi.org/10.3389/fpls.2016.01419
- Nalwanga et al. (2025). Multi-crop disease detection in computer vision for resource-constrained farms: a review.
  *IEEE Access*. https://doi.org/10.1109/ACCESS.2025.3647114
- Studer, S. et al. (2021). Towards CRISP-ML(Q): A machine learning process model with quality assurance
  methodology. *Machine Learning and Knowledge Extraction, 3*(2).
- Tan, M. y Le, Q. V. (2019). EfficientNet: Rethinking model scaling for convolutional neural networks. *ICML 2019*.
- Upadhyay et al. (2025). Deep learning and computer vision in plant disease detection: a comprehensive review.
  *Artificial Intelligence Review*. https://doi.org/10.1007/s10462-024-11100-x
- Yosinski, J., Clune, J., Bengio, Y. y Lipson, H. (2014). How transferable are features in deep neural networks?
  *NeurIPS 2014*.
- Zhou, B., Khosla, A., Lapedriza, A., Oliva, A. y Torralba, A. (2016). Learning deep features for discriminative
  localization. *CVPR 2016*.
## M22. Línea base: CNN5 entrenada desde cero (agregado el 2026-11-11)

- **Decision**: se agrega como línea base la **CNN5 de Flores et al. (2026b)**, su mejor modelo para anillado,
  reconstruida desde el texto del artículo: 5 Conv2D 3 × 3 con ReLU (32, 64, 128, 256 y 512 filtros), sin
  BatchNormalization, MaxPooling 2 × 2 tras las 4 primeras, GlobalAveragePooling → Dense 256 ReLU → Dropout →
  salida. Con 2 salidas suma **1 700 418 parámetros, la cifra que publica el artículo** (Tabla 9), lo que confirma
  la reconstrucción. Aquí la salida es de 3 clases (1 700 675 parámetros) y entrega logits, como M6.
- **Protocolo**: los mismos datos (dataset 002), caché, aumento (M8), pesos de clase, semillas (42, 43, 44), parada
  temprana sobre `val_loss` y evaluación que las arquitecturas de M6. Se entrena **desde cero en una sola fase**,
  con los valores del artículo: Adam 0,001 y hasta 100 épocas. La paciencia sube de 5 a 10 porque, sin pesos
  preentrenados, la red converge más lento. Estos valores están en `[linea_base]` de `config/modelo.toml`; esa
  sección no entra en la huella de configuración (así las 6 corridas comparadas siguen siendo comparables) y se
  guarda completa en el `registro.json` de cada corrida de línea base.
- **Papel en la comparación**: la línea base **no compite** en la regla de M12. `comparar` la reporta en la tabla y
  la figura, y calcula la diferencia de macro-F1 de validación y McNemar en prueba frente a la corrida
  representativa elegida. Responde a la pregunta P1b: ¿la transferencia desde ImageNet supera a una CNN propia y
  poco profunda en este problema?
- **Diferencias con el artículo (no son una réplica exacta del experimento)**: el artículo es binario (sano o
  anillado), usa un recorte fijo del pedúnculo (ROI de 1500 × 1500), solo fruta Fuerte, lote 16 y equilibra la
  clase minoritaria con rotaciones; aquí son 3 clases, fruto completo, varias variedades, lote 32 y pesos de clase.
  En el artículo, MobileNetV3 tenía 246 530 parámetros entrenables (base congelada, solo la cabeza) y obtuvo
  F1 = 0,618; aquí MobileNetV3 se ajusta en dos fases (M7). Por eso las cifras del artículo no se comparan
  directamente con las de este trabajo; se compara la CNN5 dentro de este protocolo.
- **Supuestos**: el artículo no indica la tasa de Dropout ni la posición exacta de las capas de pooling (la cuenta de
  parámetros no depende de ellas); se usa Dropout 0,3 (como M6) y pooling tras las 4 primeras convoluciones
  (mapa final de 14 × 14 × 512, usado por Grad-CAM++). La CAM sin gradientes (M14) no aplica a la CNN5 porque su
  cabeza tiene una capa densa intermedia; no se exporta, así que no afecta.
- **Alternatives considered**: reproducir el ROI fijo (no aplica a fotos de fruto completo tomadas sin trípode);
  CNN4 del artículo (su recuento publicado, 9 826 370, no se pudo reconstruir con el texto); MobileNetV3 sin
  ImageNet (queda como ablación opcional).