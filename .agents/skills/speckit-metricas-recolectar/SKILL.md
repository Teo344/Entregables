---
name: speckit-metricas-recolectar
description: Calcular tamano, duracion, esfuerzo, costo y desperdicio por funcionalidad
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: georaura
  source: metricas:commands/speckit.metricas.recolectar.md
---

# Recolectar metricas

Genera `metricas/salidas/resumen-funcionalidades.csv` y `metricas/salidas/resumen-proyecto.csv`
a partir de las especificaciones, el historial de Git y el registro de sesiones.

## Ejecucion

- **Windows**: `powershell -NoProfile -ExecutionPolicy Bypass -File .specify/extensions/metricas/scripts/powershell/recolectar.ps1`
- **Linux/macOS**: `pwsh -NoProfile -File .specify/extensions/metricas/scripts/powershell/recolectar.ps1`

## Despues de ejecutar

Resuma para el usuario: esfuerzo total (horas y persona-mes), duracion, costo, lineas
entregadas, tasa de desperdicio por causa y los modelos de IA usados. Si el script advierte
sesiones sin horas o eliminaciones sin clasificar, pida completarlas.