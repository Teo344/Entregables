---
description: "Tareas de la primera iteración de curación del dataset y comparación de clasificadores"
---

# Tareas: Preparación del conjunto de datos y clasificación fitosanitaria del aguacate

**Entrada**: Documentos de diseÃ±o en `specs/001-avocado-health-assessment/`

**Alcance de esta iteración**: curación trazable de imÃ¡genes de fruto sano, antracnosis y sÃ­ntomas compatibles con anillado del pedÃºnculo; particionado; entrenamiento y comparación inicial de MobileNetV3 y EfficientNet-B0. La integración Android y sus historias de usuario quedan para una iteración posterior.

**Pruebas**: Incluye pruebas automatizadas del manifiesto y los splits, verificaciones del flujo de entrenamiento y evaluación final del modelo. La partición `test` permanece reservada: no se usa para ajustar hiperparÃ¡metros ni elegir arquitectura.

**Organización**: Tareas agrupadas por las historias US1 (dataset) y US2 (comparación de modelos), siguiendo sus prioridades en `spec.md`.

## Fase 1: Preparación

**Propósito**: dejar lista la estructura de trabajo en `Modelo/` y registrar el entorno reproducible.

- [ ] T001 Crear las carpetas `Modelo/data/`, `Modelo/scripts/`, `Modelo/notebooks/`, `Modelo/artifacts/` y `Modelo/tests/` segÃºn `plan.md`, preservando las carpetas de fuentes existentes
- [ ] T002 [P] Crear `Modelo/requirements.txt` con dependencias Python para TensorFlow/Keras, NumPy, pandas, scikit-learn, lectura de imÃ¡genes y validación JSON; registrar versiones instaladas al iniciar el entorno Colab
- [ ] T003 [P] Crear `Modelo/README.md` con instrucciones para montar Google Drive, configurar rutas sin credenciales y ejecutar el flujo en Google Colab

---

## Fase 2: Fundamentos compartidos

**Propósito**: definir trazabilidad, clases y reglas que bloquean la curación, el particionado y los experimentos.

- [ ] T004 Crear `Modelo/data/class-criteria.md` con criterios observables de revisión para `healthy`, `anthracnose` y `peduncle_ring_compatible`, registro de versión y manejo de desacuerdos con revisión tÃ©cnica agrÃ­cola
- [ ] T005 [P] Crear `Modelo/data/split-config.json` con proporciones iniciales train 0.70, validation 0.15 y test 0.15, semilla 42 y estrategia de agrupación por espÃ©cimen/sesión
- [ ] T006 [P] Crear `Modelo/data/experiment-config.yaml` con orden de clases, parÃ¡metros que deben registrarse y protocolo comÃºn para MobileNetV3 y EfficientNet-B0, dejando por documentar los valores que se fijarÃ¡n en Colab

**Punto de control**: las fuentes originales siguen siendo de solo lectura; solo imÃ¡genes aceptadas con clase y procedencia verificadas pueden entrar a los splits.

---

## Fase 3: Historia US1 - Preparar un conjunto de datos confiable (Prioridad: P1) ðŸŽ¯ MVP

**Objetivo**: obtener un dataset derivado y auditable, con etiquetas revisadas, particiones reproducibles y sin contaminación entre train, validation y test.

**Prueba independiente**: validar el manifiesto y confirmar que cada imagen admitida tiene fuente, hash, clase, estado de revisión y copia de trabajo; que las imÃ¡genes originales no cambian; que `Scab` y las imÃ¡genes sin etiqueta estÃ¡n excluidas o en cuarentena; y que los splits son reproducibles, completos y no comparten imÃ¡genes/grupos.

### Pruebas de US1

- [ ] T007 [P] [US1] Crear pruebas de esquema para filas vÃ¡lidas e invÃ¡lidas del manifiesto en `Modelo/tests/test_manifest.py`, usando `contracts/dataset-manifest.schema.json`
- [ ] T008 [P] [US1] Crear pruebas de integridad y aceptación de imÃ¡genes en `Modelo/tests/test_dataset_integrity.py`, cubriendo hashes, campos obligatorios, estado de revisión, archivos originales sin cambios y exclusión de registros pendientes
- [ ] T009 [P] [US1] Crear pruebas de particionado en `Modelo/tests/test_split_dataset.py` para suma de proporciones, reproducibilidad con semilla 42, cobertura de aceptadas y ausencia de imÃ¡genes o grupos compartidos entre splits

### Implementación de US1

- [ ] T010 [P] [US1] Crear `Modelo/data/sources.csv` con una fila por dataset o recolección propia y campos de origen, licencia/condiciones de uso, fecha conocida y notas de evidencia
- [ ] T011 [P] [US1] Crear `Modelo/data/manifest.csv` conforme a `data-model.md` y `contracts/dataset-manifest.schema.json`, aplicando las reglas `image_id: Obligatorio y único`, `source_id: Referencia a Fuente de datos`, `sha256: hexadecimal`, `project_class: enum/null`, `review_status: enum`, `split: enum/null` y `solo para accepted`; preservar nombre/ruta originales y hash SHA-256
- [ ] T012 [US1] Implementar el inventario de imÃ¡genes, detección de archivos ilegibles y duplicados, cÃ¡lculo de hashes y generación/actualización del manifiesto en `Modelo/scripts/inventory_dataset.py`
- [ ] T013 [US1] Documentar en `Modelo/data/source-label-mapping.csv` la etiqueta original, clase propuesta, evidencia y decisión de inclusión por fuente; mantener `Scab` excluida y no mapearla a anillado del pedÃºnculo
- [ ] T014 [US1] Incorporar al manifiesto las imÃ¡genes propias y candidatas de fuentes pÃºblicas en `Modelo/data/manifest.csv`, manteniendo los originales intactos y las copias de trabajo separadas bajo `Modelo/data/`
- [ ] T015 [US1] Registrar la revisión de imÃ¡genes propias y la verificación semÃ¡ntica de etiquetas pÃºblicas en `Modelo/data/manifest.csv`, dejando en `pending`, `quarantined` o `excluded` todo caso ambiguo o sin evidencia tÃ©cnica suficiente
- [ ] T016 [US1] Verificar y documentar una fuente elegible para `peduncle_ring_compatible` en `Modelo/data/source-label-mapping.csv`; si no se confirma una fuente y revisión suficientes, registrar el bloqueo y no declarar un dataset final de tres clases
- [ ] T017 [US1] Implementar la validación del manifiesto y de la integridad de copias/originales en `Modelo/scripts/validate_manifest.py`, incluyendo campos, estados, hashes, clases y reglas del contrato
- [ ] T018 [US1] Implementar el particionado reproducible 70/15/15 con semilla 42 y agrupación por espÃ©cimen/sesión cuando estÃ© identificada en `Modelo/scripts/split_dataset.py`
- [ ] T019 [US1] Guardar configuración, versión del manifiesto, asignaciones y conteos por clase/total de cada split en `Modelo/data/splits/` desde `Modelo/scripts/split_dataset.py`, documentando redondeos o desviaciones por agrupación
- [ ] T020 [US1] Ejecutar las pruebas de US1 y validar el flujo descrito en `quickstart.md`; registrar cantidades inventariadas, aceptadas, excluidas y pendientes en `Modelo/data/dataset-report.md`

**Punto de control**: US1 queda completada cuando el dataset y los splits pasan las verificaciones independientes. La ausencia de datos verificables para anillado del pedÃºnculo bloquea la afirmación y evaluación de un clasificador final de tres clases.

---

## Fase 4: Historia US2 - Comparar y seleccionar un clasificador multiclase (Prioridad: P1)

**Objetivo**: entrenar y comparar MobileNetV3 y EfficientNet-B0 con las mismas clases y particiones; seleccionar una configuración Ãºnicamente con validation y evaluar una sola vez el candidato en test retenido.

**Prueba independiente**: comprobar que ambos experimentos comparten manifiesto, splits, orden de clases y protocolo; que selección y ajustes usan validation; y que el informe final de test incluye mÃ©tricas por clase y macro, matriz de confusión, ROC-AUC OVR macro (o motivo de indisponibilidad), calibración, limitaciones y el resultado frente al umbral de F1 macro especificado.

### Pruebas de US2

- [ ] T021 [P] [US2] Crear pruebas del protocolo de evaluación en `Modelo/tests/test_evaluation.py` para orden de clases, mÃ©tricas por clase/macro, matriz de confusión y ROC-AUC OVR macro o motivo documentado si no es calculable
- [ ] T022 [P] [US2] Crear pruebas de trazabilidad de experimentos en `Modelo/tests/test_experiment_record.py` para configuración, versiones, acelerador, semillas, manifiesto/split y separación entre selección con validation y evaluación final con test

### Implementación de US2

- [ ] T023 [US2] Implementar cargadores de datos que lean Ãºnicamente los manifiestos/splits aceptados, apliquen el preprocesamiento registrado y eviten aumentos sobre la partición test en `Modelo/scripts/data_pipeline.py`
- [ ] T024 [US2] Implementar el entrenamiento configurable de MobileNetV3 y EfficientNet-B0 con condiciones comparables, registro de configuración y checkpoints en `Modelo/notebooks/model_comparison.ipynb`
- [ ] T025 [US2] Registrar por experimento arquitectura, orden de clases, configuración, versiones de software, runtime/acelerador, manifiesto, split, curvas y artefactos en `Modelo/artifacts/experiments/`
- [ ] T026 [US2] Implementar cÃ¡lculo de accuracy, precision, recall y F1 por clase y macro, matriz de confusión, ROC-AUC multiclase OVR macro y anÃ¡lisis de calibración en `Modelo/scripts/evaluate_models.py`
- [ ] T027 [US2] Seleccionar arquitectura/configuración usando exclusivamente resultados de validation y registrar el criterio de selección en `Modelo/artifacts/model-selection.md`
- [ ] T028 [US2] Ejecutar la evaluación final una sola vez sobre test retenido para el candidato seleccionado y guardar informe, predicciones y matriz de confusión en `Modelo/artifacts/final-evaluation/`
- [ ] T029 [US2] Comparar F1 macro de test con el mÃ­nimo especificado de 0.90 y reportar 0.95 solo como meta aspiracional, junto con calibración, generalización, errores representativos y limitaciones en `Modelo/artifacts/final-evaluation/report.md`
- [ ] T030 [US2] Si no hay datos aceptados suficientes para las tres clases, detener la evaluación final de tres clases y documentar la limitación en `Modelo/artifacts/final-evaluation/report.md`; no sustituir anillado por `Scab` ni presentar resultados parciales como cobertura completa

**Punto de control**: la selección de modelo se sustenta en validation. El test permanece reservado hasta la evaluación final, cuyos resultados no se reutilizan para ajustar el modelo.

---

## Fase 5: Pulido y documentación de la iteración

**Propósito**: dejar instrucciones reproducibles y lÃ­mites claros para la siguiente iteración móvil.

- [ ] T031 [P] Actualizar `Modelo/README.md` con el flujo completo desde inventario hasta evaluación final, comandos/notebooks, estructura de artefactos y prerrequisitos de Google Colab/Drive
- [ ] T032 [P] Documentar en `Modelo/artifacts/model-candidate.md` el candidato, orden de clases, preprocesamiento, resultados observados y limitaciones del contrato `contracts/model-inference-contract.md`, sin fijar runtime Android todavÃ­a
- [ ] T033 Revisar consistencia entre `tasks.md`, `spec.md`, `plan.md`, `data-model.md`, contratos e informes en `specs/001-avocado-health-assessment/` y `Modelo/`

## Dependencias y orden de ejecución

### Dependencias entre fases

- **Preparación (Fase 1)**: no depende de otras fases.
- **Fundamentos (Fase 2)**: depende de la estructura de preparación; bloquea US1 y US2.
- **US1 (Fase 3)**: depende de Fases 1 y 2. Debe completar curación y particiones antes de entrenar.
- **US2 (Fase 4)**: depende del dataset/splits aceptados de US1. La evaluación de tres clases depende de contar con ejemplos verificables suficientes para cada clase.
- **Pulido (Fase 5)**: depende de las historias incluidas en esta iteración.

### Dependencias dentro de US1 y US2

- T007â€“T009 preceden a T012, T017 y T018; sus verificaciones deben cubrir el comportamiento implementado.
- T010â€“T016 producen el inventario y las etiquetas revisadas que consume T017.
- T017 precede a T018; T018 precede a T019 y T020.
- T021â€“T022 preceden a la implementación de evaluación y registro en T023â€“T026.
- T023â€“T026 preceden a selección con validation (T027); T027 precede a la evaluación final reservada (T028â€“T029).
- Si T016 no confirma la clase de anillado, T030 documenta el bloqueo y no se afirma un modelo final de tres clases.

## Oportunidades de paralelización

- Fase 1: T002 y T003 pueden avanzar en paralelo despuÃ©s de acordar la estructura de T001.
- Fase 2: T005 y T006 pueden prepararse en paralelo con T004.
- US1: T007â€“T009 son pruebas independientes; T010 y T011 pueden desarrollarse en paralelo. La curación/revisión de fuentes diferentes puede avanzar en paralelo una vez acordados los criterios T004.
- US2: T021 y T022 pueden desarrollarse en paralelo; la preparación de registro de experimentos puede avanzar junto con la prueba de validación, sin evaluar el test antes de T027.

## Ejemplo de ejecución paralela: US1

```text
T007: pruebas del esquema del manifiesto en Modelo/tests/test_manifest.py
T008: pruebas de integridad del conjunto en Modelo/tests/test_dataset_integrity.py
T009: pruebas de particionado en Modelo/tests/test_split_dataset.py
```

## Estrategia de implementación

### MVP: dataset trazable (US1)

1. Completar preparación y fundamentos.
2. Inventariar fuentes y revisar procedencia, etiquetas y criterios tÃ©cnicos.
3. Validar manifiesto, copias y particiones reproducibles.
4. Confirmar que hay datos suficientes y verificables para las tres clases antes de declarar el dataset completo.

### Entrega incremental

1. Completar US1 y revisar de forma independiente sus conteos y splits.
2. Entrenar y comparar ambas arquitecturas usando solo train/validation para los ajustes.
3. Evaluar el candidato una vez en test y documentar resultados y lÃ­mites.
4. Planificar la integración Android en una iteración posterior con el modelo y contrato ya medidos.

## Notas

- `[P]` indica tareas paralelizables sin dependencias pendientes.
- `[US1]` y `[US2]` corresponden a las historias de usuario 1 y 2 de `spec.md`.
- El objetivo de 0.90 F1 macro y la meta aspiracional de 0.95 se reportan con el protocolo especificado; no son resultados garantizados.
- No se reportarÃ¡n pruebas o experimentos como aprobados hasta ejecutarlos y registrar sus resultados.

