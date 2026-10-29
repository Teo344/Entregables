"""Figuras del EDA para la tesis (spec 002, research E12): PNG a 200 ppp y SVG, con nota de datos."""

import os
from collections import Counter, defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

from avocadoia_datos.clases import CLASES, PARTICIONES  # noqa: E402
from avocadoia_datos.eda import distribuciones  # noqa: E402

NOMBRE_CLASE = {"sano": "Sano", "antracnosis": "Antracnosis", "pedunculo": "Síntomas compatibles con anillado"}
COLOR_CLASE = {"sano": "#3B7D23", "antracnosis": "#8C4A1E", "pedunculo": "#C99A06"}
DPI = 200
plt.rcParams.update({"font.size": 9, "axes.titlesize": 10, "figure.titlesize": 11, "svg.hashsalt": "avocadoia"})


def _guardar(fig, carpeta, nombre, nota, svg=True):
    fig.text(0.01, 0.005, f"Datos: {nota}", fontsize=7, color="#555555", ha="left", va="bottom")
    os.makedirs(carpeta, exist_ok=True)
    rutas = [os.path.join(carpeta, f"{nombre}.png")]
    fig.savefig(rutas[0], dpi=DPI, bbox_inches="tight", metadata={"Software": None})
    if svg:
        rutas.append(os.path.join(carpeta, f"{nombre}.svg"))
        fig.savefig(rutas[1], bbox_inches="tight", metadata={"Date": None, "Creator": None})
    plt.close(fig)
    return rutas


def _colores_fuente(fuentes):
    paleta = plt.get_cmap("tab10").colors
    return {f: paleta[i % len(paleta)] for i, f in enumerate(sorted(fuentes))}


def distribucion(tabla, carpeta):
    filas = [f for f in tabla if f["fuente"] != "todas"]
    colores = _colores_fuente({f["fuente"] for f in filas})
    fig, ejes = plt.subplots(1, 3, figsize=(10, 3.6), sharey=False)
    for eje, clase in zip(ejes, CLASES):
        base = [0] * len(PARTICIONES)
        for f in (f for f in filas if f["clase"] == clase):
            valores = [int(f[p]) for p in PARTICIONES]
            eje.bar(PARTICIONES, valores, bottom=base, color=colores[f["fuente"]], label=f["fuente"])
            base = [a + b for a, b in zip(base, valores)]
        for x, total in enumerate(base):
            eje.text(x, total, str(total), ha="center", va="bottom", fontsize=8)
        eje.set_title(NOMBRE_CLASE[clase])
        eje.set_ylabel("Imágenes")
        eje.legend(fontsize=7, loc="upper right")
    fig.suptitle("Composición del conjunto final por clase, fuente y conjunto")
    fig.tight_layout()
    return _guardar(fig, carpeta, "distribucion_clase_fuente_conjunto", "datos/eda/tablas/distribucion_clase_fuente_conjunto.csv")


_MEDIDAS_CAJA = (("megapixeles", "Resolución original (megapíxeles)", True), ("proporcion", "Proporción ancho/alto", False),
                 ("brillo", "Brillo (L* medio, 0–100)", False), ("contraste", "Contraste (desv. de L*)", False),
                 ("nitidez", "Nitidez (var. del Laplaciano)", True), ("saturacion", "Saturación media (0–1)", False),
                 ("valor", "Valor HSV medio (0–1)", False), ("fondo_fraccion", "Fracción de borde uniforme (0–1)", False))


def caracteristicas(filas_caract, particion, carpeta):
    clase_de = {f["id_contenido"]: f["clase"] for f in distribuciones.conjunto_final(particion)}
    por_clase = defaultdict(lambda: defaultdict(list))
    for f in filas_caract:
        if f["id_contenido"] in clase_de:
            for m, _, _ in _MEDIDAS_CAJA:
                por_clase[m][clase_de[f["id_contenido"]]].append(float(f[m]))
    fig, ejes = plt.subplots(2, 4, figsize=(11, 5.4))
    for eje, (m, titulo, log) in zip(ejes.flat, _MEDIDAS_CAJA):
        caja = eje.boxplot([por_clase[m][c] for c in CLASES], patch_artist=True, showfliers=False, widths=0.6)
        for parche, c in zip(caja["boxes"], CLASES):
            parche.set_facecolor(COLOR_CLASE[c])
            parche.set_alpha(0.75)
        eje.set_xticks([1, 2, 3], ["Sano", "Antracnosis", "Anillado"], fontsize=8)
        eje.set_title(titulo, fontsize=8.5)
        if log:
            eje.set_yscale("log")
    fig.suptitle("Características de las imágenes originales por clase (conjunto final)")
    fig.tight_layout()
    rutas = _guardar(fig, carpeta, "caracteristicas_por_clase", "datos/eda/tablas/caracteristicas.csv")

    fig, eje = plt.subplots(figsize=(6, 3.2))
    tono = defaultdict(list)
    for f in filas_caract:
        if f["id_contenido"] in clase_de:
            tono[clase_de[f["id_contenido"]]].append(float(f["tono_medio"]))
    for c in CLASES:
        eje.hist(tono[c], bins=36, range=(0, 360), alpha=0.55, color=COLOR_CLASE[c], label=NOMBRE_CLASE[c], density=True)
    eje.set_xlabel("Tono medio (grados, media circular)")
    eje.set_ylabel("Densidad")
    eje.legend(fontsize=7)
    eje.set_title("Distribución del tono medio por clase")
    fig.tight_layout()
    return rutas + _guardar(fig, carpeta, "tono_por_clase", "datos/eda/tablas/caracteristicas.csv")


def fondo(tabla_fondo, carpeta):
    filas = [f for f in tabla_fondo if f["fuente"] != "todas" and f["fraccion_uniforme"]]
    etiquetas = [f"{NOMBRE_CLASE[f['clase']].split()[0]}\n{f['fuente']}" for f in filas]
    fig, eje = plt.subplots(figsize=(max(6, len(filas) * 0.9), 3.4))
    eje.bar(range(len(filas)), [float(f["fraccion_uniforme"]) for f in filas],
            color=[COLOR_CLASE[f["clase"]] for f in filas])
    eje.set_xticks(range(len(filas)), etiquetas, fontsize=7)
    eje.set_ylim(0, 1)
    eje.set_ylabel("Fracción con fondo uniforme")
    eje.set_title("Fondo uniforme (blanco o de laboratorio) por clase y fuente")
    fig.tight_layout()
    return _guardar(fig, carpeta, "fondo_por_clase_fuente", "datos/eda/tablas/fondo_por_clase.csv")


def mosaicos(particion, raiz_procesado, carpeta, semilla=42, lado=4):
    finales = distribuciones.conjunto_final(particion)
    rutas = []
    for clase in CLASES:
        for fuente in sorted({f["fuente"] for f in finales if f["clase"] == clase}):
            elegidas = distribuciones.elegir_mosaico(finales, semilla, clase, fuente, lado * lado)
            fig, ejes = plt.subplots(lado, lado, figsize=(6, 6.3))
            for eje in ejes.flat:
                eje.axis("off")
            for eje, f in zip(ejes.flat, elegidas):
                with Image.open(os.path.join(raiz_procesado, f["particion"], f["clase"], f"{f['id_contenido']}.jpg")) as im:
                    eje.imshow(im.convert("RGB"))
                eje.set_title(f["id_contenido"][:8], fontsize=6)
            n = sum(1 for f in finales if f["clase"] == clase and f["fuente"] == fuente)
            fig.suptitle(f"{NOMBRE_CLASE[clase]} — {fuente} ({len(elegidas)} de {n} imágenes)")
            fig.tight_layout()
            rutas += _guardar(fig, os.path.join(carpeta, "mosaicos"), f"mosaico_{clase}_{fuente}",
                              "Modelo/PROCESADO (muestra estable, semilla 42)", svg=False)
    return rutas


def sondas(resultados, carpeta):
    fig, eje = plt.subplots(figsize=(7, 0.45 * len(resultados) + 1.2))
    nombres = [r["sonda"] for r in resultados][::-1]
    valores = [float(r["exactitud_balanceada"]) for r in resultados][::-1]
    azar = [float(r["azar"]) for r in resultados][::-1]
    colores = ["#B33A3A" if r["alerta"] == "si" else ("#888888" if r["alerta"] == "" else "#3B7D23")
               for r in resultados][::-1]
    eje.barh(nombres, valores, color=colores)
    eje.scatter(azar, nombres, marker="|", s=200, color="black", label="Azar", zorder=3)
    eje.axvline(0.80, color="#B33A3A", linestyle="--", linewidth=1, label="Umbral de alerta (0.80)")
    eje.set_xlim(0, 1)
    eje.set_xlabel("Exactitud balanceada (validación cruzada por grupos, train + val)")
    eje.set_title("Sondas de atajo: ¿se adivina la clase sin mirar la lesión?")
    eje.legend(fontsize=7, loc="lower right")
    fig.tight_layout()
    return _guardar(fig, carpeta, "sondas_atajo", "datos/eda/tablas/sondas.csv")


def atajos_marcados(manifiesto, carpeta):
    conteo = Counter((f["clase_efectiva"], f["atajo"]) for f in manifiesto
                     if f.get("atajo") and f["atajo"] != "ninguno")
    if not conteo:
        return []
    tipos = sorted({t for _, t in conteo})
    fig, eje = plt.subplots(figsize=(6, 3))
    for k, c in enumerate(CLASES):
        eje.bar([i + k * 0.27 for i in range(len(tipos))], [conteo.get((c, t), 0) for t in tipos], width=0.27,
                color=COLOR_CLASE[c], label=NOMBRE_CLASE[c])
    eje.set_xticks([i + 0.27 for i in range(len(tipos))], tipos)
    eje.set_ylabel("Imágenes marcadas")
    eje.set_title("Atajos visuales marcados en la revisión (conteo parcial)")
    eje.legend(fontsize=7)
    fig.tight_layout()
    return _guardar(fig, carpeta, "atajos_marcados", "datos/manifiesto.csv (columna atajo)")


def tsne(filas, carpeta):
    rutas = []
    for por, nombre in (("clase", "tsne_por_clase"), ("fuente", "tsne_por_fuente")):
        colores = COLOR_CLASE if por == "clase" else _colores_fuente({f["fuente"] for f in filas})
        fig, eje = plt.subplots(figsize=(7, 6))
        for valor in (CLASES if por == "clase" else sorted(colores)):
            puntos = [f for f in filas if f[por] == valor]
            eje.scatter([float(f["x"]) for f in puntos], [float(f["y"]) for f in puntos], s=5, alpha=0.65,
                        color=colores[valor], label=NOMBRE_CLASE.get(valor, valor) if por == "clase" else valor)
        for f in filas:
            if f["rotulo"] == "si":
                eje.annotate(f["id_contenido"][:8], (float(f["x"]), float(f["y"])), fontsize=5.5,
                             xytext=(3, 3), textcoords="offset points")
        eje.set_xticks([])
        eje.set_yticks([])
        eje.set_xlabel("t-SNE 1 (sin unidades)")
        eje.set_ylabel("t-SNE 2 (sin unidades)")
        eje.set_title(f"Mapa de similitud (EfficientNet-B0 + t-SNE), coloreado por {por}")
        eje.legend(fontsize=7, markerscale=3, loc="best")
        fig.tight_layout()
        rutas += _guardar(fig, carpeta, nombre, "datos/eda/tablas/tsne.csv (rótulos: 15 imágenes con más vecinos de otra clase)")
    return rutas


def embudo(filas_embudo, carpeta):
    from avocadoia_datos.etl.embudo import PASOS
    fig, ejes = plt.subplots(1, 3, figsize=(11, 3.6), sharex=False)
    for eje, clase in zip(ejes, CLASES):
        n = Counter()
        for f in filas_embudo:
            if f["clase"] == clase:
                n[f["paso"]] += int(f["imagenes"])
        pasos = [p for p in ("inventariadas",) + PASOS if n[p]]
        eje.barh(pasos[::-1], [n[p] for p in pasos][::-1],
                 color=[COLOR_CLASE[clase] if p in ("inventariadas", "conjunto_final") else "#AAAAAA" for p in pasos][::-1])
        for y, p in enumerate(pasos[::-1]):
            eje.text(n[p], y, f" {n[p]}", va="center", fontsize=7)
        eje.set_title(NOMBRE_CLASE[clase])
        eje.set_xlabel("Imágenes")
    fig.suptitle("Embudo de calidad del ETL: de las imágenes inventariadas al conjunto final")
    fig.tight_layout()
    return _guardar(fig, carpeta, "embudo_calidad", "datos/etl/embudo.csv")
