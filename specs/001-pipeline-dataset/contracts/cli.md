# Contrato de la CLI: `avocadoia_datos`

Invocación: `python -m avocadoia_datos <subcomando> [opciones]`, desde la raíz de `Entregables`.

Opciones comunes:

| Opción | Por defecto | Descripción |
|---|---|---|
| `--config RUTA` | `config/dataset.toml` | Archivo de configuración |
| `--fuentes RUTA` | `config/fuentes.csv` | Registro de fuentes |
| `--raiz-imagenes RUTA` | `Modelo` | Raíz de las carpetas de imágenes |
| `--salida RUTA` | `datos` | Carpeta de artefactos versionables |

Códigos de salida:
- `0`: éxito.
- `1`: error de entrada (configuración o archivo inválido).
- `2`: precondición incumplida (p. ej. `particionar` sin manifiesto).

Los avisos se escriben en stderr y el resumen en stdout.

Flujo habitual: `inventario` → `particionar` → `planilla` → (experto) → `incorporar` → `particionar`
→ `preprocesar` → `informe`.

## `inventario`

Recorre las carpetas de clase y escribe `datos/manifiesto.csv`. Para ello:
- calcula las huellas, dimensiones (con la orientación EXIF aplicada), formato y modo de cada
  imagen;
- aplica las fuentes, los grupos y las decisiones del experto.

- stdout: totales por estado, por clase y por fuente, y número de grupos.
- Idempotente: si la entrada no cambia, el CSV resultante es idéntico byte a byte.

## `particionar`

Selecciona la muestra por cuotas (marca `en_muestra` en el manifiesto) y escribe
`datos/particion.csv` y `datos/particion.json`.

- `--semilla N`: anula la semilla de la configuración.
- `--definitiva`: exige que toda la muestra sea `elegible`. Si alguna imagen está `provisional`,
  sale con código 2 e indica cuántas faltan por clase.
- Sin `--definitiva`, admite las imágenes `provisional` y marca el estado `provisional` si hay
  alguna.
- stdout: tabla de clase × partición, faltantes de cuota y tamaño de la reserva.
- Precondición: existe el manifiesto.

## `planilla`

Genera `datos/validacion/planilla_<clase>_<NN>.xlsx` con las imágenes de la muestra cuya validación
está `pendiente`.

- `--clase {sano,antracnosis,pedunculo}`: opcional; sin ella genera las tres clases.
- `--lote N`: filas por planilla (por defecto, el valor de la configuración).
- `--incluir-reserva`: añade también las imágenes de la reserva.
- Precondición: existe la partición (para saber qué está en la muestra).

## `incorporar RUTA_XLSX [RUTA_XLSX ...]`

Lee las planillas completadas y añade sus filas válidas a `datos/validacion/decisiones.csv`.

- Las filas sin decisión se ignoran.
- Las filas inválidas se listan en stderr con su número de fila; el resto se procesa. Son
  inválidas:
  - id desconocido;
  - decisión, clase o columna descriptiva fuera de su lista;
  - `reasignada` sin `clase_nueva`;
  - falta validador o fecha.
- Al terminar, vuelve a ejecutar `inventario`.
- stdout: filas incorporadas, ignoradas e inválidas.

## `preprocesar`

Escribe `Modelo/PROCESADO/<particion>/<clase>/<id_contenido>.jpg` para cada fila de la partición,
incluida `test_campo` si existe.

- `--destino RUTA`: anula la carpeta de destino.
- `--forzar`: regenera aunque el archivo ya exista. Sin esta opción, se omiten las imágenes ya
  procesadas con la misma configuración.
- Borra de `PROCESADO/` los archivos que ya no están en la partición, para que la carpeta refleje
  siempre `particion.csv`.
- Escribe `datos/advertencias.csv`.
- Precondición: existe la partición.

## `informe`

Escribe `datos/informe.md` y `datos/informe.json` a partir del manifiesto, la partición, las
advertencias y la configuración.

## `todo`

Ejecuta `inventario` → `particionar` → `preprocesar` → `informe`. Acepta `--semilla` y
`--definitiva`.
