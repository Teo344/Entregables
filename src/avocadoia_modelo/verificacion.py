"""Verificación previa al entrenamiento (research M4, M19; data-model.md §2). Sin TensorFlow.

Orden: conteos de entrada → filtros de licencia y calidad → sobre las conservadas: faltantes, ilegibles,
SHA cruzados entre particiones, fuga por fruto (aviso) y etiquetas provisionales (aviso).
"""

import datetime
import os
from collections import Counter, defaultdict

from PIL import Image

from avocadoia_datos.es_csv import escribir_json, sha256_archivo

from avocadoia_modelo import CLASES, PARTICIONES
from avocadoia_modelo import manifiesto as mm

ARCHIVO = "verificacion.json"
ARCHIVO_EXCLUIDAS = "excluidas.csv"


def _conteos(filas, clave_clase="clase"):
    c = Counter((f["particion"], f[clave_clase]) for f in filas)
    claves = sorted({k for _, k in c})
    return {p: {k: c[(p, k)] for k in claves} for p in PARTICIONES}


def _legible(ruta):
    try:
        with Image.open(ruta) as im:
            im.verify()
        return True
    except Exception:  # noqa: BLE001 - cualquier fallo de decodificación cuenta como ilegible
        return False


def _resumen_excluidas(excluidas):
    por_motivo = Counter(f["motivo"] for f in excluidas)
    por_fuente = {}
    for f in excluidas:
        clave = f["fuente"] or "(sin fuente)"
        d = por_fuente.setdefault(clave, {"uso_academico": f["uso_academico"], "motivo": f["motivo"], "n": 0})
        d["n"] += 1
    return {"total": len(excluidas), "por_motivo": dict(sorted(por_motivo.items())),
            "por_fuente": dict(sorted(por_fuente.items())), "por_particion_clase": _conteos(excluidas)}


def _fuga_por_fruto(filas, por_sha):
    """Grupos de 002 (por SHA) con imágenes en más de una partición."""
    particiones = defaultdict(set)
    miembros = defaultdict(list)
    for f in filas:
        reg = por_sha.get(f["sha256"])
        if reg and reg.get("grupo"):
            particiones[reg["grupo"]].add(f["particion"])
            miembros[reg["grupo"]].append(f)
    cruzados = sorted(g for g, ps in particiones.items() if len(ps) > 1)
    imgs = [f for g in cruzados for f in miembros[g]]
    return {"grupos": len(cruzados), "imagenes": len(imgs),
            "imagenes_test": sum(f["particion"] == "test" for f in imgs),
            "detalle": [{"grupo": g, "particiones": sorted(particiones[g]), "n": len(miembros[g])}
                        for g in cruzados]}


def verificar(cfg, manifiesto, raiz, repo_datos, salida=None, comprobar_legibilidad=True):
    """Ejecuta la verificación, escribe verificacion.json y excluidas.csv y devuelve el informe."""
    filas = mm.leer_entrada(manifiesto)
    informe = {"ruta_manifiesto": manifiesto, "huella_manifiesto": mm.huella_manifiesto(manifiesto),
               "raiz_imagenes": raiz, "fecha": datetime.datetime.now().isoformat(timespec="seconds"),
               "faltantes": [], "ilegibles": [], "sha_cruzados": [], "clases_desconocidas": [],
               "excluidas": {"total": 0}, "conteos": {}, "conteos_entrada": {}}
    desconocidas = mm.clases_desconocidas(filas, cfg)
    if desconocidas:
        informe.update(clases_desconocidas=desconocidas, estado="fallida")
        escribir_json(os.path.join(repo_datos, ARCHIVO), informe)
        return informe

    normalizadas = mm.normalizar(filas, cfg)
    informe["conteos_entrada"] = _conteos(normalizadas)
    cfg002, por_sha = mm.contexto_002(cfg)
    conservadas, excluidas = mm.filtrar(normalizadas, cfg, cfg002, por_sha)
    informe["excluidas"] = _resumen_excluidas(excluidas)
    mm.escribir_excluidas(os.path.join(repo_datos, ARCHIVO_EXCLUIDAS), excluidas)

    for f in conservadas:
        ruta = os.path.join(raiz, f["ruta"])
        if not os.path.isfile(ruta):
            informe["faltantes"].append(f["ruta"])
            continue
        if comprobar_legibilidad and not _legible(ruta):
            informe["ilegibles"].append(f["ruta"])
            continue
        if not f["sha256"]:
            f["sha256"] = sha256_archivo(ruta)

    particiones_por_sha = defaultdict(set)
    for f in conservadas:
        if f["sha256"]:
            particiones_por_sha[f["sha256"]].add(f["particion"])
    informe["sha_cruzados"] = sorted(s for s, ps in particiones_por_sha.items() if len(ps) > 1)
    informe["conteos"] = {p: {c: sum(f["particion"] == p and f["clase"] == c for f in conservadas) for c in CLASES}
                          for p in PARTICIONES}
    informe["total"] = len(conservadas)
    informe["fuga_por_fruto"] = _fuga_por_fruto(conservadas, por_sha)
    informe["etiquetas_provisionales"] = {
        p: sum(f["particion"] == p and "provisional" in f["estado_etiqueta"].lower() for f in conservadas)
        for p in PARTICIONES}

    if informe["faltantes"] or informe["ilegibles"] or informe["sha_cruzados"]:
        informe["estado"] = "fallida"
    elif informe["fuga_por_fruto"]["grupos"] or any(informe["etiquetas_provisionales"].values()):
        informe["estado"] = "ok_con_avisos"
    else:
        informe["estado"] = "ok"

    if salida and informe["estado"] != "fallida":
        ruta_norm = os.path.join(salida, "manifiestos", f"{informe['huella_manifiesto'][:8]}.csv")
        mm.escribir_normalizado(ruta_norm, conservadas)
        informe["ruta_manifiesto_normalizado"] = ruta_norm
    escribir_json(os.path.join(repo_datos, ARCHIVO), informe)
    return informe
