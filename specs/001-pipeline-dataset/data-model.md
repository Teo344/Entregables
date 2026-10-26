# Data Model: Pipeline de construcción del conjunto de datos

**Feature**: `001-pipeline-dataset` | **Date**: 2026-10-25 (revisión 2)

Todos los artefactos son archivos de texto versionables: CSV UTF-8 con encabezado y fin de línea
LF, JSON o Markdown. Las imágenes no se versionan.

## Clases

| Código | Nombre en la tesis | Carpeta fuente |
|---|---|---|
| `sano` | Sano | `Modelo/AGUACATESANOS` |
| `antracnosis` | Antracnosis | `Modelo/ANTRACNOSIS` |
| `pedunculo` | Síntomas compatibles con anillado del pedúnculo | `Modelo/PEDUNCULO` |

## Fuente — `config/fuentes.csv` (entrada, editada por el equipo)

| Campo | Tipo | Regla |
|---|---|---|
| `fuente` | texto | Identificador único (p. ej. `hass`, `mdpi_pedunculo_sano`) |
| `clase` | clase | Clase de la carpeta a la que aplica |
| `patron` | glob | Ruta relativa a `Modelo/`; la primera fila que coincide gana |
| `descripcion` | texto | Nombre legible |
| `referencia` | texto | URL o cita bibliográfica |
| `licencia` | texto | Identificador SPDX (`CC-BY-4.0`…) o `pendiente` |
| `uso_academico` | `si`/`no`/`pendiente` | Solo `si` es elegible para la partición definitiva |
| `particion_origen` | `si`/`no` | Si es `si`, la partición se toma de la carpeta `train`/`val`/`test` de la ruta |
| `regla_grupo` | `ninguna`/`hass` | Regla de agrupación por nombre de archivo |
| `rol` | `general`/`test_campo` | `test_campo` queda fuera de la muestra (FR-019) |

Las cuotas por fuente viven en `dataset.toml` (ver Configuración). Una imagen sin fuente coincidente
queda con `fuente = desconocida`, sin cuota.

## Imagen — `datos/manifiesto.csv` (salida derivada, una fila por archivo)

| Campo | Tipo | Regla |
|---|---|---|
| `ruta` | texto | Relativa a `Modelo/`, con separador `/`; clave de la fila |
| `id_contenido` | hex(16) | Primeros 16 caracteres del SHA-256 |
| `sha256` | hex(64) | Huella completa |
| `clase_propuesta` | clase | Por carpeta |
| `clase_efectiva` | clase | `clase_propuesta`, salvo reasignación del experto |
| `fuente`, `licencia`, `uso_academico` | texto | De `fuentes.csv` |
| `ancho`, `alto` | entero | Píxeles tras la orientación EXIF; vacíos si la imagen es inválida |
| `formato`, `modo` | texto | Formato y modo de color originales (JPEG/PNG, RGB/RGBA…) |
| `particion_origen` | `train`/`val`/`test`/vacío | Solo para fuentes con partición propia |
| `grupo` | texto | Ver research D5 |
| `canonica` | `si`/`no` | Una sola `si` por `id_contenido` |
| `duplicado_de` | ruta o vacío | Ruta de la copia canónica |
| `validacion` | `pendiente`/`aceptada`/`rechazada`/`reasignada`/`mixto` | Última decisión |
| `estado` | ver abajo | Calculado |
| `en_muestra` | `si`/`no` | Seleccionada por las cuotas (lo escribe `particionar`) |
| `motivo` | texto | Explica las exclusiones y advertencias |

Las filas se ordenan por `ruta`.

### Estados de una imagen

```text
                ┌──────────────── archivo inválido ──────────────► excluida_invalida
archivo ───────►│──────────────── mismo SHA en 2 clases ─────────► excluida_conflicto
leído           │──────────────── copia no canónica ─────────────► duplicada
                └──► canónica ──── experto: rechazada o mixto ───► rechazada
                                ── fuente de prueba de campo ────► test_campo
                                ── licencia o validación pend. ──► provisional
                                ── aceptada + licencia "si" ─────► elegible
```

Las imágenes `provisional` o `elegible` que no entran a la muestra quedan con `en_muestra = no`;
son la **reserva**.

## Decisión de validación — `datos/validacion/decisiones.csv` (entrada acumulativa)

| Campo | Regla |
|---|---|
| `id_contenido` | Debe existir en el manifiesto al incorporarse |
| `decision` | `aceptada` / `rechazada` / `reasignada` / `mixto` |
| `clase_nueva` | Obligatoria solo si `decision = reasignada` |
| `objeto` | `fruto_completo` / `pedunculo_primer_plano` / `varios_frutos` / `no_es_fruto` / vacío |
| `toma` | `campo` / `laboratorio` / `sin_fondo` / vacío |
| `calidad` | `buena` / `aceptable` / `mala` / vacío |
| `validador`, `fecha` (AAAA-MM-DD) | Obligatorios |
| `comentario`, `planilla` | Opcionales |

Si hay varias decisiones para un mismo `id_contenido`, vale la de fecha más reciente; a igual
fecha, la última fila.

## Partición — `datos/particion.csv` + `datos/particion.json`

`particion.csv` tiene una fila por imagen de la muestra, ordenada por `particion`, `clase` e
`id_contenido`:

| Campo | Regla |
|---|---|
| `id_contenido` | Imagen de la muestra (o de `test_campo`) |
| `clase` | `clase_efectiva` |
| `fuente`, `grupo` | Del manifiesto |
| `particion` | `train` / `val` / `test` / `test_campo` |
| `origen_asignacion` | `fuente` (FR-017), `estratificada` o `test_campo` |
| `ruta` | Ruta original (para trazabilidad) |

`particion.json` guarda los metadatos:
- `estado`: `provisional` o `definitiva`;
- `semilla`, `proporciones`, `max_por_clase` y `cuotas`;
- `generado`: fecha y hora ISO;
- `version_config`: SHA-256 de `dataset.toml` y `fuentes.csv`;
- `conteos`: por clase × partición y por clase × fuente;
- `faltantes_cuota`;
- `huella_particion`: SHA-256 de `particion.csv`.

**Invariantes:**
- cada `id_contenido` y cada `grupo` aparece en una sola partición;
- cada clase tiene como máximo `max_por_clase` imágenes;
- en cada clase con 20 imágenes o más, la proporción de cada partición está a ±1 pp de su cuota.

## Advertencias — `datos/advertencias.csv`

Columnas `id_contenido`, `ruta`, `tipo` (`pequena` / `aspecto` / `oscura` / `borrosa`) y `valor`.
La escribe `preprocesar`.

## Informe del conjunto — `datos/informe.md` + `datos/informe.json`

Contiene:
- tablas de clase × partición y de clase × fuente;
- exclusiones por motivo y tamaño de la reserva por clase y fuente;
- faltantes de cuota y advertencias;
- razón de desbalance y pesos de clase;
- parámetros de aumento;
- estado de la partición y decisiones pendientes o ausentes.

## Configuración — `config/dataset.toml`

```toml
semilla = 42
proporciones = { train = 0.70, val = 0.15, test = 0.15 }
max_por_clase = 1000

[cuotas.sano]          # suma 1000
mdpi_pedunculo_sano = 360
avocare_sano = 209
rgb_sano = 83
hass = 280
sano_web = 68

[cuotas.antracnosis]   # suma 1000
avocare_antracnosis = 183
rgb_antracnosis = 367
kaggle_antracnosis = 450

[cuotas.pedunculo]     # sin tope: todas
mdpi_pedunculo = 284

[preprocesamiento]
tamano = 224
calidad_jpeg = 95
umbral_brillo = 40
umbral_borrosidad = 50

[aumento]              # solo entrenamiento; se documenta, no se aplica aquí
rotacion_grados = 45
desplazamiento = 0.20
zoom = 0.20
volteo_horizontal = true
volteo_vertical = true
brillo = [0.8, 1.2]

[planilla]
lote = 250
```
