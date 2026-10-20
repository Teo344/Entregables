# Feature Specification: Evaluación fitosanitaria asistida del aguacate

**Feature Branch**: `001-avocado-health-assessment`

**Created**: 2026-10-19

**Status**: Draft

**Input**: User description: "Especifica el flujo principal de AvocadoIA: una persona usuaria captura o selecciona una imagen de un aguacate y recibe una predicción entre fruto sano, antracnosis o síntomas compatibles con anillado del pedúnculo. La aplicación móvil está en AvocadoIA.V2/ y el desarrollo del modelo convolucional en Modelo/. El resultado debe comunicar la clase predicha y su incertidumbre; cuando estén disponibles, también mostrará una visualización Grad-CAM++ y permitirá consultar al asistente conversacional para obtener información general basada en fuentes revisadas. El propósito es apoyar el monitoreo fitosanitario, sin presentar la predicción como diagnóstico definitivo. No asumas tecnología móvil, formato de exportación, umbrales de confianza ni métricas objetivo si no están definidos: anota esas decisiones como preguntas pendientes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Obtener una predicción del fruto (Priority: P1)

Una persona que realiza monitoreo fitosanitario captura una imagen de un aguacate o selecciona una imagen existente. AvocadoIA analiza la imagen y presenta una de tres clases: fruto sano, antracnosis o síntomas compatibles con anillado del pedúnculo. El resultado muestra también la incertidumbre de la predicción y deja claro que no constituye un diagnóstico definitivo.

**Why this priority**: La clasificación de una imagen es el valor principal del flujo y permite apoyar el monitoreo.

**Independent Test**: Proporcionar imágenes representativas de las tres clases y comprobar que el flujo acepta la imagen, devuelve una clase dentro del conjunto definido y comunica la incertidumbre y el carácter no definitivo de la predicción.

**Acceptance Scenarios**:

1. **Given** que la persona puede aportar una imagen de un aguacate, **When** captura o selecciona la imagen y solicita su evaluación, **Then** recibe la clase predicha entre las tres clases admitidas y una indicación de incertidumbre.
2. **Given** que se presenta una predicción, **When** la persona consulta el resultado, **Then** la aplicación indica que es una predicción orientativa y no un diagnóstico fitosanitario definitivo.
3. **Given** que la imagen no se puede evaluar o no es adecuada para la clasificación, **When** se intenta analizarla, **Then** la aplicación informa que no hay un resultado fiable disponible y permite intentar con otra imagen.

---

### User Story 2 - Consultar una explicación visual (Priority: P2)

La persona consulta una visualización Grad-CAM++ asociada a la predicción para observar las regiones de la imagen que contribuyeron a la respuesta del modelo. La aplicación presenta esta visualización cuando está disponible y explica que no demuestra por sí misma que la predicción sea correcta.

**Why this priority**: Una explicación visual puede ayudar a interpretar el resultado, pero depende de su disponibilidad y no reemplaza la clasificación principal ni su cautela.

**Independent Test**: Evaluar una imagen con explicación disponible y otra sin ella; comprobar que en el primer caso se presenta asociada a la predicción y en el segundo se comunica su indisponibilidad sin bloquear el resultado principal.

**Acceptance Scenarios**:

1. **Given** una predicción con visualización Grad-CAM++ disponible, **When** la persona abre el detalle del resultado, **Then** ve la visualización correspondiente a esa imagen y clase.
2. **Given** una predicción sin visualización disponible, **When** la persona consulta el resultado, **Then** la aplicación indica que la explicación visual no está disponible y conserva visible la predicción y su incertidumbre.
3. **Given** una visualización Grad-CAM++ visible, **When** la persona la interpreta, **Then** la aplicación aclara que señala regiones asociadas a la salida del modelo y no acredita causalidad ni diagnóstico correcto.

---

### User Story 3 - Consultar información general (Priority: P3)

La persona hace una pregunta al asistente conversacional para obtener información general relacionada con el monitoreo o las clases presentadas. El asistente responde con información basada en fuentes revisadas y diferencia esa información de la predicción de la imagen.

**Why this priority**: La consulta puede aportar contexto educativo, pero es complementaria y no debe confundirse con una evaluación profesional del fruto.

**Independent Test**: Enviar una pregunta general y comprobar que la respuesta se vincula a fuentes revisadas, separa información general del resultado del modelo y comunica límites cuando las fuentes no permiten responder.

**Acceptance Scenarios**:

1. **Given** un resultado de clasificación, **When** la persona formula una pregunta general al asistente, **Then** recibe una respuesta basada en fuentes revisadas identificables y claramente diferenciada de la predicción.
2. **Given** una pregunta que solicita un diagnóstico definitivo o recomendaciones no respaldadas, **When** el asistente responde, **Then** comunica que la predicción no es definitiva y no presenta información no verificada como consejo autorizado.
3. **Given** que no hay fuentes revisadas suficientes para responder una pregunta, **When** la persona consulta al asistente, **Then** este declara la limitación en vez de inventar una respuesta respaldada.

### Edge Cases

- La imagen está dañada, desenfocada, demasiado oscura, no contiene un aguacate o no permite distinguir la región relevante.
- La persona cancela la captura o selección antes de iniciar el análisis.
- La evaluación no produce una clase suficientemente fiable conforme al criterio de incertidumbre que se defina.
- La visualización Grad-CAM++ no se puede generar aunque exista una predicción.
- El asistente no tiene acceso a las fuentes revisadas o las fuentes disponibles no cubren la pregunta.
- Una respuesta del asistente podría confundirse con la predicción del clasificador; ambas deben distinguirse en la presentación.
- La predicción o explicación corresponde a una imagen distinta de la que la persona está consultando.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La aplicación MUST permitir a la persona capturar una imagen de un aguacate o seleccionar una imagen disponible para evaluación.
- **FR-002**: El flujo MUST presentar, para cada evaluación completada, una sola clase predicha del conjunto: fruto sano, antracnosis o síntomas compatibles con anillado del pedúnculo.
- **FR-003**: El resultado MUST comunicar la incertidumbre de la predicción en términos comprensibles para la persona usuaria. La forma de comunicarla y los umbrales asociados quedan pendientes de decisión.
- **FR-004**: La aplicación MUST indicar junto al resultado que la predicción es orientativa, apoya el monitoreo fitosanitario y no constituye un diagnóstico definitivo.
- **FR-005**: La aplicación MUST informar cuando una imagen no pueda evaluarse de forma fiable y MUST permitir a la persona intentar con otra imagen.
- **FR-006**: Cuando esté disponible, la aplicación MUST mostrar la visualización Grad-CAM++ vinculada a la imagen evaluada y a la predicción correspondiente.
- **FR-007**: Cuando la visualización Grad-CAM++ no esté disponible, la aplicación MUST comunicarlo sin ocultar la predicción ni su incertidumbre.
- **FR-008**: La aplicación MUST explicar que Grad-CAM++ representa regiones asociadas a la salida del modelo y no prueba causalidad ni corrección diagnóstica.
- **FR-009**: La aplicación MUST permitir consultas al asistente conversacional para obtener información general relacionada con el monitoreo y las clases admitidas.
- **FR-010**: El asistente MUST basar sus respuestas en fuentes revisadas, distinguirlas de las predicciones del clasificador y declarar cuando las fuentes no respalden una respuesta.
- **FR-011**: El asistente MUST NOT presentar una predicción como diagnóstico definitivo ni información no verificada como consejo fitosanitario autorizado.
- **FR-012**: La aplicación MUST mantener la correspondencia entre la imagen consultada, su predicción, su incertidumbre y cualquier visualización asociada.

### Key Entities *(include if feature involves data)*

- **Imagen evaluada**: Imagen capturada o seleccionada por la persona y sujeto del análisis.
- **Predicción**: Resultado asociado a una imagen, con una clase del conjunto definido y su incertidumbre.
- **Visualización explicativa**: Representación Grad-CAM++ opcional vinculada a una predicción e imagen concretas.
- **Consulta conversacional**: Pregunta de la persona y respuesta general del asistente, con referencia a las fuentes revisadas que la respaldan.
- **Fuente revisada**: Material de referencia aprobado para respaldar respuestas informativas del asistente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En pruebas del flujo principal, el 100% de las evaluaciones completadas presenta una clase que pertenece exactamente al conjunto de tres clases definido.
- **SC-002**: En pruebas del flujo principal, el 100% de los resultados presenta tanto una indicación de incertidumbre como la advertencia de que no constituye un diagnóstico definitivo.
- **SC-003**: En pruebas con y sin visualización disponible, el 100% de los casos conserva visible la predicción y comunica correctamente si la visualización Grad-CAM++ está disponible.
- **SC-004**: En las pruebas del asistente, el 100% de las respuestas informativas incluye respaldo en fuentes revisadas o declara explícitamente que no dispone de respaldo suficiente.
- **SC-005**: El equipo registra los resultados de calidad de clasificación, calibración, generalización, eficiencia computacional y experiencia de uso antes de declarar que la solución cumple los objetivos cuantitativos del proyecto. Los valores objetivo siguen pendientes.

## Assumptions

- La persona usuaria busca apoyo para monitoreo fitosanitario y entiende que una evaluación visual automatizada es orientativa.
- El alcance de clasificación de esta funcionalidad se limita a las tres clases expresamente indicadas; no se infiere cobertura de otras enfermedades, variedades o condiciones.
- La captura y selección de imágenes son dos formas válidas de iniciar el mismo flujo de evaluación.
- La visualización Grad-CAM++ y las consultas al asistente son capacidades complementarias; su falta de disponibilidad no impide consultar la predicción principal.
- El conjunto de fuentes revisadas, su proceso de aprobación y las referencias que acompañarán las respuestas se definirán antes de implementar el asistente.
- Las preguntas pendientes de esta especificación deben resolverse durante la fase de aclaración y planificación antes de fijar criterios de despliegue o aceptación cuantitativa.

## Pending Decisions

1. **Tecnología y despliegue móvil**: ¿Qué plataformas y tecnologías móviles deben cubrirse, y en qué formato debe entregarse el modelo para integrarlo con la aplicación?
2. **Incertidumbre y umbrales**: ¿Cómo debe expresarse la incertidumbre a la persona usuaria y qué umbral o comportamiento se aplicará cuando la predicción no sea suficientemente fiable?
3. **Objetivos cuantitativos**: ¿Qué métricas y valores objetivo se exigirán para calidad de clasificación, calibración, generalización, eficiencia computacional y evaluación de uso?

