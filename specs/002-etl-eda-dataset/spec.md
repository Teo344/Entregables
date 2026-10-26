# Feature Specification: Proceso ETL y análisis exploratorio (EDA) del conjunto de datos

**Feature Branch**: `002-etl-eda-dataset` (los cambios quedan sin commit; el equipo los versiona manualmente)

**Created**: 2026-10-26

**Status**: Draft

**Input**: User description: "Proceso formal de ETL (extracción, transformación/limpieza, carga) y análisis exploratorio de datos (EDA) sobre el conjunto de imágenes de aguacate de la especificación 001, para obtener un conjunto más limpio y completo antes del entrenamiento (OE3, que pasa a la especificación 003). Incluye detección de etiquetas dudosas para revisión manual, revisión visual sistemática, señales de atajo, embudo de calidad antes/después, distribuciones, características de las imágenes, sesgos por fuente y fondo, mapa de similitud, mosaicos y conclusiones accionables para el entrenamiento. Entregable: informe de ETL y EDA con figuras para la tesis."

## Contexto

La especificación 001 construyó el conjunto provisional: 2 284 imágenes en tres clases (sano 1 000, antracnosis 1 000, síntomas compatibles con anillado del pedúnculo 284), preprocesadas a 224 × 224 en `Modelo/PROCESADO` y divididas 70/15/15. La limpieza de esa fase fue mayormente automática (hash, casi duplicados, exclusiones por revisión). Los evaluadores de la tesis piden demostrar una limpieza y validación rigurosa con dos fases metodológicas explícitas: **ETL** (extraer, transformar/limpiar, cargar) y **EDA** (análisis exploratorio), antes de entrenar.

Esta funcionalidad reutiliza el pipeline de la especificación 001 como base del ETL; no lo reemplaza.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Detectar y revisar imágenes con etiqueta dudosa (Priority: P1)

Los autores necesitan encontrar las imágenes cuya etiqueta probablemente es incorrecta (un aguacate sano dentro de antracnosis, una lesión dentro de sano, un fruto sin pedúnculo visible dentro de la clase pedúnculo) sin revisar a mano las 2 284 una por una. El sistema ordena las imágenes por sospecha, las presenta para revisión y registra cada decisión (mantener, reasignar, excluir) con su motivo.

**Why this priority**: es el defecto que ya apareció (la foto sana en `train/antracnosis`) y el que más daña al modelo y a la defensa de la tesis. Sin esta limpieza, el EDA describiría un conjunto con errores.

**Independent Test**: ejecutar la detección sobre el conjunto actual, revisar la lista priorizada y comprobar que cada decisión queda registrada con fecha, revisor y motivo, y que la siguiente ejecución del ETL la aplica.

**Acceptance Scenarios**:

1. **Given** el conjunto de la especificación 001, **When** se ejecuta la detección de etiquetas dudosas, **Then** se obtiene una lista ordenada por grado de sospecha, con la clase asignada, la clase que sugiere el análisis y una miniatura de cada imagen.
2. **Given** una imagen marcada como dudosa, **When** el revisor decide "excluir" o "reasignar a otra clase", **Then** la decisión queda registrada con motivo, revisor y fecha, y el ETL siguiente la refleja sin borrar el archivo original.
3. **Given** la imagen conocida `Avocado 2022.jpg` (Kaggle, etiquetada antracnosis, aspecto sano), **When** se ejecuta la detección, **Then** aparece entre las sospechosas o ya figura como excluida por la revisión 3.

---

### User Story 2 - Informe de calidad del ETL con embudo antes/después (Priority: P1)

La tutora y el tribunal necesitan ver, paso a paso, cuántas imágenes entraron desde cada fuente, cuántas salieron en cada etapa de limpieza y por qué, y con qué conjunto final se entrena.

**Why this priority**: es la evidencia de que la limpieza fue rigurosa y trazable (principio II de la constitución) y el núcleo del entregable.

**Independent Test**: generar el informe y verificar que la suma de cada paso del embudo cuadra con el inventario inicial y con el conjunto final.

**Acceptance Scenarios**:

1. **Given** el inventario completo de las 9 fuentes, **When** se genera el informe ETL, **Then** muestra un embudo por clase y por fuente: imágenes extraídas → inválidas → duplicadas exactas → casi duplicadas → conflictos de clase → excluidas por revisión → etiquetas dudosas excluidas o reasignadas → fuera de cuota → conjunto final.
2. **Given** el embudo, **When** se suman las salidas de cada paso, **Then** el total coincide exactamente con las imágenes extraídas (ninguna imagen sin explicar).
3. **Given** una fuente, **When** se consulta el informe, **Then** se ven su referencia, licencia, uso académico permitido y la cantidad aportada al conjunto final.

---

### User Story 3 - Análisis exploratorio del conjunto final (Priority: P2)

Los autores necesitan describir el conjunto con estadísticas y figuras para el capítulo de datos de la tesis: distribución por clase, fuente y conjunto; características de las imágenes originales; mosaicos de ejemplos.

**Why this priority**: el EDA es la segunda fase metodológica solicitada y fundamenta las decisiones del entrenamiento; depende de que la limpieza (P1) esté hecha.

**Independent Test**: generar el EDA y comprobar que cada figura y tabla tiene título, unidades y fuente de datos, y que las cifras coinciden con el manifiesto.

**Acceptance Scenarios**:

1. **Given** el conjunto final, **When** se genera el EDA, **Then** incluye la distribución de imágenes por clase × fuente × conjunto (train, val, test) en tablas y gráficos.
2. **Given** las imágenes originales (antes del redimensionado), **When** se analizan sus características, **Then** el EDA reporta por clase y por fuente la distribución de resolución, proporción, brillo, contraste, nitidez y color (tono, saturación, valor).
3. **Given** cada clase y cada fuente, **When** se generan los mosaicos, **Then** hay al menos un mosaico de muestras aleatorias reproducibles por combinación clase × fuente.

---

### User Story 4 - Detectar sesgos y atajos visuales (Priority: P2)

Los autores necesitan saber si alguna característica ajena a la enfermedad (fuente, fondo blanco, iluminación, carteles escritos, encuadre del pedúnculo) permite adivinar la clase, porque el modelo aprendería ese atajo en lugar de la lesión.

**Why this priority**: es el riesgo que la tesis previa no controló y que el principio IV obliga a verificar después con Grad-CAM++; detectarlo antes permite corregirlo en los datos.

**Independent Test**: ejecutar el análisis de sesgos y comprobar que reporta, por cada señal, cuánto se asocia a la clase y si supera el umbral de alerta.

**Acceptance Scenarios**:

1. **Given** el conjunto final, **When** se analiza el fondo de las imágenes, **Then** el EDA reporta qué proporción de cada clase tiene fondo uniforme (blanco o de laboratorio) frente a fondo natural.
2. **Given** las características de imagen y la fuente, **When** se mide si permiten predecir la clase sin mirar la lesión, **Then** el EDA reporta el grado de asociación y marca como riesgo cualquier señal que identifique la clase con una exactitud claramente superior al azar.
3. **Given** las imágenes con carteles o texto visibles, **When** se revisan, **Then** quedan marcadas y su cantidad por clase aparece en el informe.

---

### User Story 5 - Mapa de similitud del conjunto (Priority: P3)

Los autores necesitan una vista global que muestre si las tres clases se separan, si hay imágenes fuera de su grupo y si las fuentes forman islas propias.

**Why this priority**: complementa la detección de etiquetas dudosas y el análisis de sesgos con una figura comprensible para el tribunal; no es requisito para entrenar.

**Independent Test**: generar el mapa y verificar que cada punto se puede identificar con su imagen y que existen versiones coloreadas por clase y por fuente.

**Acceptance Scenarios**:

1. **Given** el conjunto final, **When** se genera el mapa de similitud en dos dimensiones, **Then** existen dos versiones: coloreada por clase y coloreada por fuente.
2. **Given** un punto aislado o rodeado de otra clase, **When** se consulta, **Then** se puede identificar la imagen correspondiente para revisarla.

---

### User Story 6 - Conclusiones accionables para el entrenamiento (Priority: P3)

El equipo necesita que el EDA termine en recomendaciones concretas para la especificación 003: pesos por clase, aumento de datos, riesgos de atajo y limitaciones conocidas.

**Why this priority**: conecta el análisis con el modelo; sin ellas el EDA queda como descripción sin consecuencia.

**Independent Test**: comprobar que cada conclusión cita la tabla o figura del EDA que la respalda.

**Acceptance Scenarios**:

1. **Given** la distribución final por clase, **When** se redactan las conclusiones, **Then** incluyen los pesos por clase recomendados y su cálculo.
2. **Given** los sesgos detectados, **When** se redactan las conclusiones, **Then** cada riesgo tiene una mitigación propuesta (cambio de cuotas, aumento específico, verificación con Grad-CAM++).

---

### Edge Cases

- Una imagen dudosa pertenece a un grupo (vistas del mismo fruto o casi duplicados): la decisión del revisor se aplica a todo el grupo, o el revisor decide imagen por imagen y el sistema advierte si el grupo queda partido.
- La limpieza deja una clase por debajo de su cuota: se completa con imágenes de reserva de la misma clase respetando las cuotas por fuente; si no hay reserva suficiente, la clase queda con menos imágenes y el informe lo declara.
- Una decisión manual contradice una exclusión automática anterior (revisión 3): prevalece la decisión manual más reciente, como en la especificación 001.
- Una imagen se reasigna a otra clase: cambia de clase en el manifiesto sin mover ni copiar el archivo original, y vuelve a pasar por la partición.
- Una fuente sin licencia de uso académico confirmada (las descargas de internet de `sano_web`): sus imágenes no pueden entrar al conjunto definitivo y su cuota se cubre con reserva de la misma clase.
- El análisis de similitud o de sospecha necesita un modelo preentrenado: debe ejecutarse sin conexión una vez descargado y con versión fija, para que los resultados sean reproducibles.
- La regeneración de muestra y partición cambia el conjunto de la especificación 001: el informe compara el conjunto anterior y el nuevo (imágenes que entran y salen por clase y conjunto).

## Requirements *(mandatory)*

### Functional Requirements

**Extracción (E)**

- **FR-001**: El sistema MUST documentar cada fuente con referencia completa, URL, licencia, permiso de uso académico y cantidad de imágenes extraídas por clase.
- **FR-002**: El sistema MUST reutilizar el inventario de la especificación 001 (hash SHA-256, formato, dimensiones, orientación) como resultado de la extracción, sin alterar los archivos originales.

**Transformación y limpieza (T)**

- **FR-003**: El sistema MUST reutilizar las reglas de limpieza de la especificación 001 (inválidas, duplicados exactos, casi duplicados confirmados, conflictos de clase, exclusiones por revisión, agrupación de vistas del mismo fruto) y registrar cuántas imágenes retira cada una.
- **FR-004**: El sistema MUST calcular para cada imagen candidata un puntaje de sospecha de etiqueta incorrecta, basado en la coherencia entre su etiqueta y las de las imágenes visualmente más parecidas, y producir una lista ordenada de mayor a menor sospecha.
- **FR-005**: El sistema MUST generar material de revisión (miniaturas, clase asignada, clase sugerida, puntaje, fuente, grupo) para las imágenes sospechosas y para una revisión visual sistemática por clase.
- **FR-006**: El sistema MUST registrar cada decisión de revisión (mantener, reasignar con clase nueva, excluir) con motivo, revisor y fecha, y aplicarla en la siguiente ejecución sin borrar ni mover archivos originales.
- **FR-007**: El sistema MUST marcar las imágenes con señales de atajo conocidas (carteles o texto visibles, fondo uniforme de laboratorio) para que queden visibles en el informe y en la revisión.
- **FR-008**: Cuando una decisión afecte a una imagen de un grupo, el sistema MUST aplicar la regla de grupo definida (decisión para todo el grupo por defecto) y advertir si un grupo quedaría repartido entre conjuntos.
- **FR-009**: Tras la limpieza, el sistema MUST regenerar la muestra por cuotas y la partición estratificada con la misma semilla y reglas de la especificación 001.

**Carga (L)**

- **FR-010**: El sistema MUST regenerar las imágenes preprocesadas del conjunto final en la misma estructura (`<conjunto>/<clase>/<id>.jpg`) y actualizar manifiesto y partición con su huella (hash).
- **FR-011**: El sistema MUST producir un embudo de calidad por clase y fuente donde cada imagen extraída esté contada en exactamente un paso de salida o en el conjunto final.
- **FR-012**: El sistema MUST comparar el conjunto nuevo con el de la especificación 001 y reportar las imágenes que entran y salen por clase y conjunto.
- **FR-013**: El sistema MUST permitir registrar la validación definitiva del experto sobre el conjunto final y, solo con ella y con licencias confirmadas para todas las fuentes usadas, declarar la partición definitiva.

**Análisis exploratorio (EDA)**

- **FR-014**: El EDA MUST reportar la distribución de imágenes por clase × fuente × conjunto en tablas y gráficos.
- **FR-015**: El EDA MUST reportar, sobre las imágenes originales y por clase y fuente, la distribución de resolución, proporción, brillo, contraste, nitidez y color (tono, saturación, valor).
- **FR-016**: El EDA MUST cuantificar, por clase, la proporción de fondo uniforme frente a natural, y la asociación de la fuente y de las características de imagen con la clase, marcando como riesgo las señales que predicen la clase claramente por encima del azar.
- **FR-017**: El EDA MUST incluir un mapa de similitud en dos dimensiones del conjunto final, en versiones coloreadas por clase y por fuente, con la posibilidad de identificar la imagen de cada punto.
- **FR-018**: El EDA MUST incluir mosaicos de muestras reproducibles por clase × fuente.
- **FR-019**: El EDA MUST terminar con conclusiones accionables para el entrenamiento (pesos por clase con su cálculo, aumento de datos recomendado, riesgos de atajo con mitigación y limitaciones), cada una referida a la tabla o figura que la respalda.
- **FR-020**: Ningún análisis del EDA que oriente decisiones de modelado MUST usar información del conjunto de prueba más allá de describir su tamaño y composición (principio II).

**Entregable y reproducibilidad**

- **FR-021**: El sistema MUST generar un informe de ETL y EDA, con todas las figuras en archivos independientes aptos para insertar en la tesis, y una versión en Word.
- **FR-022**: Toda la cadena (ETL, EDA, informe) MUST poder regenerarse desde el repositorio con un comando documentado, semilla fija y versiones fijas de dependencias y modelo preentrenado, produciendo las mismas cifras.
- **FR-023**: La detección de etiquetas dudosas y el mapa de similitud MUST ejecutarse sin conexión a internet una vez instaladas las dependencias.

### Key Entities

- **Fuente**: origen de imágenes; referencia, URL, licencia, uso académico, clase(s) que aporta.
- **Imagen (registro del manifiesto)**: id de contenido, ruta original, fuente, clase, estado, grupo, características medidas (resolución, brillo, contraste, nitidez, color, tipo de fondo, señales de atajo).
- **Sospecha de etiqueta**: imagen, clase asignada, clase sugerida, puntaje, vecinos más parecidos.
- **Decisión de revisión**: imagen o grupo, acción (mantener, reasignar, excluir), clase nueva, motivo, revisor, fecha.
- **Paso del embudo**: nombre del paso, clase, fuente, imágenes que entran, imágenes que salen, motivo.
- **Hallazgo del EDA**: tabla o figura, conclusión, recomendación para el entrenamiento.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de las imágenes extraídas aparece en exactamente un paso del embudo o en el conjunto final (cero imágenes sin explicar).
- **SC-002**: El 100 % de las imágenes marcadas como sospechosas por encima del umbral de revisión tiene una decisión registrada antes de declarar el conjunto definitivo.
- **SC-003**: En una muestra aleatoria de 100 imágenes del conjunto final revisada a mano después de la limpieza, a lo sumo 2 tienen una etiqueta incorrecta.
- **SC-004**: El conjunto final tiene 0 imágenes repetidas o casi idénticas entre train, val y test, y 0 grupos repartidos entre conjuntos.
- **SC-005**: Ninguna señal ajena a la lesión (fuente, fondo, brillo, encuadre) permite identificar la clase con una exactitud superior a 80 % sin que el informe la declare como riesgo con su mitigación.
- **SC-006**: Regenerar la cadena completa dos veces produce cifras, tablas y huella de partición idénticas.
- **SC-007**: Cada conclusión del EDA cita al menos una tabla o figura que la respalda, y la tutora puede verificar cada cifra contra los archivos del repositorio.

## Assumptions

- **Referencia metodológica**: Calapaqui, G., Guarderas, D. y Fuertes, W. (2026). *A Model Implementation to Detect Hate Speech Associated with Gender Violence by Natural Language Processing and Machine Learning*. En ICCSA 2026, LNCS 16768, pp. 202–219. Springer. doi:10.1007/978-3-032-30488-9_13. Su fase ETL recoge y limpia los datos, une varias fuentes en un corpus balanceado y luego entrena. Se adapta así a imágenes:

  | En el artículo (texto) | En esta funcionalidad (imágenes) |
  | --- | --- |
  | Eliminar duplicados | Duplicados exactos (SHA-256) y casi duplicados |
  | Eliminar valores nulos | Imágenes corruptas o ilegibles |
  | Eliminar caracteres especiales (ruido) | Señales de atajo y ruido visual: carteles, fondos de laboratorio |
  | Convertir etiquetas con umbral 0.5 | Consolidar etiquetas: sospecha de etiqueta incorrecta, revisión manual y validación del experto |
  | Unir tres conjuntos en un corpus balanceado | Unir 9 fuentes en un conjunto balanceado por cuotas de clase y fuente |

  El resumen del artículo no menciona un EDA. Esta funcionalidad lo agrega como fase propia porque lo exigen los evaluadores de la tesis. Si el texto completo usa otros nombres de fases, se ajustan sin cambiar los requisitos.
- **Revisores**: la revisión manual de etiquetas la hacen los autores; el experto agrónomo valida el conjunto final y resuelve los casos que los autores marquen como "no seguro".
- **Validador experto**: todavía no está designado. Esta funcionalidad se completa con el conjunto en estado **provisional**: ETL, EDA, informe y conjunto limpio quedan listos. La partición definitiva (FR-013) se declara cuando el experto valide y registre sus decisiones. Esta funcionalidad no habilita el entrenamiento: si se permite o no entrenar de forma exploratoria con datos provisionales lo decide la especificación 003 dentro de la constitución, que exige la validación del experto antes de que una imagen entre a entrenamiento.
- **Umbral de revisión**: se revisan a mano al menos las imágenes del 10 % con mayor puntaje de sospecha de cada clase, más todas las que el análisis asigne a otra clase con alta coherencia.
- **Cuotas y semilla**: se mantienen las cuotas por fuente, la semilla 42 y la proporción 70/15/15 de la especificación 001; si la limpieza obliga a cambiar una cuota, el cambio se justifica en el informe.
- **`sano_web`**: proviene de la carpeta de datos de la tesis anterior de Herrera y Marín (OneDrive), que mezcla fotos tomadas por sus autores y descargas de internet. Se divide en dos fuentes:
  - **Fotos propias de Herrera y Marín**: las 17 capturas originales de teléfono (`sano-0001` a `sano-0017`, Google Pixel 8, 3072 × 4080). Se citan como tesis previa; el equipo **tiene el permiso** de sus autores.
  - **Descargas de internet**: las otras 214, entre miniaturas y fotos de cámaras de terceros (2015–2020). No tienen autor ni licencia identificables, así que se excluyen del conjunto definitivo.
  
  **Decisión (2026-10-26):** las imágenes descargadas que hoy están en la muestra se reemplazan con **vistas adicionales de los frutos Hass que ya están en el conjunto**. Hay 1 194 vistas de reserva de los 396 frutos (otros días u otro lado), con licencia CC BY 4.0. Cada vista va al mismo conjunto que su fruto, así que no hay fugas. La clase sano mantiene 1 000 imágenes. No se descargan frutos Hass nuevos.
- **Imágenes de campo (Sigchos)**: siguen reservadas como prueba externa; el EDA las describe por separado y no entran a la muestra.
- **Alcance**: no se entrena ni evalúa el clasificador (especificación 003); el modelo preentrenado se usa solo para obtener representaciones de las imágenes con fines de limpieza y análisis.
- **Kaggle (`kaggle_antracnosis`)**: no tiene licencia abierta ("Data files © Original Authors"). Se considera apta para uso académico porque el autor la publicó para que otros la usen ("quien haga uso de esta colección de imágenes…") y porque se cita como fuente. La justificación queda escrita en `config/fuentes.csv` y en el informe, y el equipo puede reforzarla con un permiso del autor.
- **Revisión visual sistemática** (FR-005): se hace recorriendo los mosaicos por clase y fuente y, cuando se quiera revisar imagen por imagen, con planillas de tipo `sistematica`. Las imágenes con carteles se buscan en esos dos recorridos. Fuera de ellos no se buscan carteles, así que el informe declara que su conteo es parcial.
- **Fuente `avocare_`**: sigue excluida; su licencia no se verifica porque no aporta imágenes.