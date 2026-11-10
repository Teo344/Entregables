# Tasks: Construcción, calibración y exportación del modelo clasificador

**Input**: Design documents from `/specs/003-modelo-clasificador/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, contracts/modelo-tflite.md, quickstart.md

**Tests**: incluidos. La constitución exige pruebas automatizadas para la lógica determinista (FR-024): manifiesto, equivalencias, verificación, pesos de clase, métricas, bootstrap, ECE, Temperature Scaling, cobertura–exactitud, selección y registro.

**Organization**: las tareas se agrupan por historia de usuario. Orden por dependencia real y riesgo:
- US1 (corrida base de punta a punta) es el MVP.
- US6 (spike `explain`) se adelanta justo después de US1 porque es el riesgo técnico más incierto (M14).
- US2 → US3 → US4 → US5 siguen la cadena comparar → calibrar → explicar → exportar.
- Las tareas **[MANUAL]** las hacen los autores (Colab, revisión visual, teléfono), no el agente.
- Las tareas **[COLAB]** se ejecutan en Google Colab con GPU mediante `notebooks/entrenar_colab.ipynb`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede ejecutar en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1–US6)

## Path Conventions

Proyecto único en la raíz de `Entregables`: `src/avocadoia_modelo/`, `tests/`, `config/`, `datos/modelo/`, `notebooks/`. Entorno local `.venv-ml` (Python 3.12.10). Artefactos pesados en Drive: `/content/drive/MyDrive/AvocadoIA/modelo/` (Colab) = `G:\Mi unidad\AvocadoIA\modelo\` (PC), en adelante `DRIVE/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: entorno, paquete y configuración

- [X] T001 Agregar en `pyproject.toml` el extra `modelo` con `tensorflow==2.20.0`, `keras==3.15.1`, `numpy==2.5.4` y `matplotlib==3.11.2` (research M1, M17).
- [X] T002 Instalar Python 3.12 (`py install 3.12`), recrear `.venv-ml` con `py -V:3.12 -m venv .venv-ml` e instalar `pip install -e ".[dev,eda,modelo]"`; confirmar que las pruebas existentes pasan.
- [X] T003 [P] Crear el paquete `src/avocadoia_modelo/` con `__init__.py` (constante `CLASES = ("sano", "antracnosis", "pedunculo")` y `ETIQUETAS_VISIBLES` con "Síntomas compatibles con anillado del pedúnculo") y `__main__.py` que llama a `cli.main()`. TensorFlow NO se importa en `__init__.py` (plan, Structure Decision).
- [X] T004 [P] Crear `config/modelo.toml` con todas las secciones de data-model.md §4 y los valores de research: `[datos]` (manifiesto v4 `.../Dataset_split_experimental_v4_20261104_230751/reportes/manifiesto_split.csv`, raíz `.../Dataset_split_experimental_v4_20261104_230751`, mapeo `ruta_destino→ruta`, `clase_original→clase`, `conjunto→particion`, `sha256→sha256`, `estado_etiqueta→estado_etiqueta`, `grupo_duplicacion_escena→grupo`, `ruta_origen→ruta_origen` (para M19; **no** mapear `procedencia`); equivalencias M3; rutas `config/dataset.toml`, `config/fuentes.csv` y `datos/manifiesto.csv` para el filtro de licencias M19, sin opción para desactivarlo; `fuentes_excluidas = ["avocare_sano", "avocare_antracnosis"]` con `motivo_exclusion = "calidad:copias_aumentadas_roboflow_v4"`, research M19.1), `[entrada]` (224, `LANCZOS-estirar`), `[modelo]` (`mobilenetv3`, `efficientnetb0`, dropout 0.3), `[fase1]` (1e-3, 15), `[fase2]` (1e-5, 30, fracción 0.30), `[parada]` (paciencia 5, plateau 2, factor 0.5, min_lr 1e-7), `[aumento]` (rotación 45, traslación 0.2, zoom 0.2, volteos h y v, brillo 0.2, contraste 0.2), `[entrenamiento]` (lote 32, semillas [42, 43, 44], deterministico true), `[evaluacion]` (bootstrap 1000, semilla 42, min_por_fuente 10), `[seleccion]` (margen 0.02), `[calibracion]` (intervalos 15, umbral 0.60, exactitud_objetivo 0.95), `[explicacion]` (n 10, umbral_atajo 0.20), `[exportacion]` (variantes fp32/fp16/int8-dinamico, tamano_max_mb 10, perdida_max 0.01), `[metas]` (macro_f1 0.85, recall_antracnosis 0.85), `[rutas]` (salida Drive para Colab y PC, `datos/modelo`). Las rutas de Drive aceptan una variante por entorno (`colab` / `pc`).
- [X] T005 [P] Crear `datos/modelo/.gitkeep` y agregar a `.gitignore` las rutas pesadas que nunca deben entrar al repo: `*.keras`, `*.tflite`, `*.npz` bajo `datos/modelo/` (M18).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: configuración, manifiesto normalizado, verificación, registro y CLI base (todo sin TensorFlow)

**⚠️ CRITICAL**: ninguna historia empieza sin esta fase

- [X] T006 Implementar `src/avocadoia_modelo/config.py`: `cargar(ruta) -> Config` (tomllib), resolución de rutas por entorno (`colab` si existe `/content/drive`, si no `pc`), y `huella_config(config)` = sha256 del TOML canónico (claves ordenadas, JSON sin espacios) **excluyendo** `modelo.arquitectura` y `entrenamiento.semilla` (data-model.md §4, "Regla de igualdad").
- [X] T007 [P] Escribir `tests/unit/test_modelo_config.py`: carga el TOML real; dos configuraciones que solo difieren en arquitectura o semilla tienen la misma `huella_config`; cambiar `fase2.tasa` cambia la huella.
- [X] T008 Implementar `src/avocadoia_modelo/manifiesto.py` (research M2–M3, M19): `leer_entrada(ruta)` (UTF-8 con BOM, delimitador `,`), `asignar_fuente(fila, cfg_002, sha_a_fuente)` = la fuente de `datos/manifiesto.csv` por SHA-256 **primero** o, si el SHA no está, `cfg_002.fuente_de(ruta_origen)`, o `None`; `filtrar_licencias(filas) -> (conservadas, excluidas)` que conserva solo `uso_academico = si` y marca el resto con motivo `licencia:<fuente>:<uso_academico>` o `sin_fuente` (sin opción para desactivarlo, FR-026), y luego excluye las fuentes de `[datos].fuentes_excluidas` con su motivo `calidad:*` (FR-027); `normalizar(filas, config) -> list[FilaNormalizada]` con columnas `ruta, clase, particion, sha256, fuente, licencia, estado_etiqueta, grupo`; reglas de data-model.md §1 citadas: "`clase` traducida con la tabla de equivalencias (M3); desconocida → aborta", "`particion` ∈ `train|val|test` obligatoria", "Solo filas con `uso_academico = si` llegan al manifiesto normalizado"; `huella_manifiesto(ruta)` = sha256 de los bytes del CSV; `escribir_normalizado(...)` y `escribir_excluidas(...)` → `datos/modelo/excluidas.csv`.
- [X] T009 [P] Escribir `tests/unit/test_modelo_manifiesto.py` con un `fuentes.csv` y un `manifiesto.csv` sintéticos: mapeo de columnas del v4 con filas sintéticas; `AGUACATESANOS→sano`, `PEDUNCULO→pedunculo`; clase `MANZANA` lanza `ClaseDesconocida`; partición vacía lanza error; `AGUACATESANOS/sano-0972.jpeg` → `sano_web` → excluida `licencia:sano_web:no` **aunque su SHA no esté en el manifiesto de 002**; `AGUACATESANOS/sano-0005.jpg` → `herrera_marin` → conservada; `AGUACATESANOS/sano-0707.jpg` cuyo SHA está en el manifiesto como `herrera_marin` → conservada aunque el nombre coincida con `sano_web` (caso real del v4); `avocare_*` con `pendiente` → excluida `licencia:...:pendiente`; `avocare_*` con `si` pero en `fuentes_excluidas` → excluida `calidad:copias_aumentadas_roboflow_v4`; `PEDUNCULO/ring_1.jpg` sin patrón pero con SHA en el manifiesto → `mdpi_pedunculo` → conservada; sin patrón ni SHA → excluida `sin_fuente`; quitar `avocare` de `fuentes_excluidas` con licencia `si` la conserva; huella estable.
- [X] T010 Implementar `src/avocadoia_modelo/verificacion.py` (research M4, M19): primero `conteos_entrada` y el filtro de licencias de `manifiesto.filtrar_licencias` y de calidad (`excluidas` en el JSON y `datos/modelo/excluidas.csv`); después, sobre las conservadas: faltantes, ilegibles (Pillow `verify`), `sha_cruzados` (mismo SHA en dos particiones), `clases_desconocidas`, `fuga_por_fruto` cruzando por SHA-256 con los grupos de `datos/manifiesto.csv` (`grupo`, `sha256`) → `{grupos, imagenes, imagenes_test, detalle}`, `etiquetas_provisionales` por partición; `estado` = `fallida` si hay faltantes/ilegibles/SHA cruzados/clases desconocidas, `ok_con_avisos` si hay fuga o provisionales, si no `ok`. Escribe `datos/modelo/verificacion.json` (data-model.md §2) y el manifiesto normalizado en `DRIVE/manifiestos/<huella8>.csv`.
- [X] T011 [P] Escribir `tests/unit/test_modelo_verificacion.py` con imágenes sintéticas en `tmp_path`: una imagen `sano_web` no aparece en `conteos` ni en el manifiesto normalizado pero sí en `excluidas` y en el CSV de excluidas; una imagen sin licencia que además falta en disco NO vuelve `fallida` la verificación (se filtra antes); imagen faltante con licencia → `fallida`; mismo SHA en train y test → `fallida`; dos SHA del mismo grupo en train y test → `ok_con_avisos` con `imagenes_test = 1`; todo correcto → `ok`.
- [X] T012 Implementar `src/avocadoia_modelo/registro.py`: `id_corrida(fecha, arquitectura, semilla, huella_manifiesto)` = `AAAAMMDD-HHMM_<arq>_s<semilla>_<huella8>`; `versiones()` (Python, TF, Keras, NumPy, CUDA/cuDNN y GPU si TF está importado; si no, `null`); `escribir_registro(...)`/`actualizar_estado(...)` con transiciones `en_curso → completa | incompleta` (data-model.md §5); `agregar_a_bitacora(...)` con las columnas de data-model.md §6; `importar(origen, destino)` que copia solo `*.json, *.csv, *.png, *.md` (M18).
- [X] T013 [P] Escribir `tests/unit/test_modelo_registro.py`: formato del id; transición inválida `completa → en_curso` lanza error; la bitácora agrega sin duplicar el mismo id; `importar` ignora `.keras`, `.npz` y `.tflite`.
- [X] T014 Implementar `src/avocadoia_modelo/cli.py` con argparse: opciones comunes (`--config`, `--manifiesto`, `--raiz-imagenes`, `--salida`, `--repo-datos`), códigos de salida 0/1/2/3 (contracts/cli.md) y los subcomandos `verificar` e `importar`; los demás se registran en sus historias. Importar TensorFlow solo dentro de los subcomandos que lo requieren.
- [X] T015 [MANUAL] (ejecutada 2026-11-09: manifiesto `6691b967`, 2 211 → 785 excluidas → 1 426; `ok_con_avisos`; fuga real 88 grupos / 383 imágenes / 76 en test; provisionales 738/155/148; ~12 min leyendo desde Drive) Ejecutar `.venv-ml\Scripts\python -m avocadoia_modelo verificar` sobre el v4 y revisar `datos/modelo/verificacion.json`: `conteos_entrada` 2 211; `excluidas.total` 785 (`licencia:sano_web:no` 412; `calidad:copias_aumentadas_roboflow_v4` 373 = `avocare_sano` 196 + `avocare_antracnosis` 177); `conteos` 1 426 = train 998 (277/573/148), val 220 (61/127/32), test 208 (54/123/31); `estado = ok_con_avisos`; fuga por fruto recalculada sobre las conservadas (quickstart, escenario 2).
- [X] T058 [MANUAL] (agregada tras /speckit-analyze, hallazgo C1; hecha 2026-11-09: CC BY 4.0, 3 salidas por ejemplo → excluida por calidad, M19.1) Abrir en el navegador `https://universe.roboflow.com/avocare/fruit-disease-f4idq/dataset/4`, copiar la licencia declarada y los pasos de preprocesamiento/aumento de la versión 4. Registrar la licencia en la columna `licencia` de `config/fuentes.csv` (filas `avocare_sano` y `avocare_antracnosis`) y cambiar `uso_academico` a `si` **solo** si permite uso académico; si la versión declara aumentos, anotarlo en `notas` para el compañero (research M19). Volver a ejecutar `verificar`.

**Checkpoint**: datos verificados y trazables; las historias pueden empezar.

---

## Phase 3: User Story 1 - Entrenar un clasificador base de punta a punta (Priority: P1) 🎯 MVP

**Goal**: una corrida MobileNetV3 / semilla 42 sobre el v4 con registro completo, métricas en val y test, y reanudación.

**Independent Test**: `entrenar --arquitectura mobilenetv3 --semilla 42` produce `registro.json` (estado `completa`), `historial.csv`, `metricas.json`, matrices y fila en `bitacora.csv`; repetir da macro-F1 de prueba con diferencia ≤ 0,01.

### Tests for User Story 1

- [X] T016 [P] [US1] Escribir `tests/unit/test_modelo_metricas.py`: matriz de confusión con orden `[sano, antracnosis, pedunculo]`; P/R/F1 por clase y macro-F1 contra valores calculados a mano; clase sin predicciones → precisión 0 sin división por cero; bootstrap con semilla fija reproducible y con IC que contiene el valor puntual; desglose por fuente omite fuentes con < 10 imágenes; `pesos_clase` = `n / (k · n_c)`.
- [X] T017 [P] [US1] Escribir `tests/unit/test_modelo_preparacion.py`: una imagen 1536×2048 y otra 300×300 en `tmp_path` → `.npz` con `x.shape == (2, 224, 224, 3)`, `dtype uint8`, mismo resultado que `avocadoia_datos.preprocesamiento.cargar_224`; segunda ejecución reutiliza la caché (misma `huella_cache`); `--forzar` la regenera.
- [X] T018 [P] [US1] Escribir `tests/integration/test_modelo_ml.py::test_corrida_minima` (marca `ml`): 12 imágenes sintéticas, configuración con 1 época por fase y lote 4, MobileNetV3 con `weights=None`; verifica estados del registro, que `entrenar` nunca abre `test.npz` (espía sobre la carga) y que `metricas.json` tiene `val` y `test`.

### Implementation for User Story 1

- [X] T019 [P] [US1] Implementar `src/avocadoia_modelo/metricas.py` en NumPy puro (research M12): `matriz_confusion`, `por_clase`, `macro_f1`, `exactitud`, `bootstrap(y, p, metrica, n=1000, semilla=42) -> (lo, hi)`, `por_fuente(..., minimo=10)`, `pesos_clase(y_train)`, `resumen(y, logits, fuentes, experimental) -> dict` con la estructura de data-model.md §5 (`metricas.json`).
- [X] T020 [P] [US1] Implementar `src/avocadoia_modelo/preparacion.py` (research M5): reutilizar `avocadoia_datos.preprocesamiento.cargar_224` (LANCZOS, estirar, RGB); `huella_cache = sha256(huella_manifiesto | tamano=224 | metodo=LANCZOS-estirar)`; escribir `DRIVE/cache/<huella_cache>/{train,val,test}.npz` con `x uint8[n,224,224,3]`, `y int8[n]`, `sha256`, `fuente` (data-model.md §3); idempotente, `forzar` regenera. Registrar el subcomando `preparar` en `cli.py`.
- [X] T021 [US1] Implementar `src/avocadoia_modelo/datos_tf.py` (research M8): `cargar_particion(cache, particion)` (solo `train` y `val` desde entrenamiento); `dataset_entrenamiento(x, y, lote, semilla, aumento)` con `shuffle(seed)`, capas de aumento de `[aumento]` aplicadas solo aquí (`RandomFlip("horizontal_and_vertical")`, `RandomRotation(45/360)`, `RandomTranslation(0.2,0.2)`, `RandomZoom(0.2)`, `RandomBrightness(0.2, value_range=(0,255))`, `RandomContrast(0.2)`), `float32` 0–255 **sin normalizar**; `dataset_evaluacion(x, y, lote)` sin aumento ni barajado.
- [X] T022 [US1] Implementar `src/avocadoia_modelo/arquitecturas.py` (research M6): `construir(arquitectura, dropout, pesos="imagenet")` → modelo funcional **plano** sobre `base.output` (`MobileNetV3Large(include_top=False, include_preprocessing=True, minimalistic=False)` o `EfficientNetB0(include_top=False)`, entrada `224×224×3`) con `GlobalAveragePooling2D → Dropout → Dense(3)` sin activación (logits); devuelve también el nombre de la capa del mapa final (`base.output`) y la lista de capas del modelo base para congelar.
- [X] T023 [US1] Implementar `src/avocadoia_modelo/entrenamiento.py` (research M7, M9): `set_random_seed` + `enable_op_determinism` si `deterministico`; fase 1 con el modelo base congelado (Adam `fase1.tasa`, `fase1.epocas`); fase 2 descongela el `fase2.fraccion` final de capas del modelo base **excepto `BatchNormalization`** (siguen `trainable=False`), recompila con Adam `fase2.tasa`; `SparseCategoricalCrossentropy(from_logits=True)`, `class_weight` de `metricas.pesos_clase`; callbacks `EarlyStopping(val_loss, patience, restore_best_weights=True)`, `ReduceLROnPlateau`, `ModelCheckpoint(DRIVE/experimentos/<id>/mejor.keras)`, `BackupAndRestore(DRIVE/experimentos/<id>/backup)`, `CSVLogger` → `historial.csv` con columna `fase`; registro `en_curso` al empezar y `completa` al terminar; si existe `backup/`, reanuda con el mismo id.
- [X] T024 [US1] Implementar `src/avocadoia_modelo/evaluacion.py`: cargar `mejor.keras`, obtener logits de `val` y `test` (lote 64), guardar `DRIVE/experimentos/<id>/logits.npz`, escribir `metricas.json` y `matriz_confusion_{val,test}.csv` con `metricas.resumen` (rótulo `experimental` si `verificacion.etiquetas_provisionales` > 0 o hay fuga), y agregar la fila a `bitacora.csv`. Única función del flujo de entrenamiento que abre `test.npz`.
- [X] T025 [US1] Registrar en `cli.py` los subcomandos `entrenar --arquitectura {mobilenetv3,efficientnetb0} --semilla N` (llama a `evaluar` al terminar) y `evaluar --corrida ID` (contracts/cli.md). `entrenar` aborta con código 2 si `datos/modelo/verificacion.json` no existe, tiene `estado = fallida` o su `huella_manifiesto` no coincide con la de la caché (spec US1, escenario 1; hallazgo U2).
- [X] T026 [P] [US1] Implementar en `src/avocadoia_modelo/figuras.py` la curva de entrenamiento (loss y exactitud de train/val por época, con la línea de cambio de fase) → `datos/modelo/experimentos/<id>/curvas.png`.
- [X] T027 [US1] Crear `notebooks/entrenar_colab.ipynb` (sin salidas): celdas para verificar GPU, montar Drive, clonar la rama `003-modelo-clasificador`, `pip install -e ".[modelo]"`, comprobar la ruta `/content/drive/Othercomputers/Mi portátil/Modelo/...`, y una celda por subcomando (`preparar`, `spike-explain`, `entrenar`, `comparar --ejecutar`, `calibrar`, `explicar`, `exportar`). Sin lógica propia: solo llama al CLI (research M17).
- [X] T028 [US1] [COLAB] [MANUAL] (2026-11-09: corridas `20261109-2246` y `-2259` idénticas: val macro-F1 0,992, test 1,000 — sospecha de atajo por fuente, ver T045–T046; reanudación cubierta por `test_reanudacion_reutiliza_id`) Ejecutar `preparar` y `entrenar --arquitectura mobilenetv3 --semilla 42`; repetir la misma corrida y comparar macro-F1 de prueba (≤ 0,01); interrumpir el entorno durante la fase 2 y relanzar para confirmar la reanudación (quickstart, escenario 4). En el PC, `importar`.

**Checkpoint**: MVP: el flujo de punta a punta funciona y deja evidencia reproducible.

---

## Phase 4: User Story 6 - Prueba temprana de la explicación dentro del teléfono (Priority: P3, adelantada por riesgo)

**Goal**: saber si `explain` con Grad-CAM++ convierte a TFLite o si se aplica el plan B CAM.

**Independent Test**: `spike-explain` produce `datos/modelo/spike_explain/resultado.json` con `decision` y concordancia CAM vs Grad-CAM++.

- [X] T029 [P] [US6] Implementar en `src/avocadoia_modelo/explicacion.py`: `gradcam_pp(modelo, imagenes, clase)` con `GradientTape` sobre el mapa final (pesos α de Grad-CAM++ con derivadas de 2.º y 3.er orden aproximadas por la exponencial del score, ReLU, normalización 0–1); `cam(modelo, imagenes, clase)` = `Σ_k w_k^c · A_k` con los pesos de la capa `Dense` (sin gradientes); `concordancia(a, b)` → Pearson y IoU del 20 % superior.
- [X] T030 [US6] Implementar `spike_explain(...)` en `src/avocadoia_modelo/exportacion.py` (research M14): entrenar 1 época sobre `train`, construir un `tf.Module` con firmas `clasificar` y `explain` en dos variantes (gradientes / CAM), convertir cada una con `TFLiteConverter.from_saved_model`, capturar errores, medir tamaño extra y, para la que convierte, comparar su mapa con `gradcam_pp` en 20 imágenes de `val`; escribir `datos/modelo/spike_explain/resultado.json` (data-model.md §11) y `comparacion.png`. Registrar el subcomando `spike-explain`.
- [X] T031 [P] [US6] Agregar a `tests/integration/test_modelo_ml.py::test_cam_equivale_a_cabeza` (marca `ml`): para un modelo pequeño, la suma espacial media de `cam` reproduce el logit de la clase menos el sesgo (propiedad de GAP → Dense).
- [X] T032 [US6] [COLAB] [MANUAL] (2026-11-09, en PC con el modelo real: decisión **gradcam++**, ver research M14.1) Ejecutar `spike-explain`, `importar` y anotar en `research.md` (M14) la decisión final: Grad-CAM++ en TFLite o plan B CAM.

**Checkpoint**: riesgo técnico resuelto; el contrato `explain` queda fijado.

---

## Phase 5: User Story 2 - Comparar MobileNetV3 y EfficientNet-B0 en igualdad de condiciones (Priority: P1)

**Goal**: 6 corridas con configuración idéntica, tabla media ± desviación y decisión de arquitectura.

**Independent Test**: `comparar` genera `comparacion/<h>/tabla.csv` y `decision.json`; una corrida con otra `huella_config` hace salir con código 3.

- [ ] T033 [P] [US2] Escribir `tests/unit/test_modelo_seleccion.py`: agregación media ± desviación muestral con 3 corridas; regla: diferencia ≥ 0,02 → gana el mayor macro-F1 medio de **validación**; diferencia < 0,02 → gana el de menor tamaño fp16; corridas con `huella_config` o `huella_manifiesto` distintas → `ComparacionInvalida`; corridas `incompleta` se excluyen; menos de 3 corridas completas por arquitectura → `ComparacionInvalida`.
- [ ] T034 [US2] Implementar `src/avocadoia_modelo/seleccion.py` (research M12): `agregar(corridas)`, `validar_igualdad(corridas)`, `elegir(tabla, margen)`, `cumple_metas(metricas_test, metas)`; escribe `datos/modelo/comparacion/<huella_config8>/tabla.csv` y `decision.json` (arquitectura, corrida representativa = mayor val macro-F1 de esa arquitectura, regla aplicada, diferencia, cumplimiento de metas FR-015) (data-model.md §7).
- [ ] T035 [US2] Registrar `comparar [--ejecutar]` en `cli.py`: sin `--ejecutar` agrega las corridas existentes; con él lanza las corridas faltantes (2 arquitecturas × `entrenamiento.semillas`) y luego agrega; sale con código 3 si `validar_igualdad` falla. El tamaño fp16 para el desempate se estima convirtiendo `mejor.keras` (reutiliza `exportacion.convertir`, ver T048) o, si aún no existe, con `n_parametros × 2 bytes`.
- [ ] T036 [P] [US2] Implementar en `src/avocadoia_modelo/figuras.py` la figura de comparación (barras de macro-F1 y recall por clase con barras de error por arquitectura) → `comparacion/<h>/figura_comparacion.png`.
- [ ] T037 [US2] [COLAB] [MANUAL] Ejecutar `comparar --ejecutar` (6 corridas), `importar` y revisar `decision.json` (quickstart, escenario 5). Repetir una vez la corrida representativa de la arquitectura elegida y confirmar diferencia de macro-F1 de prueba ≤ 0,01 (SC-006; hallazgo A1).

**Checkpoint**: arquitectura elegida con evidencia justa.

---

## Phase 6: User Story 3 - Calibrar la confianza y definir el umbral (Priority: P1)

**Goal**: temperatura ajustada en validación, ECE antes/después y umbral de "no concluyente" justificado.

**Independent Test**: `calibrar --corrida <elegida>` produce `calibracion.json` con ECE de prueba después < antes y la curva cobertura–exactitud.

- [ ] T038 [P] [US3] Escribir `tests/unit/test_modelo_calibracion.py`: logits sobreconfiados sintéticos (escalados ×3) → `T` recuperada ≈ 3 (tolerancia 0,1); `T` no cambia el argmax; ECE de un predictor perfectamente calibrado sintético ≈ 0; ECE con 15 intervalos coincide con un cálculo a mano en 6 muestras; cobertura–exactitud monótona en cobertura; `umbral_para_exactitud(0.95)` devuelve el menor umbral que la alcanza o `None`.
- [ ] T039 [US3] Implementar `src/avocadoia_modelo/calibracion.py` en NumPy (research M10–M11): `nll(logits, y, T)`, `ajustar_temperatura(logits_val, y_val)` por sección áurea sobre `log T ∈ [log 0.05, log 20]`, `ece(probs, y, intervalos=15)`, `brier`, `curva_cobertura(probs, y, umbrales=0.34..0.99 paso 0.01)`, `umbral_para_exactitud(curva, objetivo)`. Solo recibe `val` para ajustar; `test` solo para reportar.
- [ ] T040 [US3] Registrar `calibrar --corrida ID` en `cli.py`: lee `DRIVE/experimentos/<id>/logits.npz`, escribe `datos/modelo/calibracion/<id>/calibracion.json` (data-model.md §8: `temperatura`, `nll_{antes,despues}`, `ece_{val,test}_{antes,despues}`, `brier_{...}`, `umbral`, `umbral_exactitud_95`, `cobertura_test_umbral`, `no_concluyentes_test`) y `cobertura_exactitud.csv`.
- [ ] T041 [P] [US3] Implementar en `src/avocadoia_modelo/figuras.py` los diagramas de fiabilidad antes/después y la curva cobertura–exactitud con el umbral 0,60 y el de exactitud 95 % marcados → `datos/modelo/calibracion/<id>/*.png`.
- [ ] T042 [US3] [MANUAL] Ejecutar `calibrar` sobre la corrida elegida y decidir el umbral (0,60 o el de exactitud 95 %), registrándolo en `config/modelo.toml` `[calibracion].umbral` con la justificación en `calibracion.json` (quickstart, escenario 6).

**Checkpoint**: confianza honesta y umbral justificado.

---

## Phase 7: User Story 4 - Verificar con Grad-CAM++ dónde mira el modelo (Priority: P2)

**Goal**: mapas de calor de aciertos y errores por clase, valorados y resumidos.

**Independent Test**: `explicar` genera mosaicos y planilla; tras valorarla, `resumir-explicaciones` reporta % por valoración y posibles atajos.

- [X] T043 [P] [US4] Escribir `tests/unit/test_modelo_explicaciones.py` (sin TF): selección de muestra con semilla 42 → hasta 10 aciertos y 10 errores por clase (todos los errores si hay menos), reproducible; `resumir(planilla)` calcula % `lesion_fruto | fondo_ajeno | ambiguo` por clase sobre aciertos valorados, ignora filas sin valorar y marca `posible_atajo` cuando `fondo_ajeno > 0.20`.
- [X] T044 [US4] Implementar en `src/avocadoia_modelo/explicacion.py` `seleccionar_muestra(y, pred, semilla, n)`, `generar(corrida)` (Grad-CAM++ sobre `test` con la clase predicha; mosaicos `mosaico_<clase>_{aciertos,errores}.png` con imagen, mapa y superposición; `planilla_explicaciones.csv` con columnas de data-model.md §9) y `resumir(planilla) -> resumen.json`. La columna `confianza` de la planilla es la **calibrada** (`softmax(logits / T)` con `T` de `datos/modelo/calibracion/<id>/calibracion.json`; hallazgo U3). Registrar `explicar --corrida ID` y `resumir-explicaciones --corrida ID` en `cli.py`.
- [X] T045 [US4] (2026-11-09, ejecutada en la PC: el modelo y la caché ya estaban en Drive; 30 mapas, 0 errores en test) [COLAB] Ejecutar `explicar --corrida <elegida>` e `importar`.
- [X] T046 [US4] [MANUAL] (2026-11-09, Mateo Criollo: sano 70 % / antracnosis 80 % / pedúnculo 90 %; posible atajo en sano por fondo de `rgb_sano`; ver `hallazgos.md`) Valorar cada fila de `datos/modelo/explicaciones/<id>/planilla_explicaciones.csv` (`lesion_fruto`, `fondo_ajeno` o `ambiguo`, revisor, fecha), idealmente con el agrónomo, y ejecutar `resumir-explicaciones`. Si hay `posibles_atajos`, registrar la observación para la revisión del dataset (quickstart, escenario 7).

**Checkpoint**: explicabilidad verificada (SC-005).

---

## Phase 8: User Story 5 - Exportar el modelo para el teléfono (Priority: P2)

**Goal**: variantes TFLite con calibración embebida, elección según tamaño/pérdida y latencia medida en teléfono real.

**Independent Test**: `exportar` produce `variantes.csv` y `metadatos.json`; la variante elegida cumple ≤ 10 MB y pérdida ≤ 0,01; `latencia.csv` registra ≤ 500 ms.

- [ ] T047 [P] [US5] Escribir `tests/unit/test_modelo_exportacion.py` (sin TF): `elegir_variante(variantes, tamano_max=10, perdida_max=0.01)` → la más liviana que cumple ambos; si ninguna cumple, la de menor pérdida con `excepcion=True` y motivo; `metadatos(...)` contiene todas las claves de contracts/modelo-tflite.md; la fila de cada variante incluye `test_exactitud` y `diferencia_exactitud` además de macro-F1 (principio V; hallazgo C3); `parsear_benchmark(texto)` extrae media y p90 de una salida real de `benchmark_model` guardada como fixture en `tests/fixtures/benchmark_model.txt`.
- [ ] T048 [US5] Implementar en `src/avocadoia_modelo/exportacion.py` (research M15): `modelo_inferencia(mejor.keras, T)` = entrada float32 `[1,224,224,3]` 0–255 → `softmax(logits / T)` (más `explain` según la decisión de T032); `convertir(modelo, variante)` para `fp32`, `fp16` y `int8-dinamico` vía SavedModel; `evaluar_tflite(ruta, x_test, y_test)` con `tf.lite.Interpreter` (macro-F1 **y exactitud** frente al modelo Keras); `elegir_variante`; escribe `.tflite` en `DRIVE/exportacion/<id>/`, y `variantes.csv` + `metadatos.json` en `datos/modelo/exportacion/<id>/` (data-model.md §10, contracts/modelo-tflite.md). Registrar `exportar --corrida ID`.
- [ ] T049 [P] [US5] Agregar a `tests/integration/test_modelo_ml.py::test_paridad_tflite` (marca `ml`): las probabilidades de la variante `fp32` coinciden con Keras (`atol=1e-4`) en 4 imágenes sintéticas y suman 1.
- [ ] T050 [US5] Implementar `parsear_benchmark` y el subcomando `registrar-latencia --corrida ID --archivo ... --telefono ... --ram-gb N --android V` que agrega una fila a `datos/modelo/exportacion/<id>/latencia.csv` (`fecha, variante, telefono, ram_gb, android, hilos, media_ms, p90_ms, cumple`) (research M16).
- [ ] T051 [US5] [COLAB] Ejecutar `exportar --corrida <elegida>`; en el PC, `importar` y copiar el `.tflite` elegido desde `G:\Mi unidad\AvocadoIA\modelo\exportacion\<id>\`.
- [ ] T052 [US5] [MANUAL] En un teléfono Android de gama baja: `adb push` del `.tflite` y de `benchmark_model`, ejecutar con `--num_threads=4 --num_runs=50 --warmup_runs=5`, repetir en **modo avión**, guardar la salida y `registrar-latencia` (quickstart, escenario 8).

**Checkpoint**: modelo listo para la app con su contrato y evidencia de dispositivo.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T053 Implementar `src/avocadoia_modelo/informe.py` y el subcomando `informe`: `datos/modelo/informe_modelo.{md,json}` con verificación, tabla comparativa, decisión, métricas de prueba con IC, calibración, explicabilidad, exportación y latencia; cada cifra cita el `id` de su corrida (SC-007); rótulo "EXPERIMENTAL — split v4 sin corregir / etiquetas sin validación experta" mientras aplique; advertencia de que la clase pedúnculo procede de una sola fuente (`mdpi_pedunculo`) y no permite medir generalización a fuentes nuevas (caso borde de la spec; hallazgo G1); tabla de exclusiones por licencia y calidad desde `verificacion.json`. Tablas, figuras e informe muestran la tercera clase como "Síntomas compatibles con anillado del pedúnculo" usando `ETIQUETAS_VISIBLES` (constitución, principio II; hallazgo F1).
- [ ] T054 Registrar el subcomando `todo` en `cli.py` (`verificar → preparar → comparar --ejecutar → calibrar → explicar → exportar → informe`, deteniéndose antes de los pasos manuales) y documentar el flujo en `datos/modelo/README.md`.
- [ ] T055 [P] Ejecutar `.venv-ml\Scripts\python -m pytest` completo (incluidas las marcadas `ml` en CPU) y corregir fallos.
- [ ] T056 [P] Validar todos los escenarios de `specs/003-modelo-clasificador/quickstart.md` y marcar en `datos/modelo/informe_modelo.md` cuáles se verificaron y cuándo.
- [ ] T057 [MANUAL] Cuando el compañero entregue el split corregido **y** el experto agrónomo haya validado las etiquetas (constitución, validación previa; hallazgo C2): `verificar --manifiesto <nuevo>` → repetir Phases 5–8 → `informe`; solo esas cifras se reportan en la tesis (spec, Supuestos; plan, Complexity Tracking).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup; bloquea todas las historias.
- **US1 (Phase 3)**: depende de Foundational. Es el MVP.
- **US6 (Phase 4)**: depende de `arquitecturas.py` y `datos_tf.py` (T021–T022) y de la caché (T020). Se adelanta por riesgo; su decisión condiciona T048.
- **US2 (Phase 5)**: depende de US1 (entrenar/evaluar).
- **US3 (Phase 6)**: depende de US2 (corrida elegida); la lógica (T038–T039) puede escribirse en paralelo desde Phase 2.
- **US4 (Phase 7)**: depende de US3 (confianzas calibradas en la planilla) y de T029.
- **US5 (Phase 8)**: depende de US3 (temperatura) y de la decisión de US6.
- **T035 → T048**: el desempate por tamaño de US2 usa `exportacion.convertir` (US5); mientras T048 no exista, T035 usa la estimación `n_parametros × 2 bytes` y lo registra en `decision.json` (hallazgo O1).
- **Polish (Phase 9)**: depende de las historias que se quieran reportar.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar antes de implementar.
- Lógica sin TF (`metricas`, `calibracion`, `seleccion`) antes que los módulos TF que la usan.
- Las tareas [COLAB]/[MANUAL] cierran cada historia.

### Parallel Opportunities

- Phase 1: T003, T004 y T005 en paralelo.
- Phase 2: cada prueba (T007, T009, T011, T013) en paralelo con módulos de otros archivos.
- Phase 3: T016, T017, T018, T019, T020 y T026 en paralelo.
- Lógica pura de historias posteriores (T033–T034, T038–T039, T043, T047) puede adelantarse en paralelo con US1, porque no depende de TensorFlow.

---

## Parallel Example: User Story 1

```text
Task: "T016 [US1] tests/unit/test_modelo_metricas.py"
Task: "T017 [US1] tests/unit/test_modelo_preparacion.py"
Task: "T019 [US1] src/avocadoia_modelo/metricas.py"
Task: "T020 [US1] src/avocadoia_modelo/preparacion.py"
Task: "T026 [US1] curvas de entrenamiento en src/avocadoia_modelo/figuras.py"
```

---

## Implementation Strategy

### MVP First (US1)

1. Phases 1–2 (setup y fundamentos sin TF) → `verificar` sobre el v4.
2. Phase 3 → primera corrida en Colab con registro completo.
3. **Parar y validar**: reproducibilidad (≤ 0,01) y reanudación.

### Incremental Delivery

1. MVP (US1) → spike `explain` (US6) → comparación (US2) → calibración (US3) → explicabilidad (US4) → exportación (US5) → informe.
2. Cada historia deja artefactos versionados en `datos/modelo/` que la tutora puede verificar.
3. Con el split corregido, se repiten Phases 5–8 sin cambiar código (solo `--manifiesto`).

### Notas

- Nunca pasar `test.npz` a `entrenamiento.py` ni a `calibracion.ajustar_temperatura` (FR-005).
- Toda salida visible (figuras, tablas, informes) usa `ETIQUETAS_VISIBLES`; el identificador interno `pedunculo` solo aparece en archivos de datos.
- Commits con ámbito `feat(003)`, `test(003)`, `data(003)`; trailer `Causa:` en los que eliminan o reescriben código (metodología de métricas).
- Toda cifra de tesis sale de un `registro.json` con su huella de manifiesto.
