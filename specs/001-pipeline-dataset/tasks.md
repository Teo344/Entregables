# Tasks: Pipeline de construcción del conjunto de datos

**Input**: Design documents from `/specs/001-pipeline-dataset/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/cli.md, quickstart.md

**Tests**: incluidos. La constitución exige pruebas automatizadas para la lógica determinista
(hash, deduplicación, grupos, muestra, partición, incorporación).

**Organization**: las tareas se agrupan por historia de usuario. El orden de las fases sigue la
**dependencia real**, no la prioridad: US2 (planilla del experto) necesita la muestra que produce
US3, así que se implementa después de US3 y US4. El MVP del conjunto de datos es US1 + US3 + US4.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede ejecutar en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1–US4)

## Path Conventions

Proyecto único en la raíz de `Entregables`: `src/avocadoia_datos/`, `tests/`, `config/`, `datos/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: inicializar el paquete y su configuración

- [X] T001 Crear `pyproject.toml` con el paquete `avocadoia_datos` (layout `src/`), `requires-python = ">=3.11"`, dependencias fijadas `Pillow==12.3.0` y `openpyxl==3.1.5`, extra `dev` con `pytest==8.4.2` (constitución §III), y configuración `[tool.pytest.ini_options]` con `testpaths = ["tests"]`
- [X] T002 [P] Crear `src/avocadoia_datos/__init__.py` y `src/avocadoia_datos/__main__.py` (llama a `cli.main()`)
- [X] T003 [P] Añadir al `.gitignore` las entradas `/Modelo/PROCESADO/`, `.venv/`, `__pycache__/`, `*.egg-info/` y `.pytest_cache/`
- [X] T004 [P] Crear `config/dataset.toml` con semilla 42, proporciones 0.70/0.15/0.15, `max_por_clase = 1000`, las cuotas por fuente de data-model.md (sano: mdpi_pedunculo_sano 360, avocare_sano 209, rgb_sano 83, hass 280, sano_web 68; antracnosis: avocare_antracnosis 183, rgb_antracnosis 367, kaggle_antracnosis 450; pedunculo: mdpi_pedunculo 284), preprocesamiento (224, calidad 95, brillo 40, borrosidad 50), aumento (±45°, 0.20, 0.20, volteos, brillo [0.8, 1.2]) y planilla (lote 250)
- [X] T005 [P] Crear `config/fuentes.csv` con las 9 fuentes de research.md, con las columnas `fuente,clase,patron,descripcion,referencia,licencia,uso_academico,particion_origen,regla_grupo,rol`. Usar licencia `pendiente` donde no se conozca, `particion_origen = si` y patrones `*/DRIVE_PARTICIONES_ARTICULO/*` para MDPI, y `regla_grupo = hass` para `hass_`; añadir además la fila `campo_sigchos` (patrón `CAMPO_SIGCHOS/*`, `rol = test_campo`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: utilidades que usan todas las historias

**⚠️ CRITICAL**: ninguna historia empieza sin esta fase

- [X] T006 [P] Implementar `src/avocadoia_datos/clases.py`: códigos `sano`, `antracnosis`, `pedunculo`; mapa a carpetas `AGUACATESANOS`, `ANTRACNOSIS`, `PEDUNCULO`; nombre largo "Síntomas compatibles con anillado del pedúnculo"; extensiones válidas `.jpg .jpeg .png`
- [X] T007 [P] Implementar `src/avocadoia_datos/es_csv.py`: lectura y escritura CSV deterministas (UTF-8 sin BOM, fin de línea LF, columnas fijas, orden explícito) y `sha256_archivo()`
- [X] T008 Implementar `src/avocadoia_datos/config.py`:
  - cargar `dataset.toml` con `tomllib` y `fuentes.csv`;
  - validar que las proporciones suman 1, que cada fuente con cuota existe en `fuentes.csv` y que los enums `uso_academico` (`si/no/pendiente`), `particion_origen` (`si/no`), `regla_grupo` (`ninguna/hass`) y `rol` (`general/test_campo`) tienen valores válidos;
  - exponer `version_config` (SHA-256 de ambos archivos) y `fuente_de(ruta)` (la primera coincidencia de patrón gana).
- [X] T009 Crear `tests/conftest.py` con una fábrica de árboles `Modelo/` sintéticos: imágenes Pillow con contenido distinto por semilla, opción de duplicados exactos, rotación EXIF (orientación 6), modo RGBA, archivo corrupto, `desktop.ini`, nombres `hass_T10_d01_041_a_1_<hash>.jpg` y subcarpetas `DRIVE_PARTICIONES_ARTICULO/{train,val,test}`
- [X] T010 [P] Escribir `tests/unit/test_config.py`: carga válida, proporciones inválidas, cuota con fuente inexistente, enum inválido y resolución de `fuente_de()`
- [X] T011 Implementar `src/avocadoia_datos/cli.py` con argparse: opciones comunes `--config`, `--fuentes`, `--raiz-imagenes`, `--salida`; subcomandos del contrato y códigos de salida 0/1/2

**Checkpoint**: configuración cargada y validada; la CLI responde a `--help`

---

## Phase 3: User Story 1 - Inventario trazable y sin duplicados (Priority: P1) 🎯 MVP

**Goal**: `datos/manifiesto.csv` con una fila por archivo, con fuente, huella, dimensiones EXIF, grupo y estado

**Independent Test**: ejecutar `inventario` dos veces y verificar que el manifiesto tiene 4 626 filas, que es idéntico entre ejecuciones y que las fotos `hass_` del mismo fruto comparten grupo (quickstart §2)

### Tests for User Story 1

- [X] T012 [P] [US1] Escribir `tests/unit/test_inventario.py`:
  - una fila por archivo, con `desktop.ini` ignorado;
  - duplicado exacto marcado `duplicada` con `duplicado_de` = ruta canónica (la lexicográficamente menor);
  - mismo SHA en dos clases → `excluida_conflicto`;
  - archivo corrupto → `excluida_invalida`;
  - dimensiones con EXIF aplicado (una imagen 200×100 con orientación 6 reporta 100×200);
  - `particion_origen` leída de la ruta;
  - salida idéntica en dos ejecuciones;
  - los originales conservan su SHA-256 y su fecha de modificación.
- [X] T013 [P] [US1] Escribir `tests/unit/test_grupos.py`:
  - `hass_T10_d01_041_a_*` y `hass_T10_d05_041_b_*` → grupo `hass:T10:041`;
  - `hass_T20_d01_041_*` en otro grupo;
  - unión con un grupo de `casi_duplicados_confirmados.csv`, transitiva (union-find);
  - una imagen sin regla queda en un grupo igual a su `id_contenido`.

### Implementation for User Story 1

- [X] T014 [US1] Implementar `src/avocadoia_datos/grupos.py`: regla `hass` (regex `hass_(T\w+?)_d\d+_(\d+)_`), carga de `datos/curacion/casi_duplicados_confirmados.csv` y union-find determinista (el representante es el identificador menor)
- [X] T015 [US1] Implementar `src/avocadoia_datos/inventario.py`:
  - recorrer las tres carpetas de clase;
  - calcular SHA-256, `id_contenido` (16 hex), ancho y alto tras `ImageOps.exif_transpose`, formato y modo;
  - asignar fuente, licencia, `uso_academico` y partición de origen;
  - asignar canónica y duplicados, excluir conflictos e inválidas, y aplicar el grupo;
  - aplicar la última decisión de `datos/validacion/decisiones.csv`, si existe;
  - calcular el `estado` según la máquina de estados de data-model.md;
  - escribir `datos/manifiesto.csv` ordenado por `ruta`, sin marcas de fecha (determinista), conservando `en_muestra` del manifiesto previo;
  - escribir los metadatos (`generado`, `semilla`, `version_config`, totales) en `datos/manifiesto.json`.
- [X] T016 [US1] Conectar el subcomando `inventario` en `src/avocadoia_datos/cli.py`, con un resumen en stdout por estado, clase, fuente y número de grupos

**Checkpoint**: manifiesto real generado y reproducible

---

## Phase 4: User Story 3 - Muestra por fuente y partición reproducible (Priority: P3)

**Goal**: muestra de 1 000 / 1 000 / 284 por cuotas de fuente y partición 70/15/15 por grupos, en `datos/particion.csv` y `datos/particion.json`

**Independent Test**: particionar dos veces con semilla 42 y obtener el mismo resultado, sin grupos repartidos, con cuotas cumplidas y ±1 pp por clase (quickstart §3)

### Tests for User Story 3

- [X] T017 [P] [US3] Escribir `tests/unit/test_muestra.py`:
  - cada fuente aporta como máximo su cuota;
  - una fuente con menos imágenes que su cuota entra completa y el faltante se informa;
  - primero una imagen por grupo, luego segundas fotos;
  - las fuentes con partición de origen entran completas;
  - el resto queda como reserva;
  - si una imagen pasa a `rechazada`, se repone desde la reserva de la misma fuente y las demás no cambian;
  - las excluidas, duplicadas, rechazadas y `test_campo` nunca entran.
- [X] T018 [P] [US3] Escribir `tests/unit/test_particion.py`:
  - la misma semilla da el mismo CSV y otra semilla da uno distinto;
  - el orden de entrada no afecta al resultado;
  - ningún `id_contenido` ni `grupo` en dos particiones;
  - las asignaciones de origen se conservan;
  - el caso pedúnculo (182/36/37 fijas + 29 libres) da 199/43/42;
  - ±1 pp por clase con 20 imágenes o más;
  - `--definitiva` falla con código 2 si hay `provisional`;
  - `test_campo` va a su propia partición.

### Implementation for User Story 3

- [X] T019 [US3] Implementar `src/avocadoia_datos/muestra.py`: selección por cuotas según research D6. Se ordena por `grupo`, se baraja con `random.Random(semilla)`, se toma primero una imagen por grupo y se devuelve el conjunto en muestra, los faltantes de cuota y el tamaño de la reserva por clase y fuente
- [X] T020 [US3] Implementar `src/avocadoia_datos/particion.py` según research D7:
  1. cuotas 70/15/15 por clase (mayor resto) y asignaciones de origen;
  2. déficit repartido entre fuentes libres por mayor resto;
  3. grupos barajados asignados a la partición con mayor déficit relativo, sin dividir grupos;
  4. estado `provisional`/`definitiva`.
- [X] T021 [US3] Implementar la escritura de `datos/particion.csv` (columnas `id_contenido,clase,fuente,grupo,particion,origen_asignacion,ruta`, ordenado por `particion`, `clase` e `id_contenido`) y `datos/particion.json` (`estado`, `semilla`, `proporciones`, `max_por_clase`, `cuotas`, `generado`, `version_config`, `conteos`, `faltantes_cuota`, `huella_particion`), y actualizar `en_muestra` en el manifiesto, en `src/avocadoia_datos/particion.py`
- [X] T022 [US3] Conectar el subcomando `particionar` (`--semilla`, `--definitiva`) en `src/avocadoia_datos/cli.py`, con una tabla de clase × partición, los faltantes y la reserva en stdout

**Checkpoint**: partición provisional real con los conteos previstos

---

## Phase 5: User Story 4 - Preprocesamiento e informe del conjunto (Priority: P4)

**Goal**: `Modelo/PROCESADO/<particion>/<clase>/<id_contenido>.jpg` en 224 × 224 RGB, más `datos/informe.md` y `datos/informe.json`

**Independent Test**: preprocesar y comprobar que solo hay JPEG RGB de 224 × 224 con los conteos de la partición, y que el informe cuadra con el manifiesto (quickstart §5)

### Tests for User Story 4

- [X] T023 [P] [US4] Escribir `tests/unit/test_preprocesamiento.py`:
  - salida 224×224 RGB JPEG;
  - una imagen con orientación EXIF 6 sale rotada;
  - RGBA compuesto sobre blanco;
  - el original queda intacto (mismo SHA y misma fecha de modificación);
  - se omite lo ya procesado y `--forzar` regenera;
  - se borran los archivos que ya no están en la partición;
  - advertencias `pequena`, `aspecto`, `oscura` y `borrosa`.
- [X] T024 [P] [US4] Escribir `tests/unit/test_informe.py`: los conteos cuadran con la partición, los pesos de clase siguen `N/(K·n_c)`, hay razón de desbalance, la tabla de aumento sale de la configuración y se declara el estado

### Implementation for User Story 4

- [X] T025 [US4] Implementar `src/avocadoia_datos/preprocesamiento.py` según research D9: EXIF, RGB, LANCZOS a 224, JPEG calidad 95, limpieza de sobrantes, y advertencias por brillo medio < 40 y varianza del laplaciano < 50 escritas en `datos/advertencias.csv`
- [X] T026 [US4] Implementar `src/avocadoia_datos/informe.py`:
  - tablas de clase × partición y de clase × fuente;
  - exclusiones por motivo, reserva, faltantes y advertencias;
  - desbalance y pesos de clase;
  - parámetros de aumento, estado y decisiones pendientes o ausentes;
  - salida en `datos/informe.md` y `datos/informe.json`.
- [X] T027 [US4] Conectar los subcomandos `preprocesar` (`--destino`, `--forzar`), `informe` y `todo` en `src/avocadoia_datos/cli.py`
- [X] T028 [US4] Escribir `tests/integration/test_cli_todo.py`: `todo` sobre un árbol sintético produce el manifiesto, la partición, `PROCESADO/` y el informe coherentes entre sí

**Checkpoint**: 🎯 conjunto de datos listo para OE3 en `Modelo/PROCESADO/`

---

## Phase 6: User Story 2 - Registro de validación por el experto (Priority: P2)

**Goal**: planillas xlsx para el experto y su incorporación a `datos/validacion/decisiones.csv`

**Independent Test**: generar la planilla, completar una copia con decisiones válidas e inválidas, incorporarla y verificar el manifiesto y la reposición desde la reserva (quickstart §4)

### Tests for User Story 2

- [X] T029 [P] [US2] Escribir `tests/unit/test_validacion.py`:
  - la planilla contiene solo imágenes de la muestra `pendiente`, en lotes;
  - los hipervínculos apuntan a rutas existentes;
  - las listas desplegables son `decision` (`aceptada/rechazada/reasignada/mixto`), `clase_nueva`, `objeto` (`fruto_completo/pedunculo_primer_plano/varios_frutos/no_es_fruto`), `toma` (`campo/laboratorio/sin_fondo`) y `calidad` (`buena/aceptable/mala`);
  - la incorporación acepta filas válidas, ignora las vacías y reporta las inválidas con su número de fila;
  - ante decisiones repetidas, vale la más reciente.

### Implementation for User Story 2

- [X] T030 [US2] Implementar `generar_planilla()` en `src/avocadoia_datos/validacion.py` con openpyxl: columnas según research D12, hipervínculo relativo a la imagen, validaciones de datos y lotes de `planilla.lote`
- [X] T031 [US2] Implementar `incorporar()` en `src/avocadoia_datos/validacion.py`: validar cada fila, añadirla a `datos/validacion/decisiones.csv` sin sobrescribir lo anterior y reejecutar el inventario
- [X] T032 [US2] Conectar los subcomandos `planilla` (`--clase`, `--lote`, `--incluir-reserva`) e `incorporar` en `src/avocadoia_datos/cli.py`

**Checkpoint**: ciclo completo con el experto

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T033 Ejecutar `python -m avocadoia_datos todo` sobre las imágenes reales y versionar `datos/manifiesto.csv`, `datos/particion.csv`, `datos/particion.json`, `datos/informe.md`, `datos/informe.json` y `datos/advertencias.csv`
- [X] T034 [P] Revisar visualmente una hoja de contactos de `Modelo/PROCESADO/` (orientación, recorte, color) y anotar el resultado en `datos/README.md` (el informe se regenera)
- [X] T035 [P] Escribir `datos/README.md`: cómo regenerar el conjunto, qué carpeta usa cada fase de la tesis (train, val y test en `PROCESADO/`) y qué se versiona
- [X] T036 Ejecutar la validación de `specs/001-pipeline-dataset/quickstart.md` (§1–§3, §5–§6), medir los tiempos de `inventario` (objetivo < 5 min) y `preprocesar` (objetivo < 10 min) y registrar los resultados
- [X] T038 [US1] Revisión 3: generar `datos/curacion/exclusiones_revision.csv` con `scripts/curacion/marcar_exclusiones.py` (avocare_ completa + Kaggle con ≤ 0.5 % de manchas) y leerla en `src/avocadoia_datos/inventario.py` como estado `excluida_revision`, con prueba en `tests/unit/test_inventario.py`
- [X] T039 [US1] Revisión 3: agrupar vistas del mismo fruto con `scripts/curacion/agrupar_similares.py` → `datos/curacion/grupos_similitud.csv`, unirlas en `src/avocadoia_datos/inventario.py`, con prueba en `tests/unit/test_grupos.py`
- [X] T040 Revisión 3: nuevas cuotas en `config/dataset.toml`, regenerar con `python -m avocadoia_datos todo` y verificar 0 pares casi idénticos entre conjuntos
- [ ] T037 Documentar origen, referencia y licencia de cada fuente en `config/fuentes.csv` (requiere información del equipo); sin esto la partición no puede marcarse `definitiva`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Fase 1)** → **Foundational (Fase 2)** → **US1 (Fase 3)** → **US3 (Fase 4)** → **US4 (Fase 5)** → **US2 (Fase 6)** → **Polish (Fase 7)**

### User Story Dependencies

- **US1**: solo depende de Foundational.
- **US3**: necesita el manifiesto (US1).
- **US4**: necesita la partición (US3).
- **US2**: necesita la muestra (US3) para saber qué validar. Su resultado realimenta US1 y US3, por
  ejemplo con rechazos que se reponen desde la reserva.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar antes de implementar.
- El orden es lógica del módulo → escritura de archivos → subcomando de la CLI.

### Parallel Opportunities

- T002–T005 en paralelo.
- T006, T007 y T010 en paralelo.
- Dentro de cada historia, las pruebas marcadas [P] en paralelo.
- T034 y T035 en paralelo.

## Parallel Example: User Story 3

```text
T017 tests/unit/test_muestra.py      ┐ en paralelo
T018 tests/unit/test_particion.py    ┘
T019 muestra.py → T020/T021 particion.py → T022 cli
```

## Implementation Strategy

1. **MVP del conjunto de datos** (Fases 1–5): al terminar US4 existe `Modelo/PROCESADO/` con la
   partición provisional y OE3 puede empezar a entrenar.
2. **Ciclo con el experto** (Fase 6): las planillas se entregan al agrónomo; sus decisiones
   actualizan la muestra sin rehacer el resto.
3. **Congelamiento**: cuando todas las imágenes de la muestra estén aceptadas y con licencia, se
   ejecuta `particionar --definitiva` y se versiona la partición final para toda la tesis.
