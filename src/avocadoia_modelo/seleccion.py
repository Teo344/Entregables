"""Comparación de arquitecturas y regla de selección (research M12, data-model.md §7, T034).

Sin TensorFlow. La selección usa SOLO el macro-F1 medio de validación de las semillas; las métricas de prueba
se agregan para reportar, no para elegir (FR-005). McNemar se calcula como dato informativo sobre la prueba y
no interviene en la regla.
"""

import math
import os
import statistics

from avocadoia_datos.es_csv import escribir_csv, escribir_json, leer_json

from avocadoia_modelo import CLASES


class ComparacionInvalida(ValueError):
    pass


def leer_corridas(repo_datos):
    """Corridas de `datos/modelo/experimentos/<id>/` con sus métricas de val y test aplanadas."""
    base = os.path.join(repo_datos, "experimentos")
    corridas = []
    for id_ in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        ruta_reg, ruta_met = (os.path.join(base, id_, n) for n in ("registro.json", "metricas.json"))
        if not (os.path.exists(ruta_reg) and os.path.exists(ruta_met)):
            continue
        reg, met = leer_json(ruta_reg), leer_json(ruta_met)
        corridas.append({
            "id": reg["id"], "arquitectura": reg["arquitectura"], "semilla": int(reg["semilla"]),
            "estado": reg.get("estado"), "huella_config": reg.get("huella_config"),
            "huella_manifiesto": reg.get("huella_manifiesto"), "duracion_min": reg.get("duracion_min"),
            "tamano_keras_mb": reg.get("tamano_keras_mb"), "experimental": met["test"].get("experimental", False),
            "val_macro_f1": met["val"]["macro_f1"], "test_macro_f1": met["test"]["macro_f1"],
            "test_exactitud": met["test"]["exactitud"],
            "test_recall": {c: met["test"]["por_clase"][c]["recall"] for c in CLASES},
        })
    return corridas


def seleccionar(corridas, semillas, huella_config=None, huella_manifiesto=None):
    """Una corrida completa por (arquitectura, semilla): la primera por id (las repeticiones son reproducciones)."""
    elegidas = {}
    for c in sorted(corridas, key=lambda c: c["id"]):
        if c["estado"] != "completa" or c["semilla"] not in semillas:
            continue
        if huella_config and c["huella_config"] != huella_config:
            continue
        if huella_manifiesto and c["huella_manifiesto"] != huella_manifiesto:
            continue
        elegidas.setdefault((c["arquitectura"], c["semilla"]), c)
    return list(elegidas.values())


def repetidas(corridas, elegidas):
    """Ids de corridas completas con la misma arquitectura, semilla y huellas que una elegida."""
    claves = {(c["arquitectura"], c["semilla"], c["huella_config"], c["huella_manifiesto"]) for c in elegidas}
    ids = {c["id"] for c in elegidas}
    return sorted(c["id"] for c in corridas if c["estado"] == "completa" and c["id"] not in ids
                  and (c["arquitectura"], c["semilla"], c["huella_config"], c["huella_manifiesto"]) in claves)


def validar_igualdad(corridas, minimo=3):
    if not corridas:
        raise ComparacionInvalida("no hay corridas completas")
    for clave in ("huella_config", "huella_manifiesto"):
        valores = {c[clave] for c in corridas}
        if len(valores) > 1:
            raise ComparacionInvalida(f"corridas con {clave} distinta: {sorted(v[:8] for v in valores)}")
    por_arq = {}
    for c in corridas:
        if c["estado"] != "completa":
            raise ComparacionInvalida(f"{c['id']} no está completa")
        por_arq.setdefault(c["arquitectura"], []).append(c)
    faltan = {a: len(v) for a, v in por_arq.items() if len(v) < minimo}
    if len(por_arq) < 2 or faltan:
        raise ComparacionInvalida(f"se necesitan ≥ {minimo} corridas completas por arquitectura y 2 arquitecturas: "
                                  f"{ {a: len(v) for a, v in por_arq.items()} }")
    return por_arq


def _media_desv(valores):
    return statistics.fmean(valores), (statistics.stdev(valores) if len(valores) > 1 else 0.0)


def agregar(corridas, tamanos_fp16):
    """Por arquitectura: n, media y desviación muestral de las métricas, tamaño fp16 y duración."""
    tabla = {}
    for arq in sorted({c["arquitectura"] for c in corridas}):
        grupo = sorted((c for c in corridas if c["arquitectura"] == arq), key=lambda c: c["semilla"])
        fila = {"arquitectura": arq, "n": len(grupo), "semillas": [c["semilla"] for c in grupo],
                "corridas": [c["id"] for c in grupo], "tamano_fp16_mb": tamanos_fp16.get(arq)}
        metricas = {"val_macro_f1": [c["val_macro_f1"] for c in grupo],
                    "test_macro_f1": [c["test_macro_f1"] for c in grupo],
                    "test_exactitud": [c["test_exactitud"] for c in grupo],
                    **{f"test_recall_{k}": [c["test_recall"][k] for c in grupo] for k in CLASES},
                    "duracion_min": [c["duracion_min"] for c in grupo if c.get("duracion_min") is not None]}
        for nombre, valores in metricas.items():
            if valores:
                fila[f"{nombre}_media"], fila[f"{nombre}_desv"] = _media_desv(valores)
                fila[f"{nombre}_valores"] = valores
        tabla[arq] = fila
    return tabla


def elegir(tabla, margen):
    """Regla M12: diferencia de macro-F1 medio de val ≥ margen → el mayor; si no, el de menor tamaño fp16."""
    if len(tabla) != 2:
        raise ComparacionInvalida(f"la regla compara 2 arquitecturas; hay {len(tabla)}")
    a, b = sorted(tabla.values(), key=lambda f: f["val_macro_f1_media"], reverse=True)
    diferencia = a["val_macro_f1_media"] - b["val_macro_f1_media"]
    if diferencia >= margen:
        ganadora, regla = a, "mayor_macro_f1_val"
    else:
        ganadora, regla = min((a, b), key=lambda f: (f["tamano_fp16_mb"], -f["val_macro_f1_media"])), \
            "desempate_por_tamano_fp16"
    return {"arquitectura": ganadora["arquitectura"], "regla": regla, "margen": margen,
            "diferencia_val_macro_f1": round(diferencia, 6),
            "val_macro_f1_media": {f["arquitectura"]: f["val_macro_f1_media"] for f in (a, b)},
            "tamano_fp16_mb": {f["arquitectura"]: f["tamano_fp16_mb"] for f in (a, b)}}


def representativa(corridas, arquitectura):
    """La corrida de mayor macro-F1 de validación de la arquitectura (empate: la primera por id)."""
    grupo = sorted((c for c in corridas if c["arquitectura"] == arquitectura), key=lambda c: c["id"])
    return max(grupo, key=lambda c: c["val_macro_f1"])


def cumple_metas(metricas_test, metas):
    detalle = {k: {"valor": metricas_test[k], "meta": v, "cumple": metricas_test[k] >= v} for k, v in metas.items()}
    return {"cumple": all(d["cumple"] for d in detalle.values()), "detalle": detalle}


def mcnemar(y, pred_a, pred_b):
    """McNemar exacto (binomial, dos colas) sobre los casos en que solo un modelo acierta."""
    b = sum(1 for t, pa, pb in zip(y, pred_a, pred_b) if pa == t and pb != t)
    c = sum(1 for t, pa, pb in zip(y, pred_a, pred_b) if pa != t and pb == t)
    n, k = b + c, min(b, c)
    p = 1.0 if n == 0 else min(1.0, 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n)
    return {"solo_a_acierta": b, "solo_b_acierta": c, "discordantes": n, "p_valor": p}


COLUMNAS_TABLA = ("arquitectura", "rol", "n", "semillas", "tamano_fp16_mb", "val_macro_f1_media", "val_macro_f1_desv",
                  "test_macro_f1_media", "test_macro_f1_desv", "test_exactitud_media", "test_exactitud_desv",
                  *(f"test_recall_{c}_{s}" for c in CLASES for s in ("media", "desv")),
                  "duracion_min_media", "corridas")


def escribir(destino, tabla, decision):
    os.makedirs(destino, exist_ok=True)
    filas = []
    for f in tabla.values():
        fila = {k: f.get(k, "") for k in COLUMNAS_TABLA}
        fila["semillas"] = " ".join(str(s) for s in f["semillas"])
        fila["corridas"] = " ".join(f["corridas"])
        for k, v in fila.items():
            if isinstance(v, float):
                fila[k] = round(v, 4)
        filas.append(fila)
    escribir_csv(os.path.join(destino, "tabla.csv"), COLUMNAS_TABLA, filas)
    escribir_json(os.path.join(destino, "decision.json"), decision)
    return destino
