# Auditoría de cobertura — Iteración 1

**Estado:** auditoría preliminar de trazabilidad; implementación incompleta  
**Fecha de corte:** 2026-10-21  
**Base revisada:** `spec.md`, `plan.md`, `tasks.md`, checklist de requisitos y evidencia local del conjunto de imágenes.

## 1. Propósito y alcance

Esta auditoría relaciona los requisitos funcionales de la especificación con las tareas planificadas y la evidencia disponible en el proyecto. No es un informe de cobertura de código: no hay una ejecución de pruebas instrumentada con una herramienta como `coverage.py`.

El proyecto local no contiene una skill o comando registrado llamado `Speckit-coverage`. Por ello, este documento presenta una matriz manual de trazabilidad, no una ejecución oficial de ese comando.

La iteración 1 planificada cubre la preparación del dataset y la comparación de clasificadores (US1 y US2). Las historias Android US3–US6 quedan para una iteración posterior, según `plan.md` y `tasks.md`.

## 2. Criterios de estado

- **Parcial:** existe evidencia preliminar, pero falta completar el requisito y validarlo contra sus criterios de aceptación.
- **Pendiente:** no hay evidencia suficiente de implementación verificada.
- **Fuera de esta iteración:** la especificación lo contempla, pero el plan pospone esa funcionalidad.

## 3. Resumen

| Resultado | Cantidad de requisitos |
|---|---:|
| Cumplidos con evidencia verificada | 0 |
| Parciales | 1 |
| Pendientes en esta iteración | 10 |
| Fuera de esta iteración | 7 |
| Total de requisitos funcionales | 18 |

En `tasks.md` hay 33 tareas y ninguna está marcada como completada. La checklist de requisitos tiene 16 de 16 criterios marcados; eso respalda la revisión de la especificación, pero no demuestra cobertura de implementación.

## 4. Matriz de cobertura de requisitos funcionales

| Requisito | Tareas relacionadas | Estado | Evidencia o brecha observada |
|---|---|---|---|
| FR-001 Procedencia y condiciones de uso de fuentes | T010–T014 | Pendiente | No existe aún el registro completo de fuentes y licencias/condiciones de uso. |
| FR-002 Clases del proyecto limitadas a sano, antracnosis y anillado compatible | T004, T013, T016 | Pendiente | No se ha aceptado un conjunto final con las clases y equivalencias verificadas. |
| FR-003 Revisión técnica de etiquetas propias | T004, T015 | Pendiente | No hay registro de revisión por persona experta o técnica agrícola. |
| FR-004 Verificación semántica de etiquetas públicas | T013, T015 | Pendiente | No se ha documentado por imagen/fuente la correspondencia ni la decisión de exclusión. |
| FR-005 Preservación y trazabilidad de originales y copias | T011, T014, T017 | Parcial | Se inspeccionaron hashes SHA-256 de 1.000 archivos sanos: 470 contenidos distintos y 530 copias adicionales exactas. Falta el manifiesto trazable y una validación formal de originales/copias. |
| FR-006 Partición 70/15/15, semilla 42 y conteos | T005, T018, T019 | Pendiente | No se definió ni ejecutó una partición. |
| FR-007 Agrupación para evitar fuga entre particiones | T005, T009, T018 | Pendiente | Se detectaron duplicados exactos, pero no se ha creado ni validado una asignación por grupos. |
| FR-008 Prueba retenida hasta evaluación final | T009, T022, T027, T028 | Pendiente | No existen particiones ni evaluaciones de modelos. |
| FR-009 Comparación de MobileNetV3 y EfficientNet-B0 | T006, T024, T025 | Pendiente | No se han ejecutado experimentos. |
| FR-010 Métricas, matriz, ROC-AUC, calibración, generalización y eficiencia | T021, T026, T028, T029 | Pendiente | No hay resultados ni reportes experimentales. |
| FR-011 F1 macro mínimo de 0,90 y meta aspiracional de 0,95 | T027–T029 | Pendiente | No hay evaluación final en conjunto de prueba. |
| FR-012 Clase, confianza y advertencia en la aplicación | Fuera del alcance de esta iteración | Fuera de esta iteración | Requisito móvil; no auditado en esta revisión de implementación. |
| FR-013 Cámara/galería y manejo de resultado no fiable | Fuera del alcance de esta iteración | Fuera de esta iteración | Requisito móvil; no auditado en esta revisión de implementación. |
| FR-014 Funciones centrales disponibles sin conexión | Fuera del alcance de esta iteración | Fuera de esta iteración | Requisito móvil; no auditado en esta revisión de implementación. |
| FR-015 Historial local de predicciones | Fuera del alcance de esta iteración | Fuera de esta iteración | Requisito móvil; no auditado en esta revisión de implementación. |
| FR-016 Visualización Grad-CAM++ y límites de interpretación | Fuera del alcance de esta iteración | Fuera de esta iteración | Requisito móvil; no auditado en esta revisión de implementación. |
| FR-017 Asistente con contenido local revisado | Fuera del alcance de esta iteración | Fuera de esta iteración | Requisito móvil/posterior; no auditado en esta revisión de implementación. |
| FR-018 Límites y separación del asistente respecto al diagnóstico | Fuera del alcance de esta iteración | Fuera de esta iteración | Requisito móvil/posterior; no auditado en esta revisión de implementación. |

## 5. Evidencia de datos disponible

La carpeta local `Modelo/AGUACATESANOS/` contiene 1.000 archivos (`sano-0001` a `sano-1000`). La inspección por SHA-256 encontró 470 contenidos de archivo distintos y 296 grupos de copias exactas. Esto permite identificar redundancia a nivel de archivo, pero no prueba que cada contenido distinto corresponda a un aguacate independiente. No se ha auditado similitud visual de imágenes recomprimidas, recortadas o transformadas.

No se eliminaron ni movieron imágenes, no se creó un split y no se entrenó ningún modelo. La procedencia, licencia, revisión de etiquetas y relación de las fotos con especímenes o sesiones siguen pendientes.

## 6. Hallazgos y acciones recomendadas

1. Conservar el conjunto original y registrar los grupos de copias exactas en un manifiesto reproducible antes de crear el dataset derivado.
2. Confirmar fuente, permiso/condiciones de uso y etiqueta del dataset sano reutilizado.
3. Buscar similitudes visuales adicionales y agrupar imágenes del mismo fruto/sesión cuando se pueda establecer esa relación.
4. Completar la revisión de antracnosis y confirmar una fuente elegible para anillado del pedúnculo. Sin esta última, no declarar cobertura de clasificación de tres clases.
5. Implementar y validar manifiesto y particionado antes de entrenar.
6. Mantener US3–US6 como requisitos pendientes de iteración posterior; esta auditoría no implica que estén implementados.

## 7. Conclusión

La cobertura de implementación de la iteración 1 es **insuficiente para declararla completada**. Hay evidencia de un inventario preliminar y de copias exactas en la clase sana, pero no de los artefactos y validaciones centrales exigidos por US1, ni de los experimentos de US2. Este PDF puede servir como auditoría de avance y trazabilidad; no certifica cumplimiento final ni cobertura de pruebas de código.

## 8. Referencias internas

- [Especificación](spec.md)
- [Plan de implementación](plan.md)
- [Lista de tareas](tasks.md)
- [Checklist de requisitos](checklists/requirements.md)
- [Informe de avance](implementacion-iteracion-1.md)
