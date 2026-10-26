"""Lista de exclusión por revisión (2026-10-26) → datos/curacion/exclusiones_revision.csv.

Decisiones del equipo tras la revisión visual del conjunto provisional:
- Fuente `avocare_` (sano y antracnosis): copias aumentadas (giros, recortes, zoom) de pocas escenas
  originales, repartidas entre train/val/test y con escenas en ambas clases. Se excluye completa.
- Kaggle "Anthracnose" sin lesión visible: el CSV de Kaggle las etiqueta como antracnosis, pero la
  superficie con manchas oscuras sobre el fruto es <= 0.5 %. Se apartan como dudosas; el experto
  puede devolverlas.

No mueve ni borra archivos: el pipeline lee la lista y marca esas imágenes `excluida_revision`.

Uso (desde la raíz de Entregables):
    python scripts/curacion/marcar_exclusiones.py
"""
import csv
import os

from PIL import Image

MODELO = "Modelo"
SALIDA = "datos/curacion/exclusiones_revision.csv"
UMBRAL_MANCHAS = 0.5  # % de la superficie del fruto


def porcentaje_manchas(ruta):
    """% de píxeles del fruto (fondo blanco excluido) que son marrón/negro y no verde."""
    im = Image.open(ruta).convert("RGB")
    im.thumbnail((200, 200))
    rgb, hsv = im.tobytes(), im.convert("HSV").tobytes()
    fruto = oscuro = 0
    for i in range(0, len(rgb), 3):
        r, g, b = rgb[i], rgb[i + 1], rgb[i + 2]
        if r > 235 and g > 235 and b > 235:
            continue
        h, s, v = hsv[i], hsv[i + 1], hsv[i + 2]
        fruto += 1
        if v < 110 or (s > 60 and not 40 <= h <= 110 and v < 170):
            oscuro += 1
    return 100 * oscuro / max(fruto, 1)


def main():
    filas = []
    for carpeta in ("AGUACATESANOS", "ANTRACNOSIS"):
        for nombre in sorted(os.listdir(os.path.join(MODELO, carpeta))):
            if nombre.startswith("avocare_"):
                filas.append({"ruta": f"{carpeta}/{nombre}", "motivo": "fuente_aumentada",
                              "detalle": "avocare_: copia aumentada de pocas escenas originales"})
    for nombre in sorted(os.listdir(os.path.join(MODELO, "ANTRACNOSIS"))):
        if nombre.startswith("Avocado "):
            pct = porcentaje_manchas(os.path.join(MODELO, "ANTRACNOSIS", nombre))
            if pct <= UMBRAL_MANCHAS:
                filas.append({"ruta": f"ANTRACNOSIS/{nombre}", "motivo": "sin_lesion_visible",
                              "detalle": f"Kaggle Anthracnose con {pct:.2f} % de manchas (<= {UMBRAL_MANCHAS} %)"})
    filas.sort(key=lambda f: f["ruta"])
    with open(SALIDA, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["ruta", "motivo", "detalle"], lineterminator="\n")
        w.writeheader()
        w.writerows(filas)
    por_motivo = {}
    for f in filas:
        clave = (f["ruta"].split("/")[0], f["motivo"])
        por_motivo[clave] = por_motivo.get(clave, 0) + 1
    print(f"{SALIDA}: {len(filas)} exclusiones")
    for (carpeta, motivo), n in sorted(por_motivo.items()):
        print(f"  {carpeta:14} {motivo:20} {n}")


if __name__ == "__main__":
    main()
