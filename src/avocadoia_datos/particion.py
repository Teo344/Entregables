"""Partición 70/15/15 por clase y fuente, por grupos, con relleno de déficit (US3, research D7)."""

import os
from collections import Counter, defaultdict
from datetime import datetime

from avocadoia_datos import muestra as mod_muestra
from avocadoia_datos.clases import CLASES, PARTICIONES
from avocadoia_datos.config import ErrorPrecondicion
from avocadoia_datos.es_csv import escribir_csv, escribir_json, sha256_archivo
from avocadoia_datos.inventario import COLUMNAS as COLUMNAS_MANIFIESTO

COLUMNAS = ("id_contenido", "clase", "fuente", "grupo", "particion", "origen_asignacion", "ruta")
_PRIORIDAD_ORIGEN = {"test": 0, "val": 1, "train": 2}


def mayor_resto(total, pesos):
    """Reparte `total` unidades enteras en proporción a `pesos` (método del mayor resto)."""
    suma = sum(pesos.values())
    if total <= 0 or suma <= 0:
        return {k: 0 for k in pesos}
    exactos = {k: total * v / suma for k, v in pesos.items()}
    enteros = {k: int(v) for k, v in exactos.items()}
    orden = list(pesos)
    resto = sorted(orden, key=lambda k: (-(exactos[k] - enteros[k]), orden.index(k)))
    for k in resto[: total - sum(enteros.values())]:
        enteros[k] += 1
    return enteros


def _redondeo_matriz(filas_tam, columnas_tam):
    """Matriz entera fuente × partición cuyas sumas por fila y columna coinciden con las dadas."""
    total = sum(filas_tam.values())
    exactos = {(f, c): filas_tam[f] * columnas_tam[c] / total for f in filas_tam for c in columnas_tam}
    m = {k: int(v) for k, v in exactos.items()}
    falta_f = {f: filas_tam[f] - sum(m[(f, c)] for c in columnas_tam) for f in filas_tam}
    falta_c = {c: columnas_tam[c] - sum(m[(f, c)] for f in filas_tam) for c in columnas_tam}
    celdas = sorted(exactos, key=lambda k: (-(exactos[k] - m[k]), k))
    for _ in range(2):  # primero por mayor resto; luego cualquier celda con hueco
        for f, c in celdas:
            if falta_f[f] > 0 and falta_c[c] > 0:
                m[(f, c)] += 1
                falta_f[f] -= 1
                falta_c[c] -= 1
    return m


def asignar(filas_muestra, config):
    """Devuelve {id_contenido: (particion, origen_asignacion)} para la muestra (sin test_campo)."""
    asignacion = {}
    for clase in CLASES:
        filas = [f for f in filas_muestra if f["clase_efectiva"] == clase]
        if not filas:
            continue
        cuotas = mayor_resto(len(filas), {p: config.proporciones[p] for p in PARTICIONES})

        por_grupo = defaultdict(list)
        for f in filas:
            por_grupo[f["grupo"]].append(f)

        fijas = Counter()
        libres = defaultdict(list)  # fuente → [grupo]
        for g, miembros in sorted(por_grupo.items()):
            origenes = sorted({m["particion_origen"] for m in miembros if m["particion_origen"]},
                              key=_PRIORIDAD_ORIGEN.get)
            if origenes:
                for m in miembros:
                    asignacion[m["id_contenido"]] = (origenes[0], "fuente")
                fijas[origenes[0]] += len(miembros)
            else:
                libres[min(m["fuente"] for m in miembros)].append(g)

        total_libre = sum(len(por_grupo[g]) for gs in libres.values() for g in gs)
        if not total_libre:
            continue
        deficit = {p: max(0, cuotas[p] - fijas[p]) for p in PARTICIONES}
        if sum(deficit.values()) == 0:
            deficit = {p: config.proporciones[p] for p in PARTICIONES}
        deficit = mayor_resto(total_libre, deficit)

        tam_fuente = {fu: sum(len(por_grupo[g]) for g in gs) for fu, gs in sorted(libres.items())}
        matriz = _redondeo_matriz(tam_fuente, deficit)

        for fuente, gs in sorted(libres.items()):
            restante = {p: matriz[(fuente, p)] for p in PARTICIONES}
            orden = sorted(gs, key=lambda g: (mod_muestra.clave_estable(config.semilla, "particion", clase, g), g))
            for g in orden:
                tam = len(por_grupo[g])
                destino = max(PARTICIONES, key=lambda p: (restante[p] >= tam, restante[p], -PARTICIONES.index(p)))
                restante[destino] -= tam
                for m in por_grupo[g]:
                    asignacion[m["id_contenido"]] = (destino, "estratificada")
    return asignacion


def ejecutar(manifiesto, config, salida, definitiva=False):
    """Selecciona la muestra, la particiona y escribe particion.csv/.json y el manifiesto actualizado."""
    if not manifiesto:
        raise ErrorPrecondicion("No hay manifiesto: ejecute primero `inventario`.")

    ids, faltantes, reserva = mod_muestra.seleccionar(manifiesto, config)
    if definitiva:
        pendientes = Counter(f["clase_efectiva"] for f in manifiesto
                             if f["id_contenido"] in ids and f["canonica"] == "si" and f["estado"] == "provisional")
        if pendientes:
            detalle = ", ".join(f"{c}: {n}" for c, n in sorted(pendientes.items()))
            raise ErrorPrecondicion(f"No se puede generar la partición definitiva; imágenes provisionales "
                                    f"(validación o licencia pendiente) por clase: {detalle}")

    filas_muestra = [f for f in manifiesto if f["id_contenido"] in ids and f["canonica"] == "si"]
    asignacion = asignar(filas_muestra, config)

    salida_filas = [
        {"id_contenido": f["id_contenido"], "clase": f["clase_efectiva"], "fuente": f["fuente"], "grupo": f["grupo"],
         "particion": asignacion[f["id_contenido"]][0], "origen_asignacion": asignacion[f["id_contenido"]][1],
         "ruta": f["ruta"]}
        for f in filas_muestra
    ]
    salida_filas += [
        {"id_contenido": f["id_contenido"], "clase": f["clase_efectiva"], "fuente": f["fuente"], "grupo": f["grupo"],
         "particion": "test_campo", "origen_asignacion": "test_campo", "ruta": f["ruta"]}
        for f in manifiesto if f["canonica"] == "si" and f["estado"] == "test_campo"
    ]
    orden_part = {p: i for i, p in enumerate(PARTICIONES + ("test_campo",))}
    orden_clase = {c: i for i, c in enumerate(CLASES)}
    salida_filas.sort(key=lambda f: (orden_part[f["particion"]], orden_clase[f["clase"]], f["id_contenido"]))

    ruta_csv = os.path.join(salida, "particion.csv")
    escribir_csv(ruta_csv, COLUMNAS, salida_filas)

    for f in manifiesto:
        f["en_muestra"] = "si" if f["id_contenido"] in ids and f["canonica"] == "si" else "no"
    escribir_csv(os.path.join(salida, "manifiesto.csv"), COLUMNAS_MANIFIESTO, manifiesto)

    provisional = any(f["estado"] == "provisional" for f in filas_muestra)
    conteos = defaultdict(Counter)
    por_fuente = defaultdict(Counter)
    for f in salida_filas:
        conteos[f["clase"]][f["particion"]] += 1
        por_fuente[f["clase"]][f["fuente"]] += 1
    metadatos = {
        "estado": "provisional" if provisional else "definitiva",
        "semilla": config.semilla,
        "proporciones": config.proporciones,
        "max_por_clase": config.max_por_clase,
        "cuotas": config.cuotas,
        "generado": datetime.now().isoformat(timespec="seconds"),
        "version_config": config.version_config,
        "conteos": {c: dict(sorted(v.items())) for c, v in sorted(conteos.items())},
        "conteos_por_fuente": {c: dict(sorted(v.items())) for c, v in sorted(por_fuente.items())},
        "faltantes_cuota": faltantes,
        "reserva": reserva,
        "huella_particion": sha256_archivo(ruta_csv),
    }
    escribir_json(os.path.join(salida, "particion.json"), metadatos)
    return salida_filas, metadatos
