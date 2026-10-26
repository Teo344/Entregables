# Curación inicial de las carpetas de clase (2026-10-25)

Ejecutada con [`scripts/curacion/organizar_clases.py`](../../scripts/curacion/organizar_clases.py).
Ningún archivo se borró, renombró ni cambió de formato: lo retirado está en `Modelo/RETIRADAS/<motivo>/`
(fuera de Git) y `Modelo/PORCLASIFICAR/` quedó intacto.

## Resultado

| Clase | Antes | Retiradas | Incorporadas | Después |
|---|---:|---:|---:|---:|
| Sano (`AGUACATESANOS`) | 2 882 | 769 | 360 | **2 473** |
| Antracnosis (`ANTRACNOSIS`) | 1 873 | 4 | 0 | **1 869** |
| Síntomas compatibles con anillado del pedúnculo (`PEDUNCULO`) | 284 | 0 | 0 | **284** |

## Retiros por motivo ([retiros.csv](retiros.csv))

| Motivo | Sano | Antracnosis | Criterio |
|---|---:|---:|---|
| `duplicado_exacto` | 530 | 0 | Mismo SHA-256 en la misma clase; se conserva la ruta lexicográficamente menor |
| `corrupta` | 1 | 0 | No se puede decodificar (`sano-0706.jpg`) |
| `menor_224px` | 232 | — | Lado menor < 224 px tras aplicar la orientación EXIF (solo sanos) |
| `casi_duplicado` | 6 | 4 | Grupo confirmado visualmente; se conserva la de mayor resolución |

## Casi duplicados ([casi_duplicados_confirmados.csv](casi_duplicados_confirmados.csv))

Detectados con dHash 16 × 16 calculado sobre el fruto recortado (para que el fondo blanco no
genere falsos positivos), con distancia de Hamming ≤ 12 y diferencia media absoluta de miniaturas
32 × 32 ≤ 3. Los 26 grupos resultantes se revisaron uno por uno en hojas de contacto: son la misma
imagen redimensionada o recortada, o tomas seguidas del mismo fruto. Muchos miembros ya habían
salido por `menor_224px`, por eso solo se retiraron 10.

Limitación: este criterio es conservador. Hay casi duplicados que no detecta, por ejemplo pares
Kaggle `Avocado 0107`/`Avocado 3521` del mismo fruto, y tampoco agrupa las tomas del mismo fruto en
distintos días (serie `hass_T10_dNN_<fruto>`). Ambos casos se tratarán como **grupos** en la
partición (spec 001) para que no queden repartidos entre entrenamiento y prueba.

## Pedúnculo sano incorporado ([pedunculo_sano_drive.csv](pedunculo_sano_drive.csv))

Clase 0 (pedúnculo sano) del artículo *A Lightweight Shallow CNN-Based Approach for Ring-Neck
Disease Detection in Avocado Fruits* (MDPI *Computers* 15(8):513), extraída de los ZIP de
`PORCLASIFICAR/Drive`. Se incorpora a la clase sano para que los primeros planos del pedúnculo
aparezcan en ambas clases y el modelo no aprenda "pedúnculo en primer plano = enfermo".

- 361 contenidos únicos (SHA-256); 1 excluido (`b29d286c3fd4…`) por aparecer como clase 0 y 1.
- 360 incorporados en `AGUACATESANOS/DRIVE_PARTICIONES_ARTICULO/`: train 252, val 54, test 54.
  Si un contenido aparece en varias particiones de la fuente se asigna con prioridad
  test > val > train, igual que en `PEDUNCULO`.
- Nombres originales conservados; el renombrado y la conversión de formatos se harán después.

## Pendientes

- Validación de las etiquetas por el experto agrónomo.
- Documentar el origen y la licencia de las series `hass_`, `sano-`, `rgb_*` y `avocare_`.
- La serie `sano-` contiene imágenes web (frutos partidos, árboles, catálogo); revisar si se
  mantienen.
- Kaggle "Healthy" (1 764) sigue en `PORCLASIFICAR`; todo el Kaggle "sin fondo" de las carpetas es
  antracnosis, un posible atajo que se vigilará en OE3 (métricas por fuente y Grad-CAM++).
- Borrar `PORCLASIFICAR/` y `RETIRADAS/` cuando el conjunto esté aprobado.

## Revisión 3 (2026-10-26): exclusiones y vistas del mismo fruto

Origen: en `train/antracnosis` apareció `Avocado 2022.jpg` con aspecto sano. El CSV de Kaggle es
coherente y la etiqueta "Anthracnose" vino de la fuente, no de la copia. La revisión encontró tres
problemas de origen:

| Archivo | Script | Contenido |
|---|---|---|
| [exclusiones_revision.csv](exclusiones_revision.csv) | `scripts/curacion/marcar_exclusiones.py` | 680 exclusiones: `avocare_` completa (209 sanas + 183 antracnosis, copias aumentadas de pocas escenas) y 288 Kaggle "Anthracnose" con ≤ 0.5 % de superficie manchada |
| [grupos_similitud.csv](grupos_similitud.csv) | `scripts/curacion/agrupar_similares.py` | 102 grupos de vistas del mismo fruto (100 de Kaggle con 686 fotos), por dHash del fruto con giros y volteos |
| [casi_duplicados_confirmados.csv](casi_duplicados_confirmados.csv) | (manual) | Grupo G027 agregado: dos tomas idénticas de `rgb_antracnosis_` |

Nada se movió ni se borró. El pipeline marca las exclusiones como `excluida_revision`, y si el
experto acepta una de esas imágenes, su decisión prevalece.
