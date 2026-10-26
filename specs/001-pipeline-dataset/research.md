# Research: Pipeline de construcción del conjunto de datos

**Feature**: `001-pipeline-dataset` | **Date**: 2026-10-25 (revisión 2)

Hallazgos del relevamiento de `Modelo/` y decisiones técnicas que resuelven las incógnitas del
contexto técnico. La curación previa está documentada en
[datos/curacion/README.md](../../datos/curacion/README.md).

## Relevamiento (tras la curación del 2026-10-25)

| Carpeta | Fuente (patrón) | Archivos | Partición de origen | Agrupación |
|---|---|---:|---|---|
| `AGUACATESANOS` | `hass_T<trat>_d<día>_<fruto>_<lado>_<estado>_<hash>` | 1 590 | — | 396 frutos (≈4 fotos por fruto) |
| `AGUACATESANOS/DRIVE_PARTICIONES_ARTICULO` | Pedúnculo sano MDPI (clase 0) | 360 | 252 / 54 / 54 | — |
| `AGUACATESANOS` | `sano-NNNN` | 231 | — | Casi duplicados confirmados |
| `AGUACATESANOS` | `avocare_` | 209 | — | — |
| `AGUACATESANOS` | `rgb_sano_` | 83 | — | — |
| `ANTRACNOSIS` | Kaggle `Avocado NNNN` | 1 022 | — | Casi duplicados confirmados |
| `ANTRACNOSIS` | `rgb_antracnosis_` | 664 | — | Casi duplicados confirmados |
| `ANTRACNOSIS` | `avocare_` | 183 | — | — |
| `PEDUNCULO/DRIVE_PARTICIONES_ARTICULO` | Ring-neck MDPI (clase 1) | 255 | 182 / 36 / 37 | — |
| `PEDUNCULO/DRIVE_CANDIDATAS` | Ring-neck MDPI (clase 1) | 29 | — | — |

Muestra de propiedades (1 de cada 5 imágenes):

- ~25 % de antracnosis tiene una etiqueta EXIF de rotación;
- hay modos RGBA aislados;
- en pedúnculo conviven tamaños de 1 500 × 1 500 y 3 072 × 4 080.

## Decisiones

### D1. Lenguaje y dependencias

- **Decision**: Python ≥ 3.11 con la biblioteca estándar (`hashlib`, `csv`, `json`, `tomllib`,
  `random`, `argparse`), más Pillow (imágenes) y openpyxl (planilla del experto). Las pruebas se
  hacen con pytest. Las versiones se fijan en `pyproject.toml`.
- **Rationale**: es el mismo lenguaje del entrenamiento (OE3) y basta para hashing, CSV e imágenes.
  Sin TensorFlow, el pipeline corre en la versión de Python instalada (3.14).
- **Alternatives considered**:
  - pandas: innecesario para unas 5 000 filas y añade una dependencia pesada.
  - Notebook único: no es testeable por partes y contradice el principio III.

### D2. Forma de la herramienta

- **Decision**: paquete `avocadoia_datos` con una CLI por subcomandos (`inventario`, `planilla`,
  `incorporar`, `particionar`, `preprocesar`, `informe`, `todo`). La configuración está en
  `config/dataset.toml` y el registro de fuentes en `config/fuentes.csv`.
- **Rationale**: cada historia de usuario es un subcomando que se prueba por separado, y la
  configuración versionada fija semilla, cuotas y parámetros (FR-023).

### D3. Manifiesto derivado, decisiones acumuladas

- **Decision**: el manifiesto se recalcula en cada ejecución a partir de las carpetas,
  `config/fuentes.csv`, `datos/curacion/casi_duplicados_confirmados.csv` y
  `datos/validacion/decisiones.csv`. Las decisiones se acumulan sin sobrescribirse en
  `decisiones.csv`; la planilla xlsx solo sirve de ida y vuelta con el experto.
- **Rationale**: reejecutar sin cambios da un manifiesto idéntico (US1-6), y ninguna decisión se
  pierde aunque se regenere el manifiesto.

### D4. Identificadores y copia canónica

- **Decision**: `id_contenido` son los primeros 16 caracteres hexadecimales del SHA-256. Entre
  copias exactas, la canónica es la de ruta lexicográficamente menor.
- **Rationale**: es determinista; 64 bits no colisionan en unos 10⁴ archivos.

### D5. Grupos

- **Decision**: `grupo` se calcula en este orden:
  1. Regla de la fuente. En `hass_`, `hass:<tratamiento>:<fruto>` (p. ej. `hass:T10:041`): el
     mismo fruto en distintos días y lados.
  2. Unión con los grupos de casi duplicados confirmados (`G001`…), mediante union-find.
  3. Si no aplica nada, el grupo es el propio `id_contenido`.
- **Rationale**: dos fotos del mismo fruto, una en entrenamiento y otra en prueba, inflan la
  exactitud. Es la fuga más común en datasets de frutos y la que el tribunal puede objetar.
- **Alternatives considered**:
  - Buscar casi duplicados en cada ejecución: lento, con falsos positivos en fondos blancos (se
    verificó en la curación) y no determinista ante cambios de umbral.

### D6. Muestra por cuotas de fuente

- **Decision**: para cada clase, cada fuente aporta como máximo su cuota (`[cuotas.<clase>]` en
  `dataset.toml`). Dentro de la fuente, los grupos se ordenan por `grupo` y se barajan con
  `random.Random(semilla)`. Primero se toma una imagen por grupo (elegida también con la semilla) y
  solo si faltan se toman segundas fotos. Lo elegible que no entra es `reserva`. Las fuentes con
  partición de origen y las que tienen menos imágenes que su cuota entran completas.
- **Rationale**: el tope de 1 000 por clase lo decidió el equipo. Elegir por fuente evita que un
  fondo (Kaggle blanco) o un tipo de imagen (web) quede asociado a una sola clase. Una foto por
  grupo maximiza la variedad real (en `hass_`, 280 frutos distintos en lugar de 70 frutos × 4
  fotos).
- **Cuotas iniciales**:
  - **Sano:** MDPI 360, `avocare_` 209, `rgb_sano_` 83, `hass_` 280 y `sano-` 68.
  - **Antracnosis:** `avocare_` 183, `rgb_antracnosis_` 367 y Kaggle 450.
  - Reemplazadas en la revisión 3 (D14): sano = MDPI 360, `hass_` 396, `rgb_sano_` 83, `sano-` 161;
    antracnosis = `rgb_antracnosis_` 664, Kaggle 336.
  - **Pedúnculo:** sin tope (284).
- **Alternatives considered**:
  - Muestreo aleatorio estratificado solo por clase: reproduce el sesgo de fuente actual (55 % de
    la antracnosis es Kaggle con fondo blanco).
  - Submuestrear todo a 284: desperdicia más del 70 % de los datos.

### D7. Partición: estratificada por clase y fuente, por grupos, con relleno de déficit

- **Decision**: para cada clase se calculan las cuotas 70/15/15 sobre la muestra (redondeo por
  mayor resto) y se procede así:
  1. Las imágenes con partición de origen la conservan (FR-017).
  2. Se calcula el déficit de cada partición frente a su cuota.
  3. Ese déficit se reparte entre las fuentes libres en proporción a su tamaño (mayor resto).
  4. Dentro de cada fuente, los grupos barajados con la semilla se asignan uno a uno a la partición
     con mayor déficit relativo pendiente.

  Un grupo nunca se divide.
- **Rationale**:
  - Sin particiones de origen ni grupos, se reduce a una estratificación clásica.
  - En pedúnculo (182/36/37 fijas + 29 libres) da 199/43/42, dentro de ±1 pp.
  - En sano, las 360 de MDPI fijan 252/54/54 y las 640 libres completan 700/150/150.
  - Ordenar antes de barajar hace que el resultado no dependa del orden del sistema de archivos
    (FR-015).
- **Alternatives considered**:
  - `GroupShuffleSplit` de scikit-learn: no admite asignaciones fijas ni estratificación por
    fuente, y añade una dependencia.

### D8. Elegibilidad y estado provisional

- **Decision**:
  - **Definitiva:** canónica, no excluida, licencia académica y aceptada por el experto.
  - **Provisional:** admite además imágenes con validación o licencia pendientes, y lo declara en
    `particion.json` y en el informe.
  - **Rechazo, caso mixto o reasignación:** la muestra se recalcula. La reposición sale de la
    reserva de la misma fuente, de modo que solo cambian las imágenes afectadas.
- **Rationale**: la validación y la documentación de licencias llevarán semanas; OE3 necesita una
  partición con la que preparar su pipeline mientras tanto.

### D9. Preprocesamiento

- **Decision**: aplicar `ImageOps.exif_transpose`, convertir a RGB (componiendo el canal alfa sobre
  blanco), redimensionar a 224 × 224 por estiramiento con LANCZOS y guardar en JPEG de calidad 95 en
  `Modelo/PROCESADO/<particion>/<clase>/<id_contenido>.jpg`. Se advierten:
  - lado menor < 224 px;
  - relación de aspecto > 2:1;
  - brillo medio < 40 (oscura);
  - varianza del laplaciano < 50 (borrosa), calculada sobre la miniatura de 224 px.
- **Rationale**: sin la rotación EXIF, ~25 % de la antracnosis quedaría girada. El estiramiento es
  el método de la tesis previa y no introduce bordes de relleno que puedan volverse un atajo de
  fuente. La normalización a [0, 1] y el aumento se hacen en el entrenamiento.
- **Alternatives considered**:
  - Relleno a cuadrado: riesgo de atajo.
  - Recorte central: puede cortar la lesión o el pedúnculo.

### D10. Parámetros de aumento documentados

- **Decision**: rotación ±45°, desplazamiento 20 %, zoom 20 %, volteo horizontal y vertical y brillo
  0.8–1.2, solo sobre entrenamiento. **Sin** variación de tono ni de saturación.
- **Rationale**: son los valores de Herrera & Marín, lo que permite comparar con la tesis previa.
  El tono se excluye porque la antracnosis se reconoce por el color de la lesión.

### D11. Pesos de clase sugeridos

- **Decision**: `peso_c = N_entrenamiento / (K × n_c)`, con K = 3, publicado junto con la razón de
  desbalance. Con la muestra prevista: sano 0.76, antracnosis 0.76, pedúnculo 2.68 (razón 3.5).
- **Rationale**: es la fórmula `balanced` de Keras y scikit-learn.

### D12. Planilla del experto

- **Decision**: xlsx con las columnas `id_contenido`, `clase_propuesta`, `fuente`, `ruta`
  (hipervínculo a la imagen), `decision` (desplegable: aceptada / rechazada / reasignada / mixto),
  `clase_nueva`, `objeto` (fruto completo / pedúnculo en primer plano / varios frutos / no es un
  fruto), `toma` (campo / laboratorio / sin fondo), `calidad` (buena / aceptable / mala),
  `comentario`, `validador` y `fecha`. Se genera por clase y en lotes.
- **Rationale**: el experto la abre en Excel sin herramientas técnicas (SC-005). Las columnas
  descriptivas permiten analizar el sesgo y describir el dataset en la tesis.

### D13. Prueba de campo

- **Decision**: la fuente `campo_sigchos` (carpeta `Modelo/CAMPO_SIGCHOS/<clase>/`, aún
  inexistente) queda fuera de la muestra y de las cuotas, y se procesa entera a
  `PROCESADO/test_campo/<clase>/`.
- **Rationale**: es la mejor evidencia de generalización (corrección C10) y no debe contaminarse
  con entrenamiento.

### D14. Revisión 3: exclusión de fuentes y vistas del mismo fruto (2026-10-26)

- **Hallazgos** (revisión visual del conjunto provisional, a raíz de `Avocado 2022`, que parecía
  sana en `train/antracnosis`):
  - El CSV de Kaggle es coherente (3 983 filas; `Condition` coincide con sus marcas 0/1) y la copia
    fue fiel: las 1 022 fotos Kaggle de `ANTRACNOSIS` están etiquetadas "Anthracnose" por nombre y
    contenido. El problema es de la etiqueta de origen: 288 tienen ≤ 0.5 % de superficie manchada.
  - `avocare_` (392 fotos) son copias aumentadas de pocas escenas: 27 grupos de copias estaban
    repartidos entre train y val/test, y 5 escenas aparecían en sano y en antracnosis.
  - Kaggle fotografía cada fruto desde 5 a 7 lados: 734 fotos con lesión visible = ~150 frutos.
- **Decision**: excluir `avocare_` completa y las 288 Kaggle sin lesión visible
  (`scripts/curacion/marcar_exclusiones.py` → `exclusiones_revision.csv`, estado
  `excluida_revision`; la aceptación del experto prevalece). Agrupar vistas del mismo fruto con un
  dHash 16 × 16 del fruto recortado, comparado también girado 90/180/270° y volteado, distancia ≤ 10
  (`scripts/curacion/agrupar_similares.py` → `grupos_similitud.csv`): 100 grupos Kaggle con 686
  fotos, estables entre umbrales 8–12.
- **Rationale**: copias o vistas del mismo fruto en train y test inflan las métricas (principio II).
  Una exclusión registrada y reversible respeta la decisión final del experto sobre la etiqueta.
- **Verificación**: tras regenerar, 0 pares casi idénticos (con giros y volteos, distancia ≤ 12)
  entre conjuntos distintos y 0 grupos repartidos.
- **Alternatives considered**: agrupar las variantes de `avocare_` en lugar de excluirla (la
  similitud por color confunde fondos planos y las etiquetas de la fuente también eran dudosas);
  mantener las Kaggle dudosas solo marcadas (dejaría ruido de etiqueta en train y test).
