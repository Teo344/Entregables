# Quickstart: validar el modelo clasificador de punta a punta

**Feature**: 003-modelo-clasificador

Guía para comprobar que la funcionalidad cumple la especificación. Los detalles de comandos están en
[contracts/cli.md](contracts/cli.md); las entidades y archivos, en [data-model.md](data-model.md).

## Requisitos previos

1. **PC (pruebas y verificación)**: Python 3.12 instalado y `.venv-ml` recreado:
   `py -3.12 -m venv .venv-ml` → `.venv-ml\Scripts\pip install -e ".[dev,modelo]"`.
   Google Drive para escritorio con `G:\Otros ordenadores\Mi portátil\Modelo` (lectura) y
   `G:\Mi unidad\AvocadoIA\modelo` (resultados).
2. **Colab**: cuenta con acceso al mismo Drive; entorno con GPU (T4 o superior).
3. **Teléfono**: Android de gama baja con depuración USB, `adb` y el binario `benchmark_model`
   (android_aarch64) de TFLite.

## Escenario 1: pruebas de lógica determinista (PC, sin GPU)

```text
.venv-ml\Scripts\python -m pytest tests/unit -k "modelo"
```

**Esperado**: pasan las pruebas de manifiesto, equivalencias, pesos de clase, métricas, bootstrap, ECE,
Temperature Scaling, cobertura–exactitud y regla de selección, sin importar TensorFlow.

## Escenario 2: verificación del split v4 (PC) — US1, FR-001–FR-004

```text
.venv-ml\Scripts\python -m avocadoia_modelo verificar
```

**Esperado**: `datos/modelo/verificacion.json` con 2 211 imágenes de entrada, **785 excluidas**
(412 `sano_web` por licencia; 373 `avocare` por calidad, copias aumentadas; detalle en `datos/modelo/excluidas.csv`) y 1 426 para
entrenar (train 998 / val 220 / test 208); `estado = ok_con_avisos`, aviso de fuga por fruto recalculado y de
etiquetas provisionales. Si se quita `avocare` de `[datos].fuentes_excluidas` en `config/modelo.toml`, la
siguiente ejecución conserva sus 373 imágenes (solo cuando el compañero entregue los originales). Si se borra temporalmente una imagen del manifiesto en una copia, el comando sale con
código 2 y la lista de faltantes.

## Escenario 3: spike de `explain` (Colab) — US6, FR-022

Abrir `notebooks/entrenar_colab.ipynb`, ejecutar las celdas de preparación y luego
`spike-explain`. **Esperado**: `datos/modelo/spike_explain/resultado.json` con la decisión
(Grad-CAM++ en TFLite o plan B CAM) y su concordancia.

## Escenario 4: corrida base de punta a punta (Colab) — US1

`preparar` → `entrenar --arquitectura mobilenetv3 --semilla 42`. **Esperado**: corrida `completa` con
`registro.json`, `historial.csv`, `metricas.json` (val y test) y matrices de confusión; la fila
correspondiente en `bitacora.csv`. Repetir la misma corrida: macro-F1 de prueba con diferencia ≤ 0,01
(SC-006). Desconectar el entorno a mitad de la fase 2 y relanzar: la corrida se reanuda.

## Escenario 5: comparación justa (Colab) — US2, SC-002

`comparar --ejecutar`. **Esperado**: 6 corridas completas con la misma `huella_config` y
`huella_manifiesto`; `comparacion/<h>/tabla.csv` con media ± desviación y `decision.json` con la regla
aplicada. Modificar un hiperparámetro de una sola corrida y volver a `comparar`: sale con código 3.

## Escenario 6: calibración y umbral (PC o Colab) — US3, SC-003

`calibrar --corrida <elegida>`. **Esperado**: ECE de prueba después < antes; curva cobertura–exactitud y
porcentaje de "no concluyentes" en prueba con umbral 0,60.

## Escenario 7: explicaciones (Colab + revisión manual) — US4, SC-005

`explicar --corrida <elegida>` → valorar `planilla_explicaciones.csv` (autores y, si es posible, el
agrónomo) → `resumir-explicaciones`. **Esperado**: ≥ 80 % de aciertos con foco en lesión/fruto por clase,
o atajos señalados.

## Escenario 8: exportación y latencia — US5, SC-004

`exportar --corrida <elegida>` (Colab) → `importar` (PC) → copiar el `.tflite` elegido al teléfono y
ejecutar:

```text
adb push avocadoia_fp16.tflite /data/local/tmp/
adb shell /data/local/tmp/benchmark_model --graph=/data/local/tmp/avocadoia_fp16.tflite --num_threads=4 --num_runs=50 --warmup_runs=5
```

Guardar la salida y `registrar-latencia`. **Esperado**: variante elegida ≤ 10 MB, pérdida ≤ 0,01 de
macro-F1, media ≤ 500 ms; probar también en **modo avión** (principio I).

## Escenario 9: informe

`informe` → `datos/modelo/informe_modelo.md`. **Esperado**: cada cifra enlaza con el `id` de su corrida
(SC-007) y, mientras el split sea el v4 sin corregir, aparece rotulado "experimental".
