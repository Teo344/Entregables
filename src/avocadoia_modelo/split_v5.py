"""Split v5 PROPUESTO: corrige el split experimental v4 sin copiar imágenes (punto 1, 2026-11-10).

Reglas, en orden (cada cambio queda en cambios_v5.csv con su motivo):
  1. Licencia y calidad (FR-026, FR-027): se excluyen `sano_web` (sin licencia) y `avocare` (copias aumentadas).
  2. Partición del artículo: las fuentes con `particion_origen = si` en config/fuentes.csv (Flores et al., 2026)
     conservan la partición train/val/test publicada por sus autores.
  3. Artículo completo: se agregan las imágenes utilizables de 002 del artículo de Flores et al. (2026) que faltan
     en el v4, con su partición original: los pedúnculos SANOS (`mdpi_pedunculo_sano`, clase sano) y las de
     anillado de val y test (`mdpi_pedunculo`; el v4 solo tomó las de train). Sin los sanos, «pedúnculo» es la única
     clase con primeros planos del tallo y el modelo aprende el encuadre (prueba de campo: sensibilidad 0 %).
  4. Ráfaga de Herrera y Marín: las 16 fotos (una sesión de ~40 s) forman un solo grupo.
  5. Frutos: todo grupo de 002 repartido en varias particiones se reasigna COMPLETO, en orden determinista
     (semilla 42), a la partición con mayor déficit respecto de la proporción objetivo 70/15/15 de su clase
     (partición estratificada por grupos). Ningún fruto aparece en dos particiones y las proporciones se mantienen;
     la regla de mayoría (`consolidar_grupos`) se descartó porque enviaba casi todo a train.

Las rutas quedan relativas a la carpeta Modelo/ (las del v4 apuntan a su copia dentro de Evidencia_Tesis_Aguacate).
Es una PROPUESTA para que el responsable del ETL la revise y adopte; no reemplaza al v4 por sí sola.
"""

import datetime
import hashlib
import os
from collections import Counter, defaultdict

from avocadoia_datos.es_csv import escribir_csv, escribir_json

from avocadoia_modelo import CLASES, PARTICIONES
from avocadoia_modelo import manifiesto as mm

CARPETA_DE_CLASE = {"sano": "AGUACATESANOS", "antracnosis": "ANTRACNOSIS", "pedunculo": "PEDUNCULO"}
COLUMNAS = ("ruta_origen", "ruta_destino", "clase_original", "conjunto", "sha256", "estado_etiqueta",
            "grupo_duplicacion_escena", "fuente", "licencia", "origen")
COLUMNAS_CAMBIOS = ("sha256", "ruta", "clase", "accion", "motivo", "particion_antes", "particion_despues")
GRUPO_HERRERA = "herrera_marin:sesion_2026-05-22"
FUENTES_ARTICULO = ("mdpi_pedunculo_sano", "mdpi_pedunculo")


def particion_de_articulo(fila, cfg002, por_sha):
    """Partición publicada por los autores si la fuente la tiene (particion_origen = si); si no, None."""
    fuente = cfg002.fuente_por_nombre(fila["fuente"])
    reg = por_sha.get(fila["sha256"])
    if fuente is not None and fuente.particion_origen == "si" and reg and reg.get("particion_origen") in PARTICIONES:
        return reg["particion_origen"]
    return None


def consolidar_grupos(filas, fijas=frozenset()):
    """Mueve cada grupo repartido a su partición mayoritaria (empate → orden train, val, test).

    `fijas`: shas cuya partición no se mueve (partición del artículo). Devuelve [(fila, antes, después)].
    """
    por_grupo = defaultdict(list)
    for f in filas:
        por_grupo[f["grupo"]].append(f)
    movidas = []
    for grupo, miembros in sorted(por_grupo.items()):
        particiones = Counter(f["particion"] for f in miembros)
        if len(particiones) < 2:
            continue
        fijadas = {f["particion"] for f in miembros if f["sha256"] in fijas}
        if fijadas:
            destino = sorted(fijadas, key=PARTICIONES.index)[0]
        else:
            destino = max(PARTICIONES, key=lambda p: (particiones[p], -PARTICIONES.index(p)))
        for f in miembros:
            if f["particion"] != destino:
                movidas.append((f, f["particion"], destino))
                f["particion"] = destino
    return movidas


def reasignar_grupos_estratificado(filas, fijas=frozenset(), objetivo=(0.70, 0.15, 0.15), semilla=42):
    """Reasigna cada grupo repartido (completo) a la partición con mayor déficit frente al objetivo de su clase.

    Las filas de grupos no repartidos y las de partición fija cuentan como ya asignadas. Devuelve
    [(fila, antes, después)] solo de las filas que cambian de partición.
    """
    por_grupo = defaultdict(list)
    for f in filas:
        por_grupo[f["grupo"]].append(f)
    repartidos = [g for g, m in por_grupo.items()
                  if len({f["particion"] for f in m}) > 1 and not any(f["sha256"] in fijas for f in m)]
    en_repartidos = {id(f) for g in repartidos for f in por_grupo[g]}
    total = Counter(f["clase"] for f in filas)
    cuenta = Counter((f["clase"], f["particion"]) for f in filas if id(f) not in en_repartidos)
    orden = sorted(repartidos, key=lambda g: hashlib.sha256(f"{semilla}|{g}".encode()).hexdigest())
    movidas = []
    for g in orden:
        miembros = por_grupo[g]
        clase = Counter(f["clase"] for f in miembros).most_common(1)[0][0]
        destino = max(PARTICIONES, key=lambda p: (objetivo[PARTICIONES.index(p)] * total[clase] - cuenta[(clase, p)],
                                                  -PARTICIONES.index(p)))
        for f in miembros:
            if f["particion"] != destino:
                movidas.append((f, f["particion"], destino))
                f["particion"] = destino
            cuenta[(f["clase"], destino)] += 1
    return movidas


def construir(cfg, filas_v4, prefijo_v4, cfg002, por_sha, filas_002):
    cambios = []

    def cambio(f, accion, motivo, antes="", despues=""):
        cambios.append({"sha256": f["sha256"], "ruta": f["ruta"], "clase": f["clase"], "accion": accion,
                        "motivo": motivo, "particion_antes": antes, "particion_despues": despues})

    normalizadas = mm.normalizar(filas_v4, cfg)
    entrada = Counter((f["particion"], f["clase"]) for f in normalizadas)
    conservadas, excluidas = mm.filtrar(normalizadas, cfg, cfg002, por_sha)
    for f in excluidas:
        cambio(f, "excluida", f["motivo"], f["particion"])

    filas = []
    for f in conservadas:
        reg = por_sha.get(f["sha256"])
        f = {**f, "ruta": f"{prefijo_v4}/{f['ruta']}", "origen": "v4",
             "grupo": (reg or {}).get("grupo") or f["grupo"] or f"sha256:{f['sha256']}"}
        if f["fuente"] == "herrera_marin":
            f["grupo"] = GRUPO_HERRERA
        filas.append(f)

    shas_v4 = {f["sha256"] for f in normalizadas}
    for reg in filas_002:
        if (reg.get("fuente") in FUENTES_ARTICULO and reg.get("canonica") == "si"
                and reg.get("estado") in ("provisional", "elegible") and reg["sha256"] not in shas_v4
                and reg.get("particion_origen") in PARTICIONES):
            fuente = cfg002.fuente_por_nombre(reg["fuente"])
            f = {"ruta": reg["ruta"], "ruta_origen": reg["ruta"], "clase": reg["clase_efectiva"], "particion": "",
                 "sha256": reg["sha256"], "fuente": reg["fuente"], "licencia": fuente.licencia,
                 "estado_etiqueta": "ETIQUETA_PROVISIONAL", "grupo": reg.get("grupo") or reg["sha256"][:16],
                 "origen": "agregada_002"}
            filas.append(f)
            cambio(f, "agregada", f"completar_articulo:{reg['fuente']}")

    fijas = set()
    for f in filas:
        art = particion_de_articulo(f, cfg002, por_sha)
        if art:
            fijas.add(f["sha256"])
            if f["particion"] != art:
                if f["particion"]:
                    cambio(f, "movida", "particion_del_articulo", f["particion"], art)
                f["particion"] = art
    for f in filas:  # las agregadas quedan registradas con su partición final
        if f["origen"] == "agregada_002":
            for c in cambios:
                if c["sha256"] == f["sha256"] and c["accion"] == "agregada":
                    c["particion_despues"] = f["particion"]
    for f, antes, despues in reasignar_grupos_estratificado(filas, frozenset(fijas)):
        motivo = "rafaga_herrera_marin" if f["grupo"] == GRUPO_HERRERA else "fruto_en_varias_particiones"
        cambio(f, "movida", motivo, antes, despues)

    salida = [{"ruta_origen": f["ruta_origen"], "ruta_destino": f["ruta"], "clase_original": CARPETA_DE_CLASE[f["clase"]],
               "conjunto": f["particion"], "sha256": f["sha256"], "estado_etiqueta": f["estado_etiqueta"],
               "grupo_duplicacion_escena": f["grupo"], "fuente": f["fuente"], "licencia": f["licencia"],
               "origen": f["origen"]} for f in sorted(filas, key=lambda x: (PARTICIONES.index(x["particion"]),
                                                                            CLASES.index(x["clase"]), x["ruta"]))]
    return salida, cambios, entrada


def comprobaciones(salida):
    particiones_por_grupo, particiones_por_sha = defaultdict(set), defaultdict(set)
    for f in salida:
        particiones_por_grupo[f["grupo_duplicacion_escena"]].add(f["conjunto"])
        particiones_por_sha[f["sha256"]].add(f["conjunto"])
    return {"grupos_en_varias_particiones": sum(len(p) > 1 for p in particiones_por_grupo.values()),
            "sha_en_varias_particiones": sum(len(p) > 1 for p in particiones_por_sha.values()),
            "fuentes_sin_licencia": sorted({f["fuente"] for f in salida if f["fuente"] in ("sano_web",)}),
            "avocare": sum(f["fuente"].startswith("avocare") for f in salida)}


def tabla(conteo):
    return {p: {c: conteo.get((p, c), 0) for c in CLASES} for p in PARTICIONES}


def escribir(destino, salida, cambios, entrada, huella_v4):
    os.makedirs(destino, exist_ok=True)
    escribir_csv(os.path.join(destino, "manifiesto_v5.csv"), COLUMNAS, salida)
    escribir_csv(os.path.join(destino, "cambios_v5.csv"), COLUMNAS_CAMBIOS, cambios)
    despues = Counter((f["conjunto"], {v: k for k, v in CARPETA_DE_CLASE.items()}[f["clase_original"]]) for f in salida)
    res = {"fecha": datetime.date.today().isoformat(), "huella_v4": huella_v4, "estado": "propuesta",
           "entrada_v4": tabla(entrada), "v5": tabla(despues), "total_v4": sum(entrada.values()), "total_v5": len(salida),
           "cambios": {f"{a}:{m}": n for (a, m), n in sorted(Counter((c["accion"], c["motivo"]) for c in cambios).items())},
           "por_fuente": dict(Counter(f["fuente"] for f in salida)), "comprobaciones": comprobaciones(salida)}
    escribir_json(os.path.join(destino, "resumen_v5.json"), res)
    return res
