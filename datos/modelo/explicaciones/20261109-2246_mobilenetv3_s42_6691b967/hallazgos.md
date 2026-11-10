# Hallazgos de explicabilidad · corrida 20261109-2246_mobilenetv3_s42_6691b967

**Revisor**: Mateo Criollo · **Fecha de valoración**: 2026-11-09 · **Método**: Grad-CAM++ sobre 30 aciertos de prueba
(10 por clase; no hubo errores en prueba). Confianza sin calibrar (T = 1).

| Clase | Valoradas | Lesión/fruto | Fondo/ajeno | Ambiguo | SC-005 (≥ 80 %) |
| --- | --- | --- | --- | --- | --- |
| Sano | 10 | 70 % | **30 %** | 0 % | ❌ posible atajo |
| Antracnosis | 10 | 80 % | 10 % | 10 % | ✅ (en el límite) |
| Síntomas compatibles con anillado del pedúnculo | 10 | 90 % | 10 % | 0 % | ✅ |

## Observaciones para la revisión del dataset

1. **Atajo por fondo en `rgb_sano`**: las 2 imágenes de esa fuente en la muestra (fruto verde sobre mesa de granito,
   confianzas 0,99 y 0,94) se clasifican como sano con el foco en el fondo. Son las únicas fotos sanas con ese fondo:
   el modelo asocia el granito a la clase. El revisor anota que los frutos presentan manchas negras que no
   corresponden a enfermedad.
2. **`hass`**: 1 caso con foco fuera del fruto; el fruto es sano con coloración café por madurez.
3. **`rgb_antracnosis`**: 1 caso con foco en el fondo (confianza 0,999) y 1 ambiguo (foco cerca del borde superior).
4. **`mdpi_pedunculo`**: 1 caso marca una zona inferior ajena al síntoma, aunque el síntoma es visible en la parte
   superior.
5. Cada clase procede de fuentes con estilo fotográfico propio (fondo, encuadre, iluminación); el pedúnculo son solo
   primeros planos de una fuente. El 100 % en prueba no se interpreta como desempeño en campo.

## Acciones propuestas

- Prueba independiente con fotos de campo de Sigchos (`campo_sigchos`), mismas condiciones para las tres clases.
- Ampliar sano y antracnosis con fondos variados o recortar/segmentar el fruto; reevaluar con Grad-CAM++.
- Repetir esta valoración con el agrónomo y con el split corregido (T057).
