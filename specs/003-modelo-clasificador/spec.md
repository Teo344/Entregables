# Feature Specification: Construcción, calibración y exportación del modelo clasificador

**Feature Branch**: `003-modelo-clasificador`

**Created**: 2026-11-09

**Status**: Draft

**Input**: User description: "Construcción, entrenamiento, calibración y exportación del modelo clasificador de AvocadoIA (OE3). Clasificador de 3 clases por transferencia de aprendizaje, comparando MobileNetV3 vs EfficientNet-B0 en igualdad de condiciones, con el split experimental v4 del compañero como dataset de entrada; calibración con Temperature Scaling, umbral de 'no concluyente', Grad-CAM++, exportación a TensorFlow Lite y registro reproducible de experimentos."

## Contexto

> **Decisión vigente (2026-11-10): el dataset de entrada es el de la especificación 002** (`datos/particion.csv`,
> 2 188 imágenes, huella `096faf72`, imágenes a 224 × 224 en `Modelo/PROCESADO/`). El split v4 queda como
> **experimento descartado**: con él se desarrolló y depuró el flujo, pero tiene 412 imágenes sin licencia, 373 copias
> aumentadas, 89 frutos repartidos entre particiones y no incluye los pedúnculos sanos del artículo de Flores et al.
> (2026); su modelo obtuvo 100 % en la prueba interna y **0 de 40** en la prueba de campo (ver
> `datos/modelo/campo/<corrida>/hallazgos_campo.md`). La comparación de ambos conjuntos está en research M20. El
> texto siguiente describe la etapa con el v4 y se conserva como historial.

Las especificaciones 001 y 002 construyeron y depuraron el conjunto de datos. El equipo decidió adoptar como
entrada de esta fase el **split experimental v4** preparado por el compañero (2 211 imágenes: sano 1 000,
antracnosis 1 000, síntomas compatibles con anillado del pedúnculo 211; 70/15/15), con su manifiesto
`manifiesto_split.csv` e informes de verificación. Ese split tiene tres observaciones abiertas que el compañero
debe resolver antes de reportar métricas finales en la tesis (ver Supuestos): posible presencia de copias
aumentadas (`avocare`) y frutos con fotos en más de una partición.

**Licencias (principio II, no negociable)**: el split v4 incluye imágenes de fuentes sin licencia académica
confirmada según `config/fuentes.csv` (especificación 002): 412 de `sano_web` (`sano-*`, descargas de internet,
`uso_academico = no`) y 373 de `avocare` (licencia "no verificada", `uso_academico = pendiente`). Esas imágenes
**nunca** entran al entrenamiento, ni siquiera en modo experimental. Con el filtro, el v4 queda en 1 426 imágenes
(sano 392, antracnosis 823, pedúnculo 211; train 998 / val 220 / test 208).

**Actualización 2026-11-09**: la licencia de `avocare` se verificó (CC BY 4.0, `uso_academico = si`), pero su
versión 4 en Roboflow genera 3 variantes aumentadas por imagen original (2 488 desde 1 134). Por riesgo de fuga
entre particiones se excluye **por calidad** (`[datos].fuentes_excluidas` en `config/modelo.toml`, FR-027). El
conjunto de entrenamiento sigue en 1 426 imágenes.

Esta funcionalidad cubre el objetivo OE3: obtener un clasificador que funcione sin conexión en el teléfono, con
confianza calibrada y explicación visual, y documentar con evidencia reproducible por qué se eligió la
arquitectura final.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Entrenar un clasificador base de punta a punta (Priority: P1)

Los autores necesitan entrenar un primer clasificador de tres clases a partir del manifiesto del dataset y
obtener sus métricas en validación y prueba, para confirmar que todo el flujo (lectura de datos, entrenamiento,
evaluación, registro) funciona antes de invertir en comparaciones.

**Why this priority**: sin un flujo de punta a punta que funcione, ninguna otra historia puede ejecutarse; es el
MVP del modelo.

**Independent Test**: ejecutar un entrenamiento con una sola arquitectura y una semilla sobre el manifiesto v4 y
comprobar que se genera un registro con la configuración, las métricas por clase, la matriz de confusión y la
huella del manifiesto usado.

**Acceptance Scenarios**:

1. **Given** el manifiesto v4 y la carpeta raíz de imágenes, **When** se lanza un entrenamiento, **Then** el
   sistema verifica que todas las imágenes referenciadas existen y son legibles antes de empezar, y aborta con la
   lista de faltantes si alguna no lo es.
2. **Given** un entrenamiento terminado, **When** se consulta su registro, **Then** contiene la configuración
   completa, la semilla, la huella (SHA-256) del manifiesto, las métricas en validación y prueba, la matriz de
   confusión y la fecha.
3. **Given** el mismo manifiesto, configuración y semilla, **When** se repite el entrenamiento en el mismo
   entorno, **Then** las métricas obtenidas difieren a lo sumo en la variación propia del hardware (≤ 1 punto de
   macro-F1).
4. **Given** un manifiesto distinto con el mismo formato (por ejemplo, una versión corregida del split), **When**
   se indica ese manifiesto, **Then** el entrenamiento se ejecuta sin cambios en el código.

---

### User Story 2 - Comparar MobileNetV3 y EfficientNet-B0 en igualdad de condiciones (Priority: P1)

Los autores necesitan decidir qué arquitectura llevar al teléfono con una comparación justa: mismos datos,
particiones, épocas, callbacks, aumento y semillas, repetida con varias semillas para separar la diferencia real
del azar.

**Why this priority**: es la debilidad conocida de la tesis previa (comparación desigual) y el argumento central
para defender la elección del modelo (principio III).

**Independent Test**: ejecutar la comparación y verificar que ambas arquitecturas comparten exactamente la misma
configuración salvo el modelo base, y que la tabla final reporta media ± desviación por arquitectura.

**Acceptance Scenarios**:

1. **Given** las dos arquitecturas, **When** se ejecuta la comparación, **Then** cada una se entrena con las
   semillas 42, 43 y 44 usando idéntica configuración de datos, aumento, épocas, callbacks y desbalance.
2. **Given** las seis corridas terminadas, **When** se genera la tabla comparativa, **Then** muestra para cada
   arquitectura la media ± desviación de macro-F1, recall por clase, exactitud, tamaño del modelo y tiempo de
   entrenamiento.
3. **Given** la tabla comparativa, **When** se aplica la regla de selección, **Then** se elige la arquitectura con
   mayor macro-F1 medio en validación; si la diferencia es menor a 2 puntos, se elige la más liviana, y la decisión
   queda registrada con su justificación.

---

### User Story 3 - Calibrar la confianza y definir el umbral de "no concluyente" (Priority: P1)

El productor verá un porcentaje de confianza; los autores necesitan que ese número sea honesto y que la app
diga "resultado no concluyente" cuando el modelo no esté seguro.

**Why this priority**: un porcentaje sin calibrar puede inducir decisiones fitosanitarias equivocadas
(principio IV) y es requisito previo a la exportación.

**Independent Test**: calibrar el modelo seleccionado con el conjunto de validación y verificar que el error de
calibración baja y que el umbral queda justificado con una curva.

**Acceptance Scenarios**:

1. **Given** el modelo seleccionado, **When** se calibra, **Then** el ajuste usa solo el conjunto de validación y
   se reporta el error de calibración esperado (ECE, 15 intervalos) antes y después, en validación y en prueba.
2. **Given** el modelo calibrado, **When** se analiza el umbral, **Then** se produce una curva de cobertura frente
   a exactitud en validación y se documenta el umbral elegido (0,60 como punto de partida) con la cobertura y la
   exactitud que implica.
3. **Given** una predicción con confianza calibrada inferior al umbral, **When** se evalúa, **Then** se cuenta como
   "no concluyente" y el informe reporta qué porcentaje de prueba cae en esa categoría.

---

### User Story 4 - Verificar con Grad-CAM++ dónde mira el modelo (Priority: P2)

Los autores y el experto agrónomo necesitan comprobar que el modelo se fija en la lesión o en la zona del
pedúnculo, y no en el fondo, la mano u otros elementos ajenos.

**Why this priority**: la explicabilidad es el aporte declarado frente a la tesis anterior y detecta atajos que
las métricas no muestran; depende de tener un modelo seleccionado.

**Independent Test**: generar los mapas de calor sobre una muestra fija de aciertos y errores y revisar el
mosaico resultante con una planilla de valoración.

**Acceptance Scenarios**:

1. **Given** el modelo seleccionado, **When** se generan las explicaciones, **Then** se obtienen mapas de calor
   para alrededor de 10 aciertos y 10 errores por clase (o todos los errores si hay menos), elegidos con semilla
   fija.
2. **Given** los mapas de calor, **When** el revisor los evalúa, **Then** cada uno queda marcado como "foco en
   lesión/fruto", "foco en fondo o elemento ajeno" o "ambiguo", y el informe resume los porcentajes por clase.
3. **Given** que más del 20 % de los aciertos de una clase se enfocan en el fondo o en elementos ajenos, **When**
   se cierra el análisis, **Then** se registra como posible atajo y se señala para revisión del dataset.

---

### User Story 5 - Exportar el modelo para el teléfono (Priority: P2)

La app necesita un modelo que quepa y responda rápido en teléfonos de gama baja sin conexión.

**Why this priority**: es el puente hacia la app (principios I y V); depende de tener el modelo calibrado.

**Independent Test**: convertir el modelo a las variantes de cuantización y comparar tamaño y macro-F1 de cada una
con el modelo original sobre el conjunto de prueba.

**Acceptance Scenarios**:

1. **Given** el modelo calibrado, **When** se exporta, **Then** se generan las variantes de precisión completa,
   media precisión y cuantización dinámica de 8 bits, y para cada una se reporta tamaño en disco y macro-F1 en
   prueba frente al modelo original.
2. **Given** las variantes, **When** se elige la de producción, **Then** es la más liviana que pierde como máximo
   1 punto de macro-F1 y pesa como máximo 10 MB; la calibración (temperatura) y el orden de las clases viajan con
   el modelo.
3. **Given** la variante elegida, **When** se ejecuta en un teléfono de gama baja real, **Then** la latencia media
   de una inferencia es ≤ 500 ms y se registra el modelo del teléfono, su RAM y su versión de Android.

---

### User Story 6 - Prueba temprana de la explicación dentro del teléfono (Priority: P3)

Los autores necesitan saber pronto si el mapa de calor puede calcularse dentro del modelo exportado, porque es la
parte técnicamente más incierta y, si no funciona, hay que aplicar un plan B.

**Why this priority**: reduce el riesgo del cronograma; no bloquea la entrega del clasificador.

**Independent Test**: exportar un modelo de prueba con una segunda función de explicación y verificar si produce
un mapa equivalente al calculado en el entorno de entrenamiento.

**Acceptance Scenarios**:

1. **Given** un modelo de prueba, **When** se exporta con la función de explicación, **Then** se documenta si la
   conversión funciona, el tamaño adicional y la diferencia del mapa frente al de referencia.
2. **Given** que la conversión falla o el mapa difiere de forma inaceptable, **When** se cierra el spike, **Then**
   se documenta el plan B adoptado y su justificación.

---

### Edge Cases

- Una imagen del manifiesto no existe o no abre en la raíz configurada: el entrenamiento no empieza y lista las
  faltantes.
- Una imagen pertenece a una fuente sin licencia académica confirmada (`no` o `pendiente`) o no se puede asignar
  a ninguna fuente: se excluye y se registra con su motivo; nunca se entrena con ella (FR-026).
- El manifiesto trae una clase con nombre distinto (`AGUACATESANOS`, `ANTRACNOSIS`, `PEDUNCULO`): se traduce a las
  tres clases oficiales mediante una tabla de equivalencias explícita; un nombre desconocido aborta la ejecución.
- La sesión del entorno de entrenamiento se interrumpe a mitad de una corrida: la corrida se puede reanudar desde
  el último punto de control o queda marcada como incompleta y no entra en la comparación.
- La clase pedúnculo tiene pocas imágenes en validación y prueba (~31-32): el informe muestra intervalos de
  confianza o advierte de la alta varianza de su recall.
- La pedúnculo procede de una sola fuente: el informe advierte que no se puede medir generalización a fuentes
  nuevas para esa clase.
- Ninguna variante exportada cumple tamaño y pérdida a la vez: se registra el incumplimiento y se elige la que
  mejor equilibra, justificando la excepción.
- El modelo no alcanza la meta de rendimiento: el informe lo declara sin maquillar y propone acciones (más datos,
  revisión de etiquetas, ajuste del aumento).

## Requirements *(mandatory)*

### Functional Requirements

**Datos de entrada**

- **FR-001**: El sistema DEBE leer el dataset exclusivamente desde un manifiesto CSV con, como mínimo, ruta de la
  imagen, clase y partición; la carpeta raíz de las imágenes DEBE ser configurable.
- **FR-002**: El sistema DEBE traducir los nombres de clase del manifiesto a las tres clases oficiales (sano,
  antracnosis, síntomas compatibles con anillado del pedúnculo) mediante una tabla de equivalencias y abortar ante
  un nombre desconocido.
- **FR-003**: El sistema DEBE verificar, antes de entrenar, que todas las imágenes del manifiesto existen y son
  legibles, y que ningún SHA-256 aparece en más de una partición.
- **FR-004**: El sistema DEBE calcular y registrar la huella SHA-256 del manifiesto usado en cada experimento.
- **FR-026**: El sistema DEBE excluir, antes de cualquier otro paso, toda imagen cuya fuente no tenga
  `uso_academico = si` en `config/fuentes.csv`. La fuente se determina primero por SHA-256 en `datos/manifiesto.csv`
  (especificación 002) y, si el contenido no está registrado, con las reglas de nombre sobre la ruta original; una
  imagen sin fuente determinable también se excluye. Cada exclusión queda registrada con su fuente, licencia y
  motivo, y los conteos excluidos se informan por partición y clase.
- **FR-027**: El sistema DEBE excluir además las fuentes listadas en la configuración como excluidas por calidad
  (hoy `avocare_sano` y `avocare_antracnosis`, copias aumentadas), registrando el motivo de calidad por separado
  del de licencia.
- **FR-028**: El sistema DEBE procesar las fotos de campo propias (`Modelo/CAMPO_SIGCHOS/<CLASE>/`, rol
  `test_campo`) con las reglas de la especificación 002 (fuente y licencia, SHA-256, duplicados exactos frente al
  manifiesto de 002, casi duplicados, umbrales de calidad), compararlas en el EDA con las fuentes del
  entrenamiento y usarlas SOLO como prueba de campo independiente: nunca en entrenamiento, selección ni
  calibración. Los originales HEIC se conservan y se convierten a JPG con registro.
- **FR-029**: El sistema DEBE evaluar un modelo sobre la prueba de campo y reportar, separado de la prueba
  interna, la distribución de predicciones, la sensibilidad por clase presente, la confianza calibrada, los casos
  "no concluyentes" y los mapas Grad-CAM++ de cada foto.
- **FR-005**: El conjunto de prueba NO DEBE intervenir en el entrenamiento, la selección de hiperparámetros, la
  selección de arquitectura ni la calibración; solo se usa para el reporte final.

**Entrenamiento**

- **FR-006**: El sistema DEBE entrenar clasificadores de tres clases por transferencia de aprendizaje sobre
  MobileNetV3 y EfficientNet-B0 preentrenados, con entrada de 224 × 224 píxeles.
- **FR-007**: El entrenamiento DEBE tener dos fases: (1) modelo base congelado y solo la cabeza entrenable;
  (2) ajuste fino de la parte final del modelo base con una tasa de aprendizaje baja, manteniendo congeladas las
  capas de normalización por lotes.
- **FR-008**: El sistema DEBE compensar el desbalance de clases usando pesos calculados solo sobre entrenamiento.
- **FR-009**: El aumento de datos DEBE aplicarse solo a entrenamiento.
- **FR-010**: Toda la configuración de un experimento (hiperparámetros, aumento, épocas, criterios de parada,
  semilla, arquitectura) DEBE leerse de un archivo de configuración versionado; las dos arquitecturas DEBEN
  compartir la misma configuración salvo el modelo base.
- **FR-011**: El sistema DEBE guardar puntos de control durante el entrenamiento para poder reanudar una corrida
  interrumpida.

**Evaluación y selección**

- **FR-012**: El sistema DEBE reportar por corrida: macro-F1 (métrica principal), recall y precisión por clase,
  exactitud, matriz de confusión y métricas desglosadas por fuente cuando el manifiesto la incluya.
- **FR-013**: El sistema DEBE ejecutar la comparación con las semillas 42, 43 y 44 por arquitectura y reportar
  media ± desviación.
- **FR-014**: El sistema DEBE aplicar la regla de selección (mayor macro-F1 medio en validación; si la diferencia
  es < 2 puntos, la arquitectura más liviana) y registrar la decisión.
- **FR-015**: El informe DEBE indicar si el modelo seleccionado cumple la meta (macro-F1 ≥ 0,85 y recall de
  antracnosis ≥ 0,85 en prueba).

**Calibración**

- **FR-016**: El sistema DEBE calibrar las probabilidades con Temperature Scaling ajustado sobre validación y
  reportar el ECE (15 intervalos) antes y después en validación y prueba, junto con un diagrama de fiabilidad.
- **FR-017**: El sistema DEBE producir la curva de cobertura frente a exactitud en validación y documentar el
  umbral de "no concluyente" (0,60 inicial, ajustable con evidencia).

**Explicabilidad**

- **FR-018**: El sistema DEBE generar mapas Grad-CAM++ sobre una muestra con semilla fija de aciertos y errores por
  clase, en un mosaico revisable, y una planilla para registrar la valoración de cada mapa.

**Exportación**

- **FR-019**: El sistema DEBE exportar el modelo seleccionado a TensorFlow Lite en tres variantes (precisión
  completa, media precisión y cuantización dinámica de 8 bits) y reportar tamaño y macro-F1 en prueba de cada una
  frente al original.
- **FR-020**: El modelo exportado DEBE ir acompañado de un archivo de metadatos con el orden de las clases, la
  temperatura de calibración, el umbral, el tamaño de entrada y la versión del experimento de origen.
- **FR-021**: La latencia de la variante elegida DEBE medirse en un teléfono Android real de gama baja y
  registrarse junto con el modelo del dispositivo.
- **FR-022**: Se DEBE realizar un spike de exportación con una función adicional de explicación y documentar su
  resultado y, si falla, el plan B.

**Reproducibilidad y calidad**

- **FR-023**: Cada experimento DEBE dejar un registro (configuración, métricas, huella del manifiesto, versiones de
  dependencias, fecha) en una bitácora consultable.
- **FR-024**: La lógica determinista (lectura y validación del manifiesto, equivalencia de clases, pesos de clase,
  métricas, ECE, Temperature Scaling, regla de selección) DEBE tener pruebas automatizadas que no requieran
  entrenar un modelo.
- **FR-025**: Los modelos entrenados y las imágenes NO DEBEN versionarse en Git; sí los scripts, configuraciones,
  registros de métricas e informes.

### Key Entities

- **Manifiesto de datos**: lista de imágenes con ruta, clase, partición y, si existen, SHA-256, fuente, estado de
  la etiqueta y grupo. Se identifica por su huella SHA-256.
- **Configuración de experimento**: arquitectura, hiperparámetros de ambas fases, aumento, criterios de parada,
  semilla y ruta del manifiesto.
- **Corrida**: un entrenamiento concreto (arquitectura + semilla + configuración + manifiesto) con su estado
  (completa / incompleta), métricas y punto de control.
- **Comparación**: conjunto de corridas de ambas arquitecturas con las mismas condiciones; produce la tabla
  media ± desviación y la decisión de selección.
- **Modelo calibrado**: modelo seleccionado más su temperatura, ECE antes/después y umbral de "no concluyente".
- **Variante exportada**: archivo para el teléfono con su precisión numérica, tamaño, macro-F1 en prueba, latencia
  medida y metadatos.
- **Revisión de explicaciones**: valoración de cada mapa de calor (foco en lesión/fruto, fondo/ajeno, ambiguo) con
  revisor y fecha.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El modelo seleccionado alcanza macro-F1 ≥ 0,85 y recall de antracnosis ≥ 0,85 en el conjunto de
  prueba (o el informe documenta el incumplimiento y sus causas).
- **SC-002**: La comparación de arquitecturas incluye 3 corridas completas por arquitectura con configuración
  idéntica verificable, y reporta media ± desviación de cada métrica.
- **SC-003**: El ECE del modelo en prueba es menor después de calibrar que antes, y ambos valores se reportan.
- **SC-004**: La variante exportada pesa ≤ 10 MB, pierde ≤ 1 punto de macro-F1 frente al modelo original y
  responde en ≤ 500 ms de media en un teléfono de gama baja real.
- **SC-005**: Al menos el 80 % de los mapas de calor de aciertos revisados se enfocan en la lesión o en el fruto,
  por clase.
- **SC-006**: Cualquier resultado reportado puede regenerarse desde el repositorio con el manifiesto
  identificado por su huella y la configuración registrada, con una diferencia ≤ 1 punto de macro-F1.
- **SC-007**: La tutora puede verificar cada cifra de la tesis sobre el modelo en un registro de experimento
  concreto.

## Assumptions

- **Dataset vigente (2026-11-10)**: la partición de la especificación 002 (`datos/particion.csv`, 2 188 imágenes:
  sano 967, antracnosis 958, pedúnculo 263; train 1 531 / val 330 / test 327), con las imágenes procesadas de
  `Modelo/PROCESADO/<particion>/<clase>/<id_contenido>.jpg`. Cumple FR-026/FR-027 (sin fuentes sin licencia ni
  `avocare`), respeta la partición del artículo y no tiene frutos repartidos. Sus limitaciones medidas en el EDA de
  002 se tratan como requisitos de viabilidad: auditoría de etiquetas con 6 % de error (criterio ≤ 2 %), sonda de
  fondo 0,95 (alerta de atajo) y etiquetas sin validación del agrónomo.
- **Dataset descartado (historial)**: se usó el split experimental v4 del compañero
  (`Evidencia_Tesis_Aguacate/05_datos/Dataset_split_experimental_v4_20261104_230751`, en el Google Drive del
  equipo) para desarrollar y depurar el flujo, **después** del filtro de licencias de FR-026 (1 426 imágenes).
  Antes de reportar métricas finales en la tesis, el compañero DEBE resolver y documentar: (a) retirar del split
  las 412 imágenes `sano-*` sin licencia (209 registradas en 002 y 203 nuevas con el mismo origen; las 16 renumeradas `sano-0707`…`sano-0723` son fotos propias de Herrera y Marín y sí se conservan); (b) para reincorporar
  `avocare` (licencia ya verificada), entregar solo las imágenes originales o agruparlas por original, porque la
  versión 4 de Roboflow contiene 3 variantes aumentadas por foto; (c) 89 frutos con fotos en más de una partición (76 imágenes de prueba afectadas, a
  recalcular tras el filtro). Gracias a FR-001, la versión corregida se usa sustituyendo el manifiesto.
- **Licencia de avocare**: verificada por los autores en Roboflow Universe el 2026-11-09 (CC BY 4.0). Queda
  excluida por calidad (FR-027) hasta que el compañero entregue solo los originales o los agrupe por original.
- **Balance de clases**: tras el filtro, sano queda con 392 imágenes frente a 823 de antracnosis; se compensa con
  pesos de clase (FR-008) y se vigila el recall de sano en los informes.
- **Etiquetas**: la mayoría de las etiquetas del split v4 son provisionales (pendientes de validación del experto
  agrónomo). Las métricas sobre etiquetas provisionales se rotulan como "experimentales" en los informes.
- **Entorno**: el entrenamiento se ejecuta en Google Colab con GPU, leyendo las imágenes desde Google Drive; los
  scripts viven en el repositorio y un notebook solo los lanza. Las versiones de Python, TensorFlow y Keras quedan
  fijadas (Python 3.12, TensorFlow 2.20, Keras 3.15, ya usadas en la especificación 002).
- **Hiperparámetros por defecto**: cabeza con agregación global, dropout 0,3 y salida de 3 clases; fase 1 con
  15 épocas y tasa 1e-3; fase 2 con ~30 % final descongelado, 30 épocas y tasa 1e-5; lote de 32; parada temprana
  por pérdida de validación con paciencia 5 y reducción de tasa ante estancamiento; aumento con volteos, rotación,
  zoom y brillo/contraste moderados. Pueden ajustarse en la planificación siempre que ambas arquitecturas compartan
  los mismos valores.
- **Preprocesamiento**: las imágenes ya vienen a la resolución de trabajo o se redimensionan a 224 × 224; el
  reescalado de píxeles lo hacen los propios modelos base, por lo que no se normaliza por fuera.
- **Dispositivo**: los límites de 10 MB y 500 ms se fijan aquí como referencia provisional hasta que la
  especificación de la app los confirme (TODO RNF_DISPOSITIVO de la constitución). La medición de latencia
  requiere un teléfono Android real de gama baja disponible para el equipo.
- **Alcance**: quedan fuera la integración en la app Flutter, el asistente conversacional y la validación de
  etiquetas por el experto (dependencias de otras funcionalidades).
- **Métricas SDD**: la extensión `metricas` no está instalada en el equipo actual tras el cambio de computadora;
  las sesiones de esta funcionalidad deben registrarse en cuanto se reinstale.
