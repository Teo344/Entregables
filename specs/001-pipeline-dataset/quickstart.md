# Quickstart: validar el pipeline del conjunto de datos

**Feature**: `001-pipeline-dataset`

Guía para comprobar, de principio a fin, que la funcionalidad cumple la spec. Los detalles están en
[contracts/cli.md](contracts/cli.md) y [data-model.md](data-model.md).

## Prerrequisitos

- Python ≥ 3.11 y las imágenes en `Modelo/` (no vienen con el repositorio).
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

Esperado: todas pasan. Las pruebas usan imágenes sintéticas en una carpeta temporal y cubren la
deduplicación, los conflictos, la exclusión de Scab, la reproducibilidad de la partición, la
ausencia de fugas, las cuotas ±1 pp, la incorporación de planillas con filas inválidas y el
preprocesamiento.

## 2. Inventario (US1)

```powershell
python -m avocadoia_datos inventario
python -m avocadoia_datos inventario   # segunda vez
git diff --stat datos/manifiesto.csv
```

Esperado:
- `datos/manifiesto.csv` tiene una fila por archivo de imagen.
- La segunda ejecución no cambia nada (`git diff` vacío).
- El contenido `b29d286c3fd4…` no aparece; quedó fuera en la organización previa de pedúnculo.
- Las filas Kaggle "Scab" figuran como `excluida_fuera_de_alcance`.
- Ningún archivo bajo `Modelo/` cambió de fecha de modificación (SC-001).

## 3. Validación del experto (US2)

```powershell
python -m avocadoia_datos planilla --clase pedunculo
```

1. Abrir `datos/validacion/planilla_pedunculo_01.xlsx` en Excel y comprobar que el hipervínculo
   abre la foto.
2. En una copia, marcar 3 filas como `aceptada`, 1 como `rechazada` y 1 como `reasignada` →
   `antracnosis`, completando el validador y la fecha. Dejar una fila con una decisión inventada.
3. Incorporar la planilla:

   ```powershell
   python -m avocadoia_datos incorporar datos/validacion/planilla_pedunculo_01.xlsx
   ```

Esperado: 5 filas incorporadas y 1 inválida informada con su número de fila. En el manifiesto, la
imagen rechazada queda `rechazada` y la reasignada tiene `clase_efectiva = antracnosis`. Revertir
`decisiones.csv` al terminar la prueba.

## 4. Partición (US3)

```powershell
python -m avocadoia_datos particionar
Copy-Item datos/particion.csv $env:TEMP/p1.csv
python -m avocadoia_datos particionar
Compare-Object (Get-Content $env:TEMP/p1.csv) (Get-Content datos/particion.csv)
python -m avocadoia_datos particionar --definitiva   # mientras falte validación
```

Esperado:
- La comparación sale vacía (SC-003).
- `particion.json` muestra `estado: provisional` y conteos 70/15/15 ±1 pp por clase (SC-004).
- Las imágenes de pedúnculo con partición de origen la conservan.
- `--definitiva` termina con código 2 e indica cuántas imágenes faltan por validar.

## 5. Preprocesamiento e informe (US4)

```powershell
python -m avocadoia_datos preprocesar
python -m avocadoia_datos informe
```

Esperado:
- `Modelo/PROCESADO/{train,val,test}/{sano,antracnosis,pedunculo}/` contiene solo imágenes
  JPEG RGB de 224 × 224.
- `datos/informe.md` muestra las tablas de clase × partición y de clase × fuente, las exclusiones,
  la razón de desbalance, los pesos de clase, los parámetros de aumento y el estado provisional.
- Los totales del informe cuadran con `manifiesto.csv` y `particion.csv` (SC-007).

## 6. Regeneración completa (SC-006)

En un clon limpio con las mismas imágenes, `python -m avocadoia_datos todo` reproduce
`manifiesto.csv`, `particion.csv` e `informe.json`; solo cambian las fechas de generación.
