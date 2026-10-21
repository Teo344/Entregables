# Feature Specification: Preparación del conjunto de datos y clasificación fitosanitaria del aguacate

**Feature Branch**: `001-avocado-health-assessment`

**Created**: 2026-10-20

**Status**: Draft

**Input**: User description: "Preparar un conjunto de datos trazable de aguacates sanos, con antracnosis y con síntomas compatibles con anillado del pedúnculo; verificar las etiquetas de fuentes públicas y propias con apoyo técnico agrícola; crear divisiones configurables de entrenamiento, validación y prueba; comparar MobileNetV3 y EfficientNet-B0 con métricas acordadas; y posteriormente integrar el modelo en una aplicación Android de gama media que funcione sin conexión, permita capturar o elegir imágenes, muestre predicción, incertidumbre e información complementaria revisada."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preparar un conjunto de datos confiable (Priority: P1)

El equipo del proyecto reúne imágenes públicas y propias de aguacates para las clases fruto sano, antracnosis y síntomas compatibles con anillado del pedúnculo. Las etiquetas de las imágenes propias son revisadas por una persona experta o técnica agrícola usando criterios acordados. Las etiquetas de conjuntos públicos se conservan solo cuando la definición original y su correspondencia con las clases del proyecto pueden verificarse. Las imágenes originales se preservan y las copias de trabajo mantienen un registro de su fuente y etiqueta.

**Why this priority**: La calidad, procedencia y clasificación de los datos condicionan la validez de los modelos y de las conclusiones de la tesis.

**Independent Test**: Revisar un conjunto preparado y comprobar que cada imagen admitida tiene fuente y clase documentadas, que las etiquetas propias tienen registro de revisión técnica y que los originales permanecen sin cambios. Confirmar que las imágenes sin correspondencia verificable quedan pendientes o excluidas.

**Acceptance Scenarios**:

1. **Given** imágenes originales de una o más fuentes, **When** el equipo prepara el conjunto de trabajo, **Then** los originales permanecen intactos y cada copia puede vincularse con su identificador, nombre original, fuente y etiqueta asignada.
2. **Given** una imagen propia, **When** se asigna su clase, **Then** la decisión se registra bajo criterios acordados y con revisión de una persona experta o técnica agrícola.
3. **Given** una imagen de un conjunto público con una etiqueta cuyo significado o equivalencia no está verificado, **When** se revisa su incorporación, **Then** no se asigna automáticamente a una clase del proyecto y queda pendiente o excluida.
4. **Given** las imágenes admitidas por clase, **When** se configuran las proporciones de entrenamiento, validación y prueba, **Then** el proceso calcula cantidades por clase y totales, verifica que las proporciones sumen 100% y mantiene las tres particiones separadas.

---

### User Story 2 - Comparar y seleccionar un clasificador multiclase (Priority: P1)

El equipo entrena y compara modelos que clasifican imágenes de aguacate como fruto sano, antracnosis o síntomas compatibles con anillado del pedúnculo. Compara MobileNetV3 y EfficientNet-B0 bajo las mismas particiones y condiciones, y revisa las métricas antes de seleccionar un modelo para su integración móvil.

**Why this priority**: El modelo de clasificación es el resultado central de la primera iteración y debe evaluarse con datos de prueba separados antes de integrarlo en la aplicación.

**Independent Test**: Evaluar cada modelo con el mismo conjunto de prueba retenido y comprobar que reporta resultados para las tres clases, las métricas acordadas y las limitaciones del conjunto.

**Acceptance Scenarios**:

1. **Given** las particiones aprobadas del conjunto, **When** se entrenan MobileNetV3 y EfficientNet-B0, **Then** ambos modelos se comparan usando las mismas clases, particiones y procedimiento de evaluación.
2. **Given** un modelo evaluado, **When** se revisa su informe, **Then** se presentan exactitud, precisión, recall y F1 por clase y macro, matriz de confusión y AUC-ROC multiclase con estrategia one-vs-rest macro documentada.
3. **Given** los resultados de prueba, **When** el equipo decide si el objetivo mínimo se cumple, **Then** usa F1 macro de al menos 90% en el conjunto de prueba retenido como criterio mínimo y presenta 95% como meta aspiracional, no como garantía.
4. **Given** la comparación, **When** se propone un modelo para Android, **Then** la selección considera calibración, generalización, tamaño y velocidad de inferencia en un dispositivo Android de gama media, además del desempeño de clasificación.

---

### User Story 3 - Clasificar un aguacate desde Android sin conexión (Priority: P2)

Una persona productora o vinculada al cultivo usa un teléfono Android de gama media para tomar una foto del fruto o elegirla de la galería. Recibe una predicción entre las tres clases, su nivel de confianza y una advertencia de que el resultado es orientativo, no un diagnóstico definitivo.

**Why this priority**: La aplicación lleva el modelo evaluado al contexto de uso previsto y debe funcionar en campo sin depender de internet.

**Independent Test**: En un dispositivo Android objetivo desconectado de internet, completar una clasificación desde la cámara y otra desde la galería; verificar clase, confianza, advertencia y manejo de errores.

**Acceptance Scenarios**:

1. **Given** que la persona dispone de una imagen válida, **When** la captura o la selecciona y solicita evaluación, **Then** la aplicación muestra una clase admitida, el nivel de confianza y la advertencia de uso orientativo.
2. **Given** una imagen dañada, desenfocada, demasiado oscura o que no permite evaluar el fruto, **When** se intenta clasificar, **Then** la aplicación comunica que no hay un resultado fiable y permite intentarlo con otra imagen.
3. **Given** que el teléfono no tiene conexión a internet, **When** la persona usa las funciones centrales de la aplicación, **Then** puede clasificar imágenes y consultar los resultados guardados sin conexión.

---

### User Story 4 - Consultar el historial de evaluaciones (Priority: P3)

La persona consulta evaluaciones anteriores en el teléfono. Cada registro conserva la imagen asociada, la clase predicha, la confianza y la fecha y hora local, y permite identificar a qué evaluación corresponde.

**Why this priority**: El historial facilita revisar resultados previos durante el monitoreo sin requerir conectividad.

**Independent Test**: Guardar más de una evaluación, cerrar y volver a abrir la aplicación sin conexión, y comprobar que cada registro muestra la imagen, clase, confianza y fecha y hora correctas.

**Acceptance Scenarios**:

1. **Given** una evaluación completada, **When** se consulta el historial, **Then** aparece un registro con su imagen, clase, confianza y fecha y hora.
2. **Given** varios registros, **When** la persona abre uno, **Then** la imagen y los datos mostrados corresponden a la misma evaluación.

---

### User Story 5 - Consultar una explicación visual (Priority: P4)

La persona consulta una visualización Grad-CAM++ asociada a la predicción para observar las regiones de la imagen relacionadas con la salida del modelo. La aplicación aclara que el mapa no demuestra la presencia de una enfermedad ni la corrección de la predicción.

**Why this priority**: La explicación visual complementa la clasificación y puede ayudar a inspeccionar la región que influyó en la salida.

**Independent Test**: Evaluar una imagen con explicación disponible y otra sin ella; verificar que se muestra la explicación correspondiente cuando existe y que su indisponibilidad no oculta la clasificación.

**Acceptance Scenarios**:

1. **Given** una predicción con visualización disponible, **When** la persona abre su detalle, **Then** ve el mapa vinculado a esa imagen y clase.
2. **Given** una predicción sin visualización disponible, **When** se consulta el resultado, **Then** se informa que el mapa no está disponible y se conserva visible la clase y confianza.
3. **Given** un mapa visible, **When** la persona lo interpreta, **Then** la aplicación explica que señala regiones asociadas a la salida del modelo y no prueba causalidad, enfermedad o mayor precisión.

---

### User Story 6 - Consultar información y orientación general (Priority: P5)

La persona consulta al asistente para entender información general relacionada con las tres clases y el resultado observado. El asistente funciona sin conexión, utiliza contenido local revisado y recomendaciones generales predefinidas, y diferencia esa información de la predicción del modelo.

**Why this priority**: La orientación complementa el monitoreo, pero no sustituye la predicción ni la evaluación de una persona profesional.

**Independent Test**: Sin conexión a internet, consultar preguntas cubiertas y no cubiertas por el contenido local; verificar que las respuestas respaldadas se distinguen de la predicción y que las no cubiertas declaran la limitación.

**Acceptance Scenarios**:

1. **Given** una pregunta cubierta por el contenido local revisado, **When** la persona consulta al asistente sin conexión, **Then** recibe información general y una recomendación predefinida aplicable, claramente diferenciadas de la predicción.
2. **Given** una solicitud de diagnóstico definitivo o una pregunta no cubierta, **When** el asistente responde, **Then** comunica sus límites y no inventa una respuesta ni presenta recomendaciones no revisadas como autorizadas.

### Edge Cases

- Una imagen no tiene fuente o procedencia identificable.
- La etiqueta original de un conjunto público no coincide claramente con las clases del proyecto.
- Una imagen propia presenta síntomas ambiguos o desacuerdo entre revisores; debe quedar pendiente o excluida hasta su resolución.
- Una clase tiene muy pocas imágenes para mantener una representación útil en las tres particiones.
- Imágenes derivadas del mismo fruto o sesión de captura podrían quedar en particiones distintas y producir fuga de datos.
- La división porcentual produce cantidades enteras que requieren redondeo; el total asignado debe coincidir con el número de imágenes admitidas.
- El modelo obtiene una confianza insuficiente según el criterio que se defina durante planificación.
- Grad-CAM++ no está disponible para una predicción.
- El contenido local del asistente no responde a la pregunta o no contempla la condición consultada.
- El dispositivo Android no tiene espacio o memoria suficientes para completar la evaluación local.
- La persona cancela la captura o selección antes de iniciar el análisis.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El equipo MUST incorporar imágenes de fuentes públicas y propias solo cuando pueda registrar su procedencia y condiciones de uso.
- **FR-002**: El conjunto MUST limitar las clases del proyecto a fruto sano, antracnosis y síntomas compatibles con anillado del pedúnculo.
- **FR-003**: Las etiquetas de imágenes propias MUST ser asignadas o verificadas por una persona experta o técnica agrícola conforme a criterios acordados por el equipo.
- **FR-004**: Las etiquetas de fuentes públicas MUST conservar su significado documentado; su correspondencia con las clases del proyecto MUST verificarse antes de utilizarlas. Las imágenes ambiguas o sin correspondencia verificable MUST quedar pendientes o excluidas.
- **FR-005**: El flujo de preparación MUST preservar las imágenes originales sin modificación y mantener una relación trazable entre cada copia de trabajo, su archivo original, fuente, clase y estado de revisión.
- **FR-006**: El conjunto MUST dividirse inicialmente en 70% entrenamiento, 15% validación y 15% prueba/aceptación, con semilla aleatoria 42. El proceso MUST informar cantidades totales y por clase y MUST señalar si alguna clase no puede representarse adecuadamente en todas las particiones. Cualquier cambio de proporciones o semilla MUST quedar documentado y justificado.
- **FR-007**: La división MUST evitar que imágenes vinculadas al mismo fruto, fuente original o sesión de captura queden distribuidas entre entrenamiento, validación y prueba cuando esa relación pueda identificarse.
- **FR-008**: El conjunto de prueba MUST permanecer separado del entrenamiento y de la selección o ajuste del modelo hasta la evaluación final.
- **FR-009**: El proyecto MUST comparar MobileNetV3 y EfficientNet-B0 bajo condiciones documentadas y comparables usando las tres clases del proyecto.
- **FR-010**: La evaluación MUST reportar exactitud, precisión, recall y F1 por clase y macro, matriz de confusión y AUC-ROC multiclase one-vs-rest macro. MUST documentar además resultados de calibración, generalización y eficiencia computacional, junto con sus limitaciones.
- **FR-011**: El criterio mínimo de desempeño MUST ser al menos 90% de F1 macro en el conjunto de prueba retenido. El 95% se considera una meta aspiracional. Los resultados MUST reportarse sin sustituir una métrica por otra.
- **FR-012**: Para cada evaluación completada, la aplicación MUST mostrar una clase de las tres admitidas, el nivel de confianza y que la predicción es orientativa y no constituye diagnóstico fitosanitario definitivo.
- **FR-013**: La aplicación MUST permitir capturar una imagen con la cámara o elegirla de la galería y MUST informar cuando no se obtenga un resultado fiable, permitiendo intentarlo con otra imagen.
- **FR-014**: Las funciones centrales de clasificación, historial, visualización explicativa y consulta al asistente MUST estar disponibles sin conexión a internet.
- **FR-015**: El historial MUST conservar localmente la imagen asociada, clase predicha, confianza y fecha y hora de cada evaluación, manteniendo su correspondencia.
- **FR-016**: Cuando esté disponible, la aplicación MUST mostrar Grad-CAM++ asociado a la imagen y predicción correctas; MUST indicar si no está disponible y MUST NOT presentarlo como prueba de enfermedad, causalidad o mayor precisión.
- **FR-017**: El asistente MUST cubrir información general de las tres clases y ofrecer únicamente recomendaciones predefinidas basadas en contenido local revisado.
- **FR-018**: El asistente MUST distinguir su información de la salida del clasificador, comunicar cuando el contenido no respalda una respuesta y MUST NOT presentar su resultado como diagnóstico definitivo ni consejo fitosanitario autorizado.

### Key Entities *(include if feature involves data)*

- **Imagen fuente**: Archivo original, con nombre original, procedencia y condiciones de uso conocidas.
- **Registro de etiquetado**: Relación entre una imagen de trabajo y su clase, etiqueta original, fuente, criterio aplicado, estado de revisión y persona revisora cuando corresponda.
- **Partición de datos**: Grupo de imágenes asignado a entrenamiento, validación o prueba, con porcentaje y cantidad registrada por clase.
- **Modelo evaluado**: Clasificador multiclase identificado por arquitectura y configuración experimental, con resultados asociados al conjunto de prueba.
- **Evaluación móvil**: Imagen capturada o elegida, predicción, confianza y marca temporal, asociadas en el historial local.
- **Visualización explicativa**: Mapa Grad-CAM++ opcional vinculado a una imagen y predicción concretas.
- **Contenido revisado del asistente**: Información y recomendaciones generales predefinidas, asociadas a las clases y disponibles sin conexión.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las imágenes incluidas en las particiones finales cuenta con fuente, identificador, clase y estado de revisión documentados.
- **SC-002**: El 100% de las imágenes originales usadas en el conjunto permanece sin cambios durante la preparación; cada imagen de trabajo puede rastrearse a su original.
- **SC-003**: Para cada división, los porcentajes configurados suman 100%, las cantidades por clase y totales se informan y ninguna imagen/grupo identificado aparece en más de una partición.
- **SC-004**: El informe de evaluación compara MobileNetV3 y EfficientNet-B0 con las métricas y condiciones definidas, e identifica explícitamente si F1 macro en prueba alcanza el mínimo del 90%.
- **SC-005**: En el 100% de las evaluaciones completadas, la aplicación presenta una de las tres clases admitidas, el nivel de confianza y la advertencia no diagnóstica.
- **SC-006**: En pruebas sin conexión, el 100% de los flujos centrales disponibles —clasificar, consultar historial y acceder al contenido local del asistente y a la explicación cuando esté disponible— funciona sin requerir internet.
- **SC-007**: El 100% de los registros de historial revisados mantiene la correspondencia entre imagen, clase, confianza y fecha y hora.

## Assumptions

- La primera iteración comprende preparación y revisión del conjunto, división en tres particiones, entrenamiento inicial y evaluación comparativa del clasificador; la integración móvil se desarrolla después.
- Las imágenes propias serán revisadas por una persona experta o técnica agrícola usando criterios acordados con el equipo.
- Los archivos originales no se renombrarán ni modificarán; la organización y los nombres de las copias de trabajo podrán adaptarse al conjunto de tres clases y conservarán identificadores trazables.
- Las clases describen apariencia visual. “Sano” significa sin síntomas visibles de las condiciones cubiertas, y “síntomas compatibles con anillado del pedúnculo” no equivale a confirmación fitopatológica.
- La aplicación está dirigida a productores y personas vinculadas al cultivo de aguacate que usan teléfonos Android de gama media.
- El conjunto incluirá fuentes públicas y propias; ninguna equivalencia de etiqueta se asumirá sin verificar la definición de la fuente.
- Las funciones móviles se ejecutarán sin conexión, y las imágenes y resultados del historial estarán disponibles localmente en el dispositivo.
- La ubicación geográfica no forma parte de los datos mínimos del historial en esta especificación.
- El conjunto preliminar de Kaggle contiene 3.983 imágenes etiquetadas: 1.764 `Healthy`, 1.197 `Scab` y 1.022 `Anthracnose`, además de 100 imágenes en una carpeta de evaluación sin etiquetas incluidas en el CSV. `Scab` se excluirá del conjunto del proyecto; las imágenes `Healthy` y `Anthracnose` se conservarán como candidatas si su fuente y definición son verificables. Se buscará otra fuente verificable para síntomas compatibles con anillado del pedúnculo; no se asumirá equivalencia entre `Scab` y anillado. Las 100 imágenes sin etiqueta no se usarán para entrenamiento ni evaluación cuantitativa hasta que tengan etiquetas revisadas. El entrenamiento/evaluación de tres clases queda condicionado a contar con datos aceptados para la tercera clase.

## Pending Decisions

1. **Criterio de confianza insuficiente**: Se definirá cómo se expresa la confianza y cuándo el sistema debe abstenerse de mostrar una clase como resultado fiable.
2. **Dispositivo Android de referencia**: Se identificará el modelo y la versión mínima de Android disponibles para medir latencia, memoria y tamaño de modelo.
3. **Contenido local del asistente**: Se aprobarán las fuentes y el contenido de síntomas y recomendaciones predefinidas para cada clase antes de implementar esa historia.
