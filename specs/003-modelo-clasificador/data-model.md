# Data Model: Construcción, calibración y exportación del modelo clasificador

**Feature**: 003-modelo-clasificador | **Fecha**: 2026-11-09

Todas las entidades son archivos. Las rutas `datos/...` se versionan en Git; las rutas `DRIVE/...`
(`/content/drive/MyDrive/AvocadoIA/modelo/` en Colab, `G:\Mi unidad\AvocadoIA\modelo\` en el PC) no.

---

## 1. Manifiesto normalizado

Producido por el adaptador (M2) a partir del manifiesto de entrada; se guarda en
`DRIVE/manifiestos/<huella8>.csv` y su resumen en `datos/modelo/verificacion.json`.

| Campo | Tipo | Regla |
| --- | --- | --- |
| `ruta` | texto | Relativa a `raiz_imagenes`; el archivo DEBE existir y abrir |
| `clase` | `sano` \| `antracnosis` \| `pedunculo` | Traducida con la tabla de equivalencias (M3); desconocida → aborta |
| `particion` | `train` \| `val` \| `test` | Obligatoria |
| `sha256` | hex 64 | Si falta en la entrada se calcula; no puede repetirse entre particiones |
| `fuente` | texto | Primero por SHA-256 en `datos/manifiesto.csv`; si no está registrado, reglas de `config/fuentes.csv` sobre la ruta original (M19). Solo filas con `uso_academico = si` llegan al manifiesto normalizado |
| `licencia` | texto | Copiada de `config/fuentes.csv` para la fuente asignada |
| `estado_etiqueta` | texto | Copiado de la entrada (`ETIQUETA_PROVISIONAL`, `respaldada`, ...) |
| `grupo` | texto | Grupo de la entrada; además se cruza con `datos/manifiesto.csv` para avisar de fuga por fruto |

**Identidad**: `huella_manifiesto = sha256(bytes del CSV de entrada)`.

## 2. Verificación (`datos/modelo/verificacion.json`)

| Campo | Contenido |
| --- | --- |
| `huella_manifiesto`, `ruta_manifiesto`, `fecha` | Identificación |
| `conteos_entrada` | `{particion: {clase: n}}` del manifiesto original |
| `excluidas` | `{total, por_motivo: {motivo: n}, por_fuente: {fuente: {uso_academico, motivo, n}}, por_particion_clase}`; motivos `licencia:<fuente>:<uso_academico>`, `sin_fuente`, `calidad:<razón>`; detalle fila a fila en `datos/modelo/excluidas.csv` (`sha256, ruta, particion, clase, fuente, licencia, uso_academico, motivo`) |
| `conteos` | `{particion: {clase: n}}` tras los filtros de licencia y calidad (lo que se entrena) |
| `faltantes`, `ilegibles` | Listas de rutas (no vacías → estado `fallida`) |
| `sha_cruzados` | SHA-256 presentes en más de una partición (no vacío → `fallida`) |
| `clases_desconocidas` | Nombres sin equivalencia (no vacío → `fallida`) |
| `fuga_por_fruto` | `{grupos: n, imagenes: n, imagenes_test: n, detalle: [...]}` (aviso) |
| `etiquetas_provisionales` | `{particion: n}` (aviso → métricas "experimentales") |
| `estado` | `ok` \| `ok_con_avisos` \| `fallida` |

## 3. Caché de tensores (`DRIVE/cache/<huella_cache>/{train,val,test}.npz`)

`x: uint8[n,224,224,3]`, `y: int8[n]` (índice en `[sano, antracnosis, pedunculo]`), `sha256: str[n]`,
`fuente: str[n]`. `huella_cache = sha256(huella_manifiesto | tamano=224 | metodo=LANCZOS-estirar)`.

## 4. Configuración de experimento (`config/modelo.toml`)

Secciones: `[datos]` (manifiesto, raíz, mapeo de columnas, equivalencias, reglas de fuente),
`[entrada]` (tamaño 224, método), `[modelo]` (arquitecturas, dropout), `[fase1]` y `[fase2]` (tasa,
épocas, fracción descongelada), `[parada]` (paciencias, factor), `[aumento]`, `[entrenamiento]` (lote,
semillas `[42, 43, 44]`, `deterministico`), `[evaluacion]` (bootstrap, mínimo por fuente),
`[seleccion]` (margen 0.02), `[calibracion]` (intervalos 15, umbral 0.60, exactitud objetivo 0.95),
`[explicacion]` (n por grupo 10, umbral de atajo 0.20), `[exportacion]` (variantes, tamaño máx. 10 MB,
pérdida máx. 0.01), `[metas]` (macro-F1 0.85, recall antracnosis 0.85), `[rutas]` (salida Drive,
destino de importación).

**Regla de igualdad**: una comparación solo es válida si todas sus corridas comparten la misma
`huella_config` (sha256 del TOML canónico **sin** los campos `arquitectura` y `semilla`, que son los únicos que
varían entre corridas de una comparación) y la misma `huella_manifiesto`.

## 5. Corrida (`datos/modelo/experimentos/<id>/`)

`id = AAAAMMDD-HHMM_<arquitectura>_s<semilla>_<huella8>`

| Archivo | Contenido |
| --- | --- |
| `registro.json` | id, arquitectura, semilla, `huella_config`, `huella_manifiesto`, `huella_cache`, configuración completa, versiones, GPU, estado (`en_curso` → `completa` \| `incompleta`), épocas por fase, duración, resumen de verificación, `experimental: bool` |
| `historial.csv` | época, fase, loss, val_loss, accuracy, val_accuracy, lr |
| `metricas.json` | Por partición (`val`, `test`): exactitud, macro-F1 (+IC 95 %), precisión/recall/F1 por clase (+IC), matriz de confusión, desglose por fuente |
| `matriz_confusion_{val,test}.csv` | 3 × 3 con etiquetas |

En Drive: `DRIVE/experimentos/<id>/{mejor.keras, backup/, logits.npz}`.

**Transiciones**: `en_curso → completa` al terminar fase 2 y evaluar; `en_curso → incompleta` si se
interrumpe y no se reanuda. Solo las `completa` entran en una comparación.

## 6. Bitácora (`datos/modelo/bitacora.csv`)

Una fila por corrida: `id, fecha, arquitectura, semilla, huella_config, huella_manifiesto, estado,
val_macro_f1, test_macro_f1, test_recall_antracnosis, tamano_keras_mb, duracion_min, experimental`.

## 7. Comparación (`datos/modelo/comparacion/<huella_config8>/`)

`tabla.csv` (por arquitectura: media ± desviación de macro-F1, recall por clase, exactitud, tamaño,
duración; n de corridas), `decision.json` (arquitectura elegida, corrida representativa = la de mayor
val macro-F1 de esa arquitectura, regla aplicada, diferencia, cumplimiento de metas),
`figura_comparacion.png`.

## 8. Modelo calibrado (`datos/modelo/calibracion/<id>/`)

`calibracion.json`: `temperatura`, `nll_{antes,despues}`, `ece_{val,test}_{antes,despues}`,
`brier_{...}`, `umbral` elegido, `umbral_exactitud_95`, `cobertura_test_umbral`,
`no_concluyentes_test`. Figuras: `fiabilidad_{antes,despues}.png`, `cobertura_exactitud.png`; tabla
`cobertura_exactitud.csv`.

## 9. Revisión de explicaciones (`datos/modelo/explicaciones/<id>/`)

`mosaico_<clase>_{aciertos,errores}.png`, `planilla_explicaciones.csv`
(`sha256, ruta, clase_real, clase_predicha, confianza, tipo (acierto|error), mapa, valoracion
(lesion_fruto|fondo_ajeno|ambiguo|vacío), revisor, fecha, notas`), `resumen.json` (% por valoración y
clase; `posibles_atajos`).

## 10. Variante exportada (`datos/modelo/exportacion/<id>/`)

`variantes.csv`: `variante (fp32|fp16|int8-dinamico), tamano_mb, test_macro_f1, diferencia_vs_keras,
test_exactitud, diferencia_exactitud, cumple_tamano, cumple_perdida, elegida`. `metadatos.json` (contrato
[contracts/modelo-tflite.md](contracts/modelo-tflite.md)). `latencia.csv`: `fecha, variante, telefono,
ram_gb, android, hilos, media_ms, p90_ms, cumple`. Binarios `.tflite` en `DRIVE/exportacion/<id>/`.

## 11. Spike `explain` (`datos/modelo/spike_explain/`)

`resultado.json`: `variante_gradientes: {convierte: bool, error, tamano_extra_mb}`,
`variante_cam: {convierte, tamano_extra_mb, pearson_medio, iou_top20_medio}`, `decision`,
`plan_b_aplicado: bool`; `comparacion.png`.
