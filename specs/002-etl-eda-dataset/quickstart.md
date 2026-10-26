# Quickstart: Proceso ETL y EDA del conjunto de datos

**Feature**: [spec.md](spec.md) | **Contrato**: [contracts/cli.md](contracts/cli.md) | **Datos**: [data-model.md](data-model.md)

## Prerrequisitos

- Las imágenes de 001 están en `Modelo/AGUACATESANOS`, `Modelo/ANTRACNOSIS` y `Modelo/PEDUNCULO`.
- Python 3.12 está instalado (`py -3.12 --version`).
- Para el Word: pandoc instalado (ya está en anaconda).

## 1. Crear el entorno de análisis (una sola vez)

```powershell
py -3.12 -m venv .venv-ml
.venv-ml\Scripts\python -m pip install -e ".[dev,eda]"
.venv-ml\Scripts\python -c "import tensorflow as tf; print(tf.__version__)"   # 2.20.0
```

La primera vez que se ejecuta `etl-representaciones`, se descargan los pesos de EfficientNet-B0 (21 MB). Desde entonces todo funciona sin conexión.

## 2. Pruebas

```powershell
.venv-ml\Scripts\python -m pytest -q             # todas, incluida la marca ml
.venv\Scripts\python -m pytest -q -m "not ml"    # el entorno de 001 sigue pasando sin TensorFlow
```

## 3. Cadena automática

```powershell
.venv-ml\Scripts\python -m avocadoia_datos etl-eda
```

Lo que se espera:
- **Manifiesto**:
  - las 214 descargas de `sano_web` quedan en `excluida_licencia`;
  - las 17 fotos de `herrera_marin` quedan como candidatas.
- **Muestra**: sano = 360 MDPI + 83 RGB + 17 Herrera y Marín + 540 Hass = 1 000.
- **Sospechas**: `datos/etl/sospechas.csv` contiene todas las candidatas. Las marcadas `a_revisar` son al menos el 10 % de cada clase.
- **Embudo**: `datos/etl/embudo.csv` cuadra por clase × fuente; si no, `informe-etl-eda` falla.
- **Sondas**: `datos/eda/tablas/sondas.csv` declara `conjuntos = train+val` en todas las filas.

## 4. Revisión manual (autores)

```powershell
.venv-ml\Scripts\python -m avocadoia_datos etl-revision --tipo sospecha
# completar las planillas en datos/revision/ (decision, revisor, fecha)
.venv-ml\Scripts\python -m avocadoia_datos etl-incorporar datos/revision/revision_sospecha_*.xlsx
.venv-ml\Scripts\python -m avocadoia_datos etl-eda
```

Para validar:
- **Exclusión**: una imagen marcada `excluir` pasa a `excluida_revision`. Su archivo original sigue en su carpeta.
- **Alcance de grupo**: con `alcance = grupo`, todas las vistas del mismo fruto cambian juntas.
- **Reemplazo**: la cuota de la clase se vuelve a cubrir desde la reserva.
- **Comparación**: `datos/etl/comparacion_001.csv` muestra la imagen como `sale`.

## 5. Auditoría (SC-003)

```powershell
.venv-ml\Scripts\python -m avocadoia_datos etl-auditoria --n 100
# revisar datos/revision/auditoria_01.xlsx
.venv-ml\Scripts\python -m avocadoia_datos etl-incorporar datos/revision/auditoria_01.xlsx
.venv-ml\Scripts\python -m avocadoia_datos informe-etl-eda
```

El informe muestra la tasa de error de la auditoría con su intervalo de Wilson al 95 %. El criterio es 2 errores o menos en 100.

## 6. Reproducibilidad (SC-006)

Ejecutar `etl-eda` dos veces y comparar:

```powershell
git diff --stat datos/etl datos/eda/tablas datos/eda/informe_etl_eda.json   # sin cambios
```

## 7. Informe Word

```powershell
scripts\informe\generar_word.ps1 -Fecha 2026-10-27
```

Escribe `DocumentosFInales\Informe_Fase2_ETL_EDA_AvocadoIA_2026-10-27.docx`. Si ese archivo ya existe, se detiene sin sobrescribirlo.

## Validación contra la especificación

| Criterio | Dónde se verifica |
| --- | --- |
| SC-001 | `embudo.csv` y la precondición de `informe-etl-eda` |
| SC-002 | Sección "Revisión" del informe: marcadas = decididas |
| SC-003 | Sección "Auditoría": errores ≤ 2 / 100 |
| SC-004 | Informe de 001 (fugas = 0) y sección "Carga" |
| SC-005 | `sondas.csv` y sección "Sesgos y atajos" |
| SC-006 | Paso 6 |
| SC-007 | `informe_etl_eda.json` → cada conclusión tiene evidencia |
