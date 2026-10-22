# Informe de avance de implementación — Iteración 1

**Estado:** avance preliminar; iteración no concluida  
**Fecha de corte:** 2026-10-21  
**Funcionalidad:** preparación trazable del conjunto de datos y clasificación fitosanitaria del aguacate

## 1. Alcance previsto

La iteración planificada comprende la curación de imágenes de fruto sano, antracnosis y síntomas compatibles con anillado del pedúnculo; la creación de un manifiesto; la separación reproducible de los datos; y la comparación de MobileNetV3 con EfficientNet-B0. La integración Android se mantiene fuera de esta iteración, de acuerdo con el [plan](plan.md).

## 2. Trabajo realizado y evidencia disponible

Se inspeccionó el conjunto local de imágenes sanas ubicado en `Modelo/AGUACATESANOS/`. Contiene 1.000 archivos numerados desde `sano-0001` hasta `sano-1000`.

Se calcularon hashes SHA-256 para detectar copias idénticas a nivel de archivo. El inventario encontró:

- 1.000 archivos examinados.
- 470 contenidos de archivo distintos.
- 296 grupos con copias exactas: 65 pares, 229 ternas, un grupo de cuatro y uno de cinco archivos.
- 530 archivos adicionales que repiten un contenido ya presente.

Por ejemplo, `sano-0001`, `sano-0477` y `sano-0707` tienen contenido idéntico. Este resultado identifica duplicados exactos; no demuestra que cada contenido distinto corresponda a un aguacate diferente. Tampoco detecta versiones similares que hayan sido recomprimidas, recortadas, giradas o modificadas.

La inspección fue de solo lectura. No se eliminaron ni movieron imágenes y no se generaron particiones.

## 3. Estado frente a Speckit

Al revisar `tasks.md`, las 33 tareas de implementación siguen sin marcarse como completadas. La checklist `checklists/requirements.md` registra 16 de 16 criterios marcados; esto indica que la revisión de requisitos está completa, pero no certifica que el producto haya sido implementado.

El análisis de las fotos sanas constituye evidencia preliminar para el inventario de datos. Todavía no equivale a completar las tareas de manifiesto, validación, particionado ni entrenamiento definidas en `tasks.md`.

## 4. Pendientes antes de declarar la iteración implementada

1. Confirmar la procedencia, condiciones de uso y etiqueta del conjunto sano seleccionado. La decisión actual es reutilizar el conjunto del proyecto anterior.
2. Conservar una sola copia de cada duplicado exacto en el conjunto derivado, sin alterar los originales, y generar un registro reproducible de la decisión.
3. Revisar posibles duplicados visuales que no coincidan byte por byte y, cuando sea posible, identificar fotografías del mismo fruto o sesión.
4. Confirmar las fuentes y etiquetas de antracnosis y anillado del pedúnculo. No debe declararse una clasificación de tres clases si la tercera clase no tiene datos verificables.
5. Completar fuentes, criterios de clase y manifiesto conforme al modelo y contrato de datos.
6. Validar el conjunto aceptado y, solo después de la revisión pendiente, crear particiones reproducibles agrupadas para evitar que variantes del mismo fruto crucen particiones.
7. Implementar y ejecutar las pruebas de integridad y particionado previstas.
8. Entrenar y comparar los dos modelos previstos con configuración registrada; seleccionar con validación y reservar la prueba final.
9. Documentar las métricas, limitaciones, resultados y artefactos del modelo candidato.

## 5. Conclusión para la entrega

Este documento puede presentarse como **informe de avance de curación de datos**, no como informe final de una iteración implementada. La evidencia actual confirma que el conjunto sano contiene numerosos duplicados exactos y requiere depuración y validación de procedencia antes de dividirlo o entrenar modelos. No hay todavía particiones, resultados experimentales ni modelo candidato que reportar.

## 6. Referencias internas

- [Especificación](spec.md)
- [Plan de implementación](plan.md)
- [Lista de tareas](tasks.md)
- [Modelo de datos](data-model.md)
- [Contrato del manifiesto](contracts/dataset-manifest.schema.json)
