import os

from avocadoia_datos.cli import main
from avocadoia_datos.es_csv import leer_csv, leer_json


def test_todo_coherente(arbol_completo, capsys):
    arbol = arbol_completo
    assert main(arbol.args("todo")) == 0
    manifiesto = leer_csv(os.path.join(arbol.salida, "manifiesto.csv"))
    particion = leer_csv(os.path.join(arbol.salida, "particion.csv"))
    informe = leer_json(os.path.join(arbol.salida, "informe.json"))
    assert len(particion) == sum(f["en_muestra"] == "si" for f in manifiesto) == 140
    procesadas = [os.path.join(r, n) for r, _, ns in os.walk(os.path.join(arbol.modelo, "PROCESADO"))
                  for n in ns if n.endswith(".jpg")]
    assert len(procesadas) == 140
    assert sum(informe["totales_particion"][p] for p in ("train", "val", "test")) == 140
    assert "Partición provisional" in capsys.readouterr().out


def test_codigos_de_salida(arbol_completo, capsys):
    arbol = arbol_completo
    assert main(arbol.args("particionar")) == 2  # sin manifiesto
    assert main(arbol.args("inventario")) == 0
    assert main(arbol.args("particionar", "--definitiva")) == 2  # hay provisionales
    with open(arbol.toml, "a", encoding="utf-8") as fh:
        fh.write("\n[cuotas.sano]\n")  # tabla duplicada → TOML inválido
    assert main(arbol.args("inventario")) == 1
