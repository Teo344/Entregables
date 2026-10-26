# Auditoría de consistencia: 002-etl-eda-dataset

**Comando**: `/speckit-analyze` | **Fecha**: 2026-10-26 | **Artefactos**: spec.md, plan.md, tasks.md (51 tareas), research.md, data-model.md, contracts/cli.md y la constitución v1.0.0

## Hallazgos

| ID | Categoría | Severidad | Ubicación | Hallazgo | Remediación aplicada |
|----|-----------|-----------|-----------|----------|----------------------|
| K1 | Constitución | CRITICAL | spec.md, Assumptions | La spec habilitaba el entrenamiento exploratorio de 003 con datos provisionales. La constitución exige la validación del experto antes de entrenar | R1: se quitó; la 002 no habilita el entrenamiento y la decisión queda en 003 dentro de la constitución |
| I1 | Constitución / licencias | HIGH | `config/fuentes.csv` (Kaggle) | Kaggle no tiene licencia abierta y estaba marcada `uso_academico = si` sin justificación | R2: justificación escrita en la spec y en T009 (`fuentes.csv` y el informe) |
| C1 | Cobertura | MEDIUM | FR-005, T022 | La revisión sistemática por clase no estaba programada | R3: se hace con mosaicos y planillas `sistematica`, dentro de T022 |
| C2 | Cobertura | MEDIUM | FR-007, US4 escenario 3 | Los carteles solo se detectaban entre las imágenes revisadas | R3: se buscan en la revisión sistemática y el informe declara el conteo como parcial (T042) |
| E1 | Cobertura | MEDIUM | FR-023 | Faltaba verificar que el análisis corre sin conexión | R4: T049 con `AVOCADOIA_SIN_RED=1`; contrato de `etl-representaciones` actualizado |
| D2 | Constitución / alcance | MEDIUM | research E3 | No se justificaba que el clasificador de limpieza incluya las imágenes de test | R4: justificación del principio II agregada a E3 |
| U1 | Subespecificación | MEDIUM | T019, data-model | `no_seguro` no tenía campo definido | R4: columna `revision_autores` en data-model y T019; sección "Casos para el experto" en T042 |
| N1 | Constitución (menor) | LOW | plan, T028 | Los mosaicos versionados contienen miniaturas | R5: nota en tasks.md (figuras derivadas, no imágenes del conjunto) |
| T1 | Terminología | LOW | data-model, research E9 | Los nombres de los pasos del embudo no coincidían con los estados | R5: tabla de correspondencia en data-model |
| P1 | Cobertura | LOW | plan, Performance Goals | Nadie medía el objetivo de menos de 30 min | R5: T047 registra la duración |
| F1 | Cobertura | LOW | FR-013 | No había tarea que mencionara FR-013 | R5: nota en tasks.md (comandos de 001, cuando haya validador) |

## Cobertura después de la remediación

| Concepto | Antes | Después |
| --- | --- | --- |
| Requisitos funcionales con tarea | 22 / 23 (FR-023 sin tarea) | 23 / 23 |
| Criterios de éxito con tarea | 7 / 7 | 7 / 7 |
| Tareas sin requisito | 0 | 0 |
| Hallazgos críticos | 1 | 0 |

## Pendientes fuera de esta funcionalidad

- **Validador experto**: no está designado. El conjunto queda provisional y la partición definitiva (FR-013) se declara cuando exista.
- **Permiso del autor de Kaggle**: refuerza la justificación de I1. Lo gestiona el equipo y es opcional.

## Veredicto

Sin hallazgos críticos después de la remediación. Se puede continuar con `/speckit-implement`.
