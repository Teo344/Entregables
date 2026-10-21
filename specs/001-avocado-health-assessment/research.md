# Investigación y decisiones de planificación

**Funcionalidad**: `001-avocado-health-assessment`  
**Fecha**: 2026-10-20

## 1. Alcance y orden de desarrollo

**Decisión**: La iteración 1 se limita a curación trazable, particionado y experimentos comparativos iniciales del modelo. La aplicación Android se integrará después de seleccionar y validar el modelo.

**Justificación**: La aplicación depende de clases, preprocesamiento, comportamiento de incertidumbre y artefacto de modelo que todavía deben medirse. Implementar primero los datos y el modelo reduce el riesgo de integrar una interfaz/modelo inestable. La operación offline sigue siendo requisito de producto para la fase móvil.

**Alternativas consideradas**: Desarrollar modelo y aplicación en paralelo; se difiere porque el contrato de inferencia y la arquitectura móvil dependen de los resultados de esta iteración.

## 2. Alcance de etiquetas y fuentes

**Decisión**: Excluir `Scab`. Tratar `Healthy` y `Anthracnose` como candidatas, sujetas a verificar definición original, fuente y condiciones de uso. Buscar una fuente independiente verificable para síntomas compatibles con anillado del pedúnculo. No entrenar ni reportar una clasificación de tres clases si la tercera clase no tiene datos revisados suficientes.

**Justificación**: El nombre de una etiqueta no demuestra equivalencia fitosanitaria. La Constitución prohíbe mapear etiquetas sin evidencia. Las 100 imágenes sin etiqueta del directorio de evaluación quedan en cuarentena hasta que tengan verdad de terreno revisada.

**Alternativas consideradas**: Usar `Scab` como sustituto de anillado; rechazada porque no existe evidencia de equivalencia y el alcance del proyecto los trata como clases diferentes. Usar imágenes sin etiqueta para evaluar; rechazado porque no permite calcular métricas supervisadas válidas.

## 3. Revisión y procedencia

**Decisión**: Crear un manifiesto por imagen con identificador estable, ruta/nombre de origen, fuente, licencia/condiciones, etiqueta original, clase de proyecto propuesta, estado de revisión, criterio y partición. Las imágenes originales permanecen sin cambios. Las imágenes propias deben contar con revisión según criterios acordados por experto/técnico agrícola.

**Justificación**: Permite reconstruir qué datos entraron al experimento y auditar exclusiones, discrepancias y permisos.

**Alternativas consideradas**: Clasificar solo por carpetas/nombre de archivo; rechazada porque no captura licencias ni incertidumbre semántica y es propensa a errores de mapeo.

## 4. Particionado

**Decisión**: Usar inicialmente 70% entrenamiento, 15% validación y 15% prueba con semilla aleatoria 42. Calcular proporciones sobre el conjunto aceptado después de la curación. Mantener, cuando sea identificable, imágenes del mismo fruto o sesión en un único split; informar las cantidades reales y desviaciones por agrupamiento/redondeo.

**Justificación**: El usuario confirmó estas proporciones y semilla, alineadas con los porcentajes usados en la tesis previa. Se conservan proporciones y semilla, no los recuentos absolutos de aquel conjunto, porque la composición actual es distinta.

**Alternativas consideradas**: Copiar cantidades absolutas de la tesis anterior; rechazada porque el dataset actual tiene otros tamaños/clases. Dividir al azar cada archivo sin agrupación; rechazada cuando existe riesgo de fuga entre capturas del mismo espécimen/sesión.

## 5. Entorno de entrenamiento

**Decisión**: Python con TensorFlow/Keras en Google Colab usando GPU T4 o P100 cuando esté disponible; Google Drive como almacenamiento de fuentes y artefactos. Registrar las versiones concretas al iniciar el entorno, pues todavía no están fijadas.

**Justificación**: El usuario confirmó acceso a Colab, GPU y Drive. Los frameworks y versiones deben registrarse por experimento para que el trabajo sea reproducible; la infraestructura disponible puede variar por sesión.

**Alternativas consideradas**: Entrenar localmente; no es el baseline elegido por la disponibilidad de aceleración en Colab. Fijar versiones ahora sin inspeccionar el runtime; diferido para no afirmar disponibilidad no comprobada.

## 6. Comparación y evaluación

**Decisión**: Comparar MobileNetV3 y EfficientNet-B0 bajo idénticas particiones, clases y protocolo. Informar accuracy, precision, recall y F1 por clase y macro, matriz de confusión y ROC-AUC multiclase one-vs-rest macro; incluir calibración, generalización y tamaño/latencia cuando se mida.

**Justificación**: Son las arquitecturas y métricas establecidas por la Constitución/especificación. El test se consulta solo al terminar selección con validación. El objetivo F1 macro ≥90% es umbral de aceptación propuesto y 95% meta aspiracional; ambos deben compararse con resultados reales sin sobreajustar el test.

**Alternativas consideradas**: Elegir de antemano la arquitectura más ligera; rechazada porque la Constitución exige selección basada en resultados. Usar accuracy como métrica única; rechazada por posible desbalance y ocultamiento del comportamiento por clase.

## 7. Mínimo de Android (planificación futura)

**Decisión**: Registrar API 28 (Android 9) como mínimo provisional para planificar pruebas de integración, con confirmación pendiente contra el teléfono real y el runtime seleccionado. Si se opta por TensorFlow Lite, la documentación oficial del Task Library para visión indica API 21 como mínimo; ONNX Runtime lista API 28 entre las versiones probadas y menciona compatibilidad posible desde API 21. La versión final se decide con pruebas de instalación, inferencia offline y rendimiento en el dispositivo objetivo.

**Justificación**: API 28 es una base conservadora común para comparar runtimes, pero no es un requisito universal de Android ni una decisión final. Android define `minSdk` como la versión mínima que puede instalar la app; debe corresponder con dependencias y usuarios objetivo.

**Alternativas consideradas**: API 21 desde el inicio; sería viable para TensorFlow Lite según la referencia, pero podría no coincidir con los niveles probados de ONNX Runtime y aún no se conoce el teléfono objetivo. No declarar mínimo hasta la integración; se mantiene API 28 provisional para facilitar planificación, dejando clara su condición.

**Fuentes oficiales**:

- Android Developers, [Version your app](https://developer.android.com/studio/publish/versioning?authuser=00&hl=en).
- ONNX Runtime, [Compatibility](https://onnxruntime.ai/docs/reference/compatibility).
- TensorFlow, [TensorFlow Lite Android development](https://github.com/tensorflow/tensorflow/blob/master/tensorflow/lite/g3doc/android/development.md).

## 8. Riesgos aún no resueltos

- No se ha confirmado fuente elegible de imágenes para anillado del pedúnculo; es un bloqueo para validar el alcance de tres clases.
- No se ha identificado el dispositivo Android de referencia ni se han medido recursos móviles.
- El umbral de abstención y la base documental del asistente local se acordarán antes de esas funciones.
- No se confirma todavía qué subconjunto Kaggle satisface licencia/procedencia y mapeo; las frecuencias reportadas por el CSV son inventario, no aceptación.
