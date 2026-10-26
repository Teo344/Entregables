"""Grupos de imágenes que deben repartirse juntas (mismo fruto o casi duplicados)."""

import os
import re

from avocadoia_datos.es_csv import leer_csv

# hass_T10_d14_041_a_3_<hash>.jpg → tratamiento T10, fruto 041 (el día y el lado no cuentan).
_PATRON_HASS = re.compile(r"hass_(T\w+?)_d\d+_(\d+)_")


def grupo_por_regla(nombre_archivo, regla):
    if regla == "hass":
        m = _PATRON_HASS.match(nombre_archivo)
        if m:
            return f"hass:{m.group(1)}:{m.group(2)}"
    return None


def cargar_confirmados(ruta):
    """{grupo_confirmado: [rutas]} desde datos/curacion/casi_duplicados_confirmados.csv."""
    grupos = {}
    for fila in leer_csv(ruta):
        grupos.setdefault(fila["grupo"], []).append(fila["ruta"])
    return grupos


class _UnionFind:
    def __init__(self):
        self.padre = {}

    def buscar(self, x):
        self.padre.setdefault(x, x)
        raiz = x
        while self.padre[raiz] != raiz:
            raiz = self.padre[raiz]
        while self.padre[x] != raiz:
            self.padre[x], x = raiz, self.padre[x]
        return raiz

    def unir(self, a, b):
        ra, rb = self.buscar(a), self.buscar(b)
        if ra != rb:
            # El representante es el identificador menor, para que el resultado sea determinista.
            menor, mayor = sorted((ra, rb))
            self.padre[mayor] = menor


def asignar_grupos(filas, confirmados):
    """Devuelve {ruta: grupo}.

    `filas` necesita `ruta`, `id_contenido` y `regla_grupo`. Las copias exactas comparten
    `id_contenido` y por tanto grupo.
    """
    uf = _UnionFind()
    clave_de_ruta = {}
    for fila in filas:
        clave = grupo_por_regla(os.path.basename(fila["ruta"]), fila.get("regla_grupo", "ninguna"))
        clave = clave or fila["id_contenido"]
        uf.unir(clave, fila["id_contenido"])
        clave_de_ruta[fila["ruta"]] = fila["id_contenido"]

    for rutas in confirmados.values():
        presentes = [clave_de_ruta[r] for r in rutas if r in clave_de_ruta]
        for otra in presentes[1:]:
            uf.unir(presentes[0], otra)

    # Un grupo con regla se nombra por su regla (p. ej. hass:T10:041) aunque se una a ids.
    nombre = {}
    for fila in filas:
        raiz = uf.buscar(fila["id_contenido"])
        regla = grupo_por_regla(os.path.basename(fila["ruta"]), fila.get("regla_grupo", "ninguna"))
        if regla:
            nombre[raiz] = min(nombre.get(raiz, regla), regla)
    return {f["ruta"]: nombre.get(uf.buscar(f["id_contenido"]), uf.buscar(f["id_contenido"])) for f in filas}
