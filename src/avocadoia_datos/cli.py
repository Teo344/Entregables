"""CLI `python -m avocadoia_datos <subcomando>` (contracts/cli.md)."""

import argparse
import os
import sys
from collections import Counter

from avocadoia_datos import config as mod_config
from avocadoia_datos import informe, inventario, particion, preprocesamiento, validacion
from avocadoia_datos.clases import CLASES, PARTICIONES
from avocadoia_datos.config import ErrorConfig, ErrorPrecondicion
from avocadoia_datos.es_csv import leer_csv


def _parser():
    comun = argparse.ArgumentParser(add_help=False)
    comun.add_argument("--config", default="config/dataset.toml")
    comun.add_argument("--fuentes", default="config/fuentes.csv")
    comun.add_argument("--raiz-imagenes", default="Modelo")
    comun.add_argument("--salida", default="datos")

    p = argparse.ArgumentParser(prog="avocadoia_datos", description="Pipeline del conjunto de datos AvocadoIA.")
    sub = p.add_subparsers(dest="comando", required=True)
    sub.add_parser("inventario", parents=[comun], help="Genera datos/manifiesto.csv")

    pp = sub.add_parser("particionar", parents=[comun], help="Muestra por cuotas y partición 70/15/15")
    pp.add_argument("--semilla", type=int)
    pp.add_argument("--definitiva", action="store_true")

    pl = sub.add_parser("planilla", parents=[comun], help="Planillas xlsx para el experto")
    pl.add_argument("--clase", choices=CLASES)
    pl.add_argument("--lote", type=int)
    pl.add_argument("--incluir-reserva", action="store_true")

    pi = sub.add_parser("incorporar", parents=[comun], help="Incorpora planillas completadas")
    pi.add_argument("planillas", nargs="+")

    pr = sub.add_parser("preprocesar", parents=[comun], help="Genera Modelo/PROCESADO/")
    pr.add_argument("--destino")
    pr.add_argument("--forzar", action="store_true")

    sub.add_parser("informe", parents=[comun], help="Genera datos/informe.md y .json")

    pt = sub.add_parser("todo", parents=[comun], help="inventario → particionar → preprocesar → informe")
    pt.add_argument("--semilla", type=int)
    pt.add_argument("--definitiva", action="store_true")
    return p


def _confirmados(args):
    return os.path.join(args.salida, "curacion", "casi_duplicados_confirmados.csv")


def _inventario(cfg, args):
    _, meta = inventario.ejecutar(cfg, args.raiz_imagenes, args.salida, _confirmados(args))
    print(f"Manifiesto: {meta['total_archivos']} archivos, {meta['grupos']} grupos")
    print("  por clase:  " + ", ".join(f"{k} {v}" for k, v in meta["por_clase"].items()))
    print("  por estado: " + ", ".join(f"{k} {v}" for k, v in meta["por_estado"].items()))
    print("  por fuente: " + ", ".join(f"{k} {v}" for k, v in meta["por_fuente"].items()))
    if meta["decisiones_ausentes"]:
        print(f"  decisiones sobre imágenes ausentes: {len(meta['decisiones_ausentes'])}", file=sys.stderr)


def _particionar(cfg, args):
    if getattr(args, "semilla", None) is not None:
        cfg.semilla = args.semilla
    filas, meta = particion.ejecutar(inventario.leer_manifiesto(args.salida), cfg, args.salida, args.definitiva)
    print(f"Partición {meta['estado']} (semilla {meta['semilla']})")
    print(f"  {'clase':12} {'train':>6} {'val':>6} {'test':>6} {'campo':>6}")
    for c in CLASES:
        n = meta["conteos"].get(c, {})
        print(f"  {c:12} " + " ".join(f"{n.get(p, 0):>6}" for p in PARTICIONES + ("test_campo",)))
    totales = Counter(f["particion"] for f in filas)
    print(f"  {'total':12} " + " ".join(f"{totales.get(p, 0):>6}" for p in PARTICIONES + ("test_campo",)))
    if any(meta["faltantes_cuota"].values()):
        print(f"  faltantes de cuota: {meta['faltantes_cuota']}", file=sys.stderr)
    print(f"  reserva: {sum(sum(v.values()) for v in meta['reserva'].values())} imágenes")


def _preprocesar(cfg, args):
    destino = getattr(args, "destino", None) or os.path.join(args.raiz_imagenes, "PROCESADO")
    filas = leer_csv(os.path.join(args.salida, "particion.csv"))
    if not filas:
        raise ErrorPrecondicion("No hay partición: ejecute primero `particionar`.")
    r = preprocesamiento.ejecutar(filas, inventario.leer_manifiesto(args.salida), cfg, args.raiz_imagenes,
                                  destino, args.salida, getattr(args, "forzar", False))
    print(f"Preprocesamiento en {destino}: {r['procesadas']} nuevas, {r['existentes']} ya estaban, "
          f"{r['eliminadas']} eliminadas, {r['advertencias']} advertencias")


def _informe(cfg, args):
    datos = informe.ejecutar(args.salida, cfg)
    print(f"Informe: {os.path.join(args.salida, 'informe.md')} (partición {datos['estado_particion']}, "
          f"razón de desbalance {datos['razon_desbalance']})")


def _planilla(cfg, args):
    creadas = validacion.generar_planillas(inventario.leer_manifiesto(args.salida), args.raiz_imagenes,
                                           args.salida, args.clase, args.lote or int(cfg.planilla.get("lote", 250)),
                                           args.incluir_reserva)
    print(f"Planillas generadas: {len(creadas)}")
    for ruta in creadas:
        print(f"  {ruta}")


def _incorporar(cfg, args):
    manifiesto = inventario.leer_manifiesto(args.salida)
    if not manifiesto:
        raise ErrorPrecondicion("No hay manifiesto: ejecute primero `inventario`.")
    r = validacion.incorporar(args.planillas, manifiesto, args.salida)
    for archivo, fila, msg in r["invalidas"]:
        print(f"  {archivo} fila {fila}: {msg}", file=sys.stderr)
    print(f"Incorporadas {r['incorporadas']}, ignoradas {r['ignoradas']}, inválidas {len(r['invalidas'])}")
    _inventario(cfg, args)


def main(argv=None):
    args = _parser().parse_args(argv)
    try:
        cfg = mod_config.cargar(args.config, args.fuentes)
        if args.comando == "todo":
            _inventario(cfg, args)
            _particionar(cfg, args)
            _preprocesar(cfg, args)
            _informe(cfg, args)
        else:
            {"inventario": _inventario, "particionar": _particionar, "preprocesar": _preprocesar,
             "informe": _informe, "planilla": _planilla, "incorporar": _incorporar}[args.comando](cfg, args)
    except ErrorConfig as e:
        print(f"Error de configuración: {e}", file=sys.stderr)
        return 1
    except ErrorPrecondicion as e:
        print(f"Precondición incumplida: {e}", file=sys.stderr)
        return 2
    return 0
