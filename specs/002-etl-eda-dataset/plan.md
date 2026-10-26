# Implementation Plan: Proceso ETL y análisis exploratorio (EDA) del conjunto de datos

**Branch**: `002-etl-eda-dataset` | **Date**: 2026-10-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-etl-eda-dataset/spec.md`

## Summary

Formalizar la preparación del conjunto como un proceso **ETL** seguido de un **EDA**, siguiendo la estructura de Calapaqui, Guarderas y Fuertes (2026), sobre el pipeline de la especificación 001, que se extiende y no se reemplaza:

- **Extracción**: el inventario de 001 (SHA-256, formato, EXIF), con las fuentes documentadas en `config/fuentes.csv`. `sano_web` se divide en las 17 fotos propias de Herrera y Marín y las 214 descargas sin licencia, que se excluyen; su cuota se cubre con segundas vistas de frutos Hass.
- **Transformación**: la limpieza de 001, más la detección de etiquetas dudosas con representaciones de EfficientNet-B0 y *confident learning* con validación cruzada por grupos, la revisión manual en planillas con miniaturas, la marca de atajos visuales y la regeneración de muestra y partición.
- **Carga**: regenerar `Modelo/PROCESADO`, el manifiesto y la partición. Producir el embudo de calidad y la comparación con el conjunto de 001.
- **EDA**: distribuciones por clase, fuente y conjunto; características de las imágenes originales; sondas de atajo (bajo nivel, fondo y fuente); mapa t-SNE; mosaicos; conclusiones para el entrenamiento.
- **Entregable**: informe Markdown/JSON con figuras PNG/SVG y tablas CSV, y su versión Word en `DocumentosFInales/` con nombre versionado.

El conjunto queda **provisional** hasta que haya un experto validador (spec, Assumptions).

## Technical Context

**Language/Version**: Python 3.12.4 en `.venv-ml` para ETL/EDA (TensorFlow no tiene ruedas para 3.14). Los comandos de 001 siguen funcionando en `.venv` (3.14.3). Ver research E1.

**Primary Dependencies**: las de 001 (Pillow 12.3.0, openpyxl 3.1.5), más el grupo opcional `[eda]`: tensorflow 2.20.0 (CPU), numpy, scikit-learn, matplotlib y python-docx, con versiones exactas fijadas al crear el entorno. pandoc (externo, ya instalado) solo para el Word.

**Storage**: archivos. Versionados en Git: `datos/etl/`, `datos/eda/tablas/`, `datos/eda/figuras/`, `datos/eda/informe_etl_eda.{md,json}` y `datos/curacion/revision_etiquetas.csv`. Ignorados: `datos/eda/cache/` (representaciones `.npy`), `datos/revision/*.xlsx` en curso y `Modelo/PROCESADO/`.

**Testing**: pytest. La lógica (sospecha, embudo, sondas, regla de grupos, patrones `|`, `excluida_licencia`) se prueba con representaciones sintéticas de NumPy. Una prueba de integración marcada `ml` extrae representaciones de 6 imágenes sintéticas.

**Target Platform**: Windows 11 de los investigadores (CPU, RTX 3050 no usada por TensorFlow nativo); portable a Linux y Colab.

**Project Type**: biblioteca + CLI, extensión del paquete `avocadoia_datos`.

**Performance Goals**: cadena ETL + EDA completa en menos de 30 min en CPU para unas 4 000 imágenes candidatas. Una ejecución repetida con caché tarda menos de 5 min.

**Constraints**: sin conexión una vez descargados los pesos (FR-023); determinista (SC-006); el conjunto de prueba no interviene en las sondas que orientan decisiones de modelado (FR-020); no se borran ni mueven originales (principio II).

**Scale/Scope**: unas 4 000 imágenes candidatas (muestra y reserva) de 9 fuentes; conjunto final de 2 284; revisión manual estimada en unas 300–450 imágenes (conflictos más el 10 % superior de cada clase) y 100 de auditoría.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento | Estado |
| --- | --- | --- |
| I. Sin conexión | No afecta a la app. El análisis también corre sin conexión una vez descargados los pesos (FR-023). | ✅ |
| II. Integridad y trazabilidad | Cada exclusión o reasignación queda registrada con motivo, revisor y fecha. Las fuentes sin licencia académica pasan a `excluida_licencia`. Los originales no se tocan. El test no interviene en sondas ni decisiones de modelado (E7). La validación del experto prevalece. | ✅ |
| III. Reproducibilidad | Semilla 42; versiones y pesos fijados con huella; comando único; tablas y JSON idénticos entre ejecuciones (E13). | ✅ |
| IV. Confianza y explicabilidad | Las sondas de atajo preparan la verificación con Grad-CAM++ de 003. No hay predicciones al usuario en esta funcionalidad. | ✅ (no aplica directo) |
| V. Simplicidad | Usa TensorFlow, que la constitución ya fija, y scikit-learn. Se descartan cleanlab, UMAP/numba, PyTorch y OpenCV. Un segundo entorno de Python es la única complejidad nueva (ver tabla). | ✅ con justificación |
| Validación experta antes de entrenar | Sin validador designado, el conjunto queda provisional y la partición definitiva se bloquea (FR-013, FR-018 de 001). | ✅ |
| Flujo SDD y métricas | Rama `002-etl-eda-dataset`, sesiones `metricas` por fase, `/speckit-analyze` antes de implementar. | ✅ |

**Re-check post-design**: sin violaciones nuevas. El diseño de [data-model.md](data-model.md) y [contracts/cli.md](contracts/cli.md) mantiene los estados y archivos de 001 y solo agrega `excluida_licencia`, `revision_etiquetas.csv` y las salidas de `datos/etl/` y `datos/eda/`.

## Project Structure

### Documentation (this feature)

```text
specs/002-etl-eda-dataset/
├── plan.md              # Este archivo
├── research.md          # Decisiones E1–E14
├── data-model.md        # Entidades, estados y archivos nuevos
├── quickstart.md        # Guía de ejecución y validación
├── contracts/
│   └── cli.md           # Subcomandos nuevos del CLI
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks (no lo crea este comando)
```

### Source Code (repository root)

```text
src/avocadoia_datos/
├── config.py            # + patrones alternativos con "|"
├── inventario.py        # + estado excluida_licencia, + revision_etiquetas.csv
├── etl/
│   ├── __init__.py
│   ├── representaciones.py  # EfficientNet-B0 → vectores 1 280-d con caché y huella
│   ├── sospechas.py         # confident learning + k-NN por grupos
│   ├── revision.py          # planillas de revisión y auditoría; incorporación
│   ├── embudo.py            # embudo de calidad y comparación con 001
│   └── caracteristicas.py   # resolución, brillo, contraste, nitidez, HSV, fondo
├── eda/
│   ├── __init__.py
│   ├── distribuciones.py    # tablas clase × fuente × conjunto
│   ├── sondas.py            # sondas de atajo (bajo nivel, fondo, fuente)
│   ├── similitud.py         # PCA + t-SNE, outliers
│   ├── figuras.py           # matplotlib: histogramas, cajas, embudo, mosaicos
│   └── informe.py           # informe_etl_eda.md/.json y conclusiones
└── cli.py               # + subcomandos de contracts/cli.md

scripts/informe/
├── formatear_docx.py    # bordes, encabezados y tamaños (migrado del informe de fase 1)
└── generar_word.ps1     # pandoc + formateador → DocumentosFInales/<nombre>_<fecha>.docx

tests/
├── unit/                # test_sospechas, test_embudo, test_sondas, test_caracteristicas,
│                        # test_revision, test_config_patrones, test_inventario_licencia
└── integration/
    └── test_etl_eda.py  # cadena con imágenes sintéticas (marca ml para TensorFlow)

datos/
├── curacion/revision_etiquetas.csv
├── etl/                 # particion_001.csv, sospechas.csv, embudo.csv, comparacion_001.csv
├── revision/            # planillas xlsx (ignoradas mientras están en curso)
└── eda/
    ├── tablas/  figuras/  informe_etl_eda.md  informe_etl_eda.json
    └── cache/           # ignorada por Git
```

**Structure Decision**: se extiende el paquete único `avocadoia_datos` con dos subpaquetes, `etl/` y `eda/`. Los módulos de 001 (`inventario`, `muestra`, `particion`, `preprocesamiento`) se reutilizan para la carga; solo `config` e `inventario` reciben cambios mínimos. TensorFlow se importa únicamente dentro de `etl/representaciones.py`, así que el resto del paquete y sus pruebas siguen funcionando en `.venv` sin TensorFlow.

## Fases de ejecución (vista del usuario)

1. `etl-extraer`: inventario con fuentes y licencias actualizadas. Guarda `particion_001.csv`.
2. `etl-representaciones`, luego `etl-sospechas`, luego `etl-revision` (planillas). Los autores revisan y se ejecuta `etl-incorporar`.
3. `todo`, el comando de 001, regenera muestra, partición, preprocesado e informe de 001.
4. `etl-auditoria`: planilla de 100 imágenes. Los autores revisan y se ejecuta `etl-incorporar --auditoria`.
5. `eda` (tablas, figuras, sondas, t-SNE, mosaicos), luego `etl-embudo` y luego `informe-etl-eda`.
6. `scripts/informe/generar_word.ps1` genera el Word versionado en `DocumentosFInales/`.

Los pasos 2 y 4 requieren trabajo manual. El resto se puede encadenar con `etl-eda` (ver [contracts/cli.md](contracts/cli.md)).

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
| --- | --- | --- |
| Segundo entorno de Python (`.venv-ml`, 3.12) | TensorFlow no se publica para Python 3.14, y la constitución fija TensorFlow para el modelo | Bajar todo a 3.12 obliga a revalidar 001; usar PyTorch agrega un segundo framework |
| Dependencia de pandoc (externa) | Convertir el informe Markdown a Word con tabla de contenido, como el informe de fase 1 | Generar el Word solo con python-docx duplica el trabajo de maquetación |
