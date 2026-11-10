# Prueba de campo · corrida 20261109-2246_mobilenetv3_s42_6691b967

**Fecha**: 2026-11-10 · **Fotos**: 40 propias (iPhone 14, Sigchos, 2026-11-06), clase *síntomas compatibles con anillado
del pedúnculo*, validación del agrónomo pendiente · **Confianza**: calibrada (T = 0,763), umbral 0,60.

| Métrica | Prueba interna (208 fotos del split v4) | Prueba de campo (40 fotos propias) |
| --- | --- | --- |
| Sensibilidad para anillado del pedúnculo | 100 % (31/31) | **0 % (0/40)** |
| Predicción mayoritaria | — | **Sano en 40/40** |
| Confianza media | ≈ 0,99 | **0,94** (39/40 por encima del umbral) |

## Interpretación

1. **Fallo sistemático y confiado**: el modelo clasifica todas las fotos de campo como sanas con confianza alta. La
   calibración no lo evita: Temperature Scaling corrige la confianza dentro de la distribución de entrenamiento, no
   fuera de ella.
2. **Grad-CAM++** muestra el foco sobre el **cuerpo del fruto** (piel oscura y rugosa), **no sobre el pedúnculo**.
3. **Por qué "sano"**: en el entrenamiento la clase sano son sobre todo frutos Hass maduros (oscuros y rugosos, fuente
   `hass`), y la clase pedúnculo son solo primeros planos del tallo del artículo de Flores et al. (2026). El modelo
   aprendió «fruto oscuro y rugoso = sano» y «tallo de cerca = anillado», no el síntoma.
4. Confirma con datos independientes el atajo sugerido por Grad-CAM++ en la prueba interna y por el EDA (las fotos de
   campo difieren en fondo 0 % uniforme frente a 64 %, brillo, saturación y encuadre).

## Consecuencias

- El 100 % interno no es reportable como desempeño; la prueba de campo es la evidencia principal.
- Correcciones: devolver los pedúnculos sanos del artículo (`mdpi_pedunculo_sano`, 340) a la clase sano; incluir fotos
  de campo de ambas condiciones (T063); considerar recorte o región de interés del pedúnculo (como Flores et al., 2026);
  repetir esta prueba tras reentrenar.
