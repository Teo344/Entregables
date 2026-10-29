"""CLI `python -m avocadoia_datos <subcomando>` (contracts/cli.md)."""

import argparse
import os
import sys
from collections import Counter

from avocadoia_datos import config as mod_config
from avocadoia_datos import informe, inventario, particion, preprocesamiento, validacion
from avocadoia_datos.clases import CLASES, PARTICIONES
from avocadoia_datos.config import ErrorConfig, ErrorDependencia, ErrorPrecondicion
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

    # ETL y EDA (spec 002, contracts/cli.md)
    sub.add_parser("etl-extraer", parents=[comun], help="Inventario y línea base de la partición de 001")
    sub.add_parser("etl-embudo", parents=[comun], help="Embudo de calidad y comparación con 001")
    pe = sub.add_parser("etl-representaciones", parents=[comun], help="Vectores EfficientNet-B0 (requiere .venv-ml)")
    pe.add_argument("--forzar", action="store_true")
    sub.add_parser("etl-sospechas", parents=[comun], help="Etiquetas dudosas por confident learning")
    pv = sub.add_parser("etl-revision", parents=[comun], help="Planillas de revisión con miniaturas")
    pv.add_argument("--tipo", choices=("sospecha", "sistematica"), default="sospecha")
    pv.add_argument("--clase", choices=CLASES)
    pv.add_argument("--lote", type=int, default=150)
    pa = sub.add_parser("etl-auditoria", parents=[comun], help="Planilla de auditoría al azar del conjunto final")
    pa.add_argument("--n", type=int, default=100)
    sub.add_parser("eda", parents=[comun], help="Análisis exploratorio: tablas, figuras, sondas y t-SNE")
    sub.add_parser("informe-etl-eda", parents=[comun], help="Informe datos/eda/informe_etl_eda.md y .json")
    sub.add_parser("etl-eda", parents=[comun], help="Cadena completa sin pasos manuales")
    pn = sub.add_parser("etl-incorporar", parents=[comun], help="Incorpora planillas de revisión o auditoría")
    pn.add_argument("planillas", nargs="+")
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


def _etl_extraer(cfg, args):
    from avocadoia_datos.etl import embudo
    _inventario(cfg, args)
    print(f"Línea base de 001: {embudo.guardar_linea_base(args.salida)}")


def _etl_embudo(cfg, args):
    from avocadoia_datos.etl import embudo
    manifiesto = inventario.leer_manifiesto(args.salida)
    if not manifiesto:
        raise ErrorPrecondicion("No hay manifiesto: ejecute primero `etl-extraer`.")
    if not os.path.exists(embudo.ruta_linea_base(args.salida)):
        raise ErrorPrecondicion("No hay línea base de 001: ejecute primero `etl-extraer`.")
    r = embudo.ejecutar(manifiesto, args.salida)
    print(f"Embudo: {os.path.join(args.salida, 'etl', 'embudo.csv')} "
          f"({'cuadra' if not r['descuadres'] else 'DESCUADRA en ' + str(r['descuadres'])})")
    print("  comparación con 001: " + ", ".join(f"{k} {v}" for k, v in sorted(r["cambios"].items())))


def _etl_representaciones(cfg, args):
    from avocadoia_datos.etl import representaciones
    manifiesto = inventario.leer_manifiesto(args.salida)
    if not manifiesto:
        raise ErrorPrecondicion("No hay manifiesto: ejecute primero `etl-extraer`.")
    r = representaciones.calcular(manifiesto, args.raiz_imagenes, args.salida, args.forzar)
    print(f"Representaciones: {r['imagenes']} imágenes ({r['calculadas']} calculadas, "
          f"{r['reutilizadas']} de la caché), TensorFlow {r['version_tf']}, huella {r['huella'][:16]}")


def _etl_sospechas(cfg, args):
    from avocadoia_datos.etl import representaciones, sospechas
    try:
        cache = representaciones.cargar_cache(args.salida)
    except ImportError as e:
        raise ErrorDependencia("Este subcomando requiere numpy y scikit-learn (.venv-ml)") from e
    if cache is None:
        raise ErrorPrecondicion("Ejecute antes etl-representaciones")
    r = sospechas.ejecutar(inventario.leer_manifiesto(args.salida), cache, args.salida, cfg.semilla)
    print(f"Sospechas: {os.path.join(args.salida, 'etl', 'sospechas.csv')} (umbrales {r['umbrales']})")
    for c, v in r["por_clase"].items():
        print(f"  {c:12} candidatas {v['candidatas']:>5}  a revisar {v['a_revisar']:>4}  conflictos {v['conflictos']:>4}")


def _etl_revision(cfg, args):
    from avocadoia_datos.etl import revision
    sospechas = leer_csv(os.path.join(args.salida, "etl", "sospechas.csv"))
    if args.tipo == "sospecha" and not sospechas:
        raise ErrorPrecondicion("No hay sospechas: ejecute primero `etl-sospechas`.")
    creadas = revision.generar_planillas(inventario.leer_manifiesto(args.salida), sospechas, args.raiz_imagenes,
                                         args.salida, args.tipo, args.clase, args.lote)
    print(f"Planillas de revisión ({args.tipo}): {len(creadas)}")
    for ruta in creadas:
        print(f"  {ruta}")


def _etl_auditoria(cfg, args):
    from avocadoia_datos.etl import revision
    ruta = revision.generar_auditoria(leer_csv(os.path.join(args.salida, "particion.csv")),
                                      inventario.leer_manifiesto(args.salida), args.raiz_imagenes, args.salida,
                                      args.n, cfg.semilla)
    print(f"Planilla de auditoría ({args.n} imágenes): {ruta}")


def _etl_incorporar(cfg, args):
    from avocadoia_datos.etl import revision
    manifiesto = inventario.leer_manifiesto(args.salida)
    if not manifiesto:
        raise ErrorPrecondicion("No hay manifiesto: ejecute primero `etl-extraer`.")
    r = revision.incorporar(args.planillas, manifiesto, args.salida)
    for archivo, fila, msg in r["invalidas"]:
        print(f"  {archivo} fila {fila}: {msg}", file=sys.stderr)
    print(f"Incorporadas {r['incorporadas']}, sin decisión {r['ignoradas']}, inválidas {len(r['invalidas'])} "
          f"en {revision.ruta_decisiones(args.salida)}")
    _inventario(cfg, args)


def _eda(cfg, args):
    try:
        from avocadoia_datos.eda import distribuciones, figuras, similitud, sondas
        from avocadoia_datos.etl import caracteristicas, representaciones
    except ImportError as e:
        raise ErrorDependencia("El EDA requiere numpy, scikit-learn y matplotlib (.venv-ml)") from e
    manifiesto = inventario.leer_manifiesto(args.salida)
    particion_filas = leer_csv(os.path.join(args.salida, "particion.csv"))
    if not manifiesto or not particion_filas:
        raise ErrorPrecondicion("No hay manifiesto o partición: ejecute primero `etl-extraer` y `todo`.")
    figs = os.path.join(args.salida, "eda", "figuras")
    r = caracteristicas.ejecutar(manifiesto, args.raiz_imagenes, args.salida)
    print(f"Características: {r['imagenes']} imágenes ({r['medidas']} medidas ahora)")
    caract = leer_csv(os.path.join(args.salida, "eda", "tablas", "caracteristicas.csv"))
    d = distribuciones.ejecutar(caract, particion_filas, manifiesto, args.salida)
    rutas = figuras.distribucion(d["distribucion"], figs)
    rutas += figuras.caracteristicas(caract, particion_filas, figs)
    rutas += figuras.fondo(leer_csv(os.path.join(args.salida, "eda", "tablas", "fondo_por_clase.csv")), figs)
    rutas += figuras.mosaicos(particion_filas, os.path.join(args.raiz_imagenes, "PROCESADO"), figs, cfg.semilla)
    rutas += figuras.atajos_marcados(manifiesto, figs)
    cache = representaciones.cargar_cache(args.salida)
    if cache is None:
        print("  sin representaciones: se omiten sondas de fondo y t-SNE (ejecute etl-representaciones)", file=sys.stderr)
    else:
        resultados = sondas.ejecutar(caract, cache, particion_filas, args.salida, cfg.semilla)
        for x in resultados:
            print(f"  sonda {x['sonda']:24} {x['exactitud_balanceada']} (azar {x['azar']}) {x['alerta']}")
        rutas += figuras.sondas(resultados, figs)
        rutas += figuras.tsne(similitud.ejecutar(cache, particion_filas, args.salida, cfg.semilla), figs)
    embudo_filas = leer_csv(os.path.join(args.salida, "etl", "embudo.csv"))
    if embudo_filas:
        rutas += figuras.embudo(embudo_filas, figs)
    print(f"EDA: {len(rutas)} archivos de figura en {figs}")


def _informe_etl_eda(cfg, args):
    from avocadoia_datos.eda import informe as informe_eda
    d = informe_eda.ejecutar(args.salida, cfg)
    print(f"Informe: {os.path.join(args.salida, 'eda', 'informe_etl_eda.md')} ({len(d['conclusiones'])} conclusiones, "
          f"revisión {d['revision']['decididas']}/{d['revision']['marcadas']}, auditoría "
          f"{d['auditoria']['revisadas'] or 'pendiente'})")


def _etl_eda(cfg, args):
    """etl-extraer → etl-representaciones → etl-sospechas → todo → eda → etl-embudo → informe-etl-eda."""
    import time
    inicio = time.monotonic()
    args.forzar = False
    args.semilla = None
    args.definitiva = False
    _etl_extraer(cfg, args)
    _etl_representaciones(cfg, args)
    _etl_sospechas(cfg, args)
    _particionar(cfg, args)
    _preprocesar(cfg, args)
    _informe(cfg, args)
    _etl_embudo(cfg, args)
    _eda(cfg, args)
    _informe_etl_eda(cfg, args)
    print(f"Cadena ETL + EDA completa en {(time.monotonic() - inicio) / 60:.1f} min")


COMANDOS = {"inventario": _inventario, "particionar": _particionar, "preprocesar": _preprocesar,
            "informe": _informe, "planilla": _planilla, "incorporar": _incorporar,
            "etl-extraer": _etl_extraer, "etl-embudo": _etl_embudo,
            "etl-representaciones": _etl_representaciones, "etl-sospechas": _etl_sospechas,
            "etl-revision": _etl_revision, "etl-auditoria": _etl_auditoria, "etl-incorporar": _etl_incorporar,
            "eda": _eda, "informe-etl-eda": _informe_etl_eda, "etl-eda": _etl_eda}


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
            COMANDOS[args.comando](cfg, args)
    except ErrorConfig as e:
        print(f"Error de configuración: {e}", file=sys.stderr)
        return 1
    except ErrorPrecondicion as e:
        print(f"Precondición incumplida: {e}", file=sys.stderr)
        return 2
    except ErrorDependencia as e:
        print(f"Dependencia ausente: {e}", file=sys.stderr)
        return 3
    return 0
