# Contrato del CLI: subcomandos de ETL y EDA

Extiende [001/contracts/cli.md](../../001-pipeline-dataset/contracts/cli.md). Todos los subcomandos aceptan las opciones comunes de 001 (`--config`, `--fuentes`, `--raiz-imagenes`, `--salida`) y se ejecutan con:

```text
.venv-ml/Scripts/python -m avocadoia_datos <subcomando> [opciones]
```

Los subcomandos de 001 (`inventario`, `particionar`, `planilla`, `incorporar`, `preprocesar`, `informe`, `todo`) no cambian su interfaz.

Los subcomandos marcados con **(ML)** requieren TensorFlow. Si se ejecutan sin él, terminan con el código 3 y el mensaje "Este subcomando requiere el entorno .venv-ml (TensorFlow)".

## Códigos de salida

Los mismos de 001: 0 éxito, 1 error de configuración, 2 precondición no cumplida, 3 dependencia ausente.

## Subcomandos

| Subcomando | Qué hace | Lee | Escribe |
| --- | --- | --- | --- |
| `etl-extraer` | Ejecuta `inventario` con las fuentes vigentes y, si no existe, guarda la partición de 001 como línea base | `config/`, `Modelo/`, `git show f43575e:datos/particion.csv` | `datos/manifiesto.*`, `datos/etl/particion_001.csv` |
| `etl-representaciones [--forzar]` **(ML)** | Vectores EfficientNet-B0 de todas las candidatas (normales y con el centro tapado), con caché; `--forzar` recalcula todo. Con `AVOCADOIA_SIN_RED=1` termina con el código 2 si los pesos no están en caché, en lugar de descargarlos (FR-023) | manifiesto, imágenes | `datos/eda/cache/representaciones.npz` |
| `etl-sospechas` | Probabilidades fuera de muestra, *confident learning* y vecinos, y marca `a_revisar` | caché, manifiesto | `datos/etl/sospechas.csv` |
| `etl-revision [--tipo sospecha\|sistematica] [--clase C] [--lote N]` | Planillas xlsx con miniaturas: las marcadas `a_revisar` o, con `sistematica`, un recorrido completo por clase | sospechas, manifiesto | `datos/revision/revision_<tipo>_<clase>_<NN>.xlsx` |
| `etl-auditoria [--n 100]` | Planilla de auditoría al azar, estratificada por clase, sobre el conjunto final | partición | `datos/revision/auditoria_01.xlsx` |
| `etl-incorporar <planillas...>` | Valida las filas y las agrega a `revision_etiquetas.csv`; informa filas inválidas sin abortar | planillas | `datos/curacion/revision_etiquetas.csv` |
| `eda` **(ML para t-SNE si falta caché)** | Características, distribuciones, sondas, t-SNE, mosaicos y figuras | manifiesto, partición, caché, imágenes | `datos/eda/tablas/*.csv`, `datos/eda/figuras/*.{png,svg}` |
| `etl-embudo` | Embudo de calidad y comparación con 001 | manifiesto, partición, `particion_001.csv` | `datos/etl/embudo.csv`, `datos/etl/comparacion_001.csv` |
| `informe-etl-eda` | Informe con las fases Extracción → Transformación → Carga → EDA y las conclusiones | todo lo anterior | `datos/eda/informe_etl_eda.md`, `.json` |
| `etl-eda` | Cadena sin pasos manuales: `etl-extraer` → `etl-representaciones` → `etl-sospechas` → `todo` → `eda` → `etl-embudo` → `informe-etl-eda` | — | — |

## Reglas de comportamiento

- **`etl-sospechas` sin caché** termina con el código 2 y el mensaje "Ejecute antes etl-representaciones".
- **Planilla con errores en `etl-incorporar`**: las filas inválidas se listan con su número de fila y motivo, y las demás se incorporan, igual que `incorporar` de 001. Las columnas `decision`, `revisor` y `fecha` son obligatorias en cada fila con decisión.
- **Precondición de `informe-etl-eda`**: falla con el código 2 si existe una planilla de auditoría sin incorporar o si `embudo.csv` no cuadra (la suma de los pasos es distinta de `inventariadas`).
- **Prueba en las sondas**: `eda` nunca usa imágenes de `test` en las sondas. Las tablas descriptivas sí incluyen `test` en su composición.
- **Resumen en consola**: cada subcomando imprime totales por clase y la ruta de lo que escribió.
- **Word**: no lo genera el CLI, sino `scripts/informe/generar_word.ps1 -Fecha AAAA-MM-DD`, que escribe `DocumentosFInales/Informe_Fase2_ETL_EDA_AvocadoIA_<fecha>.docx`. Si el archivo ya existe, termina con error en lugar de sobrescribir.
