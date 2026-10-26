# Tasks: Proceso ETL y análisis exploratorio (EDA) del conjunto de datos

**Input**: Design documents from `/specs/002-etl-eda-dataset/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: incluidos. La constitución exige pruebas automatizadas para la lógica determinista: sospecha, embudo, sondas, regla de grupos, patrones y estados.

**Organization**: las tareas se agrupan por historia de usuario. El orden sigue la dependencia real:
- US1 (etiquetas dudosas) va primero porque limpia el conjunto.
- US3 y US4 se pueden adelantar como **EDA preliminar** mientras los autores revisan las planillas.
- US2 (embudo) y US6 (conclusiones e informe) se cierran al final, sobre el conjunto limpio.
- Las tareas marcadas **[MANUAL]** las hacen los autores, no el agente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede ejecutar en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1–US6)

## Path Conventions

Proyecto único en la raíz de `Entregables`: `src/avocadoia_datos/`, `tests/`, `config/`, `datos/`, `scripts/`. Entorno de análisis `.venv-ml` (Python 3.12); el entorno de 001, `.venv` (Python 3.14), sigue vigente.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: entorno de análisis y estructura de los subpaquetes

- [ ] T001 Agregar en `pyproject.toml`:
  - el extra `eda` con `tensorflow==2.20.0`, `numpy`, `scikit-learn`, `matplotlib` y `python-docx`;
  - en `[tool.pytest.ini_options]`, el marcador `ml` ("requiere TensorFlow").
- [ ] T002 Crear `.venv-ml` con `py -3.12 -m venv .venv-ml` e instalar `pip install -e ".[dev,eda]"`. Después, fijar en `pyproject.toml` las versiones exactas que resolvió pip para numpy, scikit-learn, matplotlib y python-docx (research E1).
- [ ] T003 [P] Agregar a `.gitignore`: `.venv-ml/`, `/datos/eda/cache/` y `/datos/revision/*.xlsx`.
- [ ] T004 [P] Crear `src/avocadoia_datos/etl/__init__.py` y `src/avocadoia_datos/eda/__init__.py`. TensorFlow solo se importa dentro de `etl/representaciones.py` (plan, Structure Decision).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: separar `sano_web`, el estado `excluida_licencia`, las nuevas cuotas y la línea base de 001

**⚠️ CRITICAL**: ninguna historia empieza sin esta fase

- [ ] T005 Extender `Config.fuente_de` en `src/avocadoia_datos/config.py`: "`patron` acepta varias alternativas glob separadas por `|`; una ruta pertenece a la fuente si coincide con alguna", y se mantiene la regla de primera fuente que coincide.
- [ ] T006 [P] Escribir `tests/unit/test_config_patrones.py`:
  - `sano-0001.jpg` y `sano-0017.jpg` pertenecen a `herrera_marin`;
  - `sano-0018.jpg` y `sano-0019.jpeg` pertenecen a `sano_web`;
  - un patrón sin `|` se comporta igual que en 001.
- [ ] T007 Agregar el estado `excluida_licencia` en `_estado()` de `src/avocadoia_datos/inventario.py`:
  - motivo "La fuente no permite uso académico";
  - se aplica cuando la fuente tiene `uso_academico = no`;
  - se evalúa después de `duplicada` y antes de `excluida_revision`, con la precedencia de data-model.md.
  Excluir el estado de `ESTADOS_CANDIDATOS` en `muestra.py` (ya ocurre, porque solo admite `elegible` y `provisional`) y agregar su etiqueta en `informe.py`.
- [ ] T008 [P] Escribir `tests/unit/test_inventario_licencia.py`:
  - una fuente con `uso_academico = no` deja sus imágenes en `excluida_licencia` y fuera de la muestra;
  - una copia exacta sigue marcada `duplicada` (precedencia).
- [ ] T009 Actualizar `config/fuentes.csv`:
  - agregar `herrera_marin` antes de `sano_web`:
    - clase sano;
    - patrón `AGUACATESANOS/sano-000[1-9].*|AGUACATESANOS/sano-001[0-7].*`;
    - descripción "Fotos propias de la tesis previa (Google Pixel 8)";
    - referencia "Tesis previa de Herrera y Marín, carpeta OneDrive" con la URL;
    - licencia "permiso de los autores";
    - `uso_academico = si`, `particion_origen = no`, `regla_grupo = ninguna`, `rol = general`;
  - en `sano_web`, poner `uso_academico = no` y licencia "sin licencia identificable (descargas de internet)";
  - en `kaggle_antracnosis`, completar la licencia con la justificación de uso académico de la spec (publicada por el autor para uso de otros; se cita la fuente).
- [ ] T010 Actualizar `[cuotas.sano]` en `config/dataset.toml` a `mdpi_pedunculo_sano = 360`, `hass = 540`, `rgb_sano = 83`, `herrera_marin = 17`, y quitar `sano_web`. Comentar la decisión con la fecha 2026-10-26 (research E5).
- [ ] T011 Implementar `etl-extraer` en `src/avocadoia_datos/etl/embudo.py` (función `guardar_linea_base`) y en `src/avocadoia_datos/cli.py`:
  - ejecuta `inventario`;
  - si no existe `datos/etl/particion_001.csv`, lo crea con `git show f43575e:datos/particion.csv`;
  - si Git no está disponible, termina con el código 2 y un mensaje claro.
- [ ] T012 Ejecutar `.venv-ml/Scripts/python -m avocadoia_datos etl-extraer` y luego `todo`. Verificar:
  - 214 imágenes en `excluida_licencia`;
  - 17 de `herrera_marin` en la muestra;
  - sano = 1 000, con 540 Hass;
  - 0 grupos repartidos;
  - las 45 pruebas de 001 siguen pasando.

**Checkpoint**: conjunto provisional nuevo, sin descargas web; línea base de 001 guardada

---

## Phase 3: User Story 1 - Detectar y revisar imágenes con etiqueta dudosa (Priority: P1) 🎯 MVP

**Goal**: lista priorizada de imágenes sospechosas, planillas de revisión y aplicación trazable de las decisiones

**Independent Test**: ejecutar `etl-representaciones` y `etl-sospechas`, generar planillas, incorporar una planilla de prueba con `excluir` y `reasignar`, y comprobar en el manifiesto los estados, la regla de grupo y que el archivo original sigue en su carpeta

### Tests for User Story 1

- [ ] T013 [P] [US1] Escribir `tests/unit/test_sospechas.py`, con representaciones sintéticas (tres nubes gaussianas y 5 % de etiquetas cambiadas a propósito):
  - las cambiadas aparecen como `conflicto`;
  - el umbral *t_j* es la media de *p_j* en la clase *j*;
  - las validaciones cruzadas no mezclan grupos;
  - los vecinos excluyen a su propio grupo;
  - `a_revisar` incluye al menos el 10 % superior de cada clase;
  - el orden es estable (puntaje descendente y luego `id_contenido`).
- [ ] T014 [P] [US1] Escribir `tests/unit/test_revision.py`:
  - **Planilla**: tiene las columnas de data-model.md.
  - **`incorporar` rechaza** cuatro casos:
    - `decision` fuera de `mantener/reasignar/excluir/no_seguro`;
    - `reasignar` sin `clase_nueva`;
    - fecha que no cumple "AAAA-MM-DD";
    - falta de `revisor`.
  - **Precedencia**: gana la decisión más reciente.
  - **Alcance**: `alcance = grupo` se propaga a todo el grupo; `alcance = imagen` deja una advertencia si el grupo queda partido.
- [ ] T015 [P] [US1] Ampliar `tests/unit/test_inventario.py`:
  - `revision_etiquetas.csv` con `excluir` lleva la imagen a `excluida_revision`;
  - `reasignar` cambia `clase_efectiva` y la deja `provisional`;
  - una decisión del experto `aceptada` prevalece sobre la exclusión de los autores.

### Implementation for User Story 1

- [ ] T016 [US1] Implementar `src/avocadoia_datos/etl/representaciones.py` (research E2):
  - **Modelo**: EfficientNet-B0 ImageNet sin la capa superior, `pooling="avg"`, vectores de 1 280 valores normalizados L2.
  - **Entrada**: la misma transformación de `preprocesamiento.procesar_imagen` de 001 (EXIF → `a_rgb` → 224 LANCZOS), extraída a una función `cargar_224(origen, tamano)` que devuelve la imagen en memoria, para cualquier candidata, esté o no en `PROCESADO`.
  - **Vector de borde**: el mismo cálculo con el 60 % central tapado en gris (128).
  - **Caché**: `datos/eda/cache/representaciones.npz` con la huella de data-model.md; solo se recalculan las imágenes nuevas.
  - **Determinismo**: `TF_DETERMINISTIC_OPS=1` y semilla 42.
  - **Sin TensorFlow**: se lanza `ErrorDependencia` con salida 3.
- [ ] T017 [US1] Implementar `src/avocadoia_datos/etl/sospechas.py` (research E3):
  - regresión logística multinomial con `StratifiedGroupKFold(5, semilla 42)` para obtener probabilidades fuera de muestra;
  - umbrales por clase y conflicto según *confident learning*;
  - puntaje = 1 − *p*(clase asignada);
  - 10 vecinos por coseno, excluido su grupo;
  - `a_revisar` y `motivo_marca`;
  - escritura de `datos/etl/sospechas.csv`, redondeada a 4 decimales, con columnas y orden de data-model.md.
- [ ] T018 [US1] Implementar `src/avocadoia_datos/etl/revision.py`, reutilizando la escritura de planillas con miniaturas de `validacion.py`:
  - `generar_planillas(tipo=sospecha|sistematica, clase, lote)`: planillas en `datos/revision/revision_<tipo>_<clase>_<NN>.xlsx` con listas desplegables para `decision`, `clase_nueva`, `alcance` y `atajo`;
  - `incorporar(rutas)`: agrega las decisiones válidas a `datos/curacion/revision_etiquetas.csv` con la columna `tipo` y devuelve los errores por fila.
- [ ] T019 [US1] Integrar `datos/curacion/revision_etiquetas.csv` en `inventario.construir()` de `src/avocadoia_datos/inventario.py`:
  - la decisión más reciente por imagen gana;
  - una decisión de grupo se propaga a sus miembros;
  - `excluir` → `excluida_revision` con el motivo "Autores: <comentario>";
  - `reasignar` → `clase_efectiva = clase_nueva`;
  - `no_seguro` → sin cambio de estado, con `revision_autores = no_seguro`.
  Agregar al manifiesto las columnas `revision_autores` y `atajo` con los valores de data-model.md.
- [ ] T020 [US1] Agregar a `src/avocadoia_datos/cli.py` los subcomandos `etl-representaciones`, `etl-sospechas`, `etl-revision` y `etl-incorporar`, con las opciones, códigos de salida y resúmenes de `contracts/cli.md`.
- [ ] T021 [US1] Ejecutar `etl-representaciones` y `etl-sospechas`. Registrar en `datos/etl/README.md` cuántas imágenes hay a revisar por clase y si `Avocado 2022.jpg` está marcada o ya excluida (escenario 3 de US1). Después, generar las planillas con `etl-revision --tipo sospecha`.
- [ ] T022 [MANUAL] [US1] Los autores completan las planillas de `datos/revision/revision_sospecha_*.xlsx` (`decision`, `alcance`, `atajo`, `revisor`, `fecha`) y marcan como `no_seguro` los casos para el experto. Además hacen la **revisión sistemática** (FR-005): recorren los mosaicos por clase y fuente de T028 buscando etiquetas erróneas y carteles. Las imágenes que quieran registrar las anotan en una planilla `etl-revision --tipo sistematica`.
- [ ] T023 [US1] Incorporar las planillas con `etl-incorporar`. Regenerar con `etl-extraer` y `todo`, y verificar que la cuota de cada clase se vuelve a cubrir desde la reserva y que 0 grupos quedan repartidos.

**Checkpoint**: conjunto limpio (provisional) con todas las sospechosas decididas (SC-002)

---

## Phase 4: User Story 3 - Análisis exploratorio del conjunto (Priority: P2)

**Goal**: distribuciones, características de las imágenes originales y mosaicos

**Independent Test**: ejecutar `eda` y verificar que las tablas cuadran con el manifiesto y que cada figura tiene título, unidades y fuente de datos

> Puede ejecutarse como **EDA preliminar** después de T012, mientras los autores hacen T022; se regenera en T047.

### Tests for User Story 3

- [ ] T024 [P] [US3] Escribir `tests/unit/test_caracteristicas.py` con imágenes sintéticas:
  - una imagen negra tiene brillo ≈ 0;
  - un tablero de ajedrez tiene más nitidez que un desenfoque;
  - un fruto verde sobre fondo blanco da `fondo = uniforme` (fracción ≥ 0.6) y sobre ruido da `natural`;
  - el tono medio de rojo y magenta usa la media circular;
  - la proporción respeta la orientación EXIF.
- [ ] T025 [P] [US3] Escribir `tests/unit/test_distribuciones.py`: las tablas clase × fuente × conjunto suman el total de la partición y los mosaicos eligen las mismas imágenes con la misma semilla.

### Implementation for User Story 3

- [ ] T026 [P] [US3] Implementar `src/avocadoia_datos/etl/caracteristicas.py` (research E6). Mide sobre el original con EXIF y a 512 px:
  - ancho, alto, megapíxeles y proporción;
  - brillo y contraste (L*);
  - nitidez (Laplaciano sin el borde, misma función que 001);
  - tono circular, saturación y valor;
  - `fondo_fraccion` y `fondo`.
  Escribe `datos/eda/tablas/caracteristicas.csv` con 4 decimales.
- [ ] T027 [P] [US3] Implementar `src/avocadoia_datos/eda/distribuciones.py`. Genera las tablas `distribucion_clase_fuente_conjunto.csv`, `resumen_caracteristicas.csv` (mediana, cuartiles por clase y fuente) y `fondo_por_clase.csv` en `datos/eda/tablas/`. Incluye las imágenes de campo de Sigchos como un grupo descriptivo aparte.
- [ ] T028 [US3] Implementar `src/avocadoia_datos/eda/figuras.py` con matplotlib (PNG a 200 ppp y SVG, título, ejes con unidades y nota de datos). Genera en `datos/eda/figuras/`:
  - barras apiladas clase × fuente × conjunto;
  - histogramas y cajas de resolución, brillo, contraste, nitidez y HSV por clase;
  - mosaicos 4 × 4 por clase × fuente con la clave estable de 001.
- [ ] T029 [US3] Agregar el subcomando `eda` a `src/avocadoia_datos/cli.py` (características → distribuciones → figuras; las sondas y el t-SNE se agregan en US4 y US5). Ejecutarlo como EDA preliminar.

**Checkpoint**: EDA descriptivo listo para la tesis (preliminar hasta T047)

---

## Phase 5: User Story 4 - Detectar sesgos y atajos visuales (Priority: P2)

**Goal**: medir si la clase se puede adivinar sin mirar la lesión

**Independent Test**: `sondas.csv` reporta, para cada sonda, la exactitud balanceada, el azar y la alerta, con `conjuntos = train+val`

### Tests for User Story 4

- [ ] T030 [P] [US4] Escribir `tests/unit/test_sondas.py`:
  - una característica que codifica la clase produce `alerta = si` (> 0.80);
  - el ruido aleatorio da una exactitud cercana al azar;
  - las imágenes de `test` nunca entran (FR-020);
  - la validación cruzada respeta los grupos.

### Implementation for User Story 4

- [ ] T031 [US4] Implementar `src/avocadoia_datos/eda/sondas.py` (research E7), con validación cruzada por grupos solo sobre train y val. Tres sondas:
  - `bajo_nivel`: regresión logística sobre `caracteristicas.csv`, sin la fuente;
  - `fondo`: sobre `vectores_borde`;
  - `fuente_<clase>`: predice la fuente dentro de cada clase.
  Escribe `datos/eda/tablas/sondas.csv` y la tabla de contingencia clase × fuente.
- [ ] T032 [US4] Agregar a `figuras.py` la figura de las sondas (exactitud frente a azar y umbral 0.80) y la de fondo uniforme por clase y fuente. Incluir en las figuras el conteo de atajos marcados por los autores (`cartel`, `fondo`, `mano`, `otro`) por clase, leído del manifiesto (escenario 3 de US4).
- [ ] T033 [US4] Encadenar las sondas en el subcomando `eda` de `src/avocadoia_datos/cli.py`.

**Checkpoint**: riesgos de atajo cuantificados (SC-005)

---

## Phase 6: User Story 5 - Mapa de similitud del conjunto (Priority: P3)

**Goal**: figura t-SNE por clase y por fuente, con los puntos identificables

**Independent Test**: existen las dos figuras y `tsne.csv` con `id_contenido` para cada punto del conjunto final

- [ ] T034 [P] [US5] Escribir `tests/unit/test_similitud.py`:
  - con la misma semilla, las coordenadas son idénticas;
  - los 15 rótulos son las imágenes con más vecinos de otra clase;
  - el CSV tiene una fila por imagen del conjunto final.
- [ ] T035 [US5] Implementar `src/avocadoia_datos/eda/similitud.py` (research E8). Aplica PCA a 50 dimensiones y t-SNE (perplejidad 30, `init="pca"`, semilla 42) sobre el conjunto final. Escribe `datos/eda/tablas/tsne.csv` (`id_contenido`, x, y, clase, fuente, conjunto) y las figuras `tsne_por_clase` y `tsne_por_fuente` con los 15 rótulos.
- [ ] T036 [US5] Encadenar la similitud en el subcomando `eda` de `src/avocadoia_datos/cli.py`.

---

## Phase 7: User Story 2 - Informe de calidad del ETL con embudo (Priority: P1)

**Goal**: embudo por clase y fuente donde ninguna imagen queda sin explicar, más la comparación con 001

**Independent Test**: `embudo.csv` cuadra en cada clase × fuente; `comparacion_001.csv` clasifica cada imagen como `sale`, `entra`, `cambia_clase`, `cambia_conjunto` o `igual`

> Se implementa aquí porque el embudo necesita los estados finales de US1. La lógica puede escribirse en paralelo con US3–US5.

- [ ] T037 [P] [US2] Escribir `tests/unit/test_embudo.py`:
  - cada imagen cae en exactamente un paso, en el orden de research E9;
  - `inventariadas` = suma de los pasos por clase × fuente;
  - las cinco categorías de la comparación con 001 se detectan con particiones sintéticas;
  - una imagen reasignada se cuenta en su `clase_efectiva` final.
- [ ] T038 [US2] Implementar en `src/avocadoia_datos/etl/embudo.py` las funciones `calcular_embudo` y `comparar_con_001`. Escriben `datos/etl/embudo.csv` y `datos/etl/comparacion_001.csv`, con los pasos y campos de data-model.md.
- [ ] T039 [US2] Agregar la figura de embudo por clase a `src/avocadoia_datos/eda/figuras.py`, y el subcomando `etl-embudo` a `src/avocadoia_datos/cli.py`.

**Checkpoint**: trazabilidad completa del ETL (SC-001)

---

## Phase 8: User Story 6 - Conclusiones accionables e informe (Priority: P3)

**Goal**: informe con las fases Extracción → Transformación → Carga → EDA, auditoría y conclusiones con evidencia

**Independent Test**: cada conclusión de `informe_etl_eda.json` tiene al menos una ruta de evidencia existente, y `informe-etl-eda` falla con el código 2 si el embudo no cuadra o hay una auditoría sin incorporar

### Tests for User Story 6

- [ ] T040 [P] [US6] Escribir `tests/unit/test_informe_eda.py`:
  - pesos por clase = n_total / (3 · n_clase) sobre train;
  - intervalo de Wilson al 95 % para 2/100;
  - toda conclusión tiene evidencia y la ruta existe;
  - precondición de embudo descuadrado y precondición de auditoría pendiente (salida 2).

### Implementation for User Story 6

- [ ] T041 [US6] Implementar en `src/avocadoia_datos/etl/revision.py` la función `generar_auditoria(n=100)`: muestra estratificada por clase del conjunto final con semilla 42, en `datos/revision/auditoria_01.xlsx` y `tipo = auditoria`. Agregar el subcomando `etl-auditoria` a `cli.py`.
- [ ] T042 [US6] Implementar `src/avocadoia_datos/eda/informe.py`, que escribe `datos/eda/informe_etl_eda.md` y `.json`. Secciones:
  - metodología, con la tabla de equivalencias de Calapaqui et al. (research E14);
  - **Extracción**: fuentes y licencias;
  - **Transformación**: reglas, sospechas y revisión, con marcadas = decididas (SC-002);
  - **Carga**: conjunto final, fugas, comparación con 001;
  - **Embudo**;
  - **EDA**: distribuciones, características, sesgos y atajos, t-SNE, mosaicos;
  - **Auditoría** (SC-003);
  - **Casos para el experto**: imágenes con `revision_autores = no_seguro`, y la nota de que el conteo de carteles es parcial (solo cubre lo revisado);
  - **Conclusiones** C1…Cn: pesos por clase, aumento recomendado, riesgos con mitigación y limitaciones (estado provisional y validador pendiente), cada una con evidencia (SC-007);
  - **Reproducibilidad**: huellas de pesos, representaciones, partición y versiones.
- [ ] T043 [US6] Agregar a `src/avocadoia_datos/cli.py` los subcomandos `informe-etl-eda`, con sus precondiciones, y `etl-eda`, que encadena los pasos sin intervención manual según `contracts/cli.md`.
- [ ] T044 [P] [US6] Mover el formateador de Word de fase 1 a `scripts/informe/formatear_docx.py` (bordes, encabezado E8F0E0, celdas de 9.5 pt) y crear `scripts/informe/generar_word.ps1 -Fecha AAAA-MM-DD`. El script ejecuta pandoc con `--toc` y el formateador, y escribe `DocumentosFInales/Informe_Fase2_ETL_EDA_AvocadoIA_<fecha>.docx`. Si el archivo existe, termina con error y no lo sobrescribe.
- [ ] T045 [US6] Ejecutar `etl-auditoria` para generar `datos/revision/auditoria_01.xlsx`.
- [ ] T046 [MANUAL] [US6] Los autores revisan las 100 imágenes de la auditoría y la incorporan con `etl-incorporar datos/revision/auditoria_01.xlsx`.

---

## Phase 9: Polish & Cross-Cutting Concerns

- [ ] T047 Ejecutar `etl-eda` completo sobre el conjunto limpio y registrar su duración en el informe (objetivo del plan: menos de 30 min). Revisar las conclusiones y que se cumplan SC-001 a SC-007, y anotar en el informe los que no se cumplan.
- [ ] T048 [P] Escribir `tests/integration/test_etl_eda.py` (marca `ml`). Ejecuta la cadena sobre un árbol sintético de unas 30 imágenes con TensorFlow y verifica las salidas de `contracts/cli.md` y que dos ejecuciones producen tablas y JSON idénticos (SC-006).
- [ ] T049 Verificar la reproducibilidad real con `etl-eda` dos veces y `git diff --stat datos/etl datos/eda/tablas datos/eda/informe_etl_eda.json` sin cambios (quickstart, paso 6). Verificar también que `.venv/Scripts/python -m pytest -m "not ml"` sigue pasando sin TensorFlow. Verificar FR-023: con los pesos en caché, repetir `etl-representaciones --forzar` y `eda` con la variable `AVOCADOIA_SIN_RED=1`; el código falla si intenta descargar algo.
- [ ] T050 [P] Documentar las carpetas nuevas, los comandos y el estado provisional en `datos/README.md`, `datos/curacion/README.md` y `datos/etl/README.md`. Explicar la regla `herrera_marin` / `sano_web`.
- [ ] T051 Generar el Word con `scripts/informe/generar_word.ps1` y comprobar que no se sobrescribió ningún archivo de `DocumentosFInales/`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** → **Foundational (Phase 2)** → todas las historias.
- **US1 (Phase 3)** depende de Phase 2. Sus pasos de cálculo (T016–T021) bloquean la revisión manual T022.
- **US3 (Phase 4)**, **US4 (Phase 5)** y **US5 (Phase 6)** dependen de Phase 2 y de la caché de T016 (US4 y US5). Se pueden ejecutar en paralelo con T022 como EDA preliminar.
- **US2 (Phase 7)**: su lógica (T037–T039) puede escribirse en cualquier momento después de Phase 2. Su resultado final depende de T023.
- **US6 (Phase 8)** depende de US1–US5. T046 (manual) bloquea el informe definitivo.
- **Polish (Phase 9)** depende de todo lo anterior.

### Within Each User Story

- Las pruebas se escriben antes que la implementación y deben fallar primero.
- Módulo de lógica → integración en el CLI → ejecución sobre los datos reales.

### Parallel Opportunities

- T003 y T004; T006 y T008.
- Pruebas de cada historia: T013, T014 y T015; T024 y T025; T030; T034; T037; T040.
- T026 y T027 (archivos distintos).
- T044 en cualquier momento después de Phase 1.
- Mientras los autores hacen T022 y T046, el agente avanza con US3, US4, US5 y US2.

---

## Parallel Example: User Story 3

```text
T024 tests/unit/test_caracteristicas.py
T025 tests/unit/test_distribuciones.py
T026 src/avocadoia_datos/etl/caracteristicas.py
T027 src/avocadoia_datos/eda/distribuciones.py
```

---

## Implementation Strategy

### MVP First (US1)

1. Phase 1 + Phase 2: conjunto nuevo sin descargas web.
2. US1 hasta T021: sospechas y planillas listas. Es el valor más urgente, porque ataca las etiquetas incorrectas.
3. **Validar**: revisar algunas sospechosas y confirmar que corresponden a errores reales.

### Incremental Delivery

1. Durante T022 (revisión manual): EDA preliminar con US3, US4 y US5.
2. Al incorporar las decisiones (T023): embudo con US2.
3. Auditoría e informe (US6), luego regenerar todo (T047) y generar el Word (T051).

### Notas

- El conjunto sigue **provisional** hasta que haya un validador experto. La partición definitiva queda fuera de esta funcionalidad (spec, Assumptions). FR-013 ya se cumple con los subcomandos `planilla`, `incorporar` y `particionar --definitiva` de 001; se usarán cuando exista el validador.
- Los mosaicos de `datos/eda/figuras/` contienen miniaturas derivadas de baja resolución. Se versionan como figuras de tesis; no son imágenes del conjunto (constitución, Restricciones de datos).
- Las tareas [MANUAL] no las marca el agente: las confirman los autores.
