# Plan de implementación: Preparación del conjunto de datos y clasificación fitosanitaria del aguacate

**Rama**: `001-avocado-health-assessment` | **Fecha**: 2026-10-20 | **Especificación**: [spec.md](spec.md)

## Resumen

La primera iteración construirá un flujo reproducible de curación de datos y una comparación inicial de clasificadores para el proyecto AvocadoIA. Se conservarán intactas las fuentes originales, se excluirá la etiqueta `Scab`, se revisarán las etiquetas `Healthy` y `Anthracnose` y se buscarán imágenes verificables para síntomas compatibles con anillado del pedúnculo. Solo las imágenes cuya procedencia y etiqueta puedan verificarse pasarán al conjunto derivado. El conjunto aceptado se dividirá 70/15/15 con semilla 42 y se usarán esas mismas particiones para comparar MobileNetV3 y EfficientNet-B0 con TensorFlow en Google Colab. La integración Android sin conexión es una fase posterior; esta iteración dejará documentados su contrato de modelo y el nivel mínimo provisional de Android.

## Contexto técnico

**Lenguaje/versión**: Python 3.x (versión exacta a fijar y registrar al crear el entorno).  
**Dependencias principales**: TensorFlow/Keras, NumPy, pandas, scikit-learn y herramientas de lectura/verificación de imágenes; versiones se fijan al iniciar los experimentos.  
**Almacenamiento**: Google Drive para originales y artefactos de trabajo; los originales son de solo lectura durante la curación.  
**Pruebas/verificación**: validadores de manifiesto, etiquetas, integridad de archivos, exclusividad de particiones y reproducción de métricas; ejecución prevista en Google Colab.  
**Plataforma objetivo**: Colab con acelerador T4 o P100 disponible; integración futura en Android. Mínimo móvil provisional: API 28 (Android 9), sujeto a validar con dispositivo real y runtime elegido.  
**Tipo de proyecto**: pipeline de datos y experimentos de visión por computador, seguido por aplicación Android offline.  
**Metas de desempeño**: comparar modelos con exactitud, precisión, recall, F1, matriz de confusión, ROC-AUC multiclase, calibración y eficiencia. Criterio propuesto en la especificación: F1 macro ≥ 0,90 en prueba; 0,95 aspiracional, sin considerarlo garantizado.  
**Restricciones**: preservar procedencia/licencias; excluir `Scab`; no mapear etiquetas públicas por su nombre sin evidencia; evitar fuga por fruto/sesión/fuente; separar prueba de toda selección; la app futura debe clasificar sin red.  
**Escala/alcance**: primera iteración sobre el conjunto curado que pueda verificarse, inicialmente con dos arquitecturas y tres clases de proyecto. El número final de imágenes depende de conseguir y validar la clase de anillado.

## Revisión de Constitución

| Principio / requisito | Estado | Aplicación en esta iteración |
|---|---|---|
| Trazabilidad de investigación | Cumple | Manifiesto por imagen, registro de fuente, clase original/propuesta, licencia, revisión y partición; configuración y resultados por experimento. |
| Integridad y uso responsable de datos | Cumple con condición | Fuentes intactas; `Scab` excluido. No usar imágenes sin procedencia, licencia o equivalencia de etiqueta verificable. La clase anillado no se entrena hasta obtener fuente y criterios revisados. |
| Experimentos reproducibles | Cumple | Split 70/15/15, semilla 42, mismo manifiesto de particiones para ambos modelos; prueba retenida y agrupación por espécimen/sesión cuando los metadatos lo permitan. |
| Evaluación basada en evidencia | Cumple con condición | Se comparan MobileNetV3 y EfficientNet-B0 con métricas acordadas. Eficiencia móvil será una evaluación posterior si todavía no existe teléfono objetivo. |
| Cambios mantenibles y revisables | Cumple | Scripts/notebooks separados de datos crudos; versiones de dependencias, configuraciones, informes y decisiones documentados. |
| Operación móvil offline | Fuera de implementación en esta iteración | Se conserva como requisito de producto. Esta iteración define contrato de entrada/salida y recomendación provisional de plataforma para la integración posterior. |

**Gate inicial**: aprobado con las condiciones anteriores; no se permite presentar el conjunto como clasificación de tres clases hasta resolver y documentar la fuente de anillado.  
**Gate posterior al diseño**: aprobado condicionado a que los artefactos definan explícitamente cuarentena/exclusión de datos no verificados, aislamiento de prueba y el estado pendiente de la tercera clase.

## Estructura del proyecto

### Documentación de esta funcionalidad

```text
specs/001-avocado-health-assessment/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
    ├── dataset-manifest.schema.json
    └── model-inference-contract.md
```

### Áreas del repositorio

```text
Modelo/
├── PORCLASIFICAR/                 # Fuentes recibidas; preservar sin cambios
├── data/                          # Manifiesto y particiones derivadas
├── notebooks/                    # Experimentos reproducibles en Colab
├── scripts/                      # Curación, división, validación y evaluación
└── artifacts/                    # Modelos, configuraciones e informes versionados

AvocadoIA.V2/                      # Aplicación Android; implementación posterior
```

**Decisión de estructura**: mantener los datos de origen separados de datos procesados y experimentos. La ubicación concreta de Google Drive se configurará fuera de los notebooks y no se codificará una ruta personal. La aplicación actual no se modifica en esta iteración.

## Diseño de la iteración

1. Inventariar fuentes, condiciones de uso, etiquetas, archivos duplicados/corruptos y metadatos de espécimen o sesión.
2. Excluir `Scab` de los datos del proyecto. Revisar `Healthy` y `Anthracnose`; aceptar cada clase solo tras confirmar significado y procedencia.
3. Buscar y verificar una fuente para anillado del pedúnculo. Si no está disponible una fuente adecuada, registrar el bloqueo de esa clase, no sustituirla con `Scab` ni afirmar que el modelo cubre tres clases.
4. Mantener imágenes sin etiqueta fiable en cuarentena; el directorio de evaluación de 100 imágenes sin etiquetas no se emplea en entrenamiento ni en cálculo de métricas hasta obtener etiquetas verificadas.
5. Generar manifiesto derivado y particiones de 70% entrenamiento, 15% validación y 15% prueba, semilla 42. Calcular cantidades después de la depuración; redondeo determinista, recuentos por clase y totales en el informe. Si se identifican grupos de un mismo fruto/sesión, asignarlos íntegramente a una partición y documentar desviaciones inevitables de porcentajes.
6. Entrenar MobileNetV3 y EfficientNet-B0 con inicialización y condiciones comparables en Colab; registrar entorno, pesos iniciales, tamaño de imagen, preprocesamiento, aumentos, épocas, optimizador, criterio de parada y semillas.
7. Evaluar una sola vez sobre prueba retenida. Reportar métricas por clase y macro, matriz de confusión, ROC-AUC one-vs-rest macro, calibración, errores representativos y limitaciones de fuente/dominio.
8. Exportar el candidato y documentar su contrato para integración móvil posterior. No seleccionar TFLite u ONNX definitivamente hasta una prueba con el dispositivo Android objetivo.

### Política de clases durante la primera iteración

La especificación de producto contempla sano, antracnosis y síntomas compatibles con anillado del pedúnculo. La fuente preliminar de Kaggle incluye `Healthy` (1.764), `Anthracnose` (1.022) y `Scab` (1.197), con 100 imágenes en evaluación sin etiquetas CSV. `Scab` queda excluida. `Healthy` y `Anthracnose` son candidatas, pendientes de verificar las definiciones y procedencia del dataset. La tercera clase requiere fuente independiente verificable y revisión bajo los criterios acordados con experto/técnico agrícola. Los recuentos son inventario preliminar, no un compromiso de datos aceptados.

## Decisiones pendientes / riesgos

- **Fuente de anillado**: riesgo crítico para el entrenamiento de tres clases. Registrar fuentes candidatas, permiso/licencia y revisión técnica antes de incluirlas.
- **Dispositivo Android real**: modelo, RAM y versión del sistema pendientes. API 28 se usa como mínimo provisional para planear pruebas; actualizarlo si el dispositivo/runtimes seleccionados requieren otra versión.
- **Criterio de abstención**: umbral de confianza y método de calibración pendientes; no inventar ni derivar solo de confianza máxima.
- **Contenido del asistente**: fuentes y recomendaciones revisadas pendientes; fuera de la iteración de datos/modelo.
- **Acceso al Drive**: confirmar permisos y ruta compartida de datos al comenzar implementación; no copiar credenciales ni rutas personales a Git.
- **Objetivo F1 macro ≥ 0,90**: meta definida en la especificación, a tratar como criterio de evaluación. Si no se alcanza, informar el resultado, analizar causas y no ajustar sobre la prueba.

## Complejidad

No se solicitan componentes adicionales ni excepciones a la Constitución. La secuencia de modelo y aplicación refleja el alcance del proyecto; la implementación de la aplicación queda fuera de esta primera iteración.
