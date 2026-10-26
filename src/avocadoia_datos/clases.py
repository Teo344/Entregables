"""Clases diagnósticas, carpetas fuente y extensiones de imagen admitidas."""

CLASES = ("sano", "antracnosis", "pedunculo")

CARPETAS = {
    "sano": "AGUACATESANOS",
    "antracnosis": "ANTRACNOSIS",
    "pedunculo": "PEDUNCULO",
}

NOMBRES = {
    "sano": "Sano",
    "antracnosis": "Antracnosis",
    "pedunculo": "Síntomas compatibles con anillado del pedúnculo",
}

# Fotos propias de Sigchos: misma estructura de carpetas por clase, solo para test_campo.
CARPETA_CAMPO = "CAMPO_SIGCHOS"

PARTICIONES = ("train", "val", "test")

EXTENSIONES = (".jpg", ".jpeg", ".png")


def clase_de_carpeta(carpeta):
    for clase, nombre in CARPETAS.items():
        if nombre == carpeta:
            return clase
    return None


def es_imagen(nombre):
    return nombre.lower().endswith(EXTENSIONES)
