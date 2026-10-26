# Feature Specification: Pipeline de construcción del conjunto de datos

**Feature Branch**: `001-pipeline-dataset`

**Created**: 2026-10-25

**Status**: Draft (revisión 2, 2026-10-25)

**Input**: User description: "Pipeline del dataset (OE2): inventario de fuentes, deduplicación por
SHA-256, registro de validación por experto, partición estratificada con semilla fija y
preprocesamiento, usando las imágenes ya reunidas en Modelo/."

## Contexto

Corresponde al **Objetivo Específico 2** de la tesis: construir un conjunto de datos multiclase de
frutos de aguacate (**sano**, **antracnosis** y **síntomas compatibles con anillado del
pedúnculo**) para entrenar, validar y probar el modelo (OE3).

El 2026-10-25 se hizo una curación inicial de las carpetas de clase (ver
[datos/curacion/README.md](../../datos/curacion/README.md)):

- se retiraron las copias exactas, un archivo corrupto, las imágenes sanas menores de 224 px y los
  casi duplicados confirmados;
- se incorporó a la clase sano el pedúnculo sano (clase 0) del artículo MDPI.

Imágenes disponibles tras la curación:

| Clase (carpeta) | Fuente | Imágenes | Observación |
|---|---|---:|---|
| Sano (`AGUACATESANOS`) | `hass_` | 1 590 | 396 frutos fotografiados en varios días de maduración |
| | Pedúnculo sano MDPI (`DRIVE_PARTICIONES_ARTICULO`) | 360 | Partición de origen: 252 / 54 / 54 |
| | `sano-` | 231 | Imágenes web (incluye frutos partidos y árboles) |
| | `avocare_` | 209 | |
| | `rgb_sano_` | 83 | |
| Antracnosis (`ANTRACNOSIS`) | Kaggle `Avocado NNNN` | 1 022 | Fondo blanco |
| | `rgb_antracnosis_` | 664 | |
| | `avocare_` | 183 | |
| Pedúnculo (`PEDUNCULO`) | Ring-neck MDPI | 284 | Partición de origen: 182 / 36 / 37 + 29 sin asignar |

**Decisión del equipo (2026-10-25):** el conjunto tendrá como máximo **1 000 imágenes reales por
clase**: 1 000 sanas, 1 000 de antracnosis y las 284 de pedúnculo. Las 1 000 de cada clase se eligen
**por fuente**, para que ninguna fuente ni ningún fondo quede asociado a una sola clase. Las imágenes
que no entran a la muestra quedan como **reserva** en las carpetas fuente. El desbalance restante
(3.5 : 1) se compensa en el entrenamiento (OE3) solo sobre el conjunto de entrenamiento; por eso OE3
debe reportar F1 macro además de la exactitud. Validación y prueba contienen solo fotos reales.

## User Scenarios & Testing *(mandatory)*

Actores: **investigadores** (autores de la tesis), **experto agrónomo** que valida etiquetas y
**tutora** que revisa la evidencia.

### User Story 1 - Inventario trazable y sin duplicados (Priority: P1)

Un investigador ejecuta el inventario sobre las carpetas de clase y obtiene un manifiesto único en
el que cada imagen aparece con su clase, fuente, licencia, huella de contenido, grupo y estado. Los
duplicados exactos se agrupan y se conserva una sola copia; los contenidos que aparecen con
etiquetas contradictorias se excluyen y quedan registrados con su motivo. Las fotos del mismo fruto
quedan agrupadas.

**Why this priority**: sin inventario no hay forma de demostrar el origen ni la licencia de los
datos (principio II de la constitución), y cualquier partición posterior podría filtrar el mismo
fruto entre entrenamiento y prueba.

**Independent Test**: ejecutar el inventario sobre las carpetas actuales y comprobar que el
manifiesto lista cada archivo una vez, que el número de contenidos únicos coincide con un conteo
independiente de huellas, que las fotos de un mismo fruto comparten grupo y que ningún archivo
original cambió.

**Acceptance Scenarios**:

1. **Given** las carpetas de clase con imágenes, **When** se ejecuta el inventario, **Then** se
   genera un manifiesto con una fila por archivo con clase, ruta, fuente, licencia, huella de
   contenido, dimensiones (con la orientación EXIF aplicada), formato original, grupo y estado.
2. **Given** dos archivos con el mismo contenido en la misma clase, **When** se ejecuta el
   inventario, **Then** solo uno queda como "único" y el otro se marca como duplicado de él.
3. **Given** el mismo contenido en dos clases distintas, **When** se ejecuta el inventario,
   **Then** ambas apariciones se marcan "excluida por etiqueta en conflicto" y no pasan a ninguna
   partición.
4. **Given** un archivo ilegible o que no es una imagen, **When** se ejecuta el inventario,
   **Then** se marca "excluida por archivo inválido" sin detener el proceso.
5. **Given** varias fotos del mismo fruto (misma serie y número de fruto, o casi duplicados
   confirmados), **When** se ejecuta el inventario, **Then** comparten el mismo identificador de
   grupo.
6. **Given** que el inventario ya se ejecutó, **When** se ejecuta de nuevo sin cambios en las
   carpetas, **Then** el manifiesto resultante es idéntico.

---

### User Story 2 - Registro de validación por el experto (Priority: P2)

El investigador genera una planilla con las imágenes de la muestra pendientes de revisión para el
experto agrónomo. Por cada imagen, el experto:

- la marca como aceptada, rechazada o reasignada a otra clase;
- registra qué se ve (fruto completo, pedúnculo en primer plano, varios frutos, no es un fruto),
  el tipo de toma (campo, laboratorio, sin fondo) y la calidad;
- puede añadir un comentario.

Al incorporar la planilla, el manifiesto refleja la decisión, quién la tomó y cuándo.

**Why this priority**: la antracnosis y el anillado se parecen visualmente; sin validación experta
la etiqueta es el punto más débil de la tesis (corrección C8). Depende del inventario (P1).

**Independent Test**: generar la planilla, simular las decisiones del experto en una copia,
incorporarla y verificar que el manifiesto muestra cada decisión y que las rechazadas no son
elegibles para la partición.

**Acceptance Scenarios**:

1. **Given** un manifiesto con la muestra seleccionada, **When** se genera la planilla de
   validación, **Then** contiene una fila por imagen pendiente con su identificador, clase
   propuesta y un enlace que abre la imagen.
2. **Given** una planilla completada, **When** se incorpora, **Then** cada imagen queda como
   aceptada, rechazada o reasignada, con validador, fecha y las columnas descriptivas.
3. **Given** una planilla con una fila de identificador desconocido o decisión inválida, **When**
   se incorpora, **Then** esa fila se reporta como error y las demás se procesan.
4. **Given** una imagen reasignada a otra clase, **When** se incorpora la planilla, **Then** su
   clase efectiva pasa a ser la asignada por el experto y se conserva la clase original.
5. **Given** una imagen rechazada que estaba en la muestra, **When** se regenera la muestra,
   **Then** se repone con otra imagen de la reserva de la misma clase y fuente.

---

### User Story 3 - Muestra por fuente y partición reproducible (Priority: P3)

El investigador genera la muestra de hasta 1 000 imágenes por clase (con cuotas por fuente) y su
partición en entrenamiento, validación y prueba. La misma entrada y la misma semilla producen
exactamente la misma muestra y la misma partición.

**Why this priority**: la métrica final solo es válida si el conjunto de prueba nunca intervino en
el entrenamiento y no comparte frutos con él (corrección C9, principio III). Depende de P1 y, para
la versión definitiva, de P2.

**Independent Test**: generar la muestra y la partición dos veces con la misma semilla y comparar
que son idénticas; verificar que ningún grupo aparece en más de una partición, que se respetan las
cuotas por fuente y que las proporciones por clase están dentro de la tolerancia.

**Acceptance Scenarios**:

1. **Given** imágenes elegibles, **When** se genera la muestra, **Then** cada clase tiene como
   máximo el tope configurado (1 000) y cada fuente aporta su cuota configurada; si una fuente no
   alcanza su cuota, el faltante se informa.
2. **Given** la muestra, **When** se genera la partición con semilla 42, **Then** cada imagen
   queda en exactamente una de entrenamiento, validación o prueba, en proporción 70/15/15 por
   clase.
3. **Given** la misma entrada y semilla, **When** se regeneran la muestra y la partición, **Then**
   el resultado es idéntico archivo por archivo.
4. **Given** imágenes de las fuentes MDPI que traen su propia partición, **When** se genera la
   partición, **Then** se respeta la asignación original, de modo que ninguna imagen de su
   conjunto de prueba termina en entrenamiento.
5. **Given** un grupo de fotos del mismo fruto, **When** se genera la partición, **Then** todas
   las fotos del grupo quedan en la misma partición.
6. **Given** imágenes aún no validadas por el experto, **When** se genera la partición, **Then**
   la partición queda marcada como "provisional" y solo se marca "definitiva" cuando todas las
   imágenes incluidas están aceptadas y tienen licencia académica.

---

### User Story 4 - Preprocesamiento e informe del conjunto (Priority: P4)

El investigador obtiene la carpeta `Modelo/PROCESADO/` con la copia preprocesada de cada
partición: tamaño y formato uniformes, orientación corregida, lista para entrenar. Recibe además un
informe con:

- la distribución por clase, fuente y partición;
- las exclusiones con su motivo y el tamaño de la reserva;
- los pesos de clase sugeridos;
- los parámetros de aumento de datos que se aplicarán solo al entrenamiento.

**Why this priority**: es el entregable que consume OE3 y la evidencia que va a la tesis (tablas de
distribución y de aumento, capítulos 5.1 y 5.2). Depende de P3.

**Independent Test**: preprocesar una partición y verificar que todas las imágenes resultantes
tienen el tamaño, formato y orientación definidos, que los originales no cambiaron y que el informe
cuadra con el manifiesto.

**Acceptance Scenarios**:

1. **Given** una partición generada, **When** se ejecuta el preprocesamiento, **Then** se crea una
   copia de cada imagen con la orientación EXIF aplicada, en RGB, con el tamaño definido y
   organizada como `PROCESADO/<particion>/<clase>/`, sin modificar los originales.
2. **Given** el preprocesamiento completo, **When** se genera el informe, **Then** muestra conteos
   por clase × partición y por clase × fuente, exclusiones por motivo, tamaño de la reserva, pesos
   de clase y la tabla de parámetros de aumento.
3. **Given** una imagen muy pequeña, con proporción extrema, muy oscura o borrosa, **When** se
   preprocesa, **Then** se registra una advertencia en el informe en lugar de descartarla en
   silencio.

---

### Edge Cases

- Mismo contenido presente en una carpeta de clase y en `PORCLASIFICAR`: `PORCLASIFICAR` no es una
  fuente del pipeline y no se inventaría.
- Archivos del sistema (`desktop.ini`, `.gitkeep`) y formatos no soportados: se ignoran sin
  registrarse como imágenes.
- Nombres con caracteres especiales o acentos mal codificados: el proceso no falla y conserva la
  ruta original en el manifiesto.
- Fuente sin licencia conocida: la imagen queda "licencia pendiente"; puede entrar en la partición
  provisional, pero no en la definitiva.
- Imagen eliminada de la carpeta entre dos ejecuciones: el manifiesto deja de listarla y su
  decisión de validación se informa como "ausente".
- Fuente con menos imágenes que su cuota: se toman todas y el faltante se informa; no se completa
  con otra fuente salvo que la configuración lo indique.
- Grupo más grande que el déficit de una partición: el grupo entero va a la partición con mayor
  déficit, aunque se aparte de la cuota exacta (dentro de la tolerancia de SC-004).
- Fruto con antracnosis y síntomas de pedúnculo a la vez: el experto lo marca como "caso mixto" y
  la imagen se excluye de la muestra.

## Requirements *(mandatory)*

### Functional Requirements

**Inventario, grupos y deduplicación**

- **FR-001**: El sistema MUST recorrer `Modelo/AGUACATESANOS`, `Modelo/ANTRACNOSIS` y
  `Modelo/PEDUNCULO` (incluidas sus subcarpetas) y registrar cada imagen en un manifiesto único.
  `PORCLASIFICAR`, `RETIRADAS` y `PROCESADO` no son fuentes.
- **FR-002**: Cada fila del manifiesto MUST incluir: identificador de contenido, ruta original,
  clase propuesta, fuente, licencia, huella SHA-256, dimensiones con la orientación EXIF aplicada,
  formato y modo de color originales, grupo, estado y motivo.
- **FR-003**: El sistema MUST asignar fuente, licencia y partición de origen a partir de un
  registro de fuentes editable (patrón de ruta → fuente), no de valores fijos en el código.
- **FR-004**: El sistema MUST detectar duplicados exactos por huella de contenido, conservar una
  copia canónica con un criterio determinista y marcar las demás como duplicadas de ella.
- **FR-005**: El sistema MUST excluir los contenidos que aparecen con etiquetas distintas y
  registrar el motivo "etiqueta en conflicto".
- **FR-006**: El sistema MUST asignar un grupo a cada imagen. Comparten grupo las fotos del mismo
  fruto según la regla de su fuente (en la serie `hass_`, mismo tratamiento y número de fruto) y los
  casi duplicados confirmados de `datos/curacion/casi_duplicados_confirmados.csv`. El resto forma un
  grupo propio.
- **FR-007**: El sistema MUST conservar los archivos originales sin modificarlos, moverlos ni
  renombrarlos.

**Validación experta**

- **FR-008**: El sistema MUST generar una planilla de validación con las imágenes de la muestra
  pendientes, en un formato que el experto pueda abrir sin herramientas técnicas, con un enlace a
  cada imagen.
- **FR-009**: El sistema MUST incorporar las decisiones del experto (aceptada, rechazada,
  reasignada con nueva clase, caso mixto), las columnas descriptivas (objeto, toma, calidad), el
  nombre del validador, la fecha y un comentario opcional.
- **FR-010**: El sistema MUST rechazar filas inválidas de la planilla, informarlas y procesar el
  resto.
- **FR-011**: Una imagen MUST ser elegible para la partición **definitiva** solo si es canónica,
  tiene licencia académica registrada, no está excluida y fue aceptada por el experto. La partición
  **provisional** admite además imágenes con validación o licencia pendientes, pero nunca las
  rechazadas, las excluidas ni los casos mixtos.

**Muestra y partición**

- **FR-012**: El sistema MUST seleccionar una muestra de como máximo `max_por_clase` imágenes por
  clase (1 000 por defecto), respetando las cuotas por fuente de la configuración. Dentro de una
  fuente, la selección MUST ser aleatoria con semilla y priorizar una imagen por grupo antes de
  tomar una segunda foto del mismo grupo.
- **FR-013**: Las imágenes elegibles que no entran a la muestra MUST quedar marcadas como
  "reserva". Si una imagen de la muestra pasa a no elegible, se repone desde la reserva de la misma
  clase y fuente.
- **FR-014**: El sistema MUST generar particiones estratificadas por clase y fuente en proporción
  70/15/15 (entrenamiento/validación/prueba), con una semilla configurable, 42 por defecto.
- **FR-015**: La misma entrada y la misma semilla MUST producir exactamente la misma muestra y la
  misma partición.
- **FR-016**: Ningún grupo MUST quedar repartido entre particiones.
- **FR-017**: Las imágenes que traen una partición asignada por su fuente (artículos MDPI de
  pedúnculo, clases 0 y 1) MUST conservarla.
- **FR-018**: La partición MUST marcarse "provisional" mientras incluya imágenes no aceptadas por
  el experto o con licencia pendiente, y "definitiva" cuando todas estén aceptadas y con licencia
  académica. La partición provisional solo sirve para desarrollar y depurar el entrenamiento:
  ninguna métrica reportada en la tesis puede provenir de ella (constitución §II).
- **FR-019**: El sistema MUST reservar una fuente de "prueba de campo" (fotos propias de Sigchos)
  que, si existe, se procesa solo como conjunto de prueba independiente (`test_campo`) y nunca
  entra en entrenamiento, validación ni en la muestra general.

**Preprocesamiento e informe**

- **FR-020**: El sistema MUST producir en `Modelo/PROCESADO/<particion>/<clase>/` una copia
  preprocesada de cada imagen de la partición: con la orientación EXIF aplicada, en RGB (el canal
  alfa sobre fondo blanco) y de 224 × 224 píxeles.
- **FR-021**: El sistema MUST documentar los parámetros de aumento de datos que se aplicarán solo al
  conjunto de entrenamiento; esta funcionalidad no genera imágenes aumentadas en disco.
- **FR-022**: El sistema MUST generar un informe con:
  - conteos por clase × partición y por clase × fuente;
  - exclusiones por motivo y tamaño de la reserva;
  - advertencias de calidad (tamaño, proporción, oscuridad, borrosidad);
  - razón de desbalance y pesos de clase sugeridos (inversamente proporcionales a la frecuencia
    en entrenamiento);
  - la tabla de parámetros de aumento.
- **FR-023**: Todas las salidas (manifiesto, planilla, muestra, partición, informe) MUST registrar la
  fecha de generación, la semilla y la versión de la configuración usada. En el manifiesto, estos
  metadatos van en un archivo aparte para que el CSV sea idéntico entre ejecuciones (US1-6).

### Key Entities *(include if feature involves data)*

- **Imagen**: archivo de un fruto. Tiene ruta original, huella de contenido, dimensiones, clase
  propuesta, clase efectiva, fuente, grupo, estado y motivo.
- **Fuente**: origen de un grupo de imágenes. Tiene nombre, URL o referencia bibliográfica,
  licencia, cuota en la muestra, regla de agrupación y, si existe, partición propia.
- **Grupo**: conjunto de imágenes del mismo fruto o casi idénticas, que se reparten juntas.
- **Decisión de validación**: veredicto del experto sobre una imagen, con columnas descriptivas,
  validador, fecha y comentario.
- **Muestra**: selección de hasta 1 000 imágenes por clase según las cuotas por fuente. El resto de
  las elegibles es la reserva.
- **Partición**: asignación de cada imagen de la muestra a entrenamiento, validación o prueba, con
  semilla, proporciones y estado provisional o definitiva.
- **Informe del conjunto**: resumen de distribución, exclusiones, reserva, advertencias, pesos de
  clase y parámetros de aumento, ligado a una partición concreta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de las imágenes de las carpetas de clase aparece en el manifiesto con fuente,
  huella y grupo; el 0 % de los archivos originales cambia tras ejecutar el pipeline completo.
- **SC-002**: Ningún contenido ni grupo aparece en más de una partición (0 fugas verificadas por
  huella y por grupo).
- **SC-003**: Regenerar la muestra y la partición con la misma entrada y semilla da un resultado
  idéntico en el 100 % de los casos.
- **SC-004**: La proporción de cada clase en cada partición difiere como máximo en 1 punto
  porcentual del 70/15/15 objetivo, y cada fuente aporta su cuota (o todas sus imágenes, si tiene
  menos).
- **SC-005**: El experto puede revisar la planilla y devolverla sin asistencia técnica, y el 100 %
  de sus decisiones válidas queda reflejado en el manifiesto.
- **SC-006**: Un tercero (p. ej. la tutora) puede regenerar el manifiesto, la muestra, la partición y
  el informe desde cero siguiendo la documentación en menos de 30 minutos de trabajo manual.
- **SC-007**: El informe permite completar las tablas de distribución y de aumento de los capítulos
  5.1 y 5.2 de la tesis sin cálculos adicionales.

## Assumptions

- Las carpetas de clase son la fuente de verdad de la clase propuesta; la clase efectiva la fija el
  experto.
- La curación del 2026-10-25 (`scripts/curacion/organizar_clases.py`) ya se aplicó; el pipeline
  parte de las carpetas resultantes y no repite esos retiros.
- Cuotas iniciales de la muestra, ajustables en la configuración con justificación:
  - **Sano (1 000):** pedúnculo sano MDPI 360, `avocare_` 209, `rgb_sano_` 83, `hass_` 280 (una
    foto por fruto) y `sano-` 68.
  - **Antracnosis (1 000):** `avocare_` 183, `rgb_antracnosis_` 367 y Kaggle 450. Se limita Kaggle
    para que el fondo blanco no sea casi exclusivo de una clase.
  - **Pedúnculo:** las 284.
- La detección automática de casi duplicados ya se hizo en la curación; el pipeline solo usa la
  lista confirmada para agrupar y no busca casi duplicados nuevos.
- El aumento de datos se aplica en línea durante el entrenamiento (OE3); aquí solo se fijan y
  documentan sus parámetros.
- Las capturas de campo propias (OE2-A2, con el GAD de Sigchos) se registran como la fuente de
  prueba de campo de FR-019.
- `PORCLASIFICAR` y `RETIRADAS` se borrarán cuando la partición sea definitiva; no son entradas del
  pipeline.
- Las imágenes no se versionan en Git; sí se versionan el manifiesto, el registro de fuentes, las
  decisiones del experto, la muestra, la partición y el informe.
- El proceso se ejecuta en la computadora de los investigadores, sin depender de servicios en la
  nube.
