# Quickstart: validar el pipeline del conjunto de datos

**Feature**: `001-pipeline-dataset` (revisión 2)

Guía para comprobar de punta a punta que la funcionalidad cumple la spec. Para los detalles, ver
[contracts/cli.md](contracts/cli.md) y [data-model.md](data-model.md).

## Prerrequisitos

- Python ≥ 3.11 y las imágenes curadas en `Modelo/` (no vienen con el repositorio; ver
  `datos/curacion/README.md`).
- Desde la raíz de `Entregables`:

  ```powershell
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  pip install -e ".[dev]"
  ```

## 1. Pruebas automatizadas

```powershell
pytest
```

Esperado: todas las pruebas pasan. Usan imágenes sintéticas en una carpeta temporal y cubren:
- deduplicación, conflictos, rotación EXIF y grupos (`hass_` y casi duplicados);
- muestra por cuotas, reserva y reposición;
- reproducibilidad de la muestra y de la partición;
- ausencia de fugas por contenido y por grupo, y cuotas ±1 pp;
- incorporación de planillas con filas inválidas;
- preprocesamiento.

## 2. Inventario (US1)

```powershell
python -m avocadoia_datos inventario
python -m avocadoia_datos inventario   # segunda vez
git diff --stat datos/manifiesto.csv
```

Esperado:
- `datos/manifiesto.csv` tiene 4 626 filas: sano 2 473, antracnosis 1 869 y pedúnculo 284.
- La segunda ejecución no cambia nada (`git diff` vacío).
- Todas las fotos `hass_T10_dNN_041_*` comparten el grupo `hass:T10:041`.
- Las rutas de `casi_duplicados_confirmados.csv` que siguen en las carpetas comparten grupo.
- Ningún archivo bajo `Modelo/` cambió de fecha de modificación (SC-001).

## 3. Muestra y partición (US3)

```powershell
python -m avocadoia_datos particionar
Copy-Item datos/particion.csv $env:TEMP/p1.csv
python -m avocadoia_datos particionar
Compare-Object (Get-Content $env:TEMP/p1.csv) (Get-Content datos/particion.csv)
```

Esperado:
- La comparación sale vacía (SC-003).
- `particion.json` muestra `estado: provisional` y conteos aproximados de:

  | Clase | Train | Val | Test |
  |---|---:|---:|---:|
  | Sano | 700 | 150 | 150 |
  | Antracnosis | 700 | 150 | 150 |
  | Pedúnculo | 199 | 43 | 42 |

  Cada clase cae dentro de ±1 pp del 70/15/15 (SC-004).
- Cada fuente aporta su cuota (p. ej., Kaggle 450 en antracnosis y `hass_` 280 en sano, una foto por
  fruto).
- Las imágenes de los artículos MDPI conservan su partición de origen.
- Ningún `grupo` aparece en dos particiones (SC-002).

## 4. Validación del experto (US2)

```powershell
python -m avocadoia_datos planilla --clase pedunculo
```

1. Abrir `datos/validacion/planilla_pedunculo_01.xlsx` en Excel y comprobar que el hipervínculo
   abre la foto y que las columnas `decision`, `objeto`, `toma` y `calidad` tienen listas
   desplegables.
2. En una copia, completar el validador y la fecha y marcar:
   - 3 filas como `aceptada`;
   - 1 como `rechazada`;
   - 1 como `reasignada` → `antracnosis`;
   - 1 fila con una decisión inventada.
3. Incorporar la planilla y volver a particionar:

   ```powershell
   python -m avocadoia_datos incorporar datos/validacion/planilla_pedunculo_01.xlsx
   python -m avocadoia_datos particionar
   ```

Esperado:
- `incorporar` informa 5 filas incorporadas y 1 inválida, con su número de fila.
- La rechazada sale de la muestra.
- La reasignada pasa a antracnosis.
- La muestra de cada clase se repone desde la reserva; las demás asignaciones no cambian.

Revertir `decisiones.csv` al terminar la prueba.

```powershell
python -m avocadoia_datos particionar --definitiva   # mientras falte validación
```

Esperado: termina con código 2 e indica cuántas imágenes faltan por validar o por licencia.

## 5. Preprocesamiento e informe (US4)

```powershell
python -m avocadoia_datos preprocesar
python -m avocadoia_datos informe
```

Esperado:
- `Modelo/PROCESADO/{train,val,test}/{sano,antracnosis,pedunculo}/` contiene solo JPEG RGB de
  224 × 224, con los conteos de la partición (2 284 en total).
- Las fotos con rotación EXIF aparecen derechas.
- `datos/informe.md` muestra:
  - las tablas de clase × partición y de clase × fuente;
  - las exclusiones, la reserva y las advertencias;
  - la razón de desbalance (≈ 3.5) y los pesos de clase;
  - los parámetros de aumento y el estado provisional.
- Los totales del informe cuadran con `manifiesto.csv` y `particion.csv` (SC-007).

## 6. Regeneración completa (SC-006)

En un clon limpio con las mismas imágenes curadas, `python -m avocadoia_datos todo` reproduce
`manifiesto.csv`, `particion.csv` e `informe.json`. Solo cambian las fechas de generación.
