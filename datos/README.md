# Conjunto de datos AvocadoIA

Artefactos versionados del pipeline del conjunto de datos (spec
[`001-pipeline-dataset`](../specs/001-pipeline-dataset/spec.md)). Las imágenes no están en Git:
viven en `Modelo/`.

## Qué carpeta usar en cada fase de la tesis

| Uso | Carpeta | Regla |
|---|---|---|
| Entrenamiento (OE3) | `Modelo/PROCESADO/train/<clase>/` | El aumento de datos se aplica solo aquí, en línea |
| Validación (OE3) | `Modelo/PROCESADO/val/<clase>/` | Detención temprana, hiperparámetros, temperatura *T*, umbral "no concluyente" |
| Prueba (OE3) | `Modelo/PROCESADO/test/<clase>/` | Se usa **una sola vez**, al final |
| Prueba de campo | `Modelo/PROCESADO/test_campo/<clase>/` | Solo si existen fotos propias en `Modelo/CAMPO_SIGCHOS/` |

Las clases son `sano`, `antracnosis` y `pedunculo` (síntomas compatibles con anillado del
pedúnculo). Cada imagen se llama `<id_contenido>.jpg` (224 × 224 RGB) y se rastrea hasta su
original con `manifiesto.csv`.

Las carpetas `Modelo/AGUACATESANOS`, `ANTRACNOSIS` y `PEDUNCULO` son la **fuente** de los datos.
Nunca se entrena directamente desde ellas. Las subcarpetas `DRIVE_PARTICIONES_ARTICULO/{train,val,test}`
son la partición original del artículo MDPI, no la partición final.

## Regenerar

Desde la raíz de `Entregables`:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m avocadoia_datos todo     # inventario → particionar → preprocesar → informe
```

Con las mismas imágenes y la misma configuración, `manifiesto.csv` y `particion.csv` salen
idénticos byte a byte (verificado el 2026-10-25). Tiempos medidos en el equipo local: inventario
75 s y preprocesamiento 207 s.

### ETL y EDA (spec 002)

Requiere Python 3.12 y TensorFlow (no hay ruedas para 3.14):

```powershell
py -3.12 -m venv .venv-ml
.venv-ml\Scripts\python -m pip install -e ".[dev,eda]"
.venv-ml\Scripts\python -m avocadoia_datos etl-eda   # ETL + EDA + informe, sin pasos manuales
scripts\informe\generar_word.ps1 -Fecha AAAA-MM-DD    # Word en DocumentosFInales, sin sobrescribir
```

La revisión manual de etiquetas se describe en [etl/README.md](etl/README.md).

## Archivos

| Archivo | Contenido |
|---|---|
| `manifiesto.csv` / `.json` | Una fila por imagen: fuente, licencia, SHA-256, dimensiones, grupo, estado y si está en la muestra |
| `particion.csv` / `.json` | Imagen → `train` / `val` / `test` (`test_campo`), con estado, semilla, cuotas, reserva y huella |
| `informe.md` / `.json` | Tablas para los capítulos 5.1 y 5.2: distribución, fuentes, pesos de clase y aumento |
| `advertencias.csv` | Imágenes pequeñas, de aspecto extremo, oscuras o borrosas (para revisión, no se excluyen) |
| `validacion/` | Planillas del experto y `decisiones.csv` (acumulativo) |
| `curacion/` | Registro de la curación inicial del 2026-10-25, de la revisión 3 y de la revisión de los autores (`revision_etiquetas.csv`, spec 002) |
| `etl/` | ETL de la spec 002: línea base de 001, sospechas, embudo y comparación ([README](etl/README.md)) |
| `eda/` | EDA de la spec 002: `tablas/`, `figuras/` (incluye `mosaicos/`) e `informe_etl_eda.md` / `.json` |
| `revision/` | Planillas de revisión y auditoría en curso (no versionadas) |

La configuración está en [`config/dataset.toml`](../config/dataset.toml) (semilla, tope, cuotas,
preprocesamiento, aumento) y [`config/fuentes.csv`](../config/fuentes.csv) (fuentes, licencias,
grupos).

## Estado al 2026-10-26

- **Partición provisional (revisión 3, 2026-10-26)**: 2 284 imágenes, con train 1 599, val 344 y
  test 341. Detalle en [informe.md](informe.md).
- **Excluidas por revisión**: 680 imágenes (`curacion/exclusiones_revision.csv`). Son toda la fuente
  `avocare_` (copias aumentadas) y 288 fotos Kaggle etiquetadas como antracnosis sin lesión visible.
- **Vistas del mismo fruto agrupadas**: Kaggle fotografía cada fruto desde 5 a 7 lados; esas vistas
  van siempre al mismo conjunto (`curacion/grupos_similitud.csv`). Con giros y volteos, quedan 0
  pares casi idénticos entre conjuntos distintos.
- **Validación del experto**: pendiente para las 2 284 imágenes de la muestra (`planilla`).
- **Licencias**: las 9 fuentes tienen la licencia `pendiente` en `config/fuentes.csv` (tarea T037).
- Mientras la partición sea provisional, **ninguna métrica reportada en la tesis puede salir de
  ella**. Sirve para preparar y depurar el entrenamiento.

## Revisión visual (T034, 2026-10-25)

Se revisó una hoja de contactos con 8 imágenes por clase de `train` y de `test`:

- La orientación EXIF está bien aplicada en todas.
- El color se conserva y no hay bordes de relleno.
- Los primeros planos de pedúnculo sano aparecen en la clase sano, como se buscaba.

Para la revisión del experto:

- La fuente `avocare_` resultó ser copias aumentadas de pocas escenas y se excluyó en la revisión 3
  (2026-10-26).
- Hay fotos de laboratorio con carteles escritos dentro de la imagen, un posible atajo visual.
- El preprocesamiento marca 101 imágenes como borrosas y 1 con proporción extrema (`advertencias.csv`, revisión 3).
