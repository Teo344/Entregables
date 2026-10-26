# Informe del conjunto de datos AvocadoIA

- **Generado**: 2026-10-26T08:36:37
- **Estado de la partición**: **provisional**
- **Semilla**: 42
- **Versión de configuración**: `2b510c34d9c505a5`
- **Huella de la partición**: `001e3a7c62a6d3ac`

> **Partición provisional.** Contiene imágenes con validación del experto o licencia pendientes. Sirve para desarrollar y depurar el entrenamiento; ninguna métrica reportada en la tesis puede provenir de ella (constitución §II, FR-018).

## Distribución por clase y partición

| Clase | Train | Val | Test | Total |
|---|---:|---:|---:|---:|
| Sano | 700 | 150 | 150 | 1000 |
| Antracnosis | 700 | 151 | 149 | 1000 |
| Síntomas compatibles con anillado del pedúnculo | 199 | 43 | 42 | 284 |
| **Total** | **1599** | **344** | **341** | **2284** |

Proporción de cada partición dentro de la clase:

| Clase | Train | Val | Test |
|---|---:|---:|---:|
| Sano | 70.0 % | 15.0 % | 15.0 % |
| Antracnosis | 70.0 % | 15.1 % | 14.9 % |
| Síntomas compatibles con anillado del pedúnculo | 70.1 % | 15.1 % | 14.8 % |

## Distribución por fuente

| Clase | Fuente | Train | Val | Test | Total | Reserva |
|---|---|---:|---:|---:|---:|---:|
| Sano | `hass` | 277 | 60 | 59 | 396 | 1194 |
| Sano | `mdpi_pedunculo_sano` | 252 | 54 | 54 | 360 | 0 |
| Sano | `rgb_sano` | 58 | 12 | 13 | 83 | 0 |
| Sano | `sano_web` | 113 | 24 | 24 | 161 | 70 |
| Antracnosis | `kaggle_antracnosis` | 235 | 52 | 49 | 336 | 398 |
| Antracnosis | `rgb_antracnosis` | 465 | 99 | 100 | 664 | 0 |
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
| Excluida por revisión (fuente aumentada o sin lesión visible) | 680 |
| Provisional (validación o licencia pendiente) | 3946 |

Reserva (elegibles fuera de la muestra): **1662** imágenes.
En la muestra: validación pendiente 2284, licencia pendiente 2284. Decisiones del experto sobre imágenes ausentes: 0.

## Advertencias de calidad

| Tipo | Imágenes |
|---|---:|
| aspecto | 1 |
| borrosa | 101 |

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
