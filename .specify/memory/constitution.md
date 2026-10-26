# AvocadoIA Constitution

## Core Principles

### I. Funcionamiento sin conexión (NO NEGOCIABLE)

El producto final es una aplicación Android que diagnostica frutos de aguacate **sin conexión a
internet**. Todo el ciclo de diagnóstico ocurre en el teléfono: captura, clasificación, confianza
calibrada, mapa de calor Grad-CAM++, explicación del asistente y guardado del historial.

- Ningún paso del diagnóstico DEBE depender de un servidor, una API remota ni un servicio en la nube.
- El clasificador DEBE exportarse a TensorFlow Lite e incluirse en la app; el asistente
  conversacional DEBE usar un LLM ejecutado en el dispositivo con una base de conocimiento local.
- Toda decisión de diseño que añada un componente (XAI, LLM, almacenamiento) DEBE demostrar que
  funciona en modo avión antes de aceptarse; si no, se adopta un plan B documentado.
- Las pruebas de aceptación de la app DEBEN incluir un escenario en modo avión en un dispositivo
  Android real.

**Justificación:** los productores de Sigchos tienen conectividad deficiente. La tesis previa
(Herrera & Marín) ya entregó una app offline; perder esa propiedad sería un retroceso.

### II. Integridad y trazabilidad del conjunto de datos

El modelo solo vale lo que valen sus etiquetas. Cada imagen DEBE poder rastrearse hasta su origen.

- Cada imagen DEBE tener registrados: fuente (repositorio, URL o salida de campo), licencia,
  clase, hash SHA-256 del contenido y estado de validación por el experto agrónomo.
- Los duplicados DEBEN detectarse por contenido (SHA-256), no por nombre; se conserva una copia.
  Un mismo contenido con etiquetas contradictorias DEBE excluirse y registrarse con su motivo.
- Solo se usan fuentes cuya licencia permita uso académico; las demás se excluyen.
- Las clases son exactamente tres: **sano**, **antracnosis** y **síntomas compatibles con
  anillado del pedúnculo**. Ese término DEBE usarse siempre para la tercera clase.
- El conjunto de prueba NUNCA DEBE intervenir en el entrenamiento, la selección de
  hiperparámetros ni la calibración. El aumento de datos se aplica solo al entrenamiento.
- Los archivos originales descargados DEBEN conservarse intactos; toda transformación produce
  archivos nuevos y deja registro (manifiesto CSV) de cada decisión.

**Justificación:** la antracnosis y el anillado se parecen visualmente; sin validación experta y
sin trazabilidad, la etiqueta es la parte más débil y el tribunal puede objetarla.

### III. Reproducibilidad experimental

Todo resultado reportado en la tesis DEBE poder regenerarse a partir del repositorio.

- Las particiones DEBEN ser estratificadas y usar una semilla fija documentada (por defecto 42).
- La comparación MobileNetV3 vs. EfficientNet-B0 DEBE hacerse en igualdad de condiciones:
  mismos datos, particiones, épocas, callbacks, semilla y aumento.
- Las versiones de Python, TensorFlow y demás dependencias DEBEN fijarse en un archivo de
  dependencias versionado.
- El preprocesamiento y el entrenamiento DEBEN ejecutarse como scripts o notebooks versionados en
  Git, nunca como pasos manuales sin registro.
- Cada experimento DEBE dejar registro de su configuración y métricas (bitácora o archivo de
  resultados).

**Justificación:** la tesis previa comparó arquitecturas en condiciones desiguales, un punto débil
conocido. La reproducibilidad es la base para defender la elección del modelo.

### IV. Confianza calibrada y explicable

El usuario ve un porcentaje de confianza y un mapa de calor; ambos DEBEN ser honestos.

- Las probabilidades DEBEN calibrarse (Temperature Scaling) antes de exportar el modelo, y el
  Expected Calibration Error (ECE) DEBE reportarse antes y después de la calibración.
- Cada predicción en la app DEBE mostrar la confianza calibrada; si es menor al umbral definido,
  la app DEBE mostrar "resultado no concluyente" en lugar de una clase.
- Grad-CAM++ DEBE verificarse sobre aciertos y errores para confirmar que el modelo se enfoca en
  la lesión y no en el fondo, la mano o elementos ajenos.
- El asistente DEBE limitarse al resultado del clasificador y advertir que sus recomendaciones son
  generales y no reemplazan a un técnico agrónomo.

**Justificación:** un "95 %" sin calibrar puede inducir decisiones fitosanitarias equivocadas; la
explicabilidad es el aporte declarado frente a la tesis anterior.

### V. Presupuesto del dispositivo y simplicidad

El modelo y la app DEBEN caber en teléfonos de gama media o baja.

- Los requisitos no funcionales (tamaño del modelo, latencia de inferencia, RAM mínima, versión de
  Android) DEBEN ser medibles y verificarse en un dispositivo real, no inferirse del número de
  parámetros.
- La conversión a TFLite DEBE reportar el tamaño y la exactitud antes y después; la pérdida de
  exactitud DEBE justificarse.
- Se implementa solo lo que exige un objetivo de la tesis (OE1–OE4). Toda complejidad adicional
  (nuevas clases, nube, ONNX, otras arquitecturas) DEBE justificarse en el plan o diferirse a
  trabajo futuro.

**Justificación:** el contexto rural implica dispositivos modestos; el alcance acotado protege el
cronograma de sprints.

## Restricciones técnicas y de dominio

- **Modelo:** Python y TensorFlow/Keras; transferencia de aprendizaje sobre MobileNetV3 y
  EfficientNet-B0; exportación a TensorFlow Lite con firma de clasificación y, si el spike técnico
  lo permite, firma `explain` para Grad-CAM++.
- **Aplicación:** Flutter con arquitectura MVVM, intérprete TFLite, historial en SQLite local,
  objetivo Android.
- **Datos:** las imágenes NO se versionan en Git (solo marcadores `.gitkeep`, manifiestos CSV,
  scripts y documentación). Las carpetas de clase son `Modelo/AGUACATESANOS`,
  `Modelo/ANTRACNOSIS` y `Modelo/PEDUNCULO`; el material sin clasificar vive en
  `Modelo/PORCLASIFICAR`.
- **Validación experta:** un experto agrónomo (con apoyo del GAD Municipal de Sigchos) DEBE
  validar las etiquetas antes de que una imagen entre a entrenamiento.
- **Usabilidad:** la evaluación con usuarios usa SUS y UEQ; SUS ≥ 68 es la referencia de
  aceptabilidad.
- TODO(RNF_DISPOSITIVO): RAM mínima, versión mínima de Android y tamaño máximo del modelo y del
  LLM se fijan en la especificación de la app.

## Flujo de trabajo y puertas de calidad

- Cada funcionalidad sigue el flujo SDD de Spec Kit: `constitution` → `specify` → `clarify`
  (recomendado) → `plan` → `tasks` → `analyze` (auditoría de cobertura) → `implement`.
- Cada funcionalidad vive en una rama `NNN-nombre` y en `specs/NNN-nombre/`.
- Cada fase SDD DEBE registrar su sesión con la extensión `metricas` (fase, herramienta, modelo de
  IA, horas y líneas de código), y la sesión DEBE cerrarse al terminar el trabajo.
- Antes de implementar, `/speckit-analyze` DEBE ejecutarse y sus hallazgos CRÍTICOS resolverse; el
  informe se conserva como documento de auditoría de la funcionalidad.
- El código de procesamiento de datos y del modelo DEBE tener pruebas automatizadas para su
  lógica determinista (hash, deduplicación, partición, métricas).
- Una funcionalidad se da por terminada cuando sus criterios de aceptación pasan y la tutora de la
  tesis puede verificar la evidencia.

## Governance

Esta constitución prevalece sobre cualquier otra práctica del repositorio `Entregables`. Todo
`plan.md` DEBE incluir la verificación de cumplimiento (Constitution Check) y justificar cada
excepción en su tabla de complejidad.

- **Enmiendas:** se proponen por escrito, las aprueban ambos autores (Criollo y Yépez) y, si
  afectan al alcance de los objetivos, también la tutora; se registran con un nuevo Sync Impact
  Report.
- **Versionado semántico:** MAYOR para eliminar o redefinir un principio; MENOR para añadir un
  principio o sección; PARCHE para aclaraciones de redacción.
- **Revisión de cumplimiento:** al cierre de cada sprint y en cada `/speckit-analyze` se verifica
  que specs, planes y tareas respetan los principios I–V.

**Version**: 1.0.0 | **Ratified**: 2026-10-25 | **Last Amended**: 2026-10-25
