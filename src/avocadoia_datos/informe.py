"""Informe del conjunto de datos (US4) → datos/informe.md y datos/informe.json."""

import os
from collections import Counter, defaultdict
from datetime import datetime

from avocadoia_datos.clases import CLASES, NOMBRES, PARTICIONES
from avocadoia_datos.config import ErrorPrecondicion
from avocadoia_datos.es_csv import escribir_json, leer_csv, leer_json

_ETIQUETAS_ESTADO = {
    "elegible": "Elegible (validada y con licencia)",
    "provisional": "Provisional (validación o licencia pendiente)",
    "duplicada": "Copia exacta (se conserva la canónica)",
    "excluida_conflicto": "Excluida: etiqueta en conflicto",
    "excluida_invalida": "Excluida: archivo inválido",
    "excluida_licencia": "Excluida: la fuente no permite uso académico",
    "excluida_revision": "Excluida por revisión (fuente aumentada, sin lesión visible o decisión de los autores)",
    "rechazada": "Rechazada por el experto o caso mixto",
    "test_campo": "Prueba de campo",
}


def pesos_de_clase(conteos_train):
    total = sum(conteos_train.values())
    k = len([c for c in conteos_train.values() if c])
    return {c: round(total / (k * n), 4) for c, n in conteos_train.items() if n}


def construir(manifiesto, particion, metadatos_particion, metadatos_manifiesto, advertencias, config):
    conteos = {c: {p: 0 for p in PARTICIONES + ("test_campo",)} for c in CLASES}
    por_fuente = defaultdict(lambda: defaultdict(Counter))
    for f in particion:
        conteos[f["clase"]][f["particion"]] += 1
        por_fuente[f["clase"]][f["fuente"]][f["particion"]] += 1
    train = {c: conteos[c]["train"] for c in CLASES}
    con_datos = [n for n in train.values() if n]
    muestra = [f for f in manifiesto if f.get("en_muestra") == "si"]

    return {
        "generado": datetime.now().isoformat(timespec="seconds"),
        "estado_particion": metadatos_particion.get("estado", ""),
        "semilla": config.semilla,
        "version_config": config.version_config,
        "huella_particion": metadatos_particion.get("huella_particion", ""),
        "conteos": conteos,
        "totales_particion": {p: sum(conteos[c][p] for c in CLASES) for p in PARTICIONES + ("test_campo",)},
        "conteos_por_fuente": {c: {fu: dict(v) for fu, v in sorted(por_fuente[c].items())} for c in CLASES},
        "estados_manifiesto": dict(sorted(Counter(f["estado"] for f in manifiesto).items())),
        "archivos_por_clase": dict(sorted(Counter(f["clase_propuesta"] for f in manifiesto).items())),
        "reserva": metadatos_particion.get("reserva", {}),
        "faltantes_cuota": metadatos_particion.get("faltantes_cuota", {}),
        "advertencias": dict(sorted(Counter(a["tipo"] for a in advertencias).items())),
        "razon_desbalance": round(max(con_datos) / min(con_datos), 2) if con_datos else None,
        "pesos_clase": pesos_de_clase(train),
        "aumento": config.aumento,
        "preprocesamiento": config.preprocesamiento,
        "validacion_pendiente_muestra": sum(1 for f in muestra if f["validacion"] == "pendiente"),
        "licencia_pendiente_muestra": sum(1 for f in muestra if f["uso_academico"] != "si"),
        "decisiones_ausentes": len(metadatos_manifiesto.get("decisiones_ausentes", [])),
    }


def markdown(datos):
    l = []
    estado = datos["estado_particion"]
    l.append("# Informe del conjunto de datos AvocadoIA\n")
    l.append(f"- **Generado**: {datos['generado']}")
    l.append(f"- **Estado de la partición**: **{estado}**")
    l.append(f"- **Semilla**: {datos['semilla']}")
    l.append(f"- **Versión de configuración**: `{datos['version_config'][:16]}`")
    l.append(f"- **Huella de la partición**: `{datos['huella_particion'][:16]}`\n")
    if estado == "provisional":
        l.append("> **Partición provisional.** Contiene imágenes con validación del experto o licencia "
                 "pendientes. Sirve para desarrollar y depurar el entrenamiento; ninguna métrica reportada "
                 "en la tesis puede provenir de ella (constitución §II, FR-018).\n")

    l.append("## Distribución por clase y partición\n")
    l.append("| Clase | Train | Val | Test | Total |")
    l.append("|---|---:|---:|---:|---:|")
    for c in CLASES:
        fila = datos["conteos"][c]
        total = sum(fila[p] for p in PARTICIONES)
        l.append(f"| {NOMBRES[c]} | {fila['train']} | {fila['val']} | {fila['test']} | {total} |")
    t = datos["totales_particion"]
    l.append(f"| **Total** | **{t['train']}** | **{t['val']}** | **{t['test']}** | "
             f"**{t['train'] + t['val'] + t['test']}** |\n")
    l.append("Proporción de cada partición dentro de la clase:\n")
    l.append("| Clase | Train | Val | Test |")
    l.append("|---|---:|---:|---:|")
    for c in CLASES:
        fila = datos["conteos"][c]
        total = sum(fila[p] for p in PARTICIONES) or 1
        l.append(f"| {NOMBRES[c]} | " + " | ".join(f"{100 * fila[p] / total:.1f} %" for p in PARTICIONES) + " |")
    if t["test_campo"]:
        l.append(f"\nPrueba de campo independiente (`test_campo`): {t['test_campo']} imágenes.")

    l.append("\n## Distribución por fuente\n")
    l.append("| Clase | Fuente | Train | Val | Test | Total | Reserva |")
    l.append("|---|---|---:|---:|---:|---:|---:|")
    for c in CLASES:
        for fuente, cuenta in datos["conteos_por_fuente"][c].items():
            total = sum(cuenta.get(p, 0) for p in PARTICIONES)
            reserva = datos["reserva"].get(c, {}).get(fuente, 0)
            l.append(f"| {NOMBRES[c]} | `{fuente}` | " +
                     " | ".join(str(cuenta.get(p, 0)) for p in PARTICIONES) + f" | {total} | {reserva} |")
    if any(datos["faltantes_cuota"].values()):
        l.append("\nFaltantes de cuota: " + "; ".join(
            f"{c}/{fu}: {n}" for c, v in datos["faltantes_cuota"].items() for fu, n in v.items()))

    l.append("\n## Desbalance y pesos de clase sugeridos (entrenamiento)\n")
    l.append(f"Razón de desbalance (clase mayor / menor en train): **{datos['razon_desbalance']}**\n")
    l.append("| Clase | Imágenes en train | Peso sugerido `N/(K·n_c)` |")
    l.append("|---|---:|---:|")
    for c in CLASES:
        if c in datos["pesos_clase"]:
            l.append(f"| {NOMBRES[c]} | {datos['conteos'][c]['train']} | {datos['pesos_clase'][c]} |")
    l.append("\nComo las clases están desbalanceadas, OE3 debe reportar F1 macro además de la exactitud.")

    l.append("\n## Estado del inventario\n")
    l.append("| Estado | Archivos |")
    l.append("|---|---:|")
    for e, n in datos["estados_manifiesto"].items():
        l.append(f"| {_ETIQUETAS_ESTADO.get(e, e)} | {n} |")
    reserva_total = sum(sum(v.values()) for v in datos["reserva"].values())
    l.append(f"\nReserva (elegibles fuera de la muestra): **{reserva_total}** imágenes.")
    l.append(f"En la muestra: validación pendiente {datos['validacion_pendiente_muestra']}, "
             f"licencia pendiente {datos['licencia_pendiente_muestra']}. "
             f"Decisiones del experto sobre imágenes ausentes: {datos['decisiones_ausentes']}.")

    l.append("\n## Advertencias de calidad\n")
    if datos["advertencias"]:
        l.append("| Tipo | Imágenes |")
        l.append("|---|---:|")
        for tipo, n in datos["advertencias"].items():
            l.append(f"| {tipo} | {n} |")
        l.append("\nDetalle por imagen en `datos/advertencias.csv`.")
    else:
        l.append("Sin advertencias.")

    p = datos["preprocesamiento"]
    l.append("\n## Preprocesamiento\n")
    l.append(f"Orientación EXIF aplicada, conversión a RGB (transparencia sobre blanco), redimensionado a "
             f"{p.get('tamano')} × {p.get('tamano')} px por estiramiento (LANCZOS) y JPEG de calidad "
             f"{p.get('calidad_jpeg')}. La normalización a [0, 1] se hace en el entrenamiento.")

    a = datos["aumento"]
    l.append("\n## Aumento de datos (solo entrenamiento, en línea)\n")
    l.append("| Parámetro | Valor |")
    l.append("|---|---|")
    l.append(f"| Rotación | ±{a.get('rotacion_grados')}° |")
    l.append(f"| Desplazamiento | {a.get('desplazamiento')} |")
    l.append(f"| Zoom | {a.get('zoom')} |")
    l.append(f"| Volteo horizontal / vertical | {a.get('volteo_horizontal')} / {a.get('volteo_vertical')} |")
    l.append(f"| Brillo | {a.get('brillo')} |")
    l.append("| Tono / saturación | Sin variación (la lesión se reconoce por el color) |")
    return "\n".join(l) + "\n"


def ejecutar(salida, config):
    ruta_particion = os.path.join(salida, "particion.json")
    if not os.path.exists(ruta_particion):
        raise ErrorPrecondicion("No hay partición: ejecute primero `particionar`.")
    ruta_meta_manifiesto = os.path.join(salida, "manifiesto.json")
    datos = construir(
        leer_csv(os.path.join(salida, "manifiesto.csv")),
        leer_csv(os.path.join(salida, "particion.csv")),
        leer_json(ruta_particion),
        leer_json(ruta_meta_manifiesto) if os.path.exists(ruta_meta_manifiesto) else {},
        leer_csv(os.path.join(salida, "advertencias.csv")),
        config,
    )
    escribir_json(os.path.join(salida, "informe.json"), datos)
    with open(os.path.join(salida, "informe.md"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(markdown(datos))
    return datos
