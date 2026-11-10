# Informe del split v5 (propuesta)

**Fecha**: 2026-11-10 · **Estado**: propuesta para revisión del responsable del ETL · **Base**: split experimental v4
(`Dataset_split_experimental_v4_20261104_230751`, huella `6691b967`) · **Generado con**:
`python -m avocadoia_modelo generar-v5` (`src/avocadoia_modelo/split_v5.py`), reproducible y sin copiar imágenes.

## 1. Por qué hace falta un v5

| Evidencia | Resultado con el v4 |
| --- | --- |
| Licencias (`config/fuentes.csv`, principio II de la constitución) | 412 fotos `sano-*` son descargas de internet sin licencia (EXIF: 404 sin cámara, miniaturas de 13 KB, cámaras de terceros) |
| Calidad de `avocare` (verificado en Roboflow Universe) | Licencia CC BY 4.0, pero la versión 4 genera **3 variantes aumentadas por foto** (2 488 desde 1 134 originales) |
| Frutos repartidos entre particiones | 88 grupos de fotos del mismo fruto en más de una partición (76 imágenes en test) |
| Artículo de Flores et al. (2026), fuente del pedúnculo | El v4 no incluye los **340 pedúnculos sanos** del artículo ni sus fotos de anillado de **val (29) y test (33)**; solo las de train |
| Prueba interna del modelo MobileNetV3 | 100 % de exactitud: sospecha de atajo |
| **Prueba de campo** (40 fotos propias de anillado, Sigchos) | **Sensibilidad 0 %: las 40 clasificadas como sano** con confianza media 0,94; Grad-CAM++ enfoca el cuerpo del fruto, no el pedúnculo |

Conclusión: con el v4, «pedúnculo» es la única clase con primeros planos del tallo y «sano» son sobre todo Hass maduros
(oscuros y rugosos). El modelo aprende el encuadre y el aspecto del fruto, no el síntoma.

## 2. Reglas aplicadas (en este orden)

1. **Licencia** (FR-026): se excluye toda imagen cuya fuente no tenga `uso_academico = si`. La fuente se determina
   primero por SHA-256 en `datos/manifiesto.csv` (002) y, si no está, por las reglas de nombre de `config/fuentes.csv`.
   Así las 16 fotos propias de Herrera y Marín renumeradas en el v4 (`sano-0707`…`0723`) se conservan.
2. **Calidad** (FR-027): se excluye `avocare` (copias aumentadas).
3. **Artículo completo**: se agregan las imágenes utilizables de 002 del artículo de Flores et al. que faltaban:
   340 pedúnculos sanos (clase sano) y 62 de anillado de val/test, con la **partición publicada por los autores**.
4. **Partición del artículo**: las imágenes de esa fuente que el v4 había puesto en otra partición vuelven a la de
   los autores (54).
5. **Ráfaga de Herrera y Marín**: sus 16 fotos (una sesión de ~40 s) forman un solo grupo.
6. **Frutos**: cada grupo repartido se reasigna completo, en orden determinista (semilla 42), a la partición con más
   déficit respecto de 70/15/15 en su clase (partición estratificada por grupos). Se descartó la regla de mayoría
   porque enviaba casi todos los frutos a train y dejaba Hass con 17 fotos en val y 16 en test.

## 3. Antes y después

| Partición | v4 (sano / antracnosis / pedúnculo) | v5 (sano / antracnosis / pedúnculo) |
| --- | --- | --- |
| train | 700 / 700 / 148 = 1 548 | 513 / 577 / 203 = **1 293** |
| val | 150 / 150 / 32 = 332 | 108 / 122 / 33 = **263** |
| test | 150 / 150 / 31 = 331 | 109 / 124 / 39 = **272** |
| **Total** | **2 211** | **1 828** (71 / 14 / 15 %) |

| Cambio | Imágenes |
| --- | --- |
| Excluidas por licencia (`sano_web`) | 412 |
| Excluidas por calidad (`avocare`) | 373 |
| Agregadas: pedúnculos sanos del artículo | 340 |
| Agregadas: anillado val/test del artículo | 62 |
| Movidas a la partición del artículo | 54 |
| Movidas para que ningún fruto cruce particiones | 202 |
| Movidas por la ráfaga de Herrera y Marín | 2 |

### Composición por fuente

| Fuente | Clase | train | val | test |
| --- | --- | --- | --- | --- |
| hass | sano | 204 | 44 | 46 |
| rgb_sano | sano | 58 | 13 | 11 |
| herrera_marin | sano | 16 | 0 | 0 |
| mdpi_pedunculo_sano | sano | 236 | 51 | 53 |
| kaggle_antracnosis | antracnosis | 264 | 60 | 61 |
| rgb_antracnosis | antracnosis | 313 | 62 | 63 |
| mdpi_pedunculo | pedúnculo | 202 | 33 | 38 |

Ahora la clase sano incluye primeros planos de pedúnculos **sanos** de la misma fuente y condiciones que los de anillado:
el modelo tiene que distinguir el síntoma, no el encuadre.

## 4. Comprobaciones

| Comprobación | Resultado |
| --- | --- |
| Grupos (frutos) en más de una partición | 0 |
| Mismo contenido (SHA-256) en más de una partición | 0 |
| Fuentes sin licencia académica | ninguna |
| Imágenes `avocare` | 0 |
| Rutas inexistentes en `Modelo/` | 0 de 1 828 |
| Verificación oficial (`verificar`) | ver `verificacion.json` en esta carpeta |

## 5. Qué sigue pendiente (no lo resuelve el v5)

- **Validación del agrónomo**: todas las etiquetas siguen provisionales (constitución).
- **avocare**: puede volver solo con una imagen por foto original.
- **Fotos de campo**: tomar pedúnculos **sanos** en Sigchos para que la prueba de campo mida confusiones, no solo
  sensibilidad (T063).
- Las fotos de campo (`CAMPO_SIGCHOS`) **no** están en el v5: son solo prueba independiente.

## 6. Cómo usarlo y cómo adoptarlo

- Rutas relativas a `Modelo/` (raíz `G:\Otros ordenadores\Mi portátil\Modelo`; en Colab
  `/content/drive/Othercomputers/Mi portátil/Modelo`). Mismas columnas que el v4, más `fuente`, `licencia` y `origen`.
- Entrenar con el v5: `--manifiesto datos/modelo/v5/manifiesto_v5.csv --raiz-imagenes <Modelo>` en `verificar`,
  `preparar` y `entrenar`.
- **Adopción**: el responsable del ETL revisa `cambios_v5.csv` (una fila por imagen excluida, agregada o movida, con su
  motivo) y decide si lo adopta tal cual o incorpora estas reglas en su propio pipeline.

**Archivos**: `manifiesto_v5.csv` (1 828 imágenes), `cambios_v5.csv` (1 445 cambios), `resumen_v5.json`, este informe y
`verificacion.json` / `excluidas.csv` de la verificación oficial.
