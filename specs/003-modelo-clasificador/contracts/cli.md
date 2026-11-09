# Contrato CLI: `python -m avocadoia_modelo`

**Feature**: 003-modelo-clasificador

Opciones comunes a todos los subcomandos:

| Opción | Por defecto | Uso |
| --- | --- | --- |
| `--config` | `config/modelo.toml` | Configuración del experimento |
| `--manifiesto` | valor de `[datos].manifiesto` | CSV de entrada (v4 o versión corregida) |
| `--raiz-imagenes` | valor de `[datos].raiz_imagenes` | Carpeta base de las rutas del manifiesto |
| `--salida` | valor de `[rutas].salida` | Carpeta de artefactos pesados (Drive) |
| `--repo-datos` | `datos/modelo` | Carpeta de artefactos versionables |

Códigos de salida: `0` éxito; `1` error de uso o configuración; `2` verificación fallida (datos);
`3` comparación inválida (configuraciones distintas o corridas incompletas).

| Subcomando | Requiere TF | Entradas | Salidas | Notas |
| --- | --- | --- | --- | --- |
| `verificar` | No | manifiesto, raíz, `datos/manifiesto.csv` | `verificacion.json`, manifiesto normalizado | Primero excluye por licencia y calidad con registro en `excluidas.csv` (M19, M19.1); después aborta (2) si faltan imágenes, hay SHA cruzados o clases desconocidas; avisa fuga por fruto (M4) |
| `preparar` | No (Pillow + NumPy) | manifiesto normalizado | caché `.npz` | Idempotente por `huella_cache`; `--forzar` regenera |
| `entrenar --arquitectura {mobilenetv3,efficientnetb0} --semilla N` | Sí | caché `train`/`val` | corrida `en_curso → completa` | No carga `test`; reanuda desde `backup/` si existe; sale con 2 si la verificación falta, falló o no corresponde a la caché |
| `evaluar --corrida ID` | Sí | `mejor.keras`, caché `val`/`test` | `metricas.json`, matrices, `logits.npz` | Lo llama `entrenar` al terminar; se puede repetir |
| `comparar [--ejecutar]` | Sí con `--ejecutar` | corridas completas | `comparacion/<h>/` | Sin `--ejecutar` solo agrega corridas existentes; con él lanza las faltantes (2 arq. × semillas) |
| `calibrar --corrida ID` | No | `logits.npz` | `calibracion/<id>/` | Ajusta `T` solo con `val` |
| `explicar --corrida ID` | Sí | `mejor.keras`, caché `test`, `calibracion.json` | `explicaciones/<id>/` | Muestra con semilla 42 |
| `resumir-explicaciones --corrida ID` | No | planilla valorada | `resumen.json` | Tras la revisión manual |
| `exportar --corrida ID` | Sí | `mejor.keras`, `calibracion.json`, caché `test` | `exportacion/<id>/`, `.tflite` | 3 variantes + elección (M15) |
| `registrar-latencia --corrida ID --archivo salida_benchmark.txt --telefono "..." --ram-gb N --android V` | No | salida de `benchmark_model` | fila en `latencia.csv` | M16 |
| `spike-explain` | Sí | caché `train` (1 época) | `spike_explain/` | M14; se ejecuta temprano |
| `importar` | No | `[rutas].salida` en el PC | copia a `datos/modelo/` | Solo archivos livianos (M18) |
| `informe` | No | `datos/modelo/` | `datos/modelo/informe_modelo.{md,json}` | Rotula "experimental" si aplica |
| `todo --arquitectura ... ` | Sí | — | — | `verificar → preparar → comparar --ejecutar → calibrar → explicar → exportar → informe` |

Ejemplos:

```text
python -m avocadoia_modelo verificar
python -m avocadoia_modelo preparar
python -m avocadoia_modelo entrenar --arquitectura mobilenetv3 --semilla 42
python -m avocadoia_modelo comparar --ejecutar
python -m avocadoia_modelo calibrar --corrida 20261110-0930_mobilenetv3_s42_ab12cd34
```
