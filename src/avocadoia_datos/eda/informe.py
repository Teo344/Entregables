"""Informe de ETL y EDA: datos/eda/informe_etl_eda.md y .json (spec 002, US6, research E14)."""

import math
import os
from collections import Counter

from avocadoia_datos.clases import CLASES, PARTICIONES
from avocadoia_datos.config import ErrorPrecondicion
from avocadoia_datos.es_csv import escribir_json, leer_csv, leer_json
from avocadoia_datos.etl import embudo as mod_embudo
from avocadoia_datos.etl import revision

NOMBRE = {"sano": "Sano", "antracnosis": "Antracnosis",
          "pedunculo": "Síntomas compatibles con anillado del pedúnculo"}
REFERENCIA = ("Calapaqui, G., Guarderas, D. y Fuertes, W. (2026). A Model Implementation to Detect Hate Speech "
              "Associated with Gender Violence by Natural Language Processing and Machine Learning. ICCSA 2026, "
              "LNCS 16768, pp. 202–219. Springer. doi:10.1007/978-3-032-30488-9_13")
EQUIVALENCIAS = (("Eliminar duplicados", "Duplicados exactos (SHA-256) y casi duplicados"),
                 ("Eliminar valores nulos", "Imágenes corruptas o ilegibles"),
                 ("Eliminar caracteres especiales (ruido)", "Ruido visual y atajos: carteles, fondos de laboratorio"),
                 ("Convertir etiquetas con umbral 0.5", "Sospecha de etiqueta, revisión manual y validación del experto"),
                 ("Unir tres conjuntos en un corpus balanceado", "Unir 9 fuentes balanceadas por cuotas de clase y fuente"))
ERRORES_AUDITORIA = ("reasignar", "excluir")


def pesos_por_clase(particion):
    """w_c = n_total / (3 · n_c) sobre train (pesos balanceados)."""
    n = Counter(f["clase"] for f in particion if f["particion"] == "train")
    total = sum(n.values())
    return {c: round(total / (len(CLASES) * n[c]), 4) for c in CLASES if n[c]}


def wilson(k, n, z=1.96):
    """Intervalo de confianza de Wilson al 95 % para una proporción k/n."""
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    margen = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return (round(max(0.0, centro - margen), 4), round(min(1.0, centro + margen), 4))


def resumen_auditoria(decisiones):
    filas = [d for d in decisiones if d.get("tipo") == "auditoria"]
    vigentes = {d["id_contenido"]: d for d in filas}
    errores = sum(1 for d in vigentes.values() if d["decision"] in ERRORES_AUDITORIA)
    n = len(vigentes)
    return {"revisadas": n, "errores": errores, "tasa": round(errores / n, 4) if n else None,
            "ic95": wilson(errores, n), "cumple_sc003": (errores <= 2 * n / 100) if n else None}


def verificar_precondiciones(salida):
    descuadres = mod_embudo.verificar_embudo(leer_csv(os.path.join(salida, "etl", "embudo.csv")))
    if descuadres:
        raise ErrorPrecondicion(f"El embudo no cuadra en {descuadres}: ejecute `etl-embudo` tras regenerar.")
    auditoria = os.path.join(salida, "revision", "auditoria_01.xlsx")
    hechas = [d for d in leer_csv(revision.ruta_decisiones(salida)) if d.get("tipo") == "auditoria"]
    if os.path.exists(auditoria) and not hechas:
        raise ErrorPrecondicion("Hay una planilla de auditoría sin incorporar: complétela y ejecute "
                                "`etl-incorporar datos/revision/auditoria_01.xlsx`.")


def _tabla(encabezado, filas):
    lineas = ["| " + " | ".join(encabezado) + " |", "|" + "|".join(" --- " for _ in encabezado) + "|"]
    lineas += ["| " + " | ".join(str(c) for c in f) + " |" for f in filas]
    return lineas


def conclusiones(datos):
    """Hallazgos C1…Cn, cada uno con al menos una evidencia (SC-007)."""
    c = []
    pesos = datos["pesos_clase"]
    c.append(("Desbalance entre clases",
              "Usar pesos por clase en la pérdida: " + ", ".join(f"{NOMBRE[k]} {v}" for k, v in pesos.items())
              + " (n_total / (3 · n_clase) sobre train).",
              ["datos/eda/tablas/distribucion_clase_fuente_conjunto.csv"]))
    a = datos["aumento"]
    c.append(("Aumento de datos solo en entrenamiento",
              f"Aplicar en línea sobre train: rotación ±{a.get('rotacion_grados')}°, desplazamiento "
              f"{a.get('desplazamiento')}, zoom {a.get('zoom')}, volteos y brillo {a.get('brillo')}. "
              "Val y test no se aumentan.",
              ["datos/eda/figuras/caracteristicas_por_clase.png", "config/dataset.toml"]))
    sondas = {s["sonda"]: s for s in datos["sondas"]}
    for nombre, riesgo, mitigacion in (
            ("bajo_nivel", "Brillo, color, nitidez o tamaño delatan la clase",
             "Aumento de color y brillo más amplio, y verificar con Grad-CAM++ que el modelo mira la lesión"),
            ("fondo", "El fondo (borde de la imagen) delata la clase",
             "Recortes centrados en el fruto en el aumento, equilibrar fondos por clase y verificar con Grad-CAM++")):
        s = sondas.get(nombre)
        if s is None:
            continue
        if s["alerta"] == "si":
            c.append((f"Riesgo de atajo: {riesgo.lower()} (sonda {nombre} = {s['exactitud_balanceada']})",
                      mitigacion + ".", ["datos/eda/tablas/sondas.csv", "datos/eda/figuras/sondas_atajo.png"]))
        else:
            c.append((f"Sonda {nombre}: {s['exactitud_balanceada']} (umbral 0.80), sin alerta",
                      "No requiere mitigación específica; se verifica igualmente con Grad-CAM++ en 003.",
                      ["datos/eda/tablas/sondas.csv"]))
    estilos = [s for n, s in sondas.items() if n.startswith("fuente_") and float(s["exactitud_balanceada"]) > 0.80]
    if estilos:
        c.append(("Cada fuente tiene un estilo propio reconocible dentro de su clase ("
                  + ", ".join(f"{s['sonda']} = {s['exactitud_balanceada']}" for s in estilos) + ")",
                  "Reportar en 003 las métricas por fuente, además de las globales, para detectar si el modelo "
                  "acierta por la fuente y no por la enfermedad.", ["datos/eda/tablas/sondas.csv",
                                                                    "datos/eda/figuras/tsne_por_fuente.png"]))
    fondos = {f["clase"]: float(f["fraccion_uniforme"]) for f in datos["fondo"] if f["fuente"] == "todas" and f["fraccion_uniforme"]}
    if fondos and max(fondos.values()) - min(fondos.values()) > 0.30:
        c.append(("La proporción de fondo uniforme difiere mucho entre clases ("
                  + ", ".join(f"{NOMBRE[k]} {v:.0%}" for k, v in fondos.items()) + ")",
                  "Tratar el fondo como posible atajo: recortes y Grad-CAM++ en 003.",
                  ["datos/eda/tablas/fondo_por_clase.csv", "datos/eda/figuras/fondo_por_clase_fuente.png"]))
    if datos.get("faltantes_cuota"):
        totales = {c: sum(v.values()) for c, v in datos["faltantes_cuota"].items()}
        c.append(("La limpieza dejó clases bajo su cuota (" + ", ".join(f"{NOMBRE[k]} −{v}" for k, v in totales.items())
                  + ")", "No rellenar con Hass ni Kaggle, que tienen fondo blanco al 100 % y agravarían el atajo de "
                  "fondo; compensar el desbalance con los pesos por clase de C1.",
                  ["datos/particion.json", "datos/eda/tablas/fondo_por_clase.csv"]))
    c.append(("Limitaciones",
              "El conjunto es provisional: falta el experto validador; el conteo de carteles es parcial (solo lo "
              "revisado); Kaggle no tiene licencia abierta (uso académico con cita). Las métricas finales de la "
              "tesis deben salir del conjunto definitivo.", ["datos/particion.json", "config/fuentes.csv"]))
    return [{"id": f"C{i}", "conclusion": t, "recomendacion": r, "evidencia": e} for i, (t, r, e) in enumerate(c, 1)]


def recopilar(salida, config):
    particion = leer_csv(os.path.join(salida, "particion.csv"))
    meta_particion = leer_json(os.path.join(salida, "particion.json"))
    manifiesto = leer_csv(os.path.join(salida, "manifiesto.csv"))
    decisiones = leer_csv(revision.ruta_decisiones(salida))
    sospechas = leer_csv(os.path.join(salida, "etl", "sospechas.csv"))
    marcadas = {s["id_contenido"] for s in sospechas if s["a_revisar"] == "si"}
    decididas = {d["id_contenido"] for d in decisiones if d.get("tipo") == "sospecha"}
    cache_huella = ""
    try:
        from avocadoia_datos.etl.representaciones import cargar_cache
        cache = cargar_cache(salida)
        cache_huella = str(cache["huella"]) if cache is not None else ""
        version_tf = str(cache["version_tf"]) if cache is not None else ""
    except ImportError:
        version_tf = ""
    datos = {
        "estado_particion": meta_particion["estado"],
        "faltantes_cuota": {c: v for c, v in meta_particion.get("faltantes_cuota", {}).items() if v},
        "huella_particion": meta_particion["huella_particion"],
        "huella_representaciones": cache_huella,
        "version_tensorflow": version_tf,
        "semilla": config.semilla,
        "conjunto_final": {c: {p: sum(1 for f in particion if f["clase"] == c and f["particion"] == p)
                               for p in PARTICIONES} for c in CLASES},
        "fuentes": [{"fuente": f.fuente, "clase": f.clase, "licencia": f.licencia, "uso_academico": f.uso_academico,
                     "referencia": f.referencia} for f in config.fuentes],
        "estados": dict(sorted(Counter(f["estado"] for f in manifiesto).items())),
        "embudo": leer_csv(os.path.join(salida, "etl", "embudo.csv")),
        "comparacion_001": dict(sorted(Counter(f["cambio"] for f in leer_csv(os.path.join(salida, "etl", "comparacion_001.csv"))).items())),
        "sospechas": {c: {"candidatas": sum(1 for s in sospechas if s["clase_asignada"] == c),
                          "a_revisar": sum(1 for s in sospechas if s["clase_asignada"] == c and s["a_revisar"] == "si"),
                          "conflictos": sum(1 for s in sospechas if s["clase_asignada"] == c and s["conflicto"] == "si")}
                      for c in CLASES},
        "revision": {"marcadas": len(marcadas), "decididas": len(marcadas & decididas),
                     "por_decision": dict(sorted(Counter(f.get("revision_autores", "") for f in manifiesto if f.get("revision_autores")).items())),
                     "casos_para_experto": sorted(f["id_contenido"] for f in manifiesto
                                                  if f.get("revision_autores") == "no_seguro" and f["canonica"] == "si")},
        "auditoria": resumen_auditoria(decisiones),
        "sondas": leer_csv(os.path.join(salida, "eda", "tablas", "sondas.csv")),
        "fondo": leer_csv(os.path.join(salida, "eda", "tablas", "fondo_por_clase.csv")),
        "pesos_clase": pesos_por_clase(particion),
        "aumento": config.aumento,
        "rotulos_tsne": [f["id_contenido"] for f in leer_csv(os.path.join(salida, "eda", "tablas", "tsne.csv")) if f["rotulo"] == "si"],
    }
    datos["conclusiones"] = conclusiones(datos)
    return datos


def markdown(d):
    l = ["# Informe de ETL y EDA del conjunto de datos AvocadoIA", "",
         f"Partición **{d['estado_particion']}** · semilla {d['semilla']} · huella `{d['huella_particion'][:16]}…`", "",
         "## Metodología", "",
         f"El proceso sigue la estructura de fases de {REFERENCIA}: **Extracción**, **Transformación** y **Carga**, "
         "seguidas de un **Análisis exploratorio (EDA)**. Las operaciones del artículo, sobre texto, se adaptan a "
         "imágenes así:", ""]
    l += _tabla(("En el artículo (texto)", "En este conjunto (imágenes)"), EQUIVALENCIAS)
    l += ["", "## 1. Extracción", "", "Fuentes inventariadas, con su licencia y uso académico:", ""]
    l += _tabla(("Fuente", "Clase", "Licencia", "Uso académico"),
                [(f["fuente"], f["clase"], f["licencia"], f["uso_academico"]) for f in d["fuentes"]])
    l += ["", "## 2. Transformación (limpieza)", "", "Estados del inventario:", ""]
    l += _tabla(("Estado", "Imágenes"), list(d["estados"].items()))
    l += ["", "### Etiquetas dudosas (confident learning)", "",
          "Representaciones EfficientNet-B0, regresión logística con validación cruzada por grupos y umbral por clase. "
          "Se marcan los conflictos y el 10 % de mayor sospecha de cada clase.", ""]
    l += _tabla(("Clase", "Candidatas", "A revisar", "Conflictos"),
                [(NOMBRE[c], v["candidatas"], v["a_revisar"], v["conflictos"]) for c, v in d["sospechas"].items()])
    r = d["revision"]
    l += ["", f"Revisión de los autores: {r['decididas']} de {r['marcadas']} imágenes marcadas tienen decisión "
          f"(SC-002: {'cumple' if r['marcadas'] and r['decididas'] == r['marcadas'] else 'pendiente'}). "
          "Decisiones vigentes: " + (", ".join(f"{k} {v}" for k, v in r["por_decision"].items()) or "ninguna") + ".", ""]
    if r["casos_para_experto"]:
        l += [f"**Casos para el experto** (`no_seguro`): {len(r['casos_para_experto'])} imágenes, listadas en "
              "`informe_etl_eda.json`.", ""]
    l += ["El conteo de carteles y otros atajos es **parcial**: solo cubre las imágenes revisadas.", ""]
    l += ["## 3. Carga", "", "Conjunto final en `Modelo/PROCESADO` (224 × 224):", ""]
    l += _tabla(("Clase",) + PARTICIONES + ("Total",),
                [(NOMBRE[c],) + tuple(v[p] for p in PARTICIONES) + (sum(v.values()),) for c, v in d["conjunto_final"].items()])
    if d["faltantes_cuota"]:
        l += ["", "**Cuotas no cubiertas.** Estas fuentes no tienen reserva después de la limpieza, así que su "
              "clase queda con menos imágenes. No se rellenan con otras fuentes para no aumentar el atajo de fondo: "
              + "; ".join(f"{NOMBRE[c]}: " + ", ".join(f"{f} −{n}" for f, n in v.items())
                          for c, v in d["faltantes_cuota"].items()) + "."]
    l += ["", "Comparación con el conjunto de la especificación 001: "
          + ", ".join(f"{k} {v}" for k, v in d["comparacion_001"].items()) + ".", "",
          "### Embudo de calidad", "", "![Embudo](figuras/embudo_calidad.png)", "",
          "Cada imagen inventariada se cuenta en un solo paso (`datos/etl/embudo.csv`).", ""]
    a = d["auditoria"]
    l += ["### Auditoría posterior a la limpieza (SC-003)", ""]
    if a["revisadas"]:
        l += [f"{a['errores']} errores en {a['revisadas']} imágenes al azar (tasa {a['tasa']:.1%}, IC 95 % de Wilson "
              f"{a['ic95'][0]:.1%}–{a['ic95'][1]:.1%}). Criterio ≤ 2 / 100: "
              f"{'cumple' if a['cumple_sc003'] else 'no cumple'}.", ""]
    else:
        l += ["Pendiente: la planilla de auditoría aún no se ha revisado.", ""]
    l += ["## 4. Análisis exploratorio (EDA)", "", "![Distribución](figuras/distribucion_clase_fuente_conjunto.png)", "",
          "![Características](figuras/caracteristicas_por_clase.png)", "", "![Tono](figuras/tono_por_clase.png)", "",
          "### Sesgos y atajos", "", "![Fondo](figuras/fondo_por_clase_fuente.png)", ""]
    if d["sondas"]:
        l += _tabla(("Sonda", "Qué mide", "Exactitud balanceada", "Azar", "Alerta"),
                    [(s["sonda"], s["descripcion"], s["exactitud_balanceada"], s["azar"], s["alerta"] or "—")
                     for s in d["sondas"]])
        l += ["", "Las sondas usan solo train + val; el conjunto de prueba no interviene (FR-020).", "",
              "![Sondas](figuras/sondas_atajo.png)", "", "### Mapa de similitud", "",
              "![t-SNE por clase](figuras/tsne_por_clase.png)", "", "![t-SNE por fuente](figuras/tsne_por_fuente.png)", ""]
    l += ["Los mosaicos de muestras por clase y fuente están en `datos/eda/figuras/mosaicos/`.", "",
          "## 5. Conclusiones para el entrenamiento", ""]
    for c in d["conclusiones"]:
        l += [f"- **{c['id']}. {c['conclusion']}.** {c['recomendacion']} Evidencia: "
              + ", ".join(f"`{e}`" for e in c["evidencia"]) + "."]
    l += ["", "## Reproducibilidad", "",
          f"- Huella de la partición: `{d['huella_particion']}`",
          f"- Huella de las representaciones: `{d['huella_representaciones'] or 'sin calcular'}`",
          f"- TensorFlow {d['version_tensorflow'] or '—'}; semilla {d['semilla']}.",
          "- Regenerar: `.venv-ml/Scripts/python -m avocadoia_datos etl-eda`.", ""]
    return "\n".join(l)


def ejecutar(salida, config):
    verificar_precondiciones(salida)
    datos = recopilar(salida, config)
    escribir_json(os.path.join(salida, "eda", "informe_etl_eda.json"), datos)
    with open(os.path.join(salida, "eda", "informe_etl_eda.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(markdown(datos))
    return datos
