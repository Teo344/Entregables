---
name: speckit-metricas-exportar
description: Empaquetar el dataset del proyecto para compartirlo y consolidarlo
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: georaura
  source: metricas:commands/speckit.metricas.exportar.md
---

# Exportar dataset

Ejecuta la recoleccion y genera `metricas/salidas/dataset-<proyecto>-<fecha>.zip`, listo para
consolidarse con los de otros proyectos.

## Entrada del usuario

```text
$ARGUMENTS
```

## Ejecucion

Pregunte si desea anonimizar (recomendado si el dataset sale de la organizacion): reemplaza el
nombre del desarrollador por un hash y elimina las columnas de texto libre.

- **Windows**: `powershell -NoProfile -ExecutionPolicy Bypass -File .specify/extensions/metricas/scripts/powershell/exportar.ps1 [-Anonimizar]`
- **Linux/macOS**: `pwsh -NoProfile -File .specify/extensions/metricas/scripts/powershell/exportar.ps1 [-Anonimizar]`

Informe la ruta del archivo generado.