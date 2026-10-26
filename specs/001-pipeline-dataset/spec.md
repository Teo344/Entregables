# Feature Specification: Pipeline de construcción del conjunto de datos

**Feature Branch**: `001-pipeline-dataset`

**Created**: 2026-10-25

**Status**: Draft

**Input**: User description: "Pipeline del dataset (OE2): inventario de fuentes, deduplicación por
SHA-256, registro de validación por experto, partición estratificada con semilla fija y
preprocesamiento, usando las imágenes ya reunidas en Modelo/."

## Contexto

Corresponde al **Objetivo Específico 2** de la tesis: construir un conjunto de datos multiclase de
frutos de aguacate (**sano**, **antracnosis** y **síntomas compatibles con anillado del
pedúnculo**) para entrenar, validar y probar el modelo (OE3). Hoy las imágenes están reunidas en
carpetas por clase, pero no existe un registro único de su origen, licencia, duplicados ni
validación experta, y no hay una partición reproducible. Conteo aproximado al 2026-10-25:

| Carpeta | Imágenes | Origen principal |
|---|---:|---|
| `Modelo/AGUACATESANOS` | ~2 882 | Repositorios públicos (prefijo `avocare_`) |
| `Modelo/ANTRACNOSIS` | ~1 873 | Kaggle (`Avocado NNNN`) y repositorios públicos (`avocare_`) |
| `Modelo/PEDUNCULO` | ~284 | Artículo MDPI *Computers* 15(8):513 (ring-neck, clase 1) |
| `Modelo/PORCLASIFICAR` | ~4 100 | Material sin clasificar (Kaggle con etiquetas CSV, ZIP de Drive) |

La clase de pedúnculo es unas diez veces menor que la de sanos. Decisión del equipo (2026-10-25):
se conservan todas las imágenes elegibles y el desbalance se compensa en el entrenamiento; por eso
la evaluación de OE3 debe reportar métricas macro (F1 macro) además de la exactitud.

## User Scenarios & Testing *(mandatory)*

Actores: **investigadores** (autores de la tesis), **experto agrónomo** que valida etiquetas y
**tutora** que revisa la evidencia.

### User Story 1 - Inventario trazable y sin duplicados (Priority: P1)

Un investigador ejecuta el inventario sobre las carpetas de clase y obtiene un manifiesto único en
el que cada imagen aparece con su clase, fuente, licencia, huella de contenido y estado. Los
duplicados exactos se agrupan y se conserva una sola copia; los contenidos que aparecen con
etiquetas contradictorias se excluyen y quedan registrados con su motivo.

**Why this priority**: sin inventario no hay forma de demostrar el origen ni la licencia de los
datos (principio II de la constitución) y cualquier partición posterior podría filtrar duplicados
entre entrenamiento y prueba.

**Independent Test**: ejecutar el inventario sobre las carpetas actuales y comprobar que el
manifiesto lista cada archivo una vez, que el número de contenidos únicos coincide con un conteo
independiente de huellas y que ningún archivo original cambió.

**Acceptance Scenarios**:

1. **Given** las carpetas de clase con imágenes, **When** se ejecuta el inventario, **Then** se
   genera un manifiesto con una fila por archivo con clase, ruta, fuente, licencia, huella de
   contenido, dimensiones y estado.
2. **Given** dos archivos con el mismo contenido en la misma clase, **When** se ejecuta el
   inventario, **Then** solo uno queda como "único" y el otro se marca como duplicado de él.
3. **Given** el mismo contenido en dos clases distintas, **When** se ejecuta el inventario,
   **Then** ambas apariciones se marcan "excluida por etiqueta en conflicto" y no pasan a ninguna
   partición.
4. **Given** un archivo ilegible o que no es una imagen, **When** se ejecuta el inventario,
   **Then** se marca "excluida por archivo inválido" sin detener el proceso.
5. **Given** que el inventario ya se ejecutó, **When** se ejecuta de nuevo sin cambios en las
   carpetas, **Then** el manifiesto resultante es idéntico.

---

### User Story 2 - Registro de validación por el experto (Priority: P2)

El investigador genera una planilla con las imágenes únicas pendientes de revisión para el experto
agrónomo. El experto marca cada imagen como aceptada, rechazada o reasignada a otra clase, con un
comentario opcional. Al incorporar la planilla, el manifiesto refleja la decisión, quién la tomó y
cuándo.

**Why this priority**: la antracnosis y el anillado se parecen visualmente; sin validación experta
la etiqueta es el punto más débil de la tesis (corrección C8). Depende del inventario (P1).

**Independent Test**: generar la planilla, simular las decisiones del experto en una copia,
incorporarla y verificar que el manifiesto muestra cada decisión y que las rechazadas no son
elegibles para partición.

**Acceptance Scenarios**:

1. **Given** un manifiesto con imágenes únicas, **When** se genera la planilla de validación,
   **Then** contiene una fila por imagen pendiente con su identificador, clase propuesta y una
   referencia que permita ubicar la imagen.
2. **Given** una planilla completada, **When** se incorpora, **Then** cada imagen queda como
   aceptada, rechazada o reasignada, con validador y fecha.
3. **Given** una planilla con una fila de identificador desconocido o decisión inválida, **When**
   se incorpora, **Then** esa fila se reporta como error y las demás se procesan.
4. **Given** una imagen reasignada a otra clase, **When** se incorpora la planilla, **Then** su
   clase efectiva pasa a ser la asignada por el experto y se conserva la clase original.

---

### User Story 3 - Partición estratificada y reproducible (Priority: P3)

El investigador genera las particiones de entrenamiento, validación y prueba a partir de las
imágenes elegibles, con proporciones por clase y una semilla fija. La misma entrada y la misma
semilla producen exactamente la misma partición.

**Why this priority**: la métrica final solo es válida si el conjunto de prueba nunca intervino en
el entrenamiento (corrección C9, principio III). Depende de P1 y, para la versión definitiva, de P2.

**Independent Test**: generar la partición dos veces con la misma semilla y comparar que es
idéntica; verificar que ningún contenido aparece en más de una partición y que las proporciones
por clase están dentro de la tolerancia.

**Acceptance Scenarios**:

1. **Given** imágenes elegibles, **When** se genera la partición con semilla 42, **Then** cada
   imagen queda en exactamente una de entrenamiento, validación o prueba, en proporción 70/15/15
   por clase.
2. **Given** la misma entrada y semilla, **When** se regenera la partición, **Then** el resultado
   es idéntico archivo por archivo.
3. **Given** imágenes de la fuente del artículo de pedúnculo que traen su propia partición,
   **When** se genera la partición, **Then** se respeta la asignación original de la fuente para
   que ninguna imagen de su conjunto de prueba termine en entrenamiento.
4. **Given** imágenes aún no validadas por el experto, **When** se genera la partición, **Then**
   la partición queda marcada como "provisional" y solo se marca "definitiva" cuando todas las
   imágenes incluidas están aceptadas.

---

### User Story 4 - Preprocesamiento e informe del conjunto (Priority: P4)

El investigador obtiene una copia preprocesada de cada partición (tamaño y formato uniformes, listos
para entrenamiento) y un informe con la distribución por clase, fuente y partición, las exclusiones
con su motivo y los parámetros de aumento de datos que se aplicarán solo al entrenamiento.

**Why this priority**: es el entregable que consume OE3 y la evidencia que va a la tesis (tablas de
distribución y de aumento, capítulos 5.1 y 5.2). Depende de P3.

**Independent Test**: preprocesar una partición y verificar que todas las imágenes resultantes
tienen el tamaño y formato definidos, que los originales no cambiaron y que el informe cuadra con
el manifiesto.

**Acceptance Scenarios**:

1. **Given** una partición generada, **When** se ejecuta el preprocesamiento, **Then** se crea una
   copia de cada imagen con el tamaño y formato definidos, organizada por partición y clase, sin
   modificar los originales.
2. **Given** el preprocesamiento completo, **When** se genera el informe, **Then** muestra conteos
   por clase × partición, por clase × fuente, las exclusiones por motivo y la tabla de parámetros
   de aumento.
3. **Given** una imagen muy pequeña o con proporción extrema, **When** se preprocesa, **Then** se
   registra una advertencia en el informe en lugar de descartarla en silencio.

---

### Edge Cases

- Mismo contenido presente en una carpeta de clase y en `PORCLASIFICAR`: cuenta una sola vez.
- Imágenes del CSV de Kaggle etiquetadas como "Scab" (roña): no pertenecen a ninguna de las tres
  clases y se excluyen con su motivo.
- Archivos del sistema (`desktop.ini`, `.gitkeep`) y formatos no soportados: se ignoran sin
  registrarse como imágenes.
- Nombres con caracteres especiales o acentos mal codificados (p. ej. `evaluaci+¦n`): el proceso
  no falla y conserva la ruta original en el manifiesto.
- Fuente sin licencia conocida: la imagen queda "licencia pendiente" y no es elegible hasta que se
  registre una licencia que permita uso académico.
- Imagen eliminada de la carpeta entre dos ejecuciones: el manifiesto la marca como ausente en
  lugar de perder su historial.
- Clase con menos imágenes que las necesarias para cubrir las tres particiones con la proporción
  pedida: se informa el déficit en lugar de producir particiones vacías.

## Requirements *(mandatory)*

### Functional Requirements

**Inventario y deduplicación**

- **FR-001**: El sistema MUST recorrer `Modelo/AGUACATESANOS`, `Modelo/ANTRACNOSIS`,
  `Modelo/PEDUNCULO` y, cuando se indique, las fuentes de `Modelo/PORCLASIFICAR`, y registrar cada
  imagen en un manifiesto único.
- **FR-002**: Cada fila del manifiesto MUST incluir: identificador estable, ruta original, clase
  propuesta, fuente, licencia, huella de contenido (SHA-256), dimensiones, estado y motivo.
- **FR-003**: El sistema MUST asignar fuente y licencia a partir de un registro de fuentes editable
  (prefijo o carpeta → fuente, URL, licencia), no de valores fijos en el código.
- **FR-004**: El sistema MUST detectar duplicados exactos por huella de contenido, conservar una
  copia canónica con un criterio determinista y marcar las demás como duplicadas de ella.
- **FR-005**: El sistema MUST excluir los contenidos que aparecen con etiquetas distintas y
  registrar el motivo "etiqueta en conflicto".
- **FR-006**: El sistema MUST incorporar el material de Kaggle usando su archivo de etiquetas,
  mapeando "Anthracnose" → antracnosis y "Healthy" → sano, y excluyendo "Scab" con su motivo.
- **FR-007**: El sistema MUST conservar los archivos originales sin modificarlos, moverlos ni
  renombrarlos.

**Validación experta**

- **FR-008**: El sistema MUST generar una planilla de validación con las imágenes únicas pendientes,
  en un formato que el experto pueda abrir sin herramientas técnicas.
- **FR-009**: El sistema MUST incorporar las decisiones del experto (aceptada, rechazada,
  reasignada con nueva clase) junto con el nombre del validador, la fecha y un comentario opcional.
- **FR-010**: El sistema MUST rechazar filas inválidas de la planilla, informarlas y procesar el
  resto.
- **FR-011**: Una imagen MUST ser elegible para la partición **definitiva** solo si es única, tiene
  licencia académica registrada, no está excluida y fue aceptada por el experto. La partición
  **provisional** admite además imágenes con validación o licencia pendientes, pero nunca las
  rechazadas ni las excluidas.

**Partición**

- **FR-012**: El sistema MUST generar particiones estratificadas por clase en proporción 70/15/15
  (entrenamiento/validación/prueba) con una semilla configurable, 42 por defecto.
- **FR-013**: La misma entrada y la misma semilla MUST producir exactamente la misma partición.
- **FR-014**: Ningún contenido MUST aparecer en más de una partición.
- **FR-015**: Las imágenes que traen una partición asignada por su fuente MUST conservarla.
- **FR-016**: La partición MUST marcarse "provisional" mientras incluya imágenes no aceptadas por
  el experto o con licencia pendiente, y "definitiva" cuando todas estén aceptadas y con licencia
  académica.
- **FR-017**: El sistema MUST conservar todas las imágenes elegibles en la partición, sin
  submuestreo; el desbalance se compensa en el entrenamiento (OE3, mediante pesos de clase o aumento
  dirigido). El informe MUST incluir la razón de desbalance entre la clase mayor y la menor y los
  pesos de clase sugeridos (inversamente proporcionales a la frecuencia en entrenamiento).

**Preprocesamiento e informe**

- **FR-018**: El sistema MUST producir una copia preprocesada de cada imagen elegible, con tamaño de
  224 × 224 píxeles y tres canales de color, organizada por partición y clase.
- **FR-019**: El sistema MUST documentar los parámetros de aumento de datos que se aplicarán solo al
  conjunto de entrenamiento; esta funcionalidad no genera imágenes aumentadas en disco.
- **FR-020**: El sistema MUST generar un informe con conteos por clase × partición, clase × fuente,
  exclusiones por motivo, advertencias de calidad y la tabla de parámetros de aumento.
- **FR-021**: Todas las salidas (manifiesto, planilla, partición, informe) MUST registrar la fecha
  de generación, la semilla y la versión de la configuración usada.

### Key Entities *(include if feature involves data)*

- **Imagen**: archivo de un fruto; tiene ruta original, huella de contenido, dimensiones, clase
  propuesta, clase efectiva, fuente, estado y motivo.
- **Fuente**: origen de un grupo de imágenes; tiene nombre, URL o referencia bibliográfica,
  licencia y, si existe, partición propia.
- **Decisión de validación**: veredicto del experto sobre una imagen (aceptada, rechazada,
  reasignada), con validador, fecha y comentario.
- **Partición**: asignación de cada imagen elegible a entrenamiento, validación o prueba, con
  semilla, proporciones, estrategia de balance y estado provisional/definitiva.
- **Informe del conjunto**: resumen de distribución, exclusiones, advertencias y parámetros de
  aumento, ligado a una partición concreta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de las imágenes de las carpetas de clase aparece en el manifiesto con fuente
  y huella; el 0 % de los archivos originales cambia tras ejecutar el pipeline completo.
- **SC-002**: Ningún contenido duplicado aparece en más de una partición (0 fugas verificadas por
  huella).
- **SC-003**: Regenerar la partición con la misma entrada y semilla da un resultado idéntico en el
  100 % de los casos.
- **SC-004**: La proporción de cada clase en cada partición difiere como máximo en 1 punto
  porcentual del 70/15/15 objetivo.
- **SC-005**: El experto puede revisar la planilla y devolverla sin asistencia técnica, y el 100 %
  de sus decisiones válidas queda reflejado en el manifiesto.
- **SC-006**: Un tercero (p. ej. la tutora) puede regenerar el manifiesto, la partición y el informe
  desde cero siguiendo la documentación en menos de 30 minutos de trabajo manual.
- **SC-007**: El informe permite completar las tablas de distribución y de aumento de los
  capítulos 5.1 y 5.2 de la tesis sin cálculos adicionales.

## Assumptions

- Las carpetas de clase actuales son la fuente de verdad de la clase propuesta; la clase efectiva
  la fija el experto.
- La organización previa de `Modelo/PEDUNCULO` (deduplicación SHA-256, exclusión del contenido en
  conflicto y `drive_candidates.csv`) se reutiliza como entrada y se integra al manifiesto; las 29
  imágenes de `DRIVE_CANDIDATAS` sin partición de origen se reparten con la partición estratificada.
- La deduplicación es exacta (por contenido idéntico); la detección de casi-duplicados
  (recortes, recompresiones) queda fuera del alcance de esta iteración.
- El aumento de datos se aplica en línea durante el entrenamiento (funcionalidad de OE3); aquí solo
  se fijan y documentan sus parámetros.
- Las capturas de campo propias (OE2-A2, con el GAD de Sigchos) se incorporarán más adelante como
  una fuente más, sin cambiar el proceso.
- Las imágenes no se versionan en Git; sí se versionan el manifiesto, el registro de fuentes, la
  planilla devuelta por el experto, la partición y el informe.
- El proceso se ejecuta en la computadora de los investigadores, sin depender de servicios en la
  nube.
