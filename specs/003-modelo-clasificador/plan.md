# Implementation Plan: Construcción, calibración y exportación del modelo clasificador

**Branch**: `003-modelo-clasificador` | **Date**: 2026-11-09 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-modelo-clasificador/spec.md`

## Summary

Entrenar, comparar, calibrar, explicar y exportar el clasificador de tres clases de AvocadoIA (OE3) sobre
el **split experimental v4** del compañero, de forma reproducible y sustituible por su versión corregida.

- **Licencias**: antes que nada, se excluyen las imágenes de fuentes sin `uso_academico = si` en
  `config/fuentes.csv`, con las reglas de fuente de la 002 (M19). El v4 pasa de 2 211 a 1 426 imágenes
  (excluidas 412 `sano_web` sin licencia y 373 `avocare` por calidad: licencia CC BY 4.0 verificada, pero son copias aumentadas de Roboflow, M19.1).
- **Datos**: un adaptador convierte el manifiesto v4 en un manifiesto normalizado (M2–M3), `verificar`
  aborta ante faltantes, SHA cruzados o clases desconocidas y avisa de la fuga por fruto (M4); `preparar`
  redimensiona una sola vez a 224 × 224 con el mismo criterio de 001/002 y guarda una caché `.npz` (M5).
- **Modelo**: MobileNetV3Large y EfficientNetB0 con pesos ImageNet, entrada 0–255, cabeza
  `GAP → Dropout 0.3 → Dense(3)` con logits, en un modelo funcional plano (M6). Entrenamiento en dos
  fases con BatchNorm congelada, pesos de clase, aumento solo en entrenamiento y reanudación tras
  desconexión (M7–M8). Semillas 42/43/44 con determinismo de operaciones (M9).
- **Selección**: macro-F1 medio en validación; si la diferencia es < 2 puntos, gana la más liviana (M12).
- **Calibración**: Temperature Scaling en NumPy sobre validación, ECE antes/después y curva
  cobertura–exactitud para el umbral de 0,60 (M10–M11).
- **Explicabilidad**: Grad-CAM++ sobre muestras fijas de aciertos y errores con planilla de valoración
  (M13); spike temprano de la firma `explain` con plan B CAM sin gradientes (M14).
- **Exportación**: TFLite fp32/fp16/int8 dinámico con la calibración embebida, metadatos para la app y
  latencia medida con `benchmark_model` en un teléfono real (M15–M16).
- **Entorno**: entrenamiento en Colab (lee el Drive del portátil, escribe en `Mi unidad`), pruebas y
  verificación en `.venv-ml` local; `importar` trae al repo solo lo versionable (M17–M18).

## Technical Context

**Language/Version**: Python 3.12 (Colab y `.venv-ml` local, que hay que recrear: la PC nueva solo
tiene Python 3.15, sin ruedas de TensorFlow). Ver M17.

**Primary Dependencies**: grupo opcional nuevo `[modelo]` con las mismas versiones fijadas que `[eda]`:
tensorflow 2.20.0, keras 3.15.1, numpy 2.5.4, matplotlib 3.11.2, más Pillow 12.3.0 (base). Herramienta
externa: `benchmark_model` de TFLite para Android (M16). Sin SciPy, scikit-learn opcional (no
requerido): métricas y calibración en NumPy.

**Storage**: archivos. Versionados: `config/modelo.toml`, `datos/modelo/**` (JSON, CSV, PNG livianos).
En Drive (`MyDrive/AvocadoIA/modelo/`): cachés `.npz`, logits, checkpoints, `.keras`, SavedModel y
`.tflite` (M18).

**Testing**: pytest. Unitarias sin TensorFlow para manifiesto, equivalencias, verificación, pesos de
clase, métricas, bootstrap, ECE, Temperature Scaling, cobertura–exactitud, selección, igualdad de
configuraciones y registro. Integración marcada `ml`: corrida de 1 época con 12 imágenes sintéticas,
exportación TFLite y paridad Keras ↔ TFLite.

**Target Platform**: entrenamiento en Google Colab (GPU NVIDIA, Linux); modelo para Android de gama baja
(intérprete TFLite, CPU, 4 hilos).

**Project Type**: biblioteca + CLI (`python -m avocadoia_modelo`) + notebook lanzador de Colab.

**Performance Goals**: corrida completa (≤ 45 épocas, 998 imágenes de entrenamiento) ≤ 20 min en una T4; comparación de
6 corridas ≤ 2 h; inferencia en el teléfono ≤ 500 ms de media (SC-004).

**Constraints**: modelo exportado ≤ 10 MB con pérdida ≤ 1 punto de macro-F1; el test no interviene en
entrenamiento, selección ni calibración (FR-005); funcionamiento sin conexión del modelo exportado
(principio I); variación entre repeticiones ≤ 1 punto (SC-006).

**Scale/Scope**: 1 426 imágenes tras el filtro de licencias (train 998 / val 220 / test 208; sano 392,
antracnosis 823, pedúnculo 211), de 2 211 en el v4; 3 clases, 2 arquitecturas × 3 semillas = 6 corridas de
comparación + 1 spike.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento | Estado |
| --- | --- | --- |
| I. Sin conexión | Modelo TFLite con calibración embebida y metadatos; la firma `explain` se resuelve con spike temprano y plan B CAM sin gradientes (M14); latencia y modo avión verificados en teléfono real (quickstart, escenario 8). | ✅ |
| II. Integridad y trazabilidad | **Licencias sin excepción**: filtro obligatorio por `uso_academico = si` antes de cualquier paso (FR-026, M19); 412 imágenes del v4 excluidas por licencia y 373 por calidad (copias aumentadas), todas registradas con motivo. Lectura solo desde manifiesto con huella; `verificar` aborta ante SHA cruzados y avisa de fuga por fruto; test aislado por diseño (`entrenar` no lo carga). **Excepción** (solo calidad, no licencia): frutos cruzados entre particiones y etiquetas sin validación experta. | ⚠️ justificado (tabla) |
| III. Reproducibilidad | Semillas fijas, determinismo de operaciones, versiones fijadas, configuración versionada, registro por corrida con huellas, regla de igualdad verificada por `comparar` (código 3). Igualdad MobileNetV3 vs EfficientNet-B0 garantizada por `huella_config`. | ✅ |
| IV. Confianza calibrada y explicable | Temperature Scaling en validación, ECE antes/después, umbral "no concluyente" justificado con curva, Grad-CAM++ sobre aciertos y errores con valoración registrada. | ✅ |
| V. Presupuesto del dispositivo y simplicidad | Límites medibles (10 MB, 500 ms) verificados en dispositivo real; tamaño y exactitud antes/después de convertir reportados; sin dependencias nuevas fuera de las ya fijadas. Se difiere la cuantización entera completa. | ✅ |
| Validación experta antes de entrenar | No hay validador designado: se entrena en modo **experimental**; las métricas finales de tesis esperan la validación y el split corregido; T057 exige ambas condiciones. | ⚠️ justificado (tabla) |
| Flujo SDD y métricas | Rama `003-modelo-clasificador`, sesiones `metricas` por fase (extensión reinstalada 2026-11-09), `/speckit-analyze` antes de implementar, pruebas para la lógica determinista. | ✅ |

**Re-check post-design**: sin violaciones nuevas. [data-model.md](data-model.md) separa los artefactos
versionables de los pesados; [contracts/cli.md](contracts/cli.md) hace estructural el aislamiento del
test; [contracts/modelo-tflite.md](contracts/modelo-tflite.md) fija el preprocesamiento que la app debe
replicar.

## Project Structure

### Documentation (this feature)

```text
specs/003-modelo-clasificador/
├── plan.md              # Este archivo
├── research.md          # Decisiones M1–M18
├── data-model.md        # Entidades y archivos
├── quickstart.md        # Guía de validación de punta a punta
├── contracts/
│   ├── cli.md           # Subcomandos de python -m avocadoia_modelo
│   └── modelo-tflite.md # Contrato del modelo exportado para la app
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks (no lo crea este comando)
```

### Source Code (repository root)

```text
src/avocadoia_modelo/
├── __init__.py
├── __main__.py
├── cli.py              # subcomandos de contracts/cli.md
├── config.py           # carga de modelo.toml, huella_config (sin arquitectura)
├── manifiesto.py       # adaptador, equivalencias, fuente por prefijo, normalización    (sin TF)
├── verificacion.py     # faltantes, ilegibles, SHA cruzados, fuga por fruto              (sin TF)
├── preparacion.py      # redimensionado LANCZOS 224 y caché .npz                         (sin TF)
├── metricas.py         # confusión, P/R/F1, macro-F1, bootstrap, desglose por fuente     (sin TF)
├── calibracion.py      # Temperature Scaling, NLL, ECE, Brier, cobertura–exactitud       (sin TF)
├── seleccion.py        # agregación media ± desviación, regla de selección, igualdad     (sin TF)
├── registro.py         # id de corrida, registro.json, bitácora, versiones, importar     (sin TF)
├── datos_tf.py         # tf.data desde la caché, aumento solo en train                   (TF)
├── arquitecturas.py    # MobileNetV3Large / EfficientNetB0 + cabeza de logits            (TF)
├── entrenamiento.py    # dos fases, BN congelada, callbacks, reanudación                 (TF)
├── evaluacion.py       # logits val/test → metricas.json                                 (TF)
├── explicacion.py      # Grad-CAM++, CAM, mosaicos, planilla                             (TF)
├── exportacion.py      # SavedModel → TFLite ×3, paridad, metadatos, spike explain       (TF)
├── figuras.py          # curvas, fiabilidad, cobertura, comparación (matplotlib)
└── informe.py          # informe_modelo.md/json

config/modelo.toml
notebooks/entrenar_colab.ipynb   # lanzador: montar Drive, clonar rama, instalar, llamar al CLI

tests/
├── unit/       # test_modelo_manifiesto, test_modelo_verificacion, test_modelo_metricas,
│               # test_modelo_calibracion, test_modelo_seleccion, test_modelo_registro,
│               # test_modelo_config, test_modelo_preparacion
└── integration/
    └── test_modelo_ml.py   # marca ml: 1 época sintética, exportación y paridad TFLite

datos/modelo/
├── verificacion.json  bitacora.csv  informe_modelo.md  informe_modelo.json
├── experimentos/<id>/   comparacion/<h>/   calibracion/<id>/
├── explicaciones/<id>/  exportacion/<id>/  spike_explain/
```

**Structure Decision**: segundo paquete `avocadoia_modelo` en la misma distribución (M1), con un grupo
opcional `[modelo]` en `pyproject.toml`. Se reutiliza el criterio de redimensionado de
`avocadoia_datos.preprocesamiento` (LANCZOS, estirar) y los grupos de `datos/manifiesto.csv` para el aviso
de fuga. TensorFlow solo se importa en `datos_tf`, `arquitecturas`, `entrenamiento`, `evaluacion`,
`explicacion` y `exportacion`, de modo que las pruebas unitarias corren sin él.

## Fases de ejecución (vista del usuario)

1. **PC**: `verificar` (revisar avisos) y `pytest`.
2. **Colab**: `preparar` → `spike-explain` (riesgo técnico primero).
3. **Colab**: `entrenar` una corrida base (MobileNetV3, semilla 42) → revisar curvas y métricas.
4. **Colab**: `comparar --ejecutar` (6 corridas) → decisión de arquitectura.
5. **Colab/PC**: `calibrar` → `explicar` → valoración manual de la planilla → `resumir-explicaciones`.
6. **Colab**: `exportar` → **PC**: `importar` → teléfono: `benchmark_model` → `registrar-latencia`.
7. **PC**: `informe`. Al llegar el split corregido: repetir desde el paso 1 con `--manifiesto` nuevo; las
   métricas de tesis salen de esa repetición.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| Entrenar con el split v4 (ya filtrado por licencias) con frutos cruzados entre particiones y etiquetas sin validación experta (principio II, solo en su parte de calidad, y regla de validación previa). La parte de licencias **no** es excepción: se cumple con FR-026 | El equipo decidió avanzar con el modelo mientras el compañero corrige el split y no hay validador designado; el flujo se valida ahora y se repite con el manifiesto corregido | Esperar bloquea el cronograma de sprints; usar la partición de 002 contradice la decisión del equipo (2026-11-09). Mitigación: rótulo "experimental", avisos de `verificar` en cada registro y repetición obligatoria antes de reportar en la tesis |
| Segundo paquete en la misma distribución | Aislar el código del modelo y su dependencia de TensorFlow del pipeline de datos | Un subpaquete de `avocadoia_datos` mezcla responsabilidades; un repositorio aparte pierde la trazabilidad con los manifiestos |
| Dos entornos de ejecución (Colab + `.venv-ml` local) | TF en Windows nativo no usa GPU y la PC solo tiene Python 3.15 | Entrenar en CPU local multiplica el tiempo de 6 corridas; todo en Colab impide correr pruebas y `verificar` sin conexión a Colab |
