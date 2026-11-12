"""Figuras con matplotlib (backend Agg). Toda etiqueta de clase visible usa ETIQUETAS_VISIBLES."""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def curvas_entrenamiento(historial, ruta_png, titulo=""):
    """historial: filas con epoca, fase, loss, val_loss, accuracy, val_accuracy (T026)."""
    if not historial:
        return None
    ep = [int(h["epoca"]) for h in historial]
    fig, ejes = plt.subplots(1, 2, figsize=(11, 4))
    for eje, (tr, va, nombre) in zip(ejes, (("loss", "val_loss", "Pérdida"),
                                            ("accuracy", "val_accuracy", "Exactitud"))):
        eje.plot(ep, [float(h[tr]) for h in historial], label="entrenamiento")
        eje.plot(ep, [float(h[va]) for h in historial], label="validación")
        cambios = [ep[i] for i in range(1, len(historial)) if historial[i]["fase"] != historial[i - 1]["fase"]]
        for c in cambios:
            eje.axvline(c - 0.5, color="grey", linestyle="--", linewidth=1)
            eje.text(c - 0.4, eje.get_ylim()[1], "fase 2", va="top", fontsize=8, color="grey")
        eje.set_xlabel("Época")
        eje.set_title(nombre)
        eje.grid(alpha=0.3)
        eje.legend()
    if titulo:
        fig.suptitle(titulo)
    fig.tight_layout()
    os.makedirs(os.path.dirname(ruta_png) or ".", exist_ok=True)
    fig.savefig(ruta_png, dpi=150)
    plt.close(fig)
    return ruta_png


def fiabilidad(bins_por_particion, ruta_png, titulo):
    """Diagrama de fiabilidad: exactitud por intervalo de confianza frente a la diagonal ideal (T041)."""
    fig, ejes = plt.subplots(1, len(bins_por_particion), figsize=(5 * len(bins_por_particion), 4.4), squeeze=False)
    for eje, (nombre, (bins, ece)) in zip(ejes[0], bins_por_particion.items()):
        eje.plot([0, 1], [0, 1], "--", color="grey", linewidth=1, label="calibración perfecta")
        llenos = [b for b in bins if b["n"]]
        centros = [(b["desde"] + b["hasta"]) / 2 for b in llenos]
        eje.bar(centros, [b["exactitud"] for b in llenos], width=1 / len(bins) * 0.9, alpha=0.7, label="exactitud")
        eje.plot([b["confianza"] for b in llenos], [b["exactitud"] for b in llenos], "o", color="black", markersize=3)
        for c, b in zip(centros, llenos):
            eje.text(c, 0.02, str(b["n"]), ha="center", fontsize=6, rotation=90)
        eje.set_xlim(0, 1)
        eje.set_ylim(0, 1.02)
        eje.set_xlabel("Confianza")
        eje.set_ylabel("Exactitud")
        eje.set_title(f"{nombre} · ECE = {ece:.3f}")
        eje.legend(fontsize=7, loc="upper left")
    fig.suptitle(titulo)
    fig.tight_layout()
    os.makedirs(os.path.dirname(ruta_png) or ".", exist_ok=True)
    fig.savefig(ruta_png, dpi=150)
    plt.close(fig)
    return ruta_png


def cobertura_exactitud(curva, ruta_png, umbral, umbral_95, titulo):
    fig, eje = plt.subplots(figsize=(6.5, 4.4))
    u = [c["umbral"] for c in curva]
    eje.plot(u, [c["cobertura"] for c in curva], label="cobertura (aceptadas)")
    eje.plot(u, [c["exactitud"] if c["exactitud"] is not None else float("nan") for c in curva],
             label="exactitud de las aceptadas")
    eje.axvline(umbral, color="red", linestyle="--", linewidth=1, label=f"umbral elegido {umbral:.2f}")
    if umbral_95 is not None:
        eje.axvline(umbral_95, color="green", linestyle=":", linewidth=1, label=f"exactitud ≥ 95 % desde {umbral_95:.2f}")
    eje.set_xlabel("Umbral de confianza calibrada")
    eje.set_ylim(0, 1.02)
    eje.grid(alpha=0.3)
    eje.legend(fontsize=8, loc="lower left")
    eje.set_title(titulo)
    fig.tight_layout()
    os.makedirs(os.path.dirname(ruta_png) or ".", exist_ok=True)
    fig.savefig(ruta_png, dpi=150)
    plt.close(fig)
    return ruta_png


def arquitectura(info, ruta_png):
    """Diagrama de la arquitectura para la tesis, con cifras tomadas del modelo entrenado."""
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    fig, eje = plt.subplots(figsize=(8.5, 11))
    eje.set_xlim(0, 10)
    eje.set_ylim(0, 14)
    eje.axis("off")
    def dec(x, d=2):
        return f"{x:.{d}f}".replace(".", ",")

    bloques = [
        (12.2, 1.4, "#EDEDED", "Entrada", f"Fotografía RGB · {info['entrada']} × {info['entrada']} × 3\n"
                                         "Redimensionada sin recorte (LANCZOS) · rango 0–255"),
        (8.9, 2.8, "#DCE6F2", f"1 · Extractor de características: {info['nombre_base']}",
         f"Preentrenado con ImageNet · {info['capas_base']} capas · {dec(info['param_base'] / 1e6)} M de parámetros\n"
         "Reescalado interno · convoluciones separables en profundidad\n"
         "bloques residuales invertidos · activación " + info["activacion"] + "\n"
         f"Fase 1: congelado · Fase 2: últimas {info['entrenables_f2']} capas ajustadas (BatchNorm fija)"),
        (6.75, 1.3, "#FFF2CC", "Mapa de características",
         f"{info['mapa'][0]} × {info['mapa'][1]} zonas × {info['mapa'][2]} canales  →  aquí se calcula Grad-CAM++"),
        (3.7, 2.2, "#E2EFDA", "2 · Cabeza clasificadora (entrenada en este trabajo)",
         f"Global Average Pooling  →  vector de {info['mapa'][2]}\n"
         f"Dropout {info['dropout'] * 100:.0f} %  →  reduce la memorización\n"
         f"Densa de 3 salidas (logits) · {info['param_cabeza']:,} parámetros".replace(",", " ")),
        (1.35, 1.5, "#FCE4D6", "3 · Calibración y decisión",
         f"softmax(logits / T), T = {dec(info['temperatura'], 3)}  →  probabilidades calibradas\n"
         f"Si la confianza máxima < {dec(info['umbral'])}  →  «resultado no concluyente»"),
    ]
    for y, alto, color, titulo, texto in bloques:
        eje.add_patch(FancyBboxPatch((0.6, y), 8.8, alto, boxstyle="round,pad=0.08", facecolor=color,
                                     edgecolor="#404040", linewidth=1.2))
        eje.text(5, y + alto - 0.28, titulo, ha="center", va="top", fontsize=11, fontweight="bold")
        eje.text(5, y + alto / 2 - 0.15, texto, ha="center", va="center", fontsize=8.6, linespacing=1.5)
    for y0, y1 in ((12.15, 11.75), (8.85, 8.1), (6.7, 5.95), (3.65, 2.9)):
        eje.add_patch(FancyArrowPatch((5, y0), (5, y1), arrowstyle="-|>", mutation_scale=18, color="#404040"))
    eje.text(5, 0.75, "Salida: " + " · ".join(info["clases"]), ha="center", fontsize=9, style="italic")
    eje.text(5, 0.3, f"Total: {dec(info['param_total'] / 1e6)} M de parámetros · modelo {dec(info['tamano_mb'], 1)} MB (Keras) · "
                     f"corrida {info['corrida']}", ha="center", fontsize=7, color="#606060")
    eje.set_title(f"Arquitectura del clasificador AvocadoIA · {info['nombre_base']}", fontsize=13, pad=8)
    os.makedirs(os.path.dirname(ruta_png) or ".", exist_ok=True)
    fig.savefig(ruta_png, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return ruta_png


def comparacion(tabla, ruta_png, titulo, nombres=None):
    """Barras de macro-F1 (val y test) y recall por clase en test, media ± desviación y puntos por semilla (T036)."""
    from matplotlib.ticker import FuncFormatter

    from avocadoia_modelo import CLASES, ETIQUETAS_VISIBLES

    metricas = [("val_macro_f1", "Macro-F1\nvalidación"), ("test_macro_f1", "Macro-F1\nprueba")]
    # Término completo de la constitución, partido en líneas para que quepa bajo la barra.
    etiquetas = [e.replace("compatibles con ", "compatibles con\n") for e in ETIQUETAS_VISIBLES]
    metricas += [(f"test_recall_{c}", f"Recall prueba\n{e}") for c, e in zip(CLASES, etiquetas)]
    arqs = list(tabla)
    nombres = nombres or {}
    ancho = 0.8 / len(arqs)
    fig, eje = plt.subplots(figsize=(10, 4.8))
    minimo = 1.0
    for i, arq in enumerate(arqs):
        f = tabla[arq]
        xs = [j + (i - (len(arqs) - 1) / 2) * ancho for j in range(len(metricas))]
        medias = [f[f"{m}_media"] for m, _ in metricas]
        desv = [f[f"{m}_desv"] for m, _ in metricas]
        eje.bar(xs, medias, ancho * 0.95, yerr=desv, capsize=3, alpha=0.8,
                label=f"{nombres.get(arq, arq)} (n = {f['n']})")
        for x, (m, _) in zip(xs, metricas):
            valores = f[f"{m}_valores"]
            minimo = min(minimo, *valores)
            eje.plot([x] * len(valores), valores, "o", color="black", markersize=3)
        for x, v in zip(xs, medias):
            eje.text(x, 1.003, f"{v:.3f}".replace(".", ","), ha="center", va="bottom", fontsize=7)
    eje.set_xticks(range(len(metricas)))
    eje.set_xticklabels([n for _, n in metricas], fontsize=8)
    eje.set_ylim(max(0.0, minimo - 0.08), 1.03)
    eje.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:.2f}".replace(".", ",")))
    eje.grid(axis="y", alpha=0.3)
    eje.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=len(arqs), frameon=False)
    eje.set_title(titulo)
    fig.tight_layout()
    os.makedirs(os.path.dirname(ruta_png) or ".", exist_ok=True)
    fig.savefig(ruta_png, dpi=150)
    plt.close(fig)
    return ruta_png
