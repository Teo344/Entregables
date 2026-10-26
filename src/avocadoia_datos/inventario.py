"""Inventario trazable de las carpetas de clase (US1) → datos/manifiesto.csv."""

import io
import os
from collections import Counter
from datetime import datetime

from PIL import Image

from avocadoia_datos import grupos
from avocadoia_datos.clases import CARPETA_CAMPO, CARPETAS, CLASES, PARTICIONES, es_imagen
from avocadoia_datos.es_csv import escribir_csv, escribir_json, leer_csv, sha256_bytes

COLUMNAS = ("ruta", "id_contenido", "sha256", "clase_propuesta", "clase_efectiva", "fuente", "licencia",
            "uso_academico", "ancho", "alto", "formato", "modo", "particion_origen", "grupo", "canonica",
            "duplicado_de", "validacion", "estado", "en_muestra", "motivo")

DECISIONES_VALIDAS = ("aceptada", "rechazada", "reasignada", "mixto")
_ORIENTACION_ROTADA = (5, 6, 7, 8)


def leer_imagen(datos):
    """(ancho, alto, formato, modo) con la orientación EXIF aplicada, o None si no se decodifica."""
    try:
        im = Image.open(io.BytesIO(datos))
        formato, modo = im.format, im.mode
        orientacion = im.getexif().get(0x0112, 1)
        im.load()
    except Exception:
        return None
    ancho, alto = im.size
    if orientacion in _ORIENTACION_ROTADA:
        ancho, alto = alto, ancho
    return ancho, alto, formato, modo


def _recorrer(raiz_imagenes):
    """(ruta_relativa, clase) de cada imagen en las carpetas de clase y de campo."""
    bases = [(CARPETAS[c], c) for c in CLASES]
    bases += [(f"{CARPETA_CAMPO}/{CARPETAS[c]}", c) for c in CLASES]
    for base, clase in bases:
        absoluta = os.path.join(raiz_imagenes, base)
        for raiz, carpetas, archivos in os.walk(absoluta):
            carpetas.sort()
            for nombre in sorted(archivos):
                if es_imagen(nombre):
                    ruta = os.path.relpath(os.path.join(raiz, nombre), raiz_imagenes).replace(os.sep, "/")
                    yield ruta, clase


def _particion_de_ruta(ruta):
    for parte in ruta.split("/")[:-1]:
        if parte in PARTICIONES:
            return parte
    return ""


def ultimas_decisiones(ruta_decisiones):
    """{id_contenido: decisión} con la más reciente por fecha (a igual fecha, la última fila)."""
    ultimas = {}
    for orden, fila in enumerate(leer_csv(ruta_decisiones)):
        clave = (fila.get("fecha", ""), orden)
        previa = ultimas.get(fila["id_contenido"])
        if previa is None or clave >= previa[0]:
            ultimas[fila["id_contenido"]] = (clave, fila)
    return {k: v[1] for k, v in ultimas.items()}


def cargar_exclusiones(ruta):
    """{ruta: detalle} desde datos/curacion/exclusiones_revision.csv (si existe)."""
    return {f["ruta"]: f.get("detalle") or f.get("motivo", "") for f in leer_csv(ruta)}


def _estado(fila, fuente, decision, exclusion):
    if fila["formato"] == "":
        return "excluida_invalida", "No se puede decodificar la imagen"
    if fila["_conflicto"]:
        return "excluida_conflicto", "El mismo contenido aparece en clases distintas"
    if fila["canonica"] == "no":
        return "duplicada", f"Copia exacta de {fila['duplicado_de']}"
    # La decisión del experto prevalece sobre la exclusión por revisión.
    if exclusion is not None and decision not in ("aceptada", "reasignada"):
        return "excluida_revision", exclusion
    if decision in ("rechazada", "mixto"):
        return "rechazada", f"Experto: {decision}"
    if fuente is not None and fuente.rol == "test_campo":
        return "test_campo", "Reservada para la prueba de campo"
    pendientes = []
    if decision not in ("aceptada", "reasignada"):
        pendientes.append("validación pendiente")
    if fuente is None or fuente.uso_academico != "si":
        pendientes.append("licencia pendiente" if fuente else "fuente desconocida")
    if pendientes:
        return "provisional", "; ".join(pendientes)
    return "elegible", ""


def construir(config, raiz_imagenes, salida, ruta_confirmados):
    """Calcula las filas del manifiesto; devuelve (filas, metadatos)."""
    previas = {f["ruta"]: f.get("en_muestra", "no") for f in leer_csv(os.path.join(salida, "manifiesto.csv"))}
    decisiones = ultimas_decisiones(os.path.join(salida, "validacion", "decisiones.csv"))

    filas = []
    for ruta, clase in _recorrer(raiz_imagenes):
        with open(os.path.join(raiz_imagenes, ruta), "rb") as fh:
            datos = fh.read()
        sha = sha256_bytes(datos)
        info = leer_imagen(datos)
        fuente = config.fuente_de(ruta)
        filas.append({
            "ruta": ruta,
            "id_contenido": sha[:16],
            "sha256": sha,
            "clase_propuesta": clase,
            "fuente": fuente.fuente if fuente else "desconocida",
            "licencia": fuente.licencia if fuente else "pendiente",
            "uso_academico": fuente.uso_academico if fuente else "pendiente",
            "ancho": info[0] if info else "",
            "alto": info[1] if info else "",
            "formato": info[2] if info else "",
            "modo": info[3] if info else "",
            "particion_origen": _particion_de_ruta(ruta) if fuente and fuente.particion_origen == "si" else "",
            "regla_grupo": fuente.regla_grupo if fuente else "ninguna",
            "_fuente": fuente,
        })

    # Copias exactas y conflictos de etiqueta por contenido.
    por_sha = {}
    for fila in filas:
        por_sha.setdefault(fila["sha256"], []).append(fila)
    for copias in por_sha.values():
        conflicto = len({f["clase_propuesta"] for f in copias}) > 1
        canonica = min(copias, key=lambda f: f["ruta"])
        for fila in copias:
            fila["_conflicto"] = conflicto
            fila["canonica"] = "si" if fila is canonica else "no"
            fila["duplicado_de"] = "" if fila is canonica else canonica["ruta"]

    curacion = os.path.dirname(ruta_confirmados)
    confirmados = grupos.cargar_confirmados(ruta_confirmados)
    # Grupos por similitud (mismo fruto fotografiado desde varios lados), generados por
    # scripts/curacion/agrupar_similares.py; se prefijan para no chocar con los confirmados.
    for clave, rutas in grupos.cargar_confirmados(os.path.join(curacion, "grupos_similitud.csv")).items():
        confirmados[f"sim:{clave}"] = rutas
    grupo_de = grupos.asignar_grupos(filas, confirmados)
    exclusiones = cargar_exclusiones(os.path.join(curacion, "exclusiones_revision.csv"))

    for fila in filas:
        decision = decisiones.get(fila["id_contenido"])
        tipo = decision["decision"] if decision else ""
        fila["validacion"] = tipo if tipo in DECISIONES_VALIDAS else "pendiente"
        nueva = (decision or {}).get("clase_nueva", "")
        fila["clase_efectiva"] = nueva if tipo == "reasignada" and nueva in CLASES else fila["clase_propuesta"]
        fila["grupo"] = grupo_de[fila["ruta"]]
        fila["estado"], fila["motivo"] = _estado(fila, fila["_fuente"], tipo, exclusiones.get(fila["ruta"]))
        fila["en_muestra"] = previas.get(fila["ruta"], "no") if fila["estado"] in ("elegible", "provisional") else "no"

    filas.sort(key=lambda f: f["ruta"])
    presentes = {f["id_contenido"] for f in filas}
    metadatos = {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "semilla": config.semilla,
        "version_config": config.version_config,
        "total_archivos": len(filas),
        "por_clase": dict(sorted(Counter(f["clase_propuesta"] for f in filas).items())),
        "por_estado": dict(sorted(Counter(f["estado"] for f in filas).items())),
        "por_fuente": dict(sorted(Counter(f["fuente"] for f in filas).items())),
        "grupos": len({f["grupo"] for f in filas if f["canonica"] == "si"}),
        "decisiones_ausentes": sorted(i for i in decisiones if i not in presentes),
    }
    return filas, metadatos


def escribir(filas, metadatos, salida):
    escribir_csv(os.path.join(salida, "manifiesto.csv"), COLUMNAS, filas)
    escribir_json(os.path.join(salida, "manifiesto.json"), metadatos)


def ejecutar(config, raiz_imagenes, salida, ruta_confirmados):
    filas, metadatos = construir(config, raiz_imagenes, salida, ruta_confirmados)
    escribir(filas, metadatos, salida)
    return filas, metadatos


def leer_manifiesto(salida):
    return leer_csv(os.path.join(salida, "manifiesto.csv"))
