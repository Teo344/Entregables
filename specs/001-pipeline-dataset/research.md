# Research: Pipeline de construcción del conjunto de datos

**Feature**: `001-pipeline-dataset` | **Date**: 2026-10-25

Hallazgos del relevamiento de `Modelo/` (2026-10-25) y decisiones técnicas que resuelven las
incógnitas del contexto técnico.

## Relevamiento de las fuentes

| Carpeta | Prefijo de archivo | Archivos | Observación |
|---|---|---:|---|
| `AGUACATESANOS` | `hass_` | 1 590 | Origen por documentar |
| `AGUACATESANOS` | `sano_` | 1 000 | Origen por documentar (posible dataset de Herrera & Marín) |
| `AGUACATESANOS` | `avocare_` | 209 | Repositorio "avocare" |
| `AGUACATESANOS` | `rgb_sano_` | 83 | Nombre con hash; origen por documentar |
| `ANTRACNOSIS` | `Avocado NNNN` | 1 022 | Kaggle; coincide con las 1 022 filas "Anthracnose" del CSV |
| `ANTRACNOSIS` | `rgb_antracnosis_` | 668 | Origen por documentar |
| `ANTRACNOSIS` | `avocare_` | 183 | Repositorio "avocare" |
| `PEDUNCULO/DRIVE_PARTICIONES_ARTICULO` | `ring_<sha12>__` | 255 | Artículo MDPI *Computers* 15(8):513; train 182 / val 36 / test 37 |
| `PEDUNCULO/DRIVE_CANDIDATAS` | `ring_<sha12>__` | 29 | Misma fuente, sin partición de origen |
| `PORCLASIFICAR/Kaggle/...entrenamiento` | `Avocado NNNN` | 3 984 | Etiquetas en `Avocado labels 1.csv`: 1 764 Healthy, 1 022 Anthracnose, 1 197 Scab |
| `PORCLASIFICAR/Kaggle/...evaluacin` | — | 101 | Sin etiquetas en el CSV |

Implicaciones:

- Las imágenes Kaggle de antracnosis ya están copiadas en `ANTRACNOSIS`; al incluir
  `PORCLASIFICAR`, la deduplicación por SHA-256 las fusiona y solo se suman las "Healthy".
- Cuatro orígenes no tienen fuente ni licencia documentadas: el registro de fuentes nace con
  licencia `pendiente` y el equipo lo completa.
- `drive_candidates.csv` ya contiene SHA-256, dimensiones, partición de origen y la exclusión por
  conflicto de etiqueta; se reutiliza como entrada de la fuente de pedúnculo.

## Decisiones

### D1. Lenguaje y dependencias

- **Decision**: Python ≥ 3.11 con biblioteca estándar (`hashlib`, `csv`, `json`, `tomllib`,
  `random`) más Pillow (lectura y redimensionado) y openpyxl (planilla del experto). Pruebas con
  pytest. Versiones fijadas en `pyproject.toml`.
- **Rationale**: es el mismo lenguaje del entrenamiento (OE3) y basta para hashing, CSV y
  redimensionado. No hace falta TensorFlow aquí, lo que permite ejecutar el pipeline en la versión
  de Python instalada (3.14) sin esperar a que TensorFlow la soporte.
- **Alternatives considered**: pandas (innecesario para unos 9 000 registros y añade una
  dependencia pesada); notebook único (no es testeable ni reproducible por partes, contradice el
  principio III).

### D2. Forma de la herramienta

- **Decision**: paquete `avocadoia_datos` con una CLI por subcomandos (`inventario`, `planilla`,
  `incorporar`, `particionar`, `preprocesar`, `informe`, `todo`). Configuración en
  `config/dataset.toml`; registro de fuentes en `config/fuentes.csv`.
- **Rationale**: cada historia de usuario es un subcomando probado de forma independiente; la
  configuración versionada fija semilla, proporciones y parámetros (FR-021).
- **Alternatives considered**: scripts sueltos (se duplica la lógica de carga del manifiesto).

### D3. Manifiesto derivado, decisiones acumuladas

- **Decision**: el manifiesto (`datos/manifiesto.csv`) se **recalcula** en cada ejecución a partir
  de las carpetas, `config/fuentes.csv` y `datos/validacion/decisiones.csv`. Las decisiones del
  experto se acumulan en `decisiones.csv` (append-only, versionado); la planilla xlsx es solo el
  vehículo de ida y vuelta.
- **Rationale**: reejecutar sin cambios da un manifiesto idéntico (US1-5). Si una imagen
  desaparece, su decisión persiste en `decisiones.csv` y el manifiesto la marca `ausente`.
- **Alternatives considered**: editar el manifiesto a mano (se pierde la reproducibilidad).

### D4. Identificadores y copia canónica

- **Decision**: `id_contenido` = primeros 16 caracteres hexadecimales del SHA-256. Entre archivos
  con el mismo contenido, la copia canónica es la de mayor prioridad de carpeta (carpetas de clase
  > `PORCLASIFICAR`) y, a igualdad, la de ruta lexicográficamente menor.
- **Rationale**: es determinista y estable entre ejecuciones; 16 hex (64 bits) no colisionan en
  unos 10⁴ archivos.
- **Alternatives considered**: hash perceptual (detecta casi-duplicados, pero está fuera del alcance
  según la spec y da falsos positivos entre frutos parecidos).

### D5. Algoritmo de partición: estratificada con relleno de déficit

- **Decision**: para cada clase se calculan las cuotas objetivo (70/15/15 del total elegible,
  redondeo por mayor resto). Las imágenes con partición de origen la conservan (FR-015); las
  libres se barajan con `random.Random(semilla)` sobre una lista ordenada por `id_contenido` y se
  asignan para cubrir el déficit de cada partición frente a su cuota.
- **Rationale**: sin particiones de origen se reduce a una partición estratificada clásica. Con
  pedúnculo (182/36/37 fijas + 29 libres) se llega a 198/43/43 = 69.7/15.1/15.1 %, dentro de la
  tolerancia de ±1 pp (SC-004). Ordenar antes de barajar garantiza el mismo resultado sin importar
  el orden en que el sistema de archivos lista las imágenes (FR-013).
- **Alternatives considered**: `train_test_split` de scikit-learn (no admite asignaciones fijas y
  añade una dependencia); repartir las libres 70/15/15 por separado (daría 71.1 % de
  entrenamiento para pedúnculo, fuera de la tolerancia).

### D6. Elegibilidad y estado provisional

- **Decision**: una imagen es **elegible para la partición definitiva** si es canónica, no está
  excluida, tiene licencia académica y está aceptada por el experto. La partición **provisional**
  admite además imágenes `pendiente` de validación o de licencia, y lo declara en su cabecera y en
  el informe.
- **Rationale**: la validación del experto y la documentación de licencias llevarán semanas; sin
  partición provisional OE3 no puede preparar su pipeline. La definitiva sigue exigiendo todo
  (FR-011, FR-016). Esto precisa FR-011 de la spec: la exigencia de licencia aplica a la partición
  definitiva.
- **Alternatives considered**: bloquear hasta completar licencias (detiene el cronograma de
  sprints).

### D7. Preprocesamiento

- **Decision**: convertir a RGB (quitando el canal alfa sobre fondo blanco), redimensionar a
  224 × 224 por estiramiento con filtro LANCZOS y guardar en JPEG de calidad 95 en
  `Modelo/PROCESADO/<particion>/<clase>/<id_contenido>.jpg`. La normalización a [0, 1] y el
  aumento se hacen en el entrenamiento. Se advierten las imágenes menores de 224 px por lado o con
  una relación de aspecto mayor que 2:1.
- **Rationale**: el estiramiento es el método de la tesis previa (comparabilidad) y no introduce
  bordes de relleno, que podrían convertirse en un atajo correlacionado con una fuente o clase (por
  ejemplo, Kaggle "sin fondo"). Guardar en uint8 ocupa unas cuatro veces menos que tensores
  normalizados.
- **Alternatives considered**: relleno a cuadrado (riesgo de atajo); recorte central (puede cortar
  la lesión o el pedúnculo).

### D8. Parámetros de aumento documentados

- **Decision**: rotación ±45°, desplazamiento 20 %, zoom 20 %, volteo horizontal y vertical, brillo
  0.8–1.2, solo sobre entrenamiento. Se fijan en `config/dataset.toml` y el informe los publica.
- **Rationale**: son los mismos valores de Herrera & Marín, lo que permite comparar con la tesis
  previa; OE3 puede ajustarlos con justificación.

### D9. Pesos de clase sugeridos

- **Decision**: `peso_c = N_entrenamiento / (K × n_c)`, con K = 3, calculados sobre la partición de
  entrenamiento y publicados en el informe junto con la razón de desbalance `n_max / n_min`.
- **Rationale**: es la fórmula estándar de Keras/scikit-learn (`balanced`); concreta FR-017.

### D10. Planilla del experto

- **Decision**: archivo xlsx con columnas `id_contenido`, `clase_propuesta`, `ruta` (hipervínculo
  a la imagen), `decision` (lista desplegable: aceptada / rechazada / reasignada), `clase_nueva`
  (lista desplegable), `comentario`, `validador` y `fecha`. Se genera por clase o por lotes de
  tamaño configurable.
- **Rationale**: el experto la abre en Excel sin herramientas técnicas (SC-005); los desplegables
  evitan errores de tipeo y el hipervínculo abre la foto con un clic.
- **Alternatives considered**: CSV (el separador depende de la configuración regional de Excel y
  no admite desplegables).
