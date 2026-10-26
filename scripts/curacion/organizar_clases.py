"""Curación inicial de las carpetas de clase de Modelo/ (2026-10-25).

Decisiones del equipo aplicadas:
- Retirar de AGUACATESANOS las copias exactas, el archivo corrupto, las imágenes con lado menor
  a 224 px y los casi duplicados confirmados visualmente.
- Retirar los casi duplicados confirmados de ANTRACNOSIS y PEDUNCULO.
- Incorporar a AGUACATESANOS el pedúnculo sano (clase 0) del artículo MDPI de ring-neck, extraído
  de los ZIP de PORCLASIFICAR/Drive, conservando su partición de origen.
- No se borra nada: lo retirado se mueve a Modelo/RETIRADAS/<motivo>/ y PORCLASIFICAR no se toca.
- No se renombra ni se cambia el formato de ningún archivo.

Uso (desde la raíz de Entregables):
    python scripts/curacion/organizar_clases.py            # simulación, no modifica nada
    python scripts/curacion/organizar_clases.py --aplicar  # ejecuta los movimientos
"""
import argparse
import collections
import csv
import hashlib
import io
import os
import shutil
import sys
import zipfile
from datetime import date

from PIL import Image, ImageOps

EXT = ('.jpg', '.jpeg', '.png')
CLASES = ('AGUACATESANOS', 'ANTRACNOSIS', 'PEDUNCULO')
LADO_MINIMO = 224
# Mismo contenido etiquetado como clase 0 y clase 1 en la fuente (ver PEDUNCULO/README.md).
SHA_CONFLICTO = 'b29d286c3fd4'
PRIORIDAD_SPLIT = {'test': 0, 'val': 1, 'train': 2}


def leer_imagen(data):
    """Devuelve (ancho, alto) tras aplicar la orientación EXIF, o None si no se puede decodificar."""
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
        return ImageOps.exif_transpose(im).size
    except Exception:
        return None


def inventariar(modelo):
    filas = []
    for clase in CLASES:
        base = os.path.join(modelo, clase)
        for raiz, _, archivos in os.walk(base):
            for nombre in archivos:
                if not nombre.lower().endswith(EXT):
                    continue
                ruta = os.path.join(raiz, nombre)
                data = open(ruta, 'rb').read()
                filas.append({
                    'ruta': os.path.relpath(ruta, modelo).replace('\\', '/'),
                    'clase': clase,
                    'sha256': hashlib.sha256(data).hexdigest(),
                    'tam': leer_imagen(data),
                })
    filas.sort(key=lambda f: f['ruta'])
    return filas


def planificar_retiros(filas, confirmados):
    """Devuelve {ruta: (motivo, ruta_conservada)} en orden de prioridad de motivos."""
    retiros = {}

    for f in filas:
        if f['tam'] is None:
            retiros[f['ruta']] = ('corrupta', '')

    por_sha = collections.defaultdict(list)
    for f in filas:
        if f['ruta'] not in retiros:
            por_sha[(f['clase'], f['sha256'])].append(f)
    for grupo in por_sha.values():
        if len(grupo) > 1:
            canonica = min(grupo, key=lambda f: f['ruta'])
            for f in grupo:
                if f is not canonica:
                    retiros[f['ruta']] = ('duplicado_exacto', canonica['ruta'])

    for f in filas:
        if f['ruta'] not in retiros and f['clase'] == 'AGUACATESANOS' and min(f['tam']) < LADO_MINIMO:
            retiros[f['ruta']] = ('menor_224px', '')

    por_ruta = {f['ruta']: f for f in filas}
    for miembros in confirmados.values():
        vivos = [por_ruta[r] for r in miembros if r in por_ruta and r not in retiros]
        if len(vivos) < 2:
            continue
        conservada = max(vivos, key=lambda f: (f['tam'][0] * f['tam'][1], [-ord(c) for c in f['ruta']]))
        for f in vivos:
            if f is not conservada:
                retiros[f['ruta']] = ('casi_duplicado', conservada['ruta'])
    return retiros


def planificar_pedunculo_sano(modelo, shas_existentes):
    """Agrupa la clase 0 de los ZIP por contenido y decide su partición y destino."""
    contenidos = {}
    clase1 = set()
    for zip_ruta in sorted(os.listdir(os.path.join(modelo, 'PORCLASIFICAR', 'Drive'))):
        if not zip_ruta.endswith('.zip'):
            continue
        zf = zipfile.ZipFile(os.path.join(modelo, 'PORCLASIFICAR', 'Drive', zip_ruta))
        for nombre in sorted(zf.namelist()):
            if not nombre.lower().endswith(EXT):
                continue
            partes = nombre.split('/')
            clase_fuente = partes[-2]
            split = partes[-3] if len(partes) >= 4 else ''
            data = zf.read(nombre)
            sha = hashlib.sha256(data).hexdigest()
            if clase_fuente == '1':
                clase1.add(sha)
                continue
            if clase_fuente != '0':
                continue
            c = contenidos.setdefault(sha, {'sha256': sha, 'data': data, 'referencias': [], 'splits': set(),
                                            'nombres': set()})
            c['referencias'].append(f'{zip_ruta}::{nombre}')
            c['nombres'].add(partes[-1])
            if split in PRIORIDAD_SPLIT:
                c['splits'].add(split)

    plan = []
    usados = set()
    for sha in sorted(contenidos):
        c = contenidos[sha]
        nombre = sorted(c['nombres'])[0]
        tam = leer_imagen(c['data'])
        if sha.startswith(SHA_CONFLICTO) or sha in clase1:
            disposicion, destino, split = 'excluida_conflicto_clase_0_y_1', '', ''
        elif sha in shas_existentes:
            disposicion, destino, split = 'ya_presente_en_carpetas', '', ''
        elif tam is None:
            disposicion, destino, split = 'excluida_corrupta', '', ''
        else:
            if c['splits']:
                split = min(c['splits'], key=PRIORIDAD_SPLIT.get)
                carpeta = f'AGUACATESANOS/DRIVE_PARTICIONES_ARTICULO/{split}'
            else:
                split = ''
                carpeta = 'AGUACATESANOS/DRIVE_CANDIDATAS'
            destino = f'{carpeta}/{nombre}'
            if destino in usados:
                base, ext = os.path.splitext(nombre)
                destino = f'{carpeta}/{base}__{sha[:8]}{ext}'
            usados.add(destino)
            disposicion = 'incorporada'
        plan.append({
            'sha256': sha, 'nombre_original': nombre, 'ancho': tam[0] if tam else '',
            'alto': tam[1] if tam else '', 'splits_fuente': ';'.join(sorted(c['splits'])),
            'split_asignado': split, 'ocurrencias': len(c['referencias']),
            'referencias': ' | '.join(c['referencias']), 'destino': destino,
            'disposicion': disposicion, 'data': c['data'],
        })
    return plan


def escribir_csv(ruta, campos, filas):
    os.makedirs(os.path.dirname(ruta), exist_ok=True)
    with open(ruta, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=campos, lineterminator='\n', extrasaction='ignore')
        w.writeheader()
        w.writerows(filas)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--modelo', default='Modelo')
    ap.add_argument('--registro', default='datos/curacion')
    ap.add_argument('--aplicar', action='store_true', help='Ejecuta los movimientos (por defecto, simulación).')
    args = ap.parse_args()

    confirmados = collections.defaultdict(list)
    with open(os.path.join(args.registro, 'casi_duplicados_confirmados.csv'), encoding='utf-8') as fh:
        for r in csv.DictReader(fh):
            confirmados[r['grupo']].append(r['ruta'])

    filas = inventariar(args.modelo)
    retiros = planificar_retiros(filas, confirmados)
    pedunculo_sano = planificar_pedunculo_sano(args.modelo, {f['sha256'] for f in filas})

    print('Antes por clase:', dict(collections.Counter(f['clase'] for f in filas)))
    print('Retiros por clase y motivo:')
    for (clase, motivo), n in sorted(collections.Counter(
            (r.split('/')[0], m) for r, (m, _) in retiros.items()).items()):
        print(f'  {clase:14} {motivo:18} {n}')
    print('Pedúnculo sano (clase 0):', dict(collections.Counter(p['disposicion'] for p in pedunculo_sano)))
    print('  por partición:', dict(collections.Counter(
        p['split_asignado'] or 'candidata' for p in pedunculo_sano if p['disposicion'] == 'incorporada')))
    despues = collections.Counter(f['clase'] for f in filas if f['ruta'] not in retiros)
    despues['AGUACATESANOS'] += sum(p['disposicion'] == 'incorporada' for p in pedunculo_sano)
    print('Después por clase:', dict(despues))

    if not args.aplicar:
        print('\nSimulación: no se modificó nada. Use --aplicar para ejecutar.')
        return 0

    if os.path.exists(os.path.join(args.registro, 'retiros.csv')):
        print('\nYa existe un registro de una curación aplicada; no se sobrescribe.')
        return 2

    hoy = date.today().isoformat()
    registro = []
    por_ruta = {f['ruta']: f for f in filas}
    for ruta, (motivo, conservada) in sorted(retiros.items()):
        destino = f'RETIRADAS/{motivo}/{ruta}'
        os.makedirs(os.path.dirname(os.path.join(args.modelo, destino)), exist_ok=True)
        shutil.move(os.path.join(args.modelo, ruta), os.path.join(args.modelo, destino))
        tam = por_ruta[ruta]['tam']
        registro.append({'ruta_original': ruta, 'ruta_retirada': destino, 'sha256': por_ruta[ruta]['sha256'],
                         'ancho': tam[0] if tam else '', 'alto': tam[1] if tam else '',
                         'motivo': motivo, 'conservada': conservada, 'fecha': hoy})
    escribir_csv(os.path.join(args.registro, 'retiros.csv'),
                 ['ruta_original', 'ruta_retirada', 'sha256', 'ancho', 'alto', 'motivo', 'conservada', 'fecha'],
                 registro)

    for p in pedunculo_sano:
        if p['disposicion'] == 'incorporada':
            destino = os.path.join(args.modelo, p['destino'])
            os.makedirs(os.path.dirname(destino), exist_ok=True)
            with open(destino, 'xb') as fh:
                fh.write(p['data'])
        p['fecha'] = hoy
    escribir_csv(os.path.join(args.registro, 'pedunculo_sano_drive.csv'),
                 ['sha256', 'nombre_original', 'ancho', 'alto', 'splits_fuente', 'split_asignado',
                  'ocurrencias', 'referencias', 'destino', 'disposicion', 'fecha'], pedunculo_sano)
    print(f'\nAplicado: {len(registro)} archivos retirados, '
          f'{sum(p["disposicion"] == "incorporada" for p in pedunculo_sano)} incorporados.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
