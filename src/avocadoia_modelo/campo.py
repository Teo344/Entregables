"""ETL y EDA acotados al conjunto de prueba de campo (Modelo/CAMPO_SIGCHOS), con las reglas de la spec 002.

No se re-ejecuta el inventario completo de 002: en esta PC faltan 76 originales de su partición y el conjunto de
entrenamiento lo produce el ETL del compañero. Aquí solo se procesan las fotos de campo, con las MISMAS reglas:
fuente y licencia por config/fuentes.csv (rol test_campo), SHA-256, duplicados exactos contra el manifiesto de 002,
casi duplicados entre ellas (dHash), calidad con los umbrales de config/dataset.toml y características del EDA de
002 (avocadoia_datos.etl.caracteristicas.medir). Las fotos de campo NUNCA entran a entrenamiento.
"""

import datetime
import os
from collections import Counter, defaultdict

import numpy as np
from PIL import Image

from avocadoia_datos.clases import EXTENSIONES
from avocadoia_datos.es_csv import escribir_csv, escribir_json, leer_csv, sha256_archivo
from avocadoia_datos.etl.caracteristicas import COLUMNAS as COLUMNAS_CARACT
from avocadoia_datos.etl.caracteristicas import medir
from avocadoia_datos.preprocesamiento import cargar_224, medir_calidad

CARPETA = "CAMPO_SIGCHOS"
CLASE_DE_CARPETA = {"AGUACATESANOS": "sano", "ANTRACNOSIS": "antracnosis", "PEDUNCULO": "pedunculo"}
COLUMNAS = ("ruta", "clase", "sha256", "fuente", "licencia", "uso_academico", "estado", "motivo", "grupo_similitud",
            "duplicado_de", "ancho_original", "alto_original", "brillo_224", "nitidez_224", "validacion") \
    + tuple(c for c in COLUMNAS_CARACT if c != "id_contenido")
UMBRAL_DHASH = 10  # distancia de Hamming (de 64 bits) para considerar casi duplicado


def dhash(ruta, lado=8):
    with Image.open(ruta) as im:
        g = np.asarray(im.convert("L").resize((lado + 1, lado), Image.LANCZOS), dtype=float)
    return (g[:, 1:] > g[:, :-1]).flatten()


def _grupos_similitud(hashes, umbral=UMBRAL_DHASH):
    """Unión-búsqueda: imágenes conectadas por distancia de Hamming ≤ umbral comparten grupo."""
    padre = list(range(len(hashes)))

    def raiz(i):
        while padre[i] != i:
            padre[i] = padre[padre[i]]
            i = padre[i]
        return i

    for i in range(len(hashes)):
        for j in range(i + 1, len(hashes)):
            if int((hashes[i] != hashes[j]).sum()) <= umbral:
                padre[raiz(i)] = raiz(j)
    return [raiz(i) for i in range(len(hashes))]


def inventariar(raiz_modelo, cfg002, por_sha_002, prepro):
    """Filas del manifiesto de campo (una por imagen JPG/PNG de CAMPO_SIGCHOS/<CLASE>/)."""
    filas = []
    base = os.path.join(raiz_modelo, CARPETA)
    for carpeta, clase in CLASE_DE_CARPETA.items():
        directorio = os.path.join(base, carpeta)
        if not os.path.isdir(directorio):
            continue
        for nombre in sorted(os.listdir(directorio)):
            if not nombre.lower().endswith(EXTENSIONES):
                continue  # p. ej. .HEIC originales: se usan sus JPG convertidos (scripts/convertir_heic.py)
            ruta_rel = f"{CARPETA}/{carpeta}/{nombre}"
            ruta = os.path.join(directorio, nombre)
            fuente = cfg002.fuente_de(ruta_rel)
            with Image.open(ruta) as im:
                ancho, alto = im.size
            im224 = cargar_224(ruta, int(prepro.get("tamano", 224)))
            brillo, nitidez = medir_calidad(im224)
            fila = {"ruta": ruta_rel, "clase": clase, "sha256": sha256_archivo(ruta),
                    "fuente": fuente.fuente if fuente else "", "licencia": fuente.licencia if fuente else "",
                    "uso_academico": fuente.uso_academico if fuente else "", "ancho_original": ancho,
                    "alto_original": alto, "brillo_224": round(brillo, 3), "nitidez_224": round(nitidez, 3),
                    "validacion": "pendiente", "duplicado_de": "", "_hash": dhash(ruta), "_rol": fuente.rol if fuente else ""}
            fila.update({k: v for k, v in medir(ruta).items()})
            filas.append(fila)

    vistos = {}
    for f in filas:
        motivo = ""
        if f["_rol"] != "test_campo":
            motivo = "fuente_no_es_test_campo"
        elif f["uso_academico"] != "si":
            motivo = f"licencia:{f['fuente']}:{f['uso_academico']}"
        elif f["sha256"] in por_sha_002:
            motivo, f["duplicado_de"] = "duplicada_de_002", por_sha_002[f["sha256"]].get("ruta", "")
        elif f["sha256"] in vistos:
            motivo, f["duplicado_de"] = "duplicada_en_campo", vistos[f["sha256"]]
        elif min(f["ancho_original"], f["alto_original"]) < int(prepro.get("lado_minimo", 224)):
            motivo = "calidad:lado_minimo"
        elif max(f["ancho_original"], f["alto_original"]) / min(f["ancho_original"], f["alto_original"]) > float(
                prepro.get("aspecto_maximo", 2.0)):
            motivo = "calidad:aspecto"
        elif f["brillo_224"] < float(prepro.get("umbral_brillo", 40)):
            motivo = "calidad:oscura"
        elif f["nitidez_224"] < float(prepro.get("umbral_borrosidad", 50)):
            motivo = "calidad:borrosa"
        vistos.setdefault(f["sha256"], f["ruta"])
        f["estado"], f["motivo"] = ("rechazada", motivo) if motivo else ("test_campo", "")
    raices = _grupos_similitud([f["_hash"] for f in filas])
    nombres = {r: f"campo-g{n:03d}" for n, r in enumerate(dict.fromkeys(raices), start=1)}
    for f, r in zip(filas, raices):
        f["grupo_similitud"] = nombres[r]
    return filas


def resumen(filas):
    validas = [f for f in filas if f["estado"] == "test_campo"]
    grupos = Counter(f["grupo_similitud"] for f in validas)
    return {"fecha": datetime.date.today().isoformat(), "total": len(filas), "test_campo": len(validas),
            "rechazadas": dict(Counter(f["motivo"] for f in filas if f["estado"] == "rechazada")),
            "por_clase": dict(Counter(f["clase"] for f in validas)),
            "grupos_similitud": len(grupos), "grupos_con_varias_fotos": sum(1 for n in grupos.values() if n > 1),
            "fuentes": dict(Counter(f["fuente"] for f in filas)), "validacion_experta": "pendiente"}


def escribir(filas, destino):
    escribir_csv(os.path.join(destino, "manifiesto_campo.csv"), COLUMNAS, filas)
    res = resumen(filas)
    escribir_json(os.path.join(destino, "inventario_campo.json"), res)
    return res


# --- EDA: campo frente a las fuentes del conjunto de entrenamiento ---------------------------------------------

VARIABLES_EDA = ("brillo", "contraste", "nitidez", "saturacion", "tono_medio", "fondo_fraccion", "megapixeles")


def tabla_comparativa(filas_campo, caracteristicas_002, manifiesto_002, fuentes_referencia):
    """Mediana y rango intercuartílico por grupo: campo frente a cada fuente de referencia (EDA de 002)."""
    fuente_de_id = {f["id_contenido"]: f["fuente"] for f in manifiesto_002}
    grupos = defaultdict(list)
    for f in caracteristicas_002:
        fuente = fuente_de_id.get(f["id_contenido"])
        if fuente in fuentes_referencia:
            grupos[fuente].append(f)
    grupos["campo_sigchos (propias)"] = [f for f in filas_campo if f["estado"] == "test_campo"]
    salida = []
    for nombre, filas in grupos.items():
        fila = {"grupo": nombre, "n": len(filas),
                "fondo_uniforme_pct": round(100 * np.mean([f["fondo"] == "uniforme" for f in filas]), 1) if filas else ""}
        for v in VARIABLES_EDA:
            x = np.array([float(f[v]) for f in filas]) if filas else np.array([])
            fila[f"{v}_mediana"] = round(float(np.median(x)), 3) if len(x) else ""
            fila[f"{v}_riq"] = round(float(np.subtract(*np.percentile(x, [75, 25]))), 3) if len(x) else ""
        salida.append(fila)
    return salida, grupos


def figuras_eda(grupos, destino, raiz_modelo, filas_campo, n_mosaico=20):
    from avocadoia_modelo.figuras import plt

    nombres = list(grupos)
    fig, ejes = plt.subplots(2, 3, figsize=(14, 7.5))
    for eje, v in zip(ejes.flat, ("brillo", "contraste", "nitidez", "saturacion", "tono_medio", "fondo_fraccion")):
        datos = [[float(f[v]) for f in grupos[n]] for n in nombres]
        eje.boxplot(datos, showfliers=False)
        eje.set_xticks(range(1, len(nombres) + 1), [n.replace("_", "\n", 1) for n in nombres], fontsize=7)
        eje.set_title(v.replace("_", " "))
        eje.grid(alpha=0.3)
    fig.suptitle("Fotos de campo propias frente a las fuentes del entrenamiento (características del EDA de 002)")
    fig.tight_layout()
    os.makedirs(destino, exist_ok=True)
    fig.savefig(os.path.join(destino, "comparacion_campo.png"), dpi=140)
    plt.close(fig)

    validas = [f for f in filas_campo if f["estado"] == "test_campo"][:n_mosaico]
    columnas = 5
    filas_m = max(1, -(-len(validas) // columnas))
    fig, ejes = plt.subplots(filas_m, columnas, figsize=(2.6 * columnas, 2.9 * filas_m), squeeze=False)
    for eje in ejes.flat:
        eje.axis("off")
    for eje, f in zip(ejes.flat, validas):
        eje.imshow(cargar_224(os.path.join(raiz_modelo, f["ruta"]), 224))
        eje.set_title(f"{os.path.basename(f['ruta'])}\n{f['grupo_similitud']}", fontsize=7)
    fig.suptitle("Muestra de fotos de campo (224 × 224, como las ve el modelo)")
    fig.tight_layout()
    fig.savefig(os.path.join(destino, "mosaico_campo.png"), dpi=110)
    plt.close(fig)


def leer_manifiesto_002(ruta):
    return leer_csv(ruta)


# --- Evaluación del modelo sobre la prueba de campo (FR-029, T061) ---------------------------------------------

COLUMNAS_PREDICCIONES = ("ruta", "grupo_similitud", "clase_real", "clase_predicha", "confianza", "no_concluyente",
                         "p_sano", "p_antracnosis", "p_pedunculo", "acierto")


def metricas_campo(y, probs, umbral):
    """Distribución de predicciones y sensibilidad de cada clase presente (sin TF)."""
    from avocadoia_modelo import CLASES

    y, probs = np.asarray(y), np.asarray(probs)
    pred, conf = probs.argmax(1), probs.max(1)
    concluyente = conf >= umbral
    salida = {"n": int(len(y)), "umbral": umbral, "no_concluyentes": int((~concluyente).sum()),
              "predicciones": {c: int((pred == i).sum()) for i, c in enumerate(CLASES)},
              "confianza_media": float(conf.mean()) if len(y) else None, "por_clase": {}}
    for i, c in enumerate(CLASES):
        m = y == i
        if not m.any():
            continue
        salida["por_clase"][c] = {
            "n": int(m.sum()),
            "sensibilidad": float((pred[m] == i).mean()),
            "sensibilidad_concluyentes": float((pred[m & concluyente] == i).mean()) if (m & concluyente).any() else None,
            "confundida_con": {CLASES[j]: int((pred[m] == j).sum()) for j in range(len(CLASES)) if j != i},
        }
    return salida


def evaluar(cfg, id_, repo_datos, salida, raiz_modelo):
    import keras

    from avocadoia_datos.es_csv import leer_json

    from avocadoia_modelo import CLASES, ETIQUETAS_VISIBLES
    from avocadoia_modelo.explicacion import gradcam_pp, modelo_mapa, mosaico, softmax

    filas = [f for f in leer_csv(os.path.join(repo_datos, "campo", "manifiesto_campo.csv")) if f["estado"] == "test_campo"]
    if not filas:
        raise ValueError("no hay fotos test_campo: ejecute `campo-etl`")
    modelo = keras.models.load_model(os.path.join(salida, "experimentos", id_, "mejor.keras"))
    ruta_cal = os.path.join(repo_datos, "calibracion", id_, "calibracion.json")
    temperatura = leer_json(ruta_cal)["temperatura"] if os.path.exists(ruta_cal) else 1.0
    tam = cfg["entrada"]["tamano"]
    x = np.stack([np.asarray(cargar_224(os.path.join(raiz_modelo, f["ruta"]), tam), dtype=np.uint8) for f in filas])
    y = np.array([CLASES.index(f["clase"]) for f in filas])
    probs = softmax(modelo.predict(x.astype(np.float32), batch_size=16, verbose=0), temperatura)
    umbral = cfg["calibracion"]["umbral"]
    res = metricas_campo(y, probs, umbral)
    res.update(corrida=id_, temperatura=temperatura, confianza_calibrada=os.path.exists(ruta_cal),
               fecha=datetime.date.today().isoformat(), validacion_experta="pendiente",
               advertencia="Prueba de campo independiente: no se usa para entrenar, elegir ni calibrar (FR-028).")
    pred = probs.argmax(1)
    destino = os.path.join(repo_datos, "campo", id_)
    escribir_csv(os.path.join(destino, "predicciones_campo.csv"), COLUMNAS_PREDICCIONES, [
        {"ruta": f["ruta"], "grupo_similitud": f["grupo_similitud"], "clase_real": f["clase"],
         "clase_predicha": CLASES[pred[i]], "confianza": round(float(probs[i].max()), 4),
         "no_concluyente": "si" if probs[i].max() < umbral else "no",
         **{f"p_{c}": round(float(probs[i][k]), 4) for k, c in enumerate(CLASES)},
         "acierto": "si" if pred[i] == y[i] else "no"} for i, f in enumerate(filas)])
    escribir_json(os.path.join(destino, "evaluacion_campo.json"), res)
    mapas = gradcam_pp(modelo, x, pred, modelo_mapa(modelo))
    for k in range(0, len(filas), 10):
        sel = list(range(k, min(k + 10, len(filas))))
        titulos = [f"{os.path.basename(filas[i]['ruta'])} · pred {ETIQUETAS_VISIBLES[pred[i]][:26]} · "
                   f"{probs[i].max():.2f}" for i in sel]
        mosaico(x[sel], mapas[sel], titulos, os.path.join(destino, f"mosaico_gradcam_campo_{k // 10 + 1:02d}.png"),
                f"Prueba de campo · Grad-CAM++ · fotos {k + 1}–{sel[-1] + 1}")
    return res
