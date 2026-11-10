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
    px.add_argument("--forzar", action="store_true", help="regenerar aunque la planilla ya tenga valoraciones")
    pr = sub.add_parser("resumir-explicaciones", parents=[comun], help="Resume la planilla valorada")
    pr.add_argument("--corrida", required=True)
    pc = sub.add_parser("calibrar", parents=[comun], help="Temperature Scaling con validación, ECE y umbral")
    pc.add_argument("--corrida", required=True)
    sub.add_parser("generar-manifiesto-002", parents=[comun], help="Manifiesto del dataset 002 (M20)")
    sub.add_parser("generar-v5", parents=[comun], help="Split v5 propuesto a partir del v4 (punto 1)")
    sub.add_parser("campo-etl", parents=[comun], help="ETL + EDA de las fotos de campo (CAMPO_SIGCHOS)")
    pk = sub.add_parser("evaluar-campo", parents=[comun], help="Evalúa una corrida con la prueba de campo")
    pk.add_argument("--corrida", required=True)
    pd = sub.add_parser("diagrama", parents=[comun], help="Figura de la arquitectura de una corrida")
    pd.add_argument("--corrida", required=True)
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
    import os

    destino = os.path.join(r["repo_datos"], "explicaciones", args.corrida)
    valoradas = [f for f in explicacion.leer_planilla(destino) if f.get("valoracion")] if os.path.isdir(destino) else []
    if valoradas and not args.forzar:
        print(f"Error: la planilla de {args.corrida} ya tiene {len(valoradas)} valoraciones; regenerarla las borraría. "
              "Use --forzar solo si quiere descartarlas.", file=sys.stderr)
        return ERROR_USO
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


def _cmd_calibrar(args):
    import os

    import numpy as np

    from avocadoia_datos.es_csv import escribir_csv, escribir_json

    from avocadoia_modelo import calibracion, figuras

    cfg, r = _rutas(args)
    ruta = os.path.join(r["salida"], "experimentos", args.corrida, "logits.npz")
    if not os.path.exists(ruta):
        print(f"Error: no existen los logits {ruta}: ejecute `evaluar --corrida {args.corrida}`", file=sys.stderr)
        return ERROR_DATOS
    d = np.load(ruta, allow_pickle=False)
    c = cfg["calibracion"]
    res = calibracion.calibrar(d["logits_val"], d["y_val"], d["logits_test"], d["y_test"], c["intervalos"],
                               c["umbral"], c["exactitud_objetivo"])
    curva = res.pop("_curva_val")
    res["corrida"] = args.corrida
    destino = os.path.join(r["repo_datos"], "calibracion", args.corrida)
    ruta_json = os.path.join(destino, "calibracion.json")
    if os.path.exists(ruta_json):  # la justificación del umbral es manual (T042): no perderla al recalcular
        from avocadoia_datos.es_csv import leer_json

        previa = leer_json(ruta_json).get("justificacion_umbral")
        if previa:
            res["justificacion_umbral"] = previa
    escribir_json(ruta_json, res)
    escribir_csv(os.path.join(destino, "cobertura_exactitud.csv"), ("umbral", "cobertura", "exactitud", "aceptadas"),
                 curva)
    t = res["temperatura"]
    for momento, temp in (("antes", 1.0), ("despues", t)):
        bins = {p: (calibracion.fiabilidad(calibracion.softmax(d[f"logits_{p}"], temp), d[f"y_{p}"], c["intervalos"]),
                    res[f"ece_{p}_{momento}"]) for p in ("val", "test")}
        figuras.fiabilidad(bins, os.path.join(destino, f"fiabilidad_{momento}.png"),
                           f"Fiabilidad {'antes' if momento == 'antes' else 'después'} de calibrar (T = {temp:.3f})")
    figuras.cobertura_exactitud(curva, os.path.join(destino, "cobertura_exactitud.png"), c["umbral"],
                                res["umbral_exactitud_95"], "Cobertura frente a exactitud (validación calibrada)")
    print(f"Corrida {args.corrida}: temperatura T = {t:.3f}")
    for p in ("val", "test"):
        print(f"  {p}: ECE {res[f'ece_{p}_antes']:.4f} → {res[f'ece_{p}_despues']:.4f} · confianza media "
              f"{res[f'confianza_media_{p}_antes']:.3f} → {res[f'confianza_media_{p}_despues']:.3f}")
    print(f"  NLL val {res['nll_antes']:.4f} → {res['nll_despues']:.4f}")
    u95 = res["umbral_exactitud_95"]
    print(f"  Umbral {c['umbral']:.2f}: no concluyentes en test {res['no_concluyentes_test']:.1%} · "
          f"umbral con exactitud ≥ 95 % en val: {u95 if u95 is not None else 'ninguno'}")
    return EXITO


def _cmd_diagrama(args):
    import os

    import keras

    from avocadoia_datos.es_csv import leer_json

    from avocadoia_modelo import ETIQUETAS_VISIBLES, arquitecturas, figuras, registro

    cfg, r = _rutas(args)
    reg = registro.leer_registro(r["repo_datos"], args.corrida)
    ruta_modelo = os.path.join(r["salida"], "experimentos", args.corrida, "mejor.keras")
    modelo = keras.models.load_model(ruta_modelo)
    base = arquitecturas.capas_del_modelo_base(modelo)
    cabeza = sum(modelo.get_layer(n).count_params() for n in ("gap", "dropout", "logits"))
    ruta_cal = os.path.join(r["repo_datos"], "calibracion", args.corrida, "calibracion.json")
    nombres = {"mobilenetv3": ("MobileNetV3-Large", "hard-swish / ReLU"), "efficientnetb0": ("EfficientNet-B0", "swish (SiLU)")}
    nombre, activacion = nombres[reg["arquitectura"]]
    info = {"nombre_base": nombre, "activacion": activacion, "entrada": cfg["entrada"]["tamano"],
            "capas_base": len(base), "param_base": modelo.count_params() - cabeza, "param_cabeza": cabeza,
            "param_total": modelo.count_params(), "entrenables_f2": reg.get("capas_entrenables_fase2", "?"),
            "mapa": tuple(modelo.get_layer(arquitecturas.nombre_capa_mapa(modelo)).output.shape[1:]),
            "dropout": cfg["modelo"]["dropout"], "umbral": cfg["calibracion"]["umbral"],
            "temperatura": leer_json(ruta_cal)["temperatura"] if os.path.exists(ruta_cal) else 1.0,
            "clases": ETIQUETAS_VISIBLES, "tamano_mb": os.path.getsize(ruta_modelo) / 2**20, "corrida": args.corrida}
    destino = os.path.join(r["repo_datos"], "figuras", f"arquitectura_{reg['arquitectura']}.png")
    figuras.arquitectura(info, destino)
    print(f"Figura: {destino}")
    return EXITO


def _cmd_campo_etl(args):
    import os

    from avocadoia_datos.es_csv import escribir_csv, leer_csv

    from avocadoia_modelo import campo
    from avocadoia_modelo import manifiesto as mm

    cfg, r = _rutas(args)
    cfg002, por_sha = mm.contexto_002(cfg)
    filas = campo.inventariar(r["raiz_modelo"], cfg002, por_sha, cfg002.preprocesamiento)
    destino = os.path.join(r["repo_datos"], "campo")
    res = campo.escribir(filas, destino)
    referencia = ("mdpi_pedunculo", "mdpi_pedunculo_sano", "hass", "rgb_sano", "rgb_antracnosis", "kaggle_antracnosis")
    tabla, grupos = campo.tabla_comparativa(filas, leer_csv(cfg["filtros"]["caracteristicas_002"]),
                                            leer_csv(cfg["filtros"]["manifiesto_002"]), referencia)
    escribir_csv(os.path.join(destino, "comparacion_campo.csv"), list(tabla[0]), tabla)
    campo.figuras_eda(grupos, destino, r["raiz_modelo"], filas)
    print(f"Fotos de campo: {res['total']} · válidas (test_campo): {res['test_campo']} · por clase {res['por_clase']}")
    print(f"  Rechazadas: {res['rechazadas'] or 'ninguna'} · grupos de fotos casi iguales: "
          f"{res['grupos_similitud']} ({res['grupos_con_varias_fotos']} con varias fotos)")
    print("  Comparación (mediana) frente al entrenamiento:")
    for t in tabla:
        print(f"    {t['grupo']:<26} n={t['n']:<4} brillo {t['brillo_mediana']:<7} nitidez {t['nitidez_mediana']:<8} "
              f"saturación {t['saturacion_mediana']:<6} fondo uniforme {t['fondo_uniforme_pct']} %")
    print(f"  Archivos en {destino}/ · validación del agrónomo: pendiente")
    return EXITO


def _cmd_evaluar_campo(args):
    from avocadoia_modelo import campo

    cfg, r = _rutas(args)
    res = campo.evaluar(cfg, args.corrida, r["repo_datos"], r["salida"], r["raiz_modelo"])
    cal = "calibrada" if res["confianza_calibrada"] else "sin calibrar"
    print(f"Prueba de campo · corrida {args.corrida} · {res['n']} fotos · confianza {cal} (T = {res['temperatura']})")
    print(f"  Predicciones: {res['predicciones']} · no concluyentes (< {res['umbral']}): {res['no_concluyentes']}")
    for c, v in res["por_clase"].items():
        print(f"  {c}: sensibilidad {v['sensibilidad']:.1%} ({v['n']} fotos) · confundida con {v['confundida_con']}")
    print(f"  Confianza media: {res['confianza_media']:.3f}")
    return EXITO


def _cmd_generar_v5(args):
    import os

    from avocadoia_modelo import manifiesto as mm
    from avocadoia_modelo import split_v5

    cfg, r = _rutas(args)
    cfg002, por_sha = mm.contexto_002(cfg)
    from avocadoia_datos.es_csv import leer_csv

    prefijo = os.path.relpath(r["raiz_imagenes"], r["raiz_modelo"]).replace("\\", "/")
    salida, cambios, entrada = split_v5.construir(cfg, mm.leer_entrada(r["manifiesto"]), prefijo, cfg002, por_sha,
                                                  leer_csv(cfg["filtros"]["manifiesto_002"]))
    destino = os.path.join("datos", "modelo", "v5")
    res = split_v5.escribir(destino, salida, cambios, entrada, mm.huella_manifiesto(r["manifiesto"]))
    print(f"Split v5 (propuesta): {res['total_v4']} del v4 → {res['total_v5']} imágenes")
    for p in PARTICIONES:
        print(f"  {p}: v4 {res['entrada_v4'][p]} → v5 {res['v5'][p]}")
    for k, n in res["cambios"].items():
        print(f"  {k}: {n}")
    print(f"  Comprobaciones: {res['comprobaciones']}")
    print(f"  Archivos en {destino}/ (raíz de imágenes: {r['raiz_modelo']})")
    return EXITO


def _cmd_generar_manifiesto_002(args):
    import os

    from avocadoia_modelo import dataset_002

    cfg, r = _rutas(args)
    d = cfg["dataset_002"]
    filas, res = dataset_002.generar(d["particion"], cfg["filtros"]["manifiesto_002"], d["huella_particion"])
    proc = dataset_002.comprobar_procesado(os.path.join(r["raiz_modelo"], "PROCESADO"), cfg["filtros"]["dataset_002"],
                                           cfg["filtros"]["fuentes_002"])
    res.update(procesado=proc)
    ruta = dataset_002.escribir(filas, res, os.path.dirname(d["manifiesto"]))
    print(f"Dataset 002: {res['total']} imágenes · huella de la partición {res['huella_particion'][:8]} (coincide)")
    print(f"  PROCESADO generado con la configuración vigente: {'sí' if proc['coincide'] else 'NO'} "
          f"({(proc['huella_procesado'] or 'sin .configuracion')[:8]})")
    print(f"  Manifiesto: {ruta}")
    return EXITO if proc["coincide"] else ERROR_DATOS


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
            "resumir-explicaciones": _cmd_resumir_explicaciones, "calibrar": _cmd_calibrar, "diagrama": _cmd_diagrama, "campo-etl": _cmd_campo_etl, "generar-v5": _cmd_generar_v5, "generar-manifiesto-002": _cmd_generar_manifiesto_002, "evaluar-campo": _cmd_evaluar_campo, "spike-explain": _cmd_spike_explain}


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
