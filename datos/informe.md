# Informe del conjunto de datos AvocadoIA

- **Generado**: 2026-10-26T14:53:27
- **Estado de la partición**: **provisional**
- **Semilla**: 42
- **Versión de configuración**: `46897064682c9ea9`
- **Huella de la partición**: `096faf72d19fd58e`

> **Partición provisional.** Contiene imágenes con validación del experto o licencia pendientes. Sirve para desarrollar y depurar el entrenamiento; ninguna métrica reportada en la tesis puede provenir de ella (constitución §II, FR-018).

## Distribución por clase y partición

| Clase | Train | Val | Test | Total |
|---|---:|---:|---:|---:|
| Sano | 677 | 145 | 145 | 967 |
| Antracnosis | 670 | 145 | 143 | 958 |
| Síntomas compatibles con anillado del pedúnculo | 184 | 40 | 39 | 263 |
| **Total** | **1531** | **330** | **327** | **2188** |

Proporción de cada partición dentro de la clase:

| Clase | Train | Val | Test |
|---|---:|---:|---:|
| Sano | 70.0 % | 15.0 % | 15.0 % |
| Antracnosis | 69.9 % | 15.1 % | 14.9 % |
| Síntomas compatibles con anillado del pedúnculo | 70.0 % | 15.2 % | 14.8 % |

## Distribución por fuente

| Clase | Fuente | Train | Val | Test | Total | Reserva |
|---|---|---:|---:|---:|---:|---:|
| Sano | `hass` | 379 | 81 | 80 | 540 | 991 |
| Sano | `herrera_marin` | 13 | 2 | 2 | 17 | 0 |
| Sano | `mdpi_pedunculo_sano` | 235 | 51 | 52 | 338 | 0 |
| Sano | `rgb_sano` | 50 | 11 | 11 | 72 | 0 |
| Antracnosis | `kaggle_antracnosis` | 235 | 51 | 50 | 336 | 398 |
| Antracnosis | `rgb_antracnosis` | 435 | 94 | 93 | 622 | 0 |
| Síntomas compatibles con anillado del pedúnculo | `mdpi_pedunculo` | 184 | 40 | 39 | 263 | 0 |

Faltantes de cuota: antracnosis/rgb_antracnosis: 42; pedunculo/mdpi_pedunculo: 21; sano/mdpi_pedunculo_sano: 22; sano/rgb_sano: 11

## Desbalance y pesos de clase sugeridos (entrenamiento)

Razón de desbalance (clase mayor / menor en train): **3.68**

| Clase | Imágenes en train | Peso sugerido `N/(K·n_c)` |
|---|---:|---:|
| Sano | 677 | 0.7538 |
| Antracnosis | 670 | 0.7617 |
| Síntomas compatibles con anillado del pedúnculo | 184 | 2.7736 |

Como las clases están desbalanceadas, OE3 debe reportar F1 macro además de la exactitud.

## Estado del inventario

| Estado | Archivos |
|---|---:|
| Excluida: la fuente no permite uso académico | 214 |
| Excluida por revisión (fuente aumentada, sin lesión visible o decisión de los autores) | 833 |
| Provisional (validación o licencia pendiente) | 3579 |

Reserva (elegibles fuera de la muestra): **1391** imágenes.
En la muestra: validación pendiente 2188, licencia pendiente 0. Decisiones del experto sobre imágenes ausentes: 0.

## Advertencias de calidad

| Tipo | Imágenes |
|---|---:|
| borrosa | 95 |

Detalle por imagen en `datos/advertencias.csv`.

## Preprocesamiento

Orientación EXIF aplicada, conversión a RGB (transparencia sobre blanco), redimensionado a 224 × 224 px por estiramiento (LANCZOS) y JPEG de calidad 95. La normalización a [0, 1] se hace en el entrenamiento.

## Aumento de datos (solo entrenamiento, en línea)

| Parámetro | Valor |
|---|---|
| Rotación | ±45° |
| Desplazamiento | 0.2 |
| Zoom | 0.2 |
| Volteo horizontal / vertical | True / True |
| Brillo | [0.8, 1.2] |
| Tono / saturación | Sin variación (la lesión se reconoce por el color) |
