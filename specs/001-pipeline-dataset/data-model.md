# Data Model: Pipeline de construcción del conjunto de datos

**Feature**: `001-pipeline-dataset` | **Date**: 2026-10-25

Todos los artefactos son archivos de texto versionables (CSV UTF-8 con encabezado, JSON o
Markdown). Las imágenes no se versionan.

## Clases

| Código | Nombre en la tesis | Carpeta |
|---|---|---|
| `sano` | Sano | `Modelo/AGUACATESANOS` |
| `antracnosis` | Antracnosis | `Modelo/ANTRACNOSIS` |
| `pedunculo` | Síntomas compatibles con anillado del pedúnculo | `Modelo/PEDUNCULO` |

## Fuente — `config/fuentes.csv` (entrada, editada por el equipo)

| Campo | Tipo | Regla |
|---|---|---|
| `fuente` | texto | Identificador único (p. ej. `kaggle_avocado`, `mdpi_ring_neck`) |
| `patron` | glob | Ruta relativa a `Modelo/` con comodines; la primera coincidencia gana |
| `descripcion` | texto | Nombre legible |
| `referencia` | texto | URL o cita bibliográfica |
| `licencia` | texto | Identificador SPDX (`CC-BY-4.0`…) o `pendiente` |
| `uso_academico` | `si`/`no`/`pendiente` | Solo `si` es elegible para la partición definitiva |
| `particion_origen` | `si`/`no` | Si es `si`, la partición se lee del manifiesto de la fuente |

Una imagen sin fuente coincidente queda con `fuente = desconocida` y `uso_academico = pendiente`.

## Imagen — `datos/manifiesto.csv` (salida derivada, una fila por archivo)

| Campo | Tipo | Regla |
|---|---|---|
| `ruta` | texto | Relativa a `Modelo/`, separador `/`; clave de la fila |
| `id_contenido` | hex(16) | Primeros 16 caracteres del SHA-256 |
| `sha256` | hex(64) | Huella completa del contenido |
| `clase_propuesta` | clase o vacío | Por carpeta o por el CSV de Kaggle |
| `clase_efectiva` | clase o vacío | `clase_propuesta`, salvo reasignación del experto |
| `fuente` | texto | De `fuentes.csv` |
| `licencia`, `uso_academico` | texto | Copiados de la fuente |
| `ancho`, `alto` | entero | Píxeles; vacío si es inválida |
| `particion_origen` | `train`/`val`/`test`/vacío | Solo para fuentes con partición propia |
| `canonica` | `si`/`no` | Una sola `si` por `id_contenido` |
| `duplicado_de` | ruta o vacío | Ruta de la copia canónica |
| `validacion` | `pendiente`/`aceptada`/`rechazada`/`reasignada` | De `decisiones.csv` |
| `estado` | ver abajo | Estado calculado |
| `motivo` | texto | Explica las exclusiones y advertencias |

Orden de las filas: por `ruta` ascendente (salida determinista).

### Estados de una imagen

```text
                ┌──────────────── archivo inválido ──────────────► excluida_invalida
archivo ───────►│──────────────── etiqueta Scab / sin etiqueta ──► excluida_fuera_de_alcance
leído           │──────────────── mismo SHA en 2 clases ─────────► excluida_conflicto
                │──────────────── copia no canónica ─────────────► duplicada
                └──► canónica ──── experto la rechaza ───────────► rechazada
                                ── licencia o validación pend. ──► provisional
                                ── aceptada + licencia "si" ─────► elegible
```

Una entrada de `decisiones.csv` cuyo archivo ya no existe se informa como `ausente` en el informe;
no genera fila de imagen.

## Decisión de validación — `datos/validacion/decisiones.csv` (entrada acumulativa)

| Campo | Tipo | Regla |
|---|---|---|
| `id_contenido` | hex(16) | Debe existir en el manifiesto al incorporarse |
| `decision` | `aceptada`/`rechazada`/`reasignada` | Obligatorio |
| `clase_nueva` | clase o vacío | Obligatoria solo si `decision = reasignada` |
| `validador` | texto | Obligatorio |
| `fecha` | AAAA-MM-DD | Obligatoria |
| `comentario` | texto | Opcional |
| `planilla` | texto | Nombre de la planilla de la que provino |

Si hay varias decisiones sobre el mismo `id_contenido`, vale la de `fecha` más reciente (a igual
fecha, la última fila). El conflicto de etiquetas por contenido (`excluida_conflicto`) no se
resuelve con una decisión: hay que eliminar una copia de la carpeta equivocada.

## Partición — `datos/particion.csv` + `datos/particion.json`

`particion.csv`, una fila por imagen asignada:

| Campo | Regla |
|---|---|
| `id_contenido` | Imagen canónica elegible o provisional |
| `clase` | `clase_efectiva` |
| `particion` | `train` / `val` / `test` |
| `origen_asignacion` | `fuente` (FR-015) o `estratificada` |

`particion.json` (metadatos): `estado` (`provisional`/`definitiva`), `semilla`, `proporciones`,
`generado` (fecha y hora ISO), `version_config` (SHA-256 de `dataset.toml`), `conteos` por clase y
partición, y `huella_particion` (SHA-256 del CSV, para comprobar reproducibilidad).

Invariantes: cada `id_contenido` aparece una sola vez; para cada clase, la proporción de cada
partición está a ±1 pp de la cuota cuando la clase tiene 20 imágenes o más.

## Informe del conjunto — `datos/informe.md` + `datos/informe.json`

Contiene:
- tablas de clase × partición y de clase × fuente;
- exclusiones por motivo y advertencias de calidad;
- razón de desbalance y pesos de clase sugeridos;
- parámetros de aumento;
- estado de la partición;
- el número de decisiones pendientes y ausentes.

Se genera a partir del manifiesto, la partición y la configuración.

## Configuración — `config/dataset.toml`

Fija las rutas de las carpetas de clase, la inclusión de `PORCLASIFICAR`, la semilla (42), las
proporciones (0.70/0.15/0.15), el tamaño de salida (224), la calidad JPEG, los umbrales de
advertencia, los parámetros de aumento y el tamaño de lote de la planilla.
