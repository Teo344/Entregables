# Auditoría /speckit-analyze: 003-modelo-clasificador

**Fecha**: 2026-11-09 | **Artefactos**: spec.md, plan.md, tasks.md (+ research, data-model, contracts, quickstart)
| **Constitución**: v1.0.0

## Resultado

| Métrica | Valor |
| --- | --- |
| Requisitos | 27 FR + 7 SC = 34 (FR-026 y FR-027 agregados en la remediación) |
| Tareas | 58 (T058 agregada en la remediación) |
| Cobertura | 100 % |
| Hallazgos | 12: 1 CRITICAL, 1 HIGH, 6 MEDIUM, 4 LOW |
| Estado | **Todos remediados** el 2026-11-09 |

## Hallazgos y remediación

| ID | Categoría | Severidad | Hallazgo | Remediación |
| --- | --- | --- | --- | --- |
| C1 | Constitución | CRITICAL | El split v4 incluía imágenes sin licencia académica (principio II: "las demás se excluyen", sin excepción). | FR-026 y research M19: filtro obligatorio por `uso_academico = si` en `config/fuentes.csv`, fuente determinada **primero por SHA-256** en `datos/manifiesto.csv` y después por nombre; sin opción para desactivarlo. Excluidas 412 `sano_web` (evidencia EXIF: 404 sin cámara, miniaturas de 13 KB, cámaras de terceros). Se conservan las 16 fotos propias de Herrera y Marín renumeradas (`sano-0707`…`0723`). Licencia de `avocare` verificada por los autores (CC BY 4.0), pero excluida **por calidad** (FR-027, M19.1): Roboflow v4 genera 3 variantes aumentadas por original. Conjunto: 1 426 imágenes (sano 392, antracnosis 823, pedúnculo 211). |
| U1 | Subespecificación | HIGH | `procedencia` del v4 contiene nombres de reportes CSV, no fuentes; el desglose por fuente habría sido inútil. | Resuelto con M19: la fuente sale de `datos/manifiesto.csv` o de las reglas de `config/fuentes.csv`; `procedencia` ya no se mapea (T004, T008). |
| C2 | Constitución | MEDIUM | Entrenar sin validación experta (excepción justificada). | T057 exige split corregido **y** validación del agrónomo antes de reportar cifras de tesis; plan actualizado. |
| C3 | Constitución | MEDIUM | El principio V pide tamaño y **exactitud** antes/después de convertir; solo había macro-F1. | `variantes.csv` con `test_exactitud` y `diferencia_exactitud` (data-model §10, T047, T048). |
| I1 | Inconsistencia | MEDIUM | data-model excluía solo `arquitectura` de `huella_config`; T006 también la semilla. | data-model §4 alineado: se excluyen `arquitectura` y `semilla`. |
| U2 | Subespecificación | MEDIUM | `entrenar` no comprobaba la verificación previa exigida por US1. | T025 y contracts/cli.md: código 2 si la verificación falta, falló o no corresponde a la caché. |
| I2 | Inconsistencia | MEDIUM | Rotación de 45° frente a ±20° sugeridos al inicio. | Se mantiene 45° por coherencia con 002, justificado en research M8; ajustable solo antes de una comparación. |
| G1 | Cobertura | MEDIUM | Ninguna tarea advertía que el pedúnculo viene de una sola fuente. | T053 incluye la advertencia y la tabla de exclusiones. |
| F1 | Terminología | LOW | La constitución exige "síntomas compatibles con anillado del pedúnculo" en salidas visibles. | T053 y nota general de tasks.md: figuras, tablas e informe usan `ETIQUETAS_VISIBLES`. |
| U3 | Subespecificación | LOW | No se indicaba que la confianza de la planilla de explicaciones fuera la calibrada. | T044: confianza = `softmax(logits / T)` con la temperatura de `calibracion.json`. |
| O1 | Orden | LOW | T035 (US2) usa `exportacion.convertir` de T048 (US5). | Dependencia documentada; respaldo `n_parametros × 2 bytes` registrado en `decision.json`. |
| A1 | Ambigüedad | LOW | SC-006 solo se comprobaba en la corrida base. | T037 repite la corrida representativa de la arquitectura elegida. |

## Errores detectados durante la remediación

- La primera versión de M19 asignaba la fuente primero por nombre: habría excluido por error las 16 fotos
  propias renumeradas. Corregido (SHA primero) y cubierto por una prueba en T009.
- Al registrar la evidencia de Roboflow se introdujeron comas sin comillas en `config/fuentes.csv`, lo que
  rompió la carga de configuración de 001/002. Corregido; las 80 pruebas existentes pasan.

## Pendientes fuera de esta funcionalidad

- El compañero debe retirar las 412 `sano_web` de su versión corregida, entregar solo originales de `avocare`
  si quiere reincorporarlo y resolver los frutos que cruzan particiones (incluida la ráfaga de 16 fotos de
  Herrera y Marín repartida en train/val/test).
- Revisar si la carpeta OneDrive de Herrera y Marín indicada por el autor
  (`https://1drv.ms/f/c/1cf3622e6e7d7b73/IgDwRX1LBQmfSJ_UIghWEFoWAd9AYmdPDkEMjmRx4LJ4-TA`) contiene más fotos
  propias que puedan sumarse con permiso.

**Veredicto**: sin hallazgos CRITICAL abiertos. Se puede continuar con `/speckit-implement`.
