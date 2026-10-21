# Guía de validación del flujo de datos y modelo

Esta guía define escenarios reproducibles para la implementación posterior. No implica que el pipeline o los modelos ya estén implementados ni ejecutados.

## Prerrequisitos

- Acceso autorizado a la carpeta de Google Drive con las fuentes.
- Google Colab con Python y TensorFlow; GPU T4/P100 si está disponible.
- Copia de trabajo separada de los archivos originales.
- Fuentes, licencias/condiciones y criterios de etiquetado registrados.
- Revisión de imágenes propias por experto/técnico agrícola según criterios acordados.
- Entorno y versiones de librerías registrados en el informe.

## Escenario A: validar inventario y manifiesto

1. Ejecutar el inventario sobre las rutas configuradas sin modificar archivos de origen.
2. Crear/actualizar el manifiesto con el esquema descrito en [data-model.md](data-model.md) y [dataset-manifest.schema.json](contracts/dataset-manifest.schema.json).
3. Comprobar que cada imagen admitida tiene `source_id`, hash, etiqueta validada, estado `accepted` y ruta de copia.
4. Comprobar que `Scab` está excluida y que las 100 imágenes sin etiquetas no aparecen como train/validation/test.
5. Comprobar que fuentes o etiquetas desconocidas permanecen en cuarentena y que no se asignó anillado por inferencia del nombre.

**Resultado esperado**: validación del manifiesto sin errores; informe de cantidades inventariadas, aceptadas, excluidas y pendientes por fuente/clase.

## Escenario B: validar las particiones

1. Generar splits desde el manifiesto aceptado con train/validation/test = 70/15/15 y semilla 42.
2. Repetir la generación con la misma versión de manifiesto y configuración.
3. Comparar los IDs asignados y verificar que la repetición es idéntica.
4. Verificar por clase y total los recuentos y porcentajes efectivos; comprobar ausencia de IDs y grupos de espécimen/sesión compartidos entre particiones.

**Resultado esperado**: asignación reproducible, cobertura completa de aceptadas, exclusividad entre splits y reporte de diferencias por redondeo/agrupación. Ver [model-inference-contract.md](contracts/model-inference-contract.md) para que el orden de clase no cambie entre artefactos posteriores.

## Escenario C: entrenar y comparar

1. Entrenar MobileNetV3 y EfficientNet-B0 con el mismo split y clases.
2. Registrar configuración, versiones de software, acelerador, semilla, checkpoint y curva de entrenamiento.
3. Seleccionar configuración únicamente con validación.
4. Ejecutar una evaluación final en test retenido y producir las métricas requeridas.
5. Confirmar que F1 macro ≥0,90 se reporta como alcanzado/no alcanzado; 0,95 se reporta solo como aspiración.

**Resultado esperado**: informe comparable con métricas por clase y macro, matriz de confusión, ROC-AUC OVR macro o motivo de indisponibilidad, análisis de calibración/generalización y limitaciones de datos. No reportar resultados antes de ejecutar realmente el flujo.

## Escenario D: preparar integración Android posterior

1. Registrar formato de exportación y contrato de entrada/salida del candidato según [model-inference-contract.md](contracts/model-inference-contract.md).
2. Cuando se disponga del teléfono objetivo, comprobar instalación, carga del modelo e inferencia sin internet.
3. Medir tamaño, latencia y memoria en ese dispositivo; confirmar o cambiar el `minSdk` provisional API 28 con evidencia.

**Resultado esperado**: decisión documentada de runtime y nivel mínimo de Android con resultados medidos. Este escenario es posterior a la iteración de datos/modelo.
