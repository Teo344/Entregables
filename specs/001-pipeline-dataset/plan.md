# Implementation Plan: Pipeline de construcción del conjunto de datos

**Branch**: `001-pipeline-dataset` | **Date**: 2026-10-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-pipeline-dataset/spec.md`

## Summary

Construir el conjunto de datos de OE2 como un pipeline reproducible por línea de comandos. El
pipeline:

- inventaría las imágenes de `Modelo/` en un manifiesto trazable (fuente, licencia, SHA-256,
  estado);
- deduplica por contenido y excluye las etiquetas en conflicto y la clase Scab de Kaggle;
- gestiona la validación del experto con planillas xlsx de ida y vuelta;
- particiona 70/15/15 de forma estratificada con semilla 42, conservando la partición de origen
  del artículo de pedúnculo mediante relleno de déficit;
- preprocesa a 224 × 224 RGB y emite un informe listo para los capítulos 5.1 y 5.2 de la tesis.

Se conservan todas las imágenes; el desbalance se compensa en OE3 con los pesos de clase que
publica el informe.

## Technical Context

**Language/Version**: Python ≥ 3.11 (probado en 3.14.3)

**Primary Dependencies**: Pillow (lectura y redimensionado), openpyxl (planilla xlsx); el resto,
biblioteca estándar (`hashlib`, `csv`, `json`, `tomllib`, `random`, `argparse`)

**Storage**: archivos — CSV/JSON/Markdown versionados en `datos/` y `config/`; imágenes
preprocesadas en `Modelo/PROCESADO/` (ignoradas por Git)

**Testing**: pytest con imágenes sintéticas generadas en `tmp_path`

**Target Platform**: Windows 11 (equipo de los investigadores); portable a Linux/macOS y Colab

**Project Type**: biblioteca + CLI (herramienta de datos de un solo proyecto)

**Performance Goals**: inventario completo de unos 9 000 archivos en menos de 5 minutos;
preprocesamiento de unas 5 000 imágenes en menos de 10 minutos en el equipo local

**Constraints**:
- Nunca modificar los archivos originales.
- Salidas deterministas (byte a byte, salvo las marcas de fecha).
- Sin red ni servicios en la nube.
- Rutas con caracteres no ASCII soportadas.

**Scale/Scope**: unos 9 000 archivos (unos 5 000 contenidos únicos tras deduplicar), 3 clases,
unas 7 fuentes, 1 de ellas con partición de origen

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento en este plan | Estado |
|---|---|---|
| I. Sin conexión | El pipeline corre en local, sin red. No afecta a la app; su salida alimenta un modelo que se ejecutará en el dispositivo | ✅ |
| II. Integridad y trazabilidad | Manifiesto con fuente, licencia, SHA-256 y estado por archivo; deduplicación por contenido; exclusión por conflicto; originales intactos; partición de prueba aislada; aumento solo documentado para entrenamiento; término "síntomas compatibles con anillado del pedúnculo" en el informe | ✅ |
| III. Reproducibilidad | Semilla 42 configurable; orden canónico antes de barajar; `version_config` y `huella_particion` en las salidas; dependencias fijadas en `pyproject.toml`; todo es CLI versionada | ✅ |
| IV. Confianza calibrada y explicable | No aplica directamente; las particiones `val`/`test` aisladas permiten calibrar sin fuga en OE3 | ✅ N/A |
| V. Presupuesto y simplicidad | Solo dos dependencias externas; sin pandas ni scikit-learn; sin casi-duplicados ni nube (fuera de alcance) | ✅ |
| Flujo SDD y métricas | Rama `001-pipeline-dataset`, sesiones de métricas por fase y `/speckit-analyze` antes de implementar | ✅ |
| Pruebas de lógica determinista | pytest sobre hash, deduplicación, partición, cuotas e incorporación | ✅ |

**Re-check post-diseño (Fase 1)**: sin violaciones. La partición provisional (research D6) no
viola el principio II porque nunca se marca `definitiva` sin validación y licencia, y su estado
viaja en `particion.json` y en el informe.

## Project Structure

### Documentation (this feature)

```text
specs/001-pipeline-dataset/
├── plan.md              # Este archivo
├── research.md          # Fase 0: relevamiento de fuentes y decisiones D1–D10
├── data-model.md        # Fase 1: entidades, estados y archivos
├── quickstart.md        # Fase 1: guía de validación de punta a punta
├── contracts/
│   └── cli.md           # Fase 1: contrato de subcomandos
├── checklists/
│   └── requirements.md  # Calidad de la spec
└── tasks.md             # Fase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
pyproject.toml                    # Paquete, dependencias fijadas, configuración de pytest
config/
├── dataset.toml                  # Semilla, proporciones, rutas, preprocesamiento, aumento
└── fuentes.csv                   # Registro de fuentes y licencias (lo edita el equipo)
src/avocadoia_datos/
├── __init__.py
├── __main__.py                   # Punto de entrada de python -m
├── cli.py                        # argparse: subcomandos del contrato
├── config.py                     # Carga y validación de dataset.toml y fuentes.csv
├── clases.py                     # Códigos de clase, carpetas y mapeo de etiquetas Kaggle
├── inventario.py                 # Recorrido, SHA-256, dimensiones, fuentes y estados (US1)
├── validacion.py                 # Planilla xlsx e incorporación de decisiones (US2)
├── particion.py                  # Estratificada con relleno de déficit (US3)
├── preprocesamiento.py           # RGB, 224 × 224, JPEG y advertencias (US4)
├── informe.py                    # Tablas, pesos de clase, aumento, Markdown y JSON (US4)
└── es_csv.py                     # Lectura y escritura CSV deterministas (UTF-8, LF, orden)
tests/
├── conftest.py                   # Fábrica de árboles Modelo/ sintéticos con Pillow
├── unit/
│   ├── test_inventario.py
│   ├── test_validacion.py
│   ├── test_particion.py
│   ├── test_preprocesamiento.py
│   └── test_informe.py
└── integration/
    └── test_cli_todo.py          # inventario → particionar → preprocesar → informe
datos/                            # Salidas versionadas (manifiesto, partición, informe, validacion/)
Modelo/PROCESADO/                 # Salida de imágenes (ignorada por Git)
```

**Structure Decision**: un solo proyecto Python con layout `src/` en la raíz de `Entregables`. Así
OE3 (entrenamiento) puede importar `avocadoia_datos` o leer `datos/particion.csv`, y la futura app
Flutter (OE4) vivirá en su propia carpeta (`AvocadoIA.V2/`) sin mezclarse con el pipeline de datos.

## Complexity Tracking

Sin violaciones de la constitución que justificar.
