# Informe del conjunto de datos AvocadoIA

- **Generado**: 2026-10-25T22:01:08
- **Estado de la partición**: **provisional**
- **Semilla**: 42
- **Versión de configuración**: `be4174845ad7c817`
- **Huella de la partición**: `3bf5426867e8a254`

> **Partición provisional.** Contiene imágenes con validación del experto o licencia pendientes. Sirve para desarrollar y depurar el entrenamiento; ninguna métrica reportada en la tesis puede provenir de ella (constitución §II, FR-018).

## Distribución por clase y partición

| Clase | Train | Val | Test | Total |
|---|---:|---:|---:|---:|
| Sano | 700 | 150 | 150 | 1000 |
| Antracnosis | 700 | 150 | 150 | 1000 |
| Síntomas compatibles con anillado del pedúnculo | 199 | 43 | 42 | 284 |
| **Total** | **1599** | **343** | **342** | **2284** |

Proporción de cada partición dentro de la clase:

| Clase | Train | Val | Test |
|---|---:|---:|---:|
| Sano | 70.0 % | 15.0 % | 15.0 % |
| Antracnosis | 70.0 % | 15.0 % | 15.0 % |
| Síntomas compatibles con anillado del pedúnculo | 70.1 % | 15.1 % | 14.8 % |

## Distribución por fuente

| Clase | Fuente | Train | Val | Test | Total | Reserva |
|---|---|---:|---:|---:|---:|---:|
| Sano | `avocare_sano` | 146 | 32 | 31 | 209 | 0 |
| Sano | `hass` | 196 | 42 | 42 | 280 | 1310 |
| Sano | `mdpi_pedunculo_sano` | 252 | 54 | 54 | 360 | 0 |
| Sano | `rgb_sano` | 58 | 12 | 13 | 83 | 0 |
| Sano | `sano_web` | 48 | 10 | 10 | 68 | 163 |
| Antracnosis | `avocare_antracnosis` | 128 | 28 | 27 | 183 | 0 |
| Antracnosis | `kaggle_antracnosis` | 315 | 67 | 68 | 450 | 572 |
| Antracnosis | `rgb_antracnosis` | 257 | 55 | 55 | 367 | 297 |
| Síntomas compatibles con anillado del pedúnculo | `mdpi_pedunculo` | 199 | 43 | 42 | 284 | 0 |

## Desbalance y pesos de clase sugeridos (entrenamiento)

Razón de desbalance (clase mayor / menor en train): **3.52**

| Clase | Imágenes en train | Peso sugerido `N/(K·n_c)` |
|---|---:|---:|
| Sano | 700 | 0.7614 |
| Antracnosis | 700 | 0.7614 |
| Síntomas compatibles con anillado del pedúnculo | 199 | 2.6784 |

Como las clases están desbalanceadas, OE3 debe reportar F1 macro además de la exactitud.

## Estado del inventario

| Estado | Archivos |
|---|---:|
| Provisional (validación o licencia pendiente) | 4626 |

Reserva (elegibles fuera de la muestra): **2342** imágenes.
En la muestra: validación pendiente 2284, licencia pendiente 2284. Decisiones del experto sobre imágenes ausentes: 0.

## Advertencias de calidad

| Tipo | Imágenes |
|---|---:|
| borrosa | 98 |
| oscura | 10 |

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
