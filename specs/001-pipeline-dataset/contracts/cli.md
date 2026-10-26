# Contrato de la CLI: `avocadoia_datos`

Invocación: `python -m avocadoia_datos <subcomando> [opciones]`, desde la raíz de `Entregables`.

Opciones comunes:

| Opción | Por defecto | Descripción |
|---|---|---|
| `--config RUTA` | `config/dataset.toml` | Archivo de configuración |
| `--raiz-imagenes RUTA` | `Modelo` | Raíz de las carpetas de imágenes |
| `--salida RUTA` | `datos` | Carpeta de artefactos versionables |

Códigos de salida: `0` éxito; `1` error de entrada (configuración o archivo inválido); `2`
precondición incumplida (p. ej. `particionar` sin manifiesto). Los avisos se escriben en stderr y
el resumen en stdout.

## `inventario`

Recorre las carpetas, calcula huellas, aplica fuentes y decisiones, y escribe
`datos/manifiesto.csv`.

- `--incluir-porclasificar` / `--no-incluir-porclasificar`: anula el valor de la configuración.
- stdout: totales por estado y por clase.
- Idempotente: sin cambios en la entrada, el CSV resultante es idéntico byte a byte.

## `planilla`

Genera `datos/validacion/planilla_<clase>_<NN>.xlsx` con las imágenes canónicas `pendiente`.

- `--clase {sano,antracnosis,pedunculo}`: opcional; sin ella genera todas las clases.
- `--lote N`: filas por planilla (por defecto, el de la configuración).
- Precondición: existe el manifiesto (si no, código 2).

## `incorporar RUTA_XLSX [RUTA_XLSX ...]`

Lee las planillas completadas y añade sus filas válidas a `datos/validacion/decisiones.csv`.

- Las filas sin decisión se ignoran; las inválidas (id desconocido, decisión o clase inválida,
  `reasignada` sin `clase_nueva`, falta validador o fecha) se listan en stderr con su número de
  fila, y el resto se procesa.
- Al terminar, vuelve a ejecutar `inventario`.
- stdout: filas incorporadas, ignoradas e inválidas.

## `particionar`

Genera `datos/particion.csv` y `datos/particion.json`.

- `--semilla N`: anula la semilla de la configuración.
- `--definitiva`: exige que todas las imágenes sean elegibles; si alguna está `provisional`, sale
  con código 2 y lista cuántas faltan por clase.
- Sin `--definitiva` incluye las imágenes `provisional` y marca el estado `provisional` si hay
  alguna.
- Precondición: existe el manifiesto.

## `preprocesar`

Escribe `Modelo/PROCESADO/<particion>/<clase>/<id_contenido>.jpg` para cada fila de la partición.

- `--destino RUTA`: anula la carpeta de destino.
- Omite las imágenes ya procesadas con el mismo `id_contenido` y la misma configuración; `--forzar`
  las regenera.
- Las advertencias de calidad se guardan en `datos/advertencias.csv`.
- Precondición: existe la partición.

## `informe`

Escribe `datos/informe.md` y `datos/informe.json` a partir del manifiesto, la partición, las
advertencias y la configuración.

## `todo`

Ejecuta `inventario` → `particionar` → `preprocesar` → `informe`. Acepta `--semilla` y
`--definitiva`.
