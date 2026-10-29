# Informe de ETL y EDA del conjunto de datos AvocadoIA

Partición **provisional** · semilla 42 · huella `096faf72d19fd58e…`

## Metodología

El proceso sigue la estructura de fases de Calapaqui, G., Guarderas, D. y Fuertes, W. (2026). A Model Implementation to Detect Hate Speech Associated with Gender Violence by Natural Language Processing and Machine Learning. ICCSA 2026, LNCS 16768, pp. 202–219. Springer. doi:10.1007/978-3-032-30488-9_13: **Extracción**, **Transformación** y **Carga**, seguidas de un **Análisis exploratorio (EDA)**. Las operaciones del artículo, sobre texto, se adaptan a imágenes así:

| En el artículo (texto) | En este conjunto (imágenes) |
| --- | --- |
| Eliminar duplicados | Duplicados exactos (SHA-256) y casi duplicados |
| Eliminar valores nulos | Imágenes corruptas o ilegibles |
| Eliminar caracteres especiales (ruido) | Ruido visual y atajos: carteles, fondos de laboratorio |
| Convertir etiquetas con umbral 0.5 | Sospecha de etiqueta, revisión manual y validación del experto |
| Unir tres conjuntos en un corpus balanceado | Unir 9 fuentes balanceadas por cuotas de clase y fuente |

## 1. Extracción

Fuentes inventariadas, con su licencia y uso académico:

| Fuente | Clase | Licencia | Uso académico |
| --- | --- | --- | --- |
| mdpi_pedunculo_sano | sano | CC BY 4.0 | si |
| hass | sano | CC BY 4.0 | si |
| avocare_sano | sano | no verificada (fuente excluida) | pendiente |
| rgb_sano | sano | Artistic-2.0 | si |
| herrera_marin | sano | permiso de los autores (tesis previa) | si |
| sano_web | sano | sin licencia identificable (descargas de internet) | no |
| avocare_antracnosis | antracnosis | no verificada (fuente excluida) | pendiente |
| rgb_antracnosis | antracnosis | Artistic-2.0 | si |
| kaggle_antracnosis | antracnosis | Data files © Original Authors; sin licencia abierta. Uso académico: el autor la publicó para que otros la usen y se cita la fuente (spec 002) | si |
| mdpi_pedunculo | pedunculo | CC BY 4.0 | si |
| campo_sigchos_sano | sano | propia | si |
| campo_sigchos_antracnosis | antracnosis | propia | si |
| campo_sigchos_pedunculo | pedunculo | propia | si |

## 2. Transformación (limpieza)

Estados del inventario:

| Estado | Imágenes |
| --- | --- |
| excluida_licencia | 214 |
| excluida_revision | 833 |
| provisional | 3579 |

### Etiquetas dudosas (confident learning)

Representaciones EfficientNet-B0, regresión logística con validación cruzada por grupos y umbral por clase. Se marcan los conflictos y el 10 % de mayor sospecha de cada clase.

| Clase | Candidatas | A revisar | Conflictos |
| --- | --- | --- | --- |
| Sano | 2048 | 205 | 3 |
| Antracnosis | 1398 | 140 | 0 |
| Síntomas compatibles con anillado del pedúnculo | 286 | 29 | 0 |

Revisión de los autores: 374 de 374 imágenes marcadas tienen decisión (SC-002: cumple). Decisiones vigentes: excluir 153, mantener 553, reasignar 2.

El conteo de carteles y otros atajos es **parcial**: solo cubre las imágenes revisadas.

## 3. Carga

Conjunto final en `Modelo/PROCESADO` (224 × 224):

| Clase | train | val | test | Total |
| --- | --- | --- | --- | --- |
| Sano | 677 | 145 | 145 | 967 |
| Antracnosis | 670 | 145 | 143 | 958 |
| Síntomas compatibles con anillado del pedúnculo | 184 | 40 | 39 | 263 |

**Cuotas no cubiertas.** Estas fuentes no tienen reserva después de la limpieza, así que su clase queda con menos imágenes. No se rellenan con otras fuentes para no aumentar el atajo de fondo: Antracnosis: rgb_antracnosis −42; Síntomas compatibles con anillado del pedúnculo: mdpi_pedunculo −21; Sano: mdpi_pedunculo_sano −22, rgb_sano −11.

Comparación con el conjunto de la especificación 001: cambia_conjunto 304, entra 158, igual 1726, sale 254.

### Embudo de calidad

![Embudo](figuras/embudo_calidad.png)

Cada imagen inventariada se cuenta en un solo paso (`datos/etl/embudo.csv`).

### Auditoría posterior a la limpieza (SC-003)

6 errores en 100 imágenes al azar (tasa 6.0%, IC 95 % de Wilson 2.8%–12.5%). Criterio ≤ 2 / 100: no cumple.

## 4. Análisis exploratorio (EDA)

![Distribución](figuras/distribucion_clase_fuente_conjunto.png)

![Características](figuras/caracteristicas_por_clase.png)

![Tono](figuras/tono_por_clase.png)

### Sesgos y atajos

![Fondo](figuras/fondo_por_clase_fuente.png)

| Sonda | Qué mide | Exactitud balanceada | Azar | Alerta |
| --- | --- | --- | --- | --- |
| bajo_nivel | Clase desde brillo, contraste, nitidez, color, tamaño y fondo (sin la fuente) | 0.7764 | 0.3333 | no |
| fondo | Clase desde la imagen con el 60 % central tapado (solo el borde) | 0.9524 | 0.3333 | si |
| imagen_completa | Referencia: clase desde la imagen completa (clasificador lineal) | 0.9950 | 0.3333 | — |
| fuente_sano | Fuente dentro de la clase sano desde la imagen completa | 0.9959 | 0.2500 | — |
| fuente_antracnosis | Fuente dentro de la clase antracnosis desde la imagen completa | 1.0000 | 0.5000 | — |

Las sondas usan solo train + val; el conjunto de prueba no interviene (FR-020).

![Sondas](figuras/sondas_atajo.png)

### Mapa de similitud

![t-SNE por clase](figuras/tsne_por_clase.png)

![t-SNE por fuente](figuras/tsne_por_fuente.png)

Los mosaicos de muestras por clase y fuente están en `datos/eda/figuras/mosaicos/`.

## 5. Conclusiones para el entrenamiento

- **C1. Desbalance entre clases.** Usar pesos por clase en la pérdida: Sano 0.7538, Antracnosis 0.7617, Síntomas compatibles con anillado del pedúnculo 2.7736 (n_total / (3 · n_clase) sobre train). Evidencia: `datos/eda/tablas/distribucion_clase_fuente_conjunto.csv`.
- **C2. Aumento de datos solo en entrenamiento.** Aplicar en línea sobre train: rotación ±45°, desplazamiento 0.2, zoom 0.2, volteos y brillo [0.8, 1.2]. Val y test no se aumentan. Evidencia: `datos/eda/figuras/caracteristicas_por_clase.png`, `config/dataset.toml`.
- **C3. Sonda bajo_nivel: 0.7764 (umbral 0.80), sin alerta.** No requiere mitigación específica; se verifica igualmente con Grad-CAM++ en 003. Evidencia: `datos/eda/tablas/sondas.csv`.
- **C4. Riesgo de atajo: el fondo (borde de la imagen) delata la clase (sonda fondo = 0.9524).** Recortes centrados en el fruto en el aumento, equilibrar fondos por clase y verificar con Grad-CAM++. Evidencia: `datos/eda/tablas/sondas.csv`, `datos/eda/figuras/sondas_atajo.png`.
- **C5. Cada fuente tiene un estilo propio reconocible dentro de su clase (fuente_sano = 0.9959, fuente_antracnosis = 1.0000).** Reportar en 003 las métricas por fuente, además de las globales, para detectar si el modelo acierta por la fuente y no por la enfermedad. Evidencia: `datos/eda/tablas/sondas.csv`, `datos/eda/figuras/tsne_por_fuente.png`.
- **C6. La proporción de fondo uniforme difiere mucho entre clases (Sano 75%, Antracnosis 94%, Síntomas compatibles con anillado del pedúnculo 64%).** Tratar el fondo como posible atajo: recortes y Grad-CAM++ en 003. Evidencia: `datos/eda/tablas/fondo_por_clase.csv`, `datos/eda/figuras/fondo_por_clase_fuente.png`.
- **C7. La limpieza dejó clases bajo su cuota (Antracnosis −42, Síntomas compatibles con anillado del pedúnculo −21, Sano −33).** No rellenar con Hass ni Kaggle, que tienen fondo blanco al 100 % y agravarían el atajo de fondo; compensar el desbalance con los pesos por clase de C1. Evidencia: `datos/particion.json`, `datos/eda/tablas/fondo_por_clase.csv`.
- **C8. Limitaciones.** El conjunto es provisional: falta el experto validador; el conteo de carteles es parcial (solo lo revisado); Kaggle no tiene licencia abierta (uso académico con cita). Las métricas finales de la tesis deben salir del conjunto definitivo. Evidencia: `datos/particion.json`, `config/fuentes.csv`.

## Reproducibilidad

- Huella de la partición: `096faf72d19fd58e0714c998fa4afefa97a6b97df4172fbdea6f3f73365a4bef`
- Huella de las representaciones: `d44a400de5af4d038a9243e22866dfc5a2a7f9f3267ec848ba7e9d7dbc7ba823`
- TensorFlow 2.20.0; semilla 42.
- Regenerar: `.venv-ml/Scripts/python -m avocadoia_datos etl-eda`.
