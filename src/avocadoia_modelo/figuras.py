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
