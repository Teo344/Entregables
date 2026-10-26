# Research: Proceso ETL y EDA del conjunto de datos

**Feature**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md) | **Fecha**: 2026-10-26

Cada decisión sigue el formato Decisión / Justificación / Alternativas. Las decisiones D1–D14 de la especificación 001 siguen vigentes; esta funcionalidad las numera desde E1.

## E1. Entorno de Python para el análisis con redes preentrenadas

- **Decisión**: un segundo entorno `.venv-ml` con **Python 3.12.4** y **TensorFlow 2.20.0** (CPU), que también usará la especificación 003. El paquete `avocadoia_datos` se instala en ambos entornos; los comandos de 001 siguen funcionando en `.venv` (Python 3.14) y los nuevos de ETL/EDA requieren `.venv-ml`. Las dependencias nuevas van al grupo opcional `[eda]` de `pyproject.toml` con versiones exactas.
- **Justificación**: TensorFlow no publica ruedas para Python 3.14 (`pip` no encuentra distribución) y sí para 3.12. La constitución fija TensorFlow/Keras para el modelo, y usar la misma familia de redes para limpiar y para entrenar evita resultados de distinta naturaleza. En Windows nativo TensorFlow ≥ 2.11 no usa la GPU (RTX 3050, 4 GB), pero extraer representaciones de unas 4 000 imágenes en CPU toma minutos.
- **Alternativas**: PyTorch con DINOv2 o CLIP, que dan mejores representaciones, pero agregan un segundo framework (principio V); WSL2 con GPU, que se deja como opción para el entrenamiento de 003; bajar todo el proyecto a 3.12, que obligaría a repetir la validación de 001.

## E2. Representación de las imágenes (embeddings)

- **Decisión**: **EfficientNet-B0** con pesos ImageNet (`keras.applications`), sin la capa de clasificación, con *global average pooling*: un vector de 1 280 valores por imagen, normalizado (L2). La entrada es la versión 224 × 224 que produce el preprocesamiento de 001 (misma transformación EXIF → RGB → 224 × 224), generada al vuelo para las imágenes de reserva que no están en `PROCESADO`. Se registra el SHA-256 del archivo de pesos y la versión de TensorFlow en el resultado. Las representaciones se guardan en caché (`datos/eda/cache/`, ignorada por Git) con su huella.
- **Justificación**: EfficientNet-B0 es una de las dos arquitecturas candidatas de la constitución, pesa 21 MB y funciona sin conexión una vez descargada (FR-023). Las representaciones de ImageNet separan bien textura, color y forma, que es lo que distingue manchas de antracnosis y lesiones del pedúnculo.
- **Alternativas**: MobileNetV3 (más liviana, representaciones algo más pobres; se puede comparar si hace falta); características manuales de color y textura (insuficientes para detectar etiquetas incorrectas).

## E3. Detección de etiquetas dudosas (*confident learning*)

- **Decisión**: sobre todas las imágenes candidatas (muestra y reserva) de las tres clases:
  1. Regresión logística multinomial sobre las representaciones, con validación cruzada **por grupos** (5 particiones, `StratifiedGroupKFold`, semilla 42) para obtener probabilidades fuera de muestra: ninguna imagen se juzga con un modelo que vio su propio fruto.
  2. Regla de *confident learning* (Northcutt et al., 2021): umbral por clase *t_j* = media de *p_j* en las imágenes etiquetadas *j*; una imagen es **conflicto** si existe otra clase *k* ≠ etiqueta con *p_k* ≥ *t_k* y es la de mayor probabilidad entre las que superan su umbral.
  3. **Puntaje de sospecha** = 1 − *p*(clase asignada), complementado con la proporción de los 10 vecinos más cercanos (coseno, excluyendo su propio grupo) que tienen otra clase.
  4. **Conjunto a revisar** = conflictos ∪ 10 % de mayor puntaje en cada clase (supuesto de la spec).
- **Justificación**: es el método estándar para ruido de etiquetas, explicable ante el tribunal y sin dependencias nuevas fuera de scikit-learn. La validación por grupos impide que las vistas del mismo fruto se "voten" entre sí.
- **Alternativas**: la librería `cleanlab` (misma idea, dependencia extra con muchas funciones que no se usan); solo k-NN (más sensible a grupos de fotos parecidas); revisar todo a mano (2 284 imágenes, inviable con trazabilidad).

## E4. Revisión manual y registro de decisiones

- **Decisión**: planillas xlsx de revisión con miniatura incrustada, reutilizando el mecanismo de `validacion.py` de 001. Columnas: `id_contenido`, miniatura, fuente, grupo, clase asignada, clase sugerida, puntaje, motivo de la marca, `decision` (`mantener` · `reasignar` · `excluir` · `no_seguro`), `clase_nueva`, `atajo` (`ninguno` · `cartel` · `fondo` · `mano` · `otro`), `comentario`, `revisor`, `fecha`. Las decisiones se incorporan a `datos/curacion/revision_etiquetas.csv` (versionado) y el inventario las aplica:
  - `excluir` → estado `excluida_revision` con el motivo;
  - `reasignar` → cambia `clase_efectiva` (sin mover el archivo) y queda pendiente del experto;
  - `no_seguro` → queda en el conjunto, marcada para el experto;
  - por defecto la decisión se aplica a **todo el grupo**; si el revisor quiere decidir imagen por imagen, se indica en `comentario` con `solo_imagen` y el sistema advierte si el grupo queda partido.
  La decisión del experto (`validacion/decisiones.csv`) prevalece sobre la de los autores.
- **Justificación**: los autores ya conocen este flujo de 001 y la planilla con miniaturas permite revisar sin abrir carpetas. Separar las decisiones de los autores de las del experto mantiene la trazabilidad del principio II.
- **Alternativas**: una interfaz web local (más código, sin beneficio para unas 400 imágenes); mover archivos entre carpetas (rompe el principio II).

## E5. División de `sano_web` y reemplazo con vistas Hass

- **Decisión**: en `config/fuentes.csv`, nueva fuente `herrera_marin` con patrón `AGUACATESANOS/sano-000[1-9].*|AGUACATESANOS/sano-001[0-7].*`, listada antes de `sano_web`,, con licencia "permiso de los autores (tesis previa)" y `uso_academico = si`. `sano_web` pasa a `uso_academico = no`, y el inventario gana el estado **`excluida_licencia`** para fuentes con `uso_academico = no`. Cuotas de sano: `mdpi_pedunculo_sano` 360, `rgb_sano` 83, `herrera_marin` 17, `hass` 540 (396 frutos + 144 segundas vistas) = 1 000.
- **Justificación**: `_por_grupos` de 001 ya toma una foto por fruto y luego segundas vistas en orden estable, y los grupos nunca se reparten entre conjuntos, así que no hay fugas. La configuración rechaza fuentes repetidas, y un solo patrón glob no cubre exactamente 0001–0017 (`sano-0019.jpeg` es una descarga). Por eso la columna `patron` acepta **varias alternativas separadas por `|`**, en un cambio mínimo de `Config.fuente_de`. Como el código toma la primera coincidencia, `herrera_marin` va antes que `sano_web`.
- **Alternativas**: descargar frutos Hass nuevos (descartado por el equipo); bajar la clase sano a 852 imágenes (más desbalance).

## E6. Características de imagen para el EDA

- **Decisión**: medidas sobre la imagen **original** con la orientación EXIF aplicada y reducida a 512 px de lado mayor para velocidad: ancho, alto, megapíxeles, proporción, brillo (media de L en Lab), contraste (desviación de L), nitidez (varianza del Laplaciano, misma función de 001 recortando el borde), color HSV (media circular y dispersión de tono, media de saturación y valor), y **tipo de fondo**: fracción de píxeles del borde exterior (8 %) con saturación < 0.12 y valor > 0.85 (blanco) o desviación baja (uniforme). Fondo "uniforme" si la fracción ≥ 0.6. Solo Pillow y NumPy.
- **Justificación**: cubre FR-015 y FR-016 con medidas interpretables y rápidas (unas 4 000 imágenes en pocos minutos). El borde es una buena aproximación del fondo porque el fruto suele estar centrado.
- **Alternativas**: segmentación del fruto con un modelo (más precisa, más dependencias); OpenCV (no aporta frente a NumPy aquí).

## E7. Pruebas de atajo (sesgos)

- **Decisión**: tres sondas, todas con validación cruzada por grupos sobre **train + val** únicamente (FR-020):
  1. **Sonda de bajo nivel**: regresión logística sobre las características de E6 (sin la fuente) → exactitud balanceada para predecir la clase.
  2. **Sonda de fondo**: las mismas representaciones de E2 pero con el **60 % central de la imagen tapado** con gris medio → si el borde solo predice la clase, el fondo es un atajo.
  3. **Sonda de fuente dentro de la clase**: ¿las representaciones identifican la fuente dentro de cada clase? Mide si cada fuente tiene un "estilo" propio.
  Además se reporta la tabla de contingencia clase × fuente y clase × tipo de fondo. Umbral de alerta (SC-005): exactitud balanceada > 0.80 en las sondas 1 o 2.
- **Justificación**: la exactitud de un clasificador simple que no ve la lesión es la medida más directa y explicable de "¿se puede adivinar la clase sin mirar la enfermedad?". Tapar el centro es una técnica conocida para detectar atajos de fondo.
- **Alternativas**: V de Cramér por variable (no capta combinaciones); esperar a Grad-CAM++ de 003 (demasiado tarde para corregir datos).

## E8. Mapa de similitud

- **Decisión**: PCA a 50 dimensiones y **t-SNE** (scikit-learn, perplejidad 30, `init="pca"`, semilla 42) sobre las representaciones del conjunto final. Dos figuras (por clase y por fuente) y un CSV con `id_contenido`, coordenadas, clase, fuente y conjunto. En la figura se rotulan con su `id_contenido` las 15 imágenes con más vecinos de otra clase.
- **Justificación**: t-SNE es el estándar de figura de tesis y viene en scikit-learn; el CSV y los rótulos permiten identificar cada punto (FR-017).
- **Alternativas**: UMAP (requiere `numba`, dependencia pesada; aporte marginal para 2 284 puntos).

## E9. Embudo de calidad

- **Decisión**: cada imagen inventariada se asigna al **primer** paso que la retira, en este orden: `invalida` → `duplicada` → `conflicto_clase` → `excluida_licencia` → `excluida_revision` (revisión 3 y autores) → `rechazada` (experto) → `test_campo` (reservada) → `fuera_de_cuota` (reserva) → `conjunto_final`. Tabla por clase × fuente y figura de embudo. Prueba automática: la suma de todos los pasos = total inventariado (SC-001).
- **Justificación**: un orden fijo hace que cada imagen se cuente una sola vez y que el embudo sea auditable.
- **Alternativas**: contar todas las causas de cada imagen (suma mayor al total; confunde al lector).

## E10. Comparación con el conjunto de 001

- **Decisión**: antes de regenerar, se copia la partición de 001 (`git show f43575e:datos/particion.csv`) a `datos/etl/particion_001.csv`. El informe lista, por clase y conjunto, las imágenes que salen, las que entran y las que cambian de clase.
- **Justificación**: FR-012; deja evidencia del efecto de la limpieza.
- **Alternativas**: comparar solo totales (no muestra qué imágenes cambiaron).

## E11. Auditoría posterior a la limpieza (SC-003)

- **Decisión**: planilla de 100 imágenes al azar del conjunto final (semilla 42, estratificada por clase), revisada a mano. El informe reporta la tasa de error con su intervalo de confianza de Wilson al 95 %.
- **Justificación**: mide la calidad de las etiquetas de forma independiente de la detección automática.
- **Alternativas**: auditar solo las sospechosas (sesgado hacia los errores).

## E12. Figuras e informe

- **Decisión**: figuras con **matplotlib** (PNG a 200 ppp y SVG) en `datos/eda/figuras/`, con título, ejes con unidades y nota de fuente de datos; tablas en CSV en `datos/eda/tablas/`. El informe `datos/eda/informe_etl_eda.md` (y `.json` con las cifras) lo genera el CLI; la versión Word se produce con **pandoc** y un formateador con **python-docx** movido al repositorio (`scripts/informe/`). El Word se guarda en `DocumentosFInales/` con nombre versionado y fecha, nunca sobre un archivo existente. Mosaicos: 4 × 4 imágenes por clase × fuente, elegidas con la clave estable de 001.
- **Justificación**: la tesis necesita figuras independientes (FR-021); reutiliza el flujo de Word que el equipo ya aprobó.
- **Alternativas**: notebook de Jupyter (difícil de probar y de regenerar idéntico); generar el Word solo con python-docx (más código para el mismo resultado).

## E13. Reproducibilidad y pruebas

- **Decisión**: semilla 42 en NumPy, scikit-learn y TensorFlow; `TF_DETERMINISTIC_OPS=1`; probabilidades y medidas redondeadas a 4 decimales en los CSV; huella SHA-256 de las representaciones, del archivo de pesos y de la partición en `informe_etl_eda.json`. Las pruebas usan representaciones sintéticas (NumPy) para la lógica de sospecha, embudo, sondas y regla de grupos, y no requieren TensorFlow; una prueba de integración marcada `ml` ejecuta la extracción sobre 6 imágenes sintéticas.
- **Justificación**: SC-006 y la regla de la constitución de probar la lógica determinista.
- **Alternativas**: comparar figuras byte a byte (frágil entre versiones de matplotlib); se comparan las tablas y el JSON.

## E14. Alineación con el artículo de referencia

- **Decisión**: el informe nombra las fases como en Calapaqui, Guarderas y Fuertes (2026): **Extracción**, **Transformación** (limpieza: duplicados, nulos, ruido, consolidación de etiquetas, unión balanceada) y **Carga**, seguidas de **Análisis exploratorio (EDA)**, con la tabla de equivalencias texto → imagen de la especificación.
- **Justificación**: el equipo adopta ese artículo como base metodológica.
- **Alternativas**: CRISP-DM completo (más fases que esta funcionalidad no cubre).
