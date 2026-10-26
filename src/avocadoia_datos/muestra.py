"""Selección de la muestra por cuotas de fuente (US3, research D6)."""

import hashlib
from collections import defaultdict

from avocadoia_datos.clases import CLASES

ESTADOS_CANDIDATOS = ("elegible", "provisional")


def clave_estable(semilla, *partes):
    """Orden pseudoaleatorio estable: no cambia si se agregan o quitan otros elementos."""
    texto = "\x1f".join([str(semilla), *map(str, partes)])
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def candidatas(manifiesto):
    return [f for f in manifiesto if f["canonica"] == "si" and f["estado"] in ESTADOS_CANDIDATOS]


def seleccionar(manifiesto, config):
    """Devuelve (ids_en_muestra, faltantes, reserva).

    - faltantes: {clase: {fuente: cuota_no_cubierta}}
    - reserva: {clase: {fuente: imágenes_candidatas_fuera_de_la_muestra}}
    """
    por_clase_fuente = defaultdict(list)
    for fila in candidatas(manifiesto):
        por_clase_fuente[(fila["clase_efectiva"], fila["fuente"])].append(fila)

    elegidas, faltantes, reserva = set(), defaultdict(dict), defaultdict(dict)
    for clase in CLASES:
        for fuente_nombre, cuota in sorted(config.cuotas.get(clase, {}).items()):
            filas = por_clase_fuente.get((clase, fuente_nombre), [])
            fuente = config.fuente_por_nombre(fuente_nombre)
            if fuente is not None and fuente.particion_origen == "si":
                tomadas = filas  # su partición viene de la fuente: entran completas
            else:
                tomadas = _por_grupos(filas, cuota, config.semilla, clase, fuente_nombre)
            elegidas.update(f["id_contenido"] for f in tomadas)
            if len(tomadas) < cuota:
                faltantes[clase][fuente_nombre] = cuota - len(tomadas)
        # Fuentes sin cuota en la clase: todo queda en reserva.
        for (c, fuente_nombre), filas in por_clase_fuente.items():
            if c == clase:
                fuera = sum(1 for f in filas if f["id_contenido"] not in elegidas)
                if fuera:
                    reserva[clase][fuente_nombre] = fuera
    return elegidas, {k: dict(v) for k, v in faltantes.items()}, {k: dict(sorted(v.items())) for k, v in reserva.items()}


def _por_grupos(filas, cuota, semilla, clase, fuente):
    """Primero una imagen por grupo; si falta, segundas fotos, en orden estable."""
    por_grupo = defaultdict(list)
    for fila in filas:
        por_grupo[fila["grupo"]].append(fila)
    orden_grupos = sorted(por_grupo, key=lambda g: (clave_estable(semilla, clase, fuente, g), g))
    for g in orden_grupos:
        por_grupo[g].sort(key=lambda f: (clave_estable(semilla, f["id_contenido"]), f["id_contenido"]))

    tomadas = []
    ronda = 0
    while len(tomadas) < cuota:
        agregadas = 0
        for g in orden_grupos:
            if ronda < len(por_grupo[g]):
                tomadas.append(por_grupo[g][ronda])
                agregadas += 1
                if len(tomadas) == cuota:
                    break
        if agregadas == 0:
            break
        ronda += 1
    return tomadas
