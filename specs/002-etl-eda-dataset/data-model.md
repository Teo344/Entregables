# Data Model: Proceso ETL y EDA del conjunto de datos

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Extiende el modelo de datos de [001](../001-pipeline-dataset/data-model.md). Las entidades de 001 (Fuente, Imagen del manifiesto, Grupo, Decisión del experto, Partición) no cambian salvo lo indicado.

## Cambios a entidades de 001

### Fuente (`config/fuentes.csv`)

- `patron` acepta varias alternativas glob separadas por `|`; una ruta pertenece a la fuente si coincide con alguna. Se sigue usando la primera fuente que coincide, en el orden del archivo.
- Fuente nueva **`herrera_marin`**:
  - clase sano;
  - patrón `AGUACATESANOS/sano-000[1-9].*|AGUACATESANOS/sano-001[0-7].*`;
  - referencia: tesis previa de Herrera y Marín, carpeta OneDrive;
  - licencia: "permiso de los autores";
  - `uso_academico = si`.
- `sano_web` → `uso_academico = no` (descargas de internet sin autor ni licencia).

### Imagen (`datos/manifiesto.csv`)

- Estado nuevo **`excluida_licencia`**: la fuente tiene `uso_academico = no`. Se evalúa después de `duplicada` y antes de `excluida_revision`.
- `excluida_revision` ahora también se origina en `datos/curacion/revision_etiquetas.csv` (decisión `excluir` de los autores), además de `exclusiones_revision.csv` (revisión 3).
- `clase_efectiva` puede cambiar por una decisión `reasignar` de los autores; la imagen queda `provisional` hasta la validación del experto.

Precedencia de estados, de mayor a menor: `excluida_invalida`, `excluida_conflicto`, `duplicada`, `excluida_licencia`, `excluida_revision`, `rechazada`, `test_campo`, `provisional`, `elegible`.

La decisión del experto (`aceptada` o `reasignada`) sigue prevaleciendo sobre `excluida_revision`.

## Entidades nuevas

### Representación (`datos/eda/cache/representaciones.npz`, ignorada por Git)

| Campo | Descripción |
| --- | --- |
| `ids` | `id_contenido` en el orden de las filas |
| `vectores` | matriz N × 1 280 (float32, normalizada L2) |
| `vectores_borde` | matriz N × 1 280 con el 60 % central tapado (sonda de fondo) |
| `huella` | SHA-256 de: pesos, versión de TensorFlow, lista de ids y SHA-256 de las imágenes |

Si una imagen nueva o modificada no está en la caché, se recalcula solo esa.

### Sospecha de etiqueta (`datos/etl/sospechas.csv`)

| Campo | Regla |
| --- | --- |
| `id_contenido`, `fuente`, `grupo` | del manifiesto |
| `clase_asignada` | `clase_efectiva` |
| `p_sano`, `p_antracnosis`, `p_pedunculo` | probabilidades fuera de muestra (4 decimales) |
| `clase_sugerida` | argmax de las clases que superan su umbral *t_k*; vacía si ninguna |
| `conflicto` | `si` cuando `clase_sugerida` ≠ `clase_asignada` |
| `puntaje` | 1 − *p*(clase asignada) |
| `vecinos_otra_clase` | fracción de los 10 vecinos (excluido su grupo) con otra clase |
| `a_revisar` | `si` si es conflicto o está en el 10 % superior de `puntaje` de su clase |
| `motivo_marca` | `conflicto`, `top10` o ambos |

Las filas se ordenan por `puntaje` descendente y luego por `id_contenido`.

### Decisión de revisión (`datos/curacion/revision_etiquetas.csv`, versionado)

| Campo | Valores |
| --- | --- |
| `id_contenido` | existente en el manifiesto |
| `decision` | `mantener`, `reasignar`, `excluir`, `no_seguro` |
| `clase_nueva` | obligatoria si `reasignar`; una de las tres clases |
| `alcance` | `grupo` (por defecto) o `imagen` |
| `atajo` | `ninguno`, `cartel`, `fondo`, `mano`, `otro` |
| `comentario`, `revisor`, `fecha` (AAAA-MM-DD), `planilla`, `tipo` (`sospecha`, `sistematica` o `auditoria`) | — |

Reglas:
- Gana la decisión más reciente por `id_contenido`.
- Con `alcance = grupo`, la decisión se aplica a todos los miembros del grupo que no tengan una decisión propia más reciente.
- Si una decisión de alcance `imagen` deja al grupo con clases o estados distintos, se emite una advertencia en el informe.

### Características de imagen (`datos/eda/tablas/caracteristicas.csv`)

| Campo | Descripción |
| --- | --- |
| `id_contenido` | — |
| `ancho`, `alto`, `megapixeles`, `proporcion` | de la imagen original con la orientación EXIF aplicada |
| `brillo`, `contraste` | media y desviación de L* |
| `nitidez` | varianza del Laplaciano a 512 px, sin el borde de 1 px |
| `tono_medio`, `tono_dispersion`, `saturacion`, `valor` | HSV |
| `fondo_fraccion` | fracción del borde (8 %) que es blanco o uniforme |
| `fondo` | `uniforme` si `fondo_fraccion` ≥ 0.6; si no, `natural` |

### Paso del embudo (`datos/etl/embudo.csv`)

| Campo | Descripción |
| --- | --- |
| `paso` | orden fijo: `inventariadas`, `invalida`, `duplicada`, `conflicto_clase`, `excluida_licencia`, `excluida_revision`, `rechazada`, `test_campo`, `fuera_de_cuota`, `conjunto_final` |
| `clase`, `fuente`, `imagenes` | — |

Invariante: para cada clase × fuente, `inventariadas` = suma de los demás pasos.

### Comparación con 001 (`datos/etl/comparacion_001.csv`)

| Campo | Valores |
| --- | --- |
| `id_contenido` | — |
| `clase_001`, `conjunto_001` | de `datos/etl/particion_001.csv` |
| `clase_002`, `conjunto_002` | de la partición nueva |
| `cambio` | `sale`, `entra`, `cambia_clase`, `cambia_conjunto`, `igual` |

### Resultado de sonda (`datos/eda/tablas/sondas.csv`)

| Campo | Descripción |
| --- | --- |
| `sonda` | `bajo_nivel`, `fondo` o `fuente_<clase>` |
| `exactitud_balanceada`, `azar` | — |
| `alerta` | `si` si la exactitud supera 0.80 (sondas `bajo_nivel` y `fondo`) |
| `n`, `conjuntos` | siempre `train+val` |

### Hallazgo del EDA (sección del informe y `informe_etl_eda.json` → `conclusiones[]`)

| Campo | Descripción |
| --- | --- |
| `id` | C1, C2, … |
| `conclusion`, `recomendacion` | — |
| `evidencia` | lista de rutas de tabla o figura (al menos una, SC-007) |

## Transiciones nuevas

```text
provisional/elegible --(revisión: excluir)--> excluida_revision
provisional/elegible --(revisión: reasignar)--> provisional (clase_efectiva = clase_nueva)
cualquier estado de candidata --(fuente uso_academico = no)--> excluida_licencia
excluida_revision --(experto: aceptada/reasignada)--> provisional/elegible   (igual que en 001)
```
