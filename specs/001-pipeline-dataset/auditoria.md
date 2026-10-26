# Documento de auditoría: `001-pipeline-dataset`

**Comando**: `/speckit-analyze` (Spec Kit 1.2.3) | **Fecha**: 2026-10-25 | **Rama**: `001-pipeline-dataset`

**Artefactos auditados**:
- `spec.md` (revisión 2)
- `plan.md` (revisión 2)
- `tasks.md` (36 tareas)
- `.specify/memory/constitution.md` v1.0.0

**Apoyo**: `research.md`, `data-model.md`, `contracts/cli.md`, `quickstart.md`

Auditoría de consistencia y cobertura previa a la implementación. El análisis es de solo lectura;
las remediaciones de la sección final se aplicaron después, en un commit aparte.

## Specification Analysis Report

| ID | Categoría | Severidad | Ubicación | Hallazgo | Recomendación |
|----|-----------|-----------|-----------|----------|---------------|
| K1 | Constitución | CRITICAL | tasks.md T001; constitución §III | T001 declara rangos (`Pillow>=12,<13`, `openpyxl>=3.1,<4`, `pytest>=8`). La constitución exige que las versiones de las dependencias **se fijen** | Fijar versiones exactas (`Pillow==12.3.0`, `openpyxl==3.1.5`, `pytest==8.4.2`) |
| K2 | Constitución | CRITICAL | spec.md FR-011/FR-018, research D8; constitución §II | La partición provisional admite imágenes con licencia `pendiente`. La constitución dice "solo se usan fuentes cuya licencia permita uso académico". Hoy las 9 fuentes están `pendiente`, así que ninguna imagen sería elegible para la definitiva | (a) Limitar la partición provisional a desarrollo y depuración: ninguna métrica reportada en la tesis puede salir de ella. (b) Añadir una tarea para documentar la licencia de cada fuente antes de congelar |
| I1 | Inconsistencia | HIGH | spec.md FR-023 vs US1-6 / contracts `inventario` | FR-023 pide registrar la fecha de generación en **todas** las salidas, pero el manifiesto debe ser idéntico byte a byte entre ejecuciones | Guardar los metadatos del manifiesto (fecha, semilla, `version_config`) en un archivo aparte, `datos/manifiesto.json`, y dejar el CSV determinista |
| C1 | Cobertura | MEDIUM | spec.md FR-019; tasks.md T005 | FR-019 reserva la fuente de prueba de campo, pero T005 no incluye su fila en `fuentes.csv`, así que `rol = test_campo` no tendría a qué aplicarse | Añadir a T005 la fila `campo_sigchos` (`Modelo/CAMPO_SIGCHOS/*`, `rol = test_campo`) |
| C2 | Cobertura | MEDIUM | plan.md Performance Goals | Ninguna tarea mide los objetivos de rendimiento (inventario < 5 min, preprocesamiento < 10 min) | Registrar los tiempos en T036 |
| C3 | Cobertura | LOW | spec.md FR-007, SC-001; tasks.md T012 | Solo T023 verifica que los originales no cambian, y solo durante el preprocesamiento | Añadir esa verificación a T012 (inventario) |
| C4 | Cobertura | LOW | spec.md SC-006 | El criterio de regenerar en menos de 30 min no tiene una medición explícita | Cubierto por T035 (README) y T036; no requiere tarea nueva |
| F1 | Inconsistencia | LOW | spec.md (prioridades) vs tasks.md (orden de fases) | US2 (P2) se implementa después de US3 y US4 | Ya está justificado en tasks.md: US2 depende de la muestra de US3. Sin cambios |
| U1 | Subespecificación | LOW | spec.md Edge Cases (grupo mayor que el déficit) | No acota cuánto puede desviarse una partición por grupos grandes | Los grupos reales tienen como máximo ≈4 imágenes (`hass_`) o 3 (casi duplicados), dentro de ±1 pp con ≥ 150 imágenes por partición. Sin cambios |

### Coverage Summary Table

| Requisito | ¿Tiene tarea? | Tareas | Notas |
|---|---|---|---|
| FR-001 recorrido de carpetas | ✅ | T015, T012 | |
| FR-002 campos del manifiesto | ✅ | T015, T012 | |
| FR-003 registro de fuentes editable | ✅ | T005, T008, T010 | |
| FR-004 duplicados exactos | ✅ | T015, T012 | |
| FR-005 conflicto de etiquetas | ✅ | T015, T012 | |
| FR-006 grupos | ✅ | T014, T013 | |
| FR-007 originales intactos | ✅ | T015, T023 | C3 |
| FR-008 planilla | ✅ | T030, T029 | |
| FR-009 decisiones y descriptivos | ✅ | T031, T029 | |
| FR-010 filas inválidas | ✅ | T031, T029 | |
| FR-011 elegibilidad | ✅ | T015, T019, T017 | K2 |
| FR-012 muestra por cuotas | ✅ | T019, T017 | |
| FR-013 reserva y reposición | ✅ | T019, T017 | |
| FR-014 estratificación clase × fuente | ✅ | T020, T018 | |
| FR-015 reproducibilidad | ✅ | T018, T020 | |
| FR-016 grupos sin repartir | ✅ | T020, T018 | |
| FR-017 partición de origen | ✅ | T020, T018 | |
| FR-018 provisional / definitiva | ✅ | T020, T021, T018 | K2 |
| FR-019 prueba de campo | ⚠️ parcial | T008, T015, T020, T025 | C1 |
| FR-020 preprocesamiento | ✅ | T025, T023 | |
| FR-021 aumento documentado | ✅ | T004, T026 | |
| FR-022 informe | ✅ | T026, T024 | |
| FR-023 metadatos de las salidas | ✅ | T021, T026 | I1 |
| SC-001 inventario completo, originales intactos | ✅ | T015, T023, T036 | |
| SC-002 cero fugas | ✅ | T018 | |
| SC-003 reproducibilidad | ✅ | T018, T036 | |
| SC-004 ±1 pp y cuotas | ✅ | T018, T017 | |
| SC-005 experto sin asistencia | ✅ | T029, T030 | Validación final manual con el experto |
| SC-006 regeneración < 30 min | ✅ | T035, T036 | C4 |
| SC-007 informe para capítulos 5.1–5.2 | ✅ | T026, T024 | |

### Constitution Alignment Issues

- **§III Reproducibilidad, "dependencias fijadas"** → K1.
- **§II Integridad, "solo fuentes con licencia académica"** → K2.

El resto de principios se cumple:
- **I (sin conexión):** el pipeline es local.
- **II:** hay trazabilidad por SHA-256, la prueba está aislada y los grupos no se reparten.
- **III:** semilla, orden canónico y CLI versionada.
- **IV:** no aplica; val y test aislados permiten calibrar.
- **V:** dos dependencias y sin nube.
- **Flujo SDD:** se cumple, con sesiones de métricas y esta auditoría.

### Unmapped Tasks

Ninguna. Las tareas de polish se asignan así:
- T033 → SC-001 y SC-007;
- T034 → FR-020 (control visual);
- T035 → SC-006;
- T036 → quickstart.

### Metrics

| Métrica | Valor |
|---|---|
| Requisitos (FR + SC) | 30 (23 FR + 7 SC) |
| Tareas | 36 |
| Cobertura (requisitos con ≥ 1 tarea) | 100 % (1 parcial: FR-019) |
| Ambigüedades | 1 (U1) |
| Duplicaciones | 0 |
| Hallazgos CRITICAL | 2 (K1, K2) |
| Hallazgos HIGH / MEDIUM / LOW | 1 / 2 / 4 |

## Next Actions

Los dos hallazgos CRITICAL deben resolverse antes de `/speckit-implement`. Plan de remediación:

| # | Hallazgo | Cambio |
|---|---|---|
| R1 | K1 | tasks.md T001: versiones exactas `Pillow==12.3.0`, `openpyxl==3.1.5`, `pytest==8.4.2` |
| R2 | K2 | spec.md: restricción explícita "la partición provisional solo sirve para desarrollo; ninguna métrica reportada en la tesis puede provenir de ella". Nueva tarea T037 para documentar la licencia de cada fuente en `config/fuentes.csv`, que requiere información del equipo |
| R3 | I1 | spec.md FR-023 y tasks.md T015/T016: metadatos del manifiesto en `datos/manifiesto.json`; el CSV queda determinista |
| R4 | C1 | tasks.md T005: fila `campo_sigchos` con `rol = test_campo` |
| R5 | C2 | tasks.md T036: medir y registrar los tiempos de inventario y preprocesamiento |
| R6 | C3 | tasks.md T012: verificar que el inventario no modifica los originales |

## Estado de la remediación

Las remediaciones R1–R6 se aplicaron el 2026-10-25 en spec.md y tasks.md (ver el historial de Git
de la rama). **K2 queda parcialmente abierto:** la restricción de uso ya está escrita, pero la
partición solo podrá marcarse `definitiva` cuando el equipo documente las licencias (T037).
