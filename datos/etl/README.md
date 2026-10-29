# ETL del conjunto de datos (spec 002)

Salidas de la fase de **Transformación** y **Carga** del proceso ETL
([spec](../../specs/002-etl-eda-dataset/spec.md), [contrato del CLI](../../specs/002-etl-eda-dataset/contracts/cli.md)).
Se regeneran con `.venv-ml/Scripts/python -m avocadoia_datos etl-eda`.

| Archivo | Contenido |
|---|---|
| `particion_001.csv` | Línea base: partición de la spec 001 (commit `f43575e`), para comparar |
| `sospechas.csv` | Una fila por candidata: probabilidades fuera de muestra, clase sugerida, conflicto, puntaje, vecinos de otra clase y si va a revisión |
| `embudo.csv` | Embudo de calidad: cada imagen inventariada contada en un solo paso, por clase y fuente |
| `comparacion_001.csv` | Cada imagen: `sale`, `entra`, `cambia_clase`, `cambia_conjunto` o `igual` frente a 001 |

## Fuentes de `AGUACATESANOS/sano-*`

La serie `sano-` viene de la carpeta de datos de la tesis previa de Herrera y Marín (OneDrive):

- `herrera_marin`: `sano-0001` a `sano-0017`, fotos propias (Google Pixel 8) usadas con permiso.
- `sano_web`: las otras 214, descargas de internet sin autor ni licencia; estado `excluida_licencia`.
  Su cuota se cubre con segundas vistas de frutos Hass (hass 540 = 396 frutos + 144 vistas).

## Revisión manual

1. `etl-revision --tipo sospecha` genera `datos/revision/revision_sospecha_<clase>_NN.xlsx` con miniaturas.
2. Los autores completan `decision` (`mantener`, `reasignar`, `excluir`, `no_seguro`), `clase_nueva`,
   `alcance` (`grupo` por defecto), `atajo`, `revisor` y `fecha` (AAAA-MM-DD).
3. `etl-incorporar <planillas>` las agrega a `datos/curacion/revision_etiquetas.csv` (versionado).
4. `etl-eda` regenera muestra, partición, EDA e informe.

Las planillas `.xlsx` no se versionan; la evidencia de cada decisión queda en `revision_etiquetas.csv`.
