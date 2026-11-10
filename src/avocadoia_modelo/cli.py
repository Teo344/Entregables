"""CLI `python -m avocadoia_modelo <subcomando>` (contracts/cli.md).

Códigos de salida: 0 éxito; 1 uso o configuración; 2 verificación fallida (datos); 3 comparación inválida.
TensorFlow solo se importa dentro de los subcomandos que lo necesitan.
"""

import argparse
import sys

from avocadoia_modelo import CLASES, PARTICIONES
from avocadoia_modelo import config as mconfig

EXITO, ERROR_USO, ERROR_DATOS, ERROR_COMPARACION = 0, 1, 2, 3


def _comunes():
    p = argparse.ArgumentParser(add_help=False)
    p.add_argument("--config", default="config/modelo.toml")
    p.add_argument("--entorno", choices=("pc", "colab"), help="por defecto se detecta (colab si existe /content/drive)")
    p.add_argument("--manifiesto", help="por defecto [rutas.<entorno>].manifiesto")
    p.add_argument("--raiz-imagenes", help="por defecto [rutas.<entorno>].raiz_imagenes")
    p.add_argument("--salida", help="artefactos pesados (Drive); por defecto [rutas.<entorno>].salida")
    p.add_argument("--repo-datos", help="artefactos versionables; por defecto datos/modelo")
    return p


def _parser():
    comun = _comunes()
    p = argparse.ArgumentParser(prog="avocadoia_modelo", description="Modelo clasificador de AvocadoIA (spec 003).")
    sub = p.add_subparsers(dest="comando", required=True)
    sub.add_parser("verificar", parents=[comun], help="Filtros de licencia/calidad y verificación del manifiesto")
    pi = sub.add_parser("importar", parents=[comun], help="Copia de Drive al repo solo archivos livianos")
    pi.add_argument("--origen", help="por defecto <salida>/datos_modelo (lo que escribió Colab)")
    pp = sub.add_parser("preparar", parents=[comun], help="Caché 224 × 224 (.npz) desde el manifiesto verificado")
    pp.add_argument("--forzar", action="store_true")
    pe = sub.add_parser("entrenar", parents=[comun], help="Entrena una corrida y la evalúa")
    pe.add_argument("--arquitectura", required=True, choices=("mobilenetv3", "efficientnetb0"))
    pe.add_argument("--semilla", required=True, type=int)
    pv = sub.add_parser("evaluar", parents=[comun], help="Evalúa una corrida (val y test)")
    pv.add_argument("--corrida", required=True)
    px = sub.add_parser("explicar", parents=[comun], help="Mapas Grad-CAM++ de aciertos y errores + planilla")
    px.add_argument("--corrida", required=True)
    pr = sub.add_parser("resumir-explicaciones", parents=[comun], help="Resume la planilla valorada")
    pr.add_argument("--corrida", required=True)
    ps = sub.add_parser("spike-explain", parents=[comun], help="Prueba la firma explain en TFLite (M14)")
    ps.add_argument("--corrida", help="modelo entrenado a usar; sin él, entrena 1 época solo para la prueba")
    return p


def _rutas(args):
    cfg = mconfig.cargar(args.config, entorno_=args.entorno)
    r = cfg["_rutas"]
    r["manifiesto"] = args.manifiesto or r["manifiesto"]
    r["raiz_imagenes"] = args.raiz_imagenes or r["raiz_imagenes"]
    r["salida"] = args.salida or r["salida"]
    r["repo_datos"] = args.repo_datos or r["repo_datos"]
    return cfg, r


def _cmd_verificar(args):
    from avocadoia_modelo import verificacion

    cfg, r = _rutas(args)
    inf = verificacion.verificar(cfg, r["manifiesto"], r["raiz_imagenes"], r["repo_datos"], r["salida"])
    print(f"Manifiesto {inf['huella_manifiesto'][:8]}: estado {inf['estado']}")
    if inf.get("clases_desconocidas"):
        print(f"  Clases desconocidas: {inf['clases_desconocidas']}")
        return ERROR_DATOS
    entrada = sum(sum(d.values()) for d in inf["conteos_entrada"].values())
    print(f"  Entrada: {entrada} | excluidas: {inf['excluidas']['total']} | para entrenar: {inf['total']}")
    for motivo, n in inf["excluidas"].get("por_motivo", {}).items():
        print(f"    - {motivo}: {n}")
    print("  " + " | ".join(f"{p}: " + "/".join(str(inf["conteos"][p][c]) for c in CLASES) + f" = "
                            f"{sum(inf['conteos'][p].values())}" for p in PARTICIONES) + "  (sano/antracnosis/pedúnculo)")
    for clave in ("faltantes", "ilegibles", "sha_cruzados"):
        if inf[clave]:
            print(f"  {clave}: {len(inf[clave])} (p. ej. {inf[clave][:3]})")
    fuga = inf["fuga_por_fruto"]
    if fuga["grupos"]:
        print(f"  Aviso: {fuga['grupos']} frutos cruzan particiones ({fuga['imagenes']} imágenes, "
              f"{fuga['imagenes_test']} en test)")
    prov = inf["etiquetas_provisionales"]
    if any(prov.values()):
        print(f"  Aviso: etiquetas provisionales {prov} → métricas experimentales")
    return ERROR_DATOS if inf["estado"] == "fallida" else EXITO


def _verificacion_y_cache(r):
    """Verificación válida y caché que le corresponde; si no, (None, mensaje) → código 2 (hallazgo U2)."""
    import os

    from avocadoia_datos.es_csv import leer_json

    from avocadoia_modelo import preparacion

    ruta = os.path.join(r["repo_datos"], "verificacion.json")
    if not os.path.exists(ruta):
        return None, None, "no hay verificacion.json: ejecute `verificar`"
    ver = leer_json(ruta)
    if ver.get("estado") == "fallida":
        return None, None, "la verificación está fallida: corrija los datos y vuelva a `verificar`"
    cache = preparacion.directorio(r["salida"], preparacion.huella_cache(ver["huella_manifiesto"]))
    meta = os.path.join(cache, "meta.json")
    if not os.path.exists(meta) or leer_json(meta).get("huella_manifiesto") != ver["huella_manifiesto"]:
        return ver, None, "no hay caché para este manifiesto: ejecute `preparar`"
    return ver, cache, None


def _cmd_preparar(args):
    import os

    from avocadoia_datos.es_csv import leer_json

    from avocadoia_modelo import preparacion

    _, r = _rutas(args)
    ruta = os.path.join(r["repo_datos"], "verificacion.json")
    if not os.path.exists(ruta):
        print("Error: no hay verificacion.json: ejecute `verificar`", file=sys.stderr)
        return ERROR_DATOS
    ver = leer_json(ruta)
    if ver.get("estado") == "fallida":
        print("Error: la verificación está fallida", file=sys.stderr)
        return ERROR_DATOS

    def progreso(p, i, n):
        if i == n or i % 100 == 0:
            print(f"  {p}: {i}/{n}", flush=True)

    res = preparacion.preparar_desde_verificacion(ver, r["raiz_imagenes"], r["salida"], args.forzar, progreso)
    estado = "reutilizada" if res["reutilizada"] else "creada"
    print(f"Caché {res['huella_cache'][:8]} {estado} en {res['ruta']}: {res['conteos']}")
    return EXITO


def _cmd_entrenar(args):
    from avocadoia_modelo import entrenamiento, evaluacion, registro

    cfg, r = _rutas(args)
    ver, cache, error = _verificacion_y_cache(r)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        return ERROR_DATOS
    cfg = mconfig.con_corrida(cfg, args.arquitectura, args.semilla)
    id_ = None
    try:
        id_ = entrenamiento.entrenar(cfg, cache, r["repo_datos"], r["salida"], ver)
        res = evaluacion.evaluar(cfg, id_, cache, r["repo_datos"], r["salida"])
        registro.actualizar_estado(r["repo_datos"], id_, "completa")
    except BaseException:
        if id_:
            registro.actualizar_estado(r["repo_datos"], id_, "incompleta")
        raise
    _imprimir_metricas(id_, res)
    return EXITO


def _cmd_evaluar(args):
    from avocadoia_modelo import evaluacion

    cfg, r = _rutas(args)
    _, cache, error = _verificacion_y_cache(r)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        return ERROR_DATOS
    _imprimir_metricas(args.corrida, evaluacion.evaluar(cfg, args.corrida, cache, r["repo_datos"], r["salida"]))
    return EXITO


def _imprimir_metricas(id_, res):
    print(f"Corrida {id_}")
    for p in ("val", "test"):
        m = res[p]
        lo, hi = m["macro_f1_ic95"]
        rec = " ".join(f"{c}={m['por_clase'][c]['recall']:.3f}" for c in CLASES)
        print(f"  {p}: macro-F1 {m['macro_f1']:.3f} (IC95 {lo:.3f}–{hi:.3f}) | exactitud {m['exactitud']:.3f} | "
              f"recall {rec}" + ("  [EXPERIMENTAL]" if m["experimental"] else ""))


def _cmd_explicar(args):
    from avocadoia_modelo import explicacion

    cfg, r = _rutas(args)
    ver, cache, error = _verificacion_y_cache(r)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        return ERROR_DATOS
    info = explicacion.generar(cfg, args.corrida, cache, r["repo_datos"], r["salida"], ver)
    cal = "calibrada" if info["confianza_calibrada"] else "SIN calibrar (T = 1; ejecute `calibrar` antes)"
    print(f"{info['n_mapas']} mapas en {r['repo_datos']}/explicaciones/{args.corrida}/ · confianza {cal}")
    print("Valore planilla_explicaciones.xlsx (columna amarilla: lesion_fruto | fondo_ajeno | ambiguo) "
          "y ejecute resumir-explicaciones")
    return EXITO


def _cmd_resumir_explicaciones(args):
    from avocadoia_modelo import explicacion

    cfg, r = _rutas(args)
    res = explicacion.resumir_corrida(r["repo_datos"], args.corrida, cfg["explicacion"]["umbral_atajo"])
    for c, v in res["por_clase"].items():
        print(f"  {c}: {v['valoradas']} valoradas · lesión/fruto {v['lesion_fruto']:.0%} · "
              f"fondo/ajeno {v['fondo_ajeno']:.0%} · ambiguo {v['ambiguo']:.0%}")
    print(f"Posibles atajos: {res['posibles_atajos'] or 'ninguno'} · SC-005 {'cumple' if res['cumple_sc005'] else 'NO cumple'}"
          f" · sin valorar: {res['sin_valorar']}")
    return EXITO


def _cmd_spike_explain(args):
    from avocadoia_modelo import exportacion

    cfg, r = _rutas(args)
    _, cache, error = _verificacion_y_cache(r)
    if error:
        print(f"Error: {error}", file=sys.stderr)
        return ERROR_DATOS
    res = exportacion.spike_explain(cfg, cache, r["repo_datos"], r["salida"], args.corrida)
    for clave in ("variante_gradientes", "variante_cam"):
        v = res[clave]
        detalle = (f"+{v['tamano_extra_mb']} MB · Pearson {v.get('pearson_medio')} · IoU {v.get('iou_top20_medio')}"
                   if v["convierte"] else v["error"][:200])
        print(f"  {clave}: {'convierte' if v['convierte'] else 'NO convierte'} · {detalle}")
    print(f"Decisión: {res['decision']} (plan B aplicado: {res['plan_b_aplicado']})")
    return EXITO


def _cmd_importar(args):
    from avocadoia_modelo import registro

    import os

    _, r = _rutas(args)
    origen = args.origen or os.path.join(r["salida"], "datos_modelo")
    copiados = registro.importar(origen, r["repo_datos"])
    print(f"Importados {len(copiados)} archivos a {r['repo_datos']}")
    return EXITO


COMANDOS = {"verificar": _cmd_verificar, "importar": _cmd_importar, "preparar": _cmd_preparar,
            "entrenar": _cmd_entrenar, "evaluar": _cmd_evaluar, "explicar": _cmd_explicar,
            "resumir-explicaciones": _cmd_resumir_explicaciones, "spike-explain": _cmd_spike_explain}


def main(argv=None):
    # La consola de Windows (cp1252) no imprime caracteres como "→" o "×": forzar UTF-8.
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8", errors="replace")
    args = _parser().parse_args(argv)
    try:
        return COMANDOS[args.comando](args)
    except (mconfig.ErrorConfig, FileNotFoundError, ValueError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return ERROR_USO
