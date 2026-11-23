#!/usr/bin/env python
"""Genera el diagrama ER de JobDevs (.drawio) directamente desde los modelos Django.

El diagrama se deriva del ORM, no del dibujo manual: cada migración nueva se
refleja regenerando el archivo. No toca la base de datos (solo introspección de
metadatos via django.setup()).

Dos notaciones:

  fisico  tablas con PK/FK dentro y flechas de FK   -> docs/ER_JOBDEVS.drawio
  chen    rectángulo=entidad, elipse=atributo, rombo=relación, 1/N=cardinalidad
          (modelo conceptual completo, los 216 atributos) -> docs/ER_JOBDEVS_chen.drawio

Uso:
    .venv/bin/python scripts/generate_er_drawio.py
    .venv/bin/python scripts/generate_er_drawio.py --notacion chen
    .venv/bin/python scripts/generate_er_drawio.py --notacion chen --check   # CI
    .venv/bin/python scripts/generate_er_drawio.py --con-auth                # + tablas de auth
"""

from __future__ import annotations

import argparse
import os
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# El generador solo lee metadatos: valores inocuos para que settings.py cargue
# fuera del entorno de producción.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('DJANGO_SECRET_KEY', 'er-generator-local')
os.environ.setdefault('DB_ENGINE', 'sqlite3')
os.environ.setdefault('DB_NAME', ':memory:')
sys.path.insert(0, str(BASE_DIR))

import django  # noqa: E402

django.setup()

from django.apps import apps  # noqa: E402

# --------------------------------------------------------------------------- #
# Estilo
# --------------------------------------------------------------------------- #

APPS_ORDEN = ['proyectos', 'postulaciones', 'contrataciones', 'usuarios',
              'avances', 'mensajes', 'notificaciones', 'favoritos',
              'logs', 'disputas', 'auth']

COLORES = {
    'usuarios':       ('#dae8fc', '#6c8ebf'),
    'proyectos':      ('#d5e8d4', '#82b366'),
    'postulaciones':  ('#fff2cc', '#d6b656'),
    'contrataciones': ('#ffe6cc', '#d79b00'),
    'avances':        ('#e1d5e7', '#9673a6'),
    'mensajes':       ('#f5f5f5', '#999999'),
    'notificaciones': ('#fbe7e6', '#b85450'),
    'favoritos':      ('#e6f2f8', '#5b8db8'),
    'logs':           ('#eeeeee', '#666666'),
    'disputas':       ('#f8cecc', '#b85450'),
    'auth':           ('#f0f0f0', '#aaaaaa'),
}

ANCHO = 320          # ancho de cada tabla
ALTO_FILA = 22
ALTO_CABECERA = 34
GAP_X = 210
GAP_Y = 46
TOP_TABLAS = 176           # y donde empieza la primera tabla (bajo leyenda)
MAX_ALTO_COLUMNA = 1450    # a partir de aquí la columna se parte en otra
MAX_ANCHO_FILA = 3900      # ancho máximo antes de abrir una nueva banda
GAP_BANDA = 120            # separación vertical entre bandas

TIPOS_CORTOS = {
    'AutoField': 'Auto',
    'BigAutoField': 'BigAuto',
    'CharField': 'Char',
    'TextField': 'Text',
    'EmailField': 'Email',
    'SlugField': 'Slug',
    'URLField': 'URL',
    'BooleanField': 'Bool',
    'IntegerField': 'Int',
    'PositiveSmallIntegerField': 'PosSmallInt',
    'PositiveIntegerField': 'PosInt',
    'BigIntegerField': 'BigInt',
    'DecimalField': 'Decimal',
    'FloatField': 'Float',
    'DateTimeField': 'DateTime',
    'DateField': 'Date',
    'TimeField': 'Time',
    'DurationField': 'Duration',
    'FileField': 'File',
    'ImageField': 'Image',
    'JSONField': 'JSON',
    'UUIDField': 'UUID',
    'ForeignKey': 'FK',
    'OneToOneField': 'O2O',
}


# --------------------------------------------------------------------------- #
# Recolección de metadatos
# --------------------------------------------------------------------------- #

def _tipo(f) -> str:
    nombre = type(f).__name__
    if f.is_relation:
        return TIPOS_CORTOS.get(nombre, nombre)
    corto = TIPOS_CORTOS.get(nombre, nombre)
    if getattr(f, 'max_length', None) and nombre in ('CharField', 'SlugField', 'EmailField', 'URLField'):
        return f'{corto}({f.max_length})'
    return corto


def recolectar(incluir_auth: bool) -> dict:
    tablas: dict[str, dict] = {}
    for modelo in apps.get_models():
        etiqueta = modelo._meta.app_label
        if modelo.__module__.startswith('django.'):
            continue
        if etiqueta in ('auth', 'admin', 'contenttypes', 'sessions') and not incluir_auth:
            continue

        filas = []
        for f in modelo._meta.concrete_fields:
            fila = {
                'nombre': f.column,
                'tipo': _tipo(f),
                'pk': bool(f.primary_key),
                'fk': f.related_model._meta.db_table if f.is_relation else None,
                'o2o': bool(getattr(f, 'one_to_one', False)),
                'null': bool(getattr(f, 'null', False)),
                'unico': bool(getattr(f, 'unique', False)),
                'choices': bool(getattr(f, 'choices', None)),
            }
            filas.append(fila)

        tablas[modelo._meta.db_table] = {
            'tabla': modelo._meta.db_table,
            'modelo': f'{etiqueta}.{modelo.__name__}',
            'app': etiqueta,
            'filas': filas,
            'm2m': False,
        }

        if incluir_auth and etiqueta in ('auth', 'admin', 'contenttypes', 'sessions'):
            continue

        for campo in modelo._meta.many_to_many:
            if (not incluir_auth
                    and campo.related_model._meta.app_label in ('auth', 'admin', 'contenttypes', 'sessions')):
                continue  # M2M internas de auth (groups, user_permissions)
            through = campo.remote_field.through
            if through._meta.auto_created is False:
                continue  # through explícito: ya existe como modelo propio
            tablas[through._meta.db_table] = {
                'tabla': through._meta.db_table,
                'modelo': f'{etiqueta}.{modelo.__name__}.{campo.name} (M2M)',
                'app': etiqueta,
                'filas': [{
                    'nombre': f.column,
                    'tipo': _tipo(f),
                    'pk': bool(f.primary_key),
                    'fk': f.related_model._meta.db_table if f.is_relation else None,
                    'o2o': bool(getattr(f, 'one_to_one', False)),
                    'null': bool(getattr(f, 'null', False)),
                    'unico': bool(getattr(f, 'unique', False)),
                    'choices': bool(getattr(f, 'choices', None)),
                } for f in through._meta.concrete_fields],
                'm2m': True,
            }
    return tablas


# --------------------------------------------------------------------------- #
# Layout
# --------------------------------------------------------------------------- #

def ordenar_tablas(tablas: dict) -> list[str]:
    def clave(t):
        info = tablas[t]
        try:
            iapp = APPS_ORDEN.index(info['app'])
        except ValueError:
            iapp = len(APPS_ORDEN)
        # dentro de la app: primero la tabla cabecera (la que tiene PK propia),
        # luego por número de campos descendente
        return (iapp, info['app'], -len(info['filas']), t)

    return sorted(tablas, key=clave)


def layout(tablas: dict) -> dict[str, dict]:
    """Columnas por app, empaquetadas en bandas y partidas si son muy altas.

    `usuarios` queda en el centro porque casi todas las FK apuntan a ella: así
    las aristas recorren distancias cortas y cruzan menos tablas. Las columnas se
    agrupan en bandas horizontales para que la página no quede desproporcionada.
    """
    por_app: dict[str, list[str]] = defaultdict(list)
    for t in ordenar_tablas(tablas):
        por_app[tablas[t]['app']].append(t)

    apps_ordenadas = sorted(
        por_app,
        key=lambda a: (APPS_ORDEN.index(a) if a in APPS_ORDEN else len(APPS_ORDEN), a),
    )

    # 1) columnas lógicas: una por app, partida si excede MAX_ALTO_COLUMNA
    columnas: list[dict] = []
    for app in apps_ordenadas:
        actual = {'app': app, 'etiqueta': app, 'tablas': [], 'alto': 0}
        for t in por_app[app]:
            alto = ALTO_CABECERA + ALTO_FILA * len(tablas[t]['filas'])
            if actual['tablas'] and actual['alto'] + alto > MAX_ALTO_COLUMNA:
                columnas.append(actual)
                actual = {'app': app, 'etiqueta': f'{app} (cont.)', 'tablas': [], 'alto': 0}
            actual['tablas'].append(t)
            actual['alto'] += alto + GAP_Y
        if actual['tablas']:
            columnas.append(actual)

    # 2) empaquetar en bandas horizontales
    bandas: list[list[dict]] = [[]]
    x = 40
    for col in columnas:
        if bandas[-1] and x + ANCHO > MAX_ANCHO_FILA:
            bandas.append([])
            x = 40
        bandas[-1].append(col)
        x += ANCHO + GAP_X

    # 3) posicionar, centrando cada columna dentro de su banda
    posiciones: dict = {}
    y_banda = TOP_TABLAS
    for banda in bandas:
        alto_banda = max(c['alto'] for c in banda)
        x = 40
        for col in banda:
            y = y_banda + (alto_banda - col['alto']) / 2
            col['x'] = x
            col['y'] = y
            col['y_cabecera'] = y - 30
            for t in col['tablas']:
                alto = ALTO_CABECERA + ALTO_FILA * len(tablas[t]['filas'])
                posiciones[t] = {'x': x, 'y': y, 'w': ANCHO, 'h': alto,
                                 'app': col['app'], 'etiqueta': col['etiqueta']}
                y += alto + GAP_Y
            x += ANCHO + GAP_X
        y_banda += alto_banda + GAP_BANDA

    posiciones['__columnas__'] = {'columnas': [
        {'x': c['x'], 'y': c['y'], 'y_cabecera': c['y_cabecera'], 'etiqueta': c['etiqueta']}
        for banda in bandas for c in banda
    ]}
    return posiciones


def limites(posiciones: dict) -> tuple[int, int]:
    tablas = {k: v for k, v in posiciones.items() if not k.startswith('__')}
    max_x = max(p['x'] + p['w'] for p in tablas.values()) + 80
    max_y = max(p['y'] + p['h'] for p in tablas.values()) + 80
    return int(max_x), int(max_y)


# --------------------------------------------------------------------------- #
# Emisión XML
# --------------------------------------------------------------------------- #

def valor_fila(fila: dict) -> str:
    marca = ''
    if fila['pk']:
        marca = '<font color="#b85450"><b>PK</b></font> '
    elif fila['fk']:
        marca = '<font color="#6c8ebf"><b>FK</b></font> '

    nombre = f'<b>{fila["nombre"]}</b>'
    extra = f'<font color="#888888">{fila["tipo"]}</font>'
    if fila['fk']:
        extra = f'<font color="#6c8ebf">{fila["tipo"]}→{fila["fk"]}</font>'

    flags = ''
    if fila['null']:
        flags += ' <font color="#999999">null</font>'
    if fila['unico']:
        flags += ' <font color="#d79b00">úq</font>'
    if fila['choices']:
        flags += ' <font color="#82b366">enum</font>'

    return f'{marca}{nombre}&nbsp;&nbsp;{extra}{flags}'


def construir_xml(tablas: dict, posiciones: dict, titulo: str) -> ET.ElementTree:
    ancho_pag, alto_pag = limites(posiciones)
    mxfile = ET.Element('mxfile', {
        'host': 'jobdevs-er-generator',
        'agent': 'scripts/generate_er_drawio.py',
        'version': '24.0.0',
        'type': 'device',
    })
    diagrama = ET.SubElement(mxfile, 'diagram', {'id': 'er-jobdevs', 'name': titulo})
    modelo = ET.SubElement(diagrama, 'mxGraphModel', {
        'dx': str(ancho_pag), 'dy': str(alto_pag), 'grid': '1', 'gridSize': '10',
        'guides': '1', 'tooltips': '1', 'connect': '1', 'arrows': '1', 'fold': '1',
        'page': '1', 'pageScale': '1', 'pageWidth': str(ancho_pag),
        'pageHeight': str(alto_pag), 'math': '0', 'shadow': '0',
    })
    raiz = ET.SubElement(modelo, 'root')
    ET.SubElement(raiz, 'mxCell', {'id': '0'})
    ET.SubElement(raiz, 'mxCell', {'id': '1', 'parent': '0'})

    # --- Título y leyenda -------------------------------------------------- #
    titulo_cell = ET.SubElement(raiz, 'mxCell', {
        'id': 'titulo', 'value': valor_titulo(tablas), 'vertex': '1', 'parent': '1',
        'style': 'text;html=1;align=left;verticalAlign=top;fontSize=14;whiteSpace=wrap;',
    })
    ET.SubElement(titulo_cell, 'mxGeometry', {
        'x': '40', 'y': '18', 'width': '1500', 'height': '52', 'as': 'geometry',
    })
    leyenda = ET.SubElement(raiz, 'mxCell', {
        'id': 'leyenda', 'value': valor_leyenda(), 'vertex': '1', 'parent': '1',
        'style': ('text;html=1;align=left;verticalAlign=middle;fontSize=11;'
                  'spacing=6;whiteSpace=wrap;fillColor=#ffffff;strokeColor=#cccccc;'),
    })
    ET.SubElement(leyenda, 'mxGeometry', {
        'x': '40', 'y': '74', 'width': '1040', 'height': '56', 'as': 'geometry',
    })

    # --- Cabeceras de columna por app -------------------------------------- #
    for i, col in enumerate(posiciones['__columnas__']['columnas']):
        cab = ET.SubElement(raiz, 'mxCell', {
            'id': f'col_{i}',
            'value': f'<b>{col["etiqueta"]}</b>',
            'vertex': '1', 'parent': '1',
            'style': 'text;html=1;align=center;verticalAlign=middle;fontSize=13;fontColor=#555555;',
        })
        ET.SubElement(cab, 'mxGeometry', {
            'x': str(col['x']), 'y': str(col['y_cabecera']),
            'width': str(ANCHO), 'height': '24', 'as': 'geometry',
        })

    # --- Tablas ------------------------------------------------------------ #
    for t in ordenar_tablas(tablas):
        info = tablas[t]
        p = posiciones[t]
        fill, stroke = COLORES.get(info['app'], ('#ffffff', '#666666'))
        cabecera = f'<b>{t}</b>'
        if info['m2m']:
            cabecera += ' <font style="font-size:10px">· M2M</font>'
        cabecera += f'<br><font style="font-size:9px" color="#666666">{info["modelo"]}</font>'

        celda = ET.SubElement(raiz, 'mxCell', {
            'id': f't_{t}', 'value': cabecera, 'vertex': '1', 'parent': '1',
            'style': ('swimlane;fontStyle=1;align=center;verticalAlign=top;childLayout=stackLayout;'
                      'horizontal=1;startSize=%d;horizontalStack=0;resizeParent=1;resizeParentMax=0;'
                      'resizeLast=0;collapsible=0;marginBottom=0;html=1;rounded=0;'
                      'fillColor=%s;strokeColor=%s;verticalAlign=top;spacingTop=2;'
                      'fontSize=12;swimlaneFillColor=%s;' % (ALTO_CABECERA, fill, stroke, '#ffffff')),
        })
        geo = ET.SubElement(celda, 'mxGeometry', {
            'x': str(p['x']), 'y': str(p['y']), 'width': str(p['w']), 'height': str(p['h']),
            'as': 'geometry',
        })

        for i, fila in enumerate(info['filas']):
            valor = valor_fila(fila)
            color_fondo = '#f5f5f5' if fila['pk'] else 'none'
            estilo = ('text;strokeColor=none;fillColor=%s;align=left;verticalAlign=middle;'
                      'spacingLeft=6;spacingRight=4;overflow=hidden;rotatable=0;'
                      'points=[[0,0.5],[1,0.5]];portConstraint=eastwest;fontSize=11;html=1;'
                      % color_fondo)
            fila_cell = ET.SubElement(raiz, 'mxCell', {
                'id': f'f_{t}_{fila["nombre"]}', 'value': valor, 'vertex': '1',
                'parent': f't_{t}', 'style': estilo,
            })
            ET.SubElement(fila_cell, 'mxGeometry', {
                'x': '0', 'y': str(ALTO_CABECERA + i * ALTO_FILA),
                'width': str(p['w']), 'height': str(ALTO_FILA), 'as': 'geometry',
            })

    # --- Relaciones (FK) --------------------------------------------------- #
    for t in ordenar_tablas(tablas):
        info = tablas[t]
        for fila in info['filas']:
            destino = fila['fk']
            if not destino or destino not in tablas:
                continue
            # apuntar a la fila PK de la tabla destino
            pk_destino = next((f['nombre'] for f in tablas[destino]['filas'] if f['pk']), None)
            if pk_destino is None:
                continue
            _, stroke = COLORES.get(info['app'], ('#ffffff', '#666666'))
            origen_id = f'f_{t}_{fila["nombre"]}'
            destino_id = f'f_{destino}_{pk_destino}'
            arista = ET.SubElement(raiz, 'mxCell', {
                'id': f'e_{t}_{fila["nombre"]}',
                'value': '',
                'edge': '1', 'parent': '1',
                'source': origen_id, 'target': destino_id,
                'style': ('edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;'
                          'jettySize=auto;html=1;endArrow=ERone;endFill=0;'
                          'startArrow=ERmany;startFill=0;strokeColor=%s;'
                          'fontSize=10;labelBackgroundColor=#ffffff;' % stroke),
            })
            ET.SubElement(arista, 'mxGeometry', {'relative': '1', 'as': 'geometry'})

    return ET.ElementTree(mxfile)


def valor_titulo(tablas: dict) -> str:
    n_filas = sum(len(t['filas']) for t in tablas.values())
    fks = sum(1 for t in tablas.values() for f in t['filas'] if f['fk'])
    return (f'<b>JobDevs — Modelo Entidad-Relación</b><br>'
            f'<font style="font-size:10px" color="#666666">Generado desde los modelos Django · '
            f'{len(tablas)} tablas · {n_filas} columnas · {fks} relaciones FK</font>')


def valor_leyenda() -> str:
    return ('<b>PK</b> clave primaria · <b>FK</b> clave foránea (la flecha apunta a la tabla '
            'referenciada) · <b>null</b> admite NULL · <b>úq</b> unique · <b>enum</b> choices · '
            '<b>M2M</b> tabla intermedia de ManyToMany.<br>'
            '<font color="#888888">Regenerar tras cada migración: '
            '<code>.venv/bin/python scripts/generate_er_drawio.py</code></font>')


# --------------------------------------------------------------------------- #
# Notación Chen (modelo conceptual): rectángulo = entidad, elipse = atributo,
# rombo = relación, 1/N = cardinalidad.
# --------------------------------------------------------------------------- #

CHEN_ENT_W, CHEN_ENT_H = 200, 56
CHEN_ELIPSE_H = 28
CHEN_PITCH_ATRIBUTO = 34
CHEN_DIAM_W, CHEN_DIAM_H = 132, 74
CHEN_GAP_ATRIBUTO = 48        # separación elipse ↔ rectángulo
CHEN_GAP_COLUMNA = 620        # pasillo entre celdas (donde viven los rombos)
CHEN_GAP_FILA = 540
CHEN_COLUMNAS = 4

VERBOS_RELACION = {
    'proyecto_id': 'pertenece',
    'empresa_id': 'publica',
    'usuario_id': 'tiene',
    'desarrollador_id': 'asigna',
    'equipo_id': 'agrupa',
    'entregable_id': 'entrega',
    'categoria_id': 'clasifica',
    'contratacion_id': 'origina',
    'postulacion_id': 'genera',
    'ficha_sena_id': 'acredita',
    'disputa_id': 'contiene',
    'mediador_id': 'media',
    'emisor_id': 'envia',
    'remitente_id': 'envia',
    'receptor_id': 'recibe',
    'verificado_por_id': 'verifica',
    'creada_por_id': 'crea',
    'autorizado_por_id': 'autoriza',
    'cambiado_por': 'cambia',
    'ejecutado_por': 'ejecuta',
    'iniciado_por_id': 'inicia',
}

# nombres de relación que dependen de la tabla, no solo de la columna
VERBOS_POR_TABLA = {
    ('equipos_miembros', 'usuario_id'): 'integra',
    ('equipos_miembros', 'equipo_id'): 'agrupa',
    ('perfil_empresa', 'usuario_id'): 'perfila',
    ('perfil_desarrollador', 'usuario_id'): 'perfila',
    ('usuarios', 'id'): 'tiene',
}


def texto_atributo(fila: dict) -> str:
    etiqueta = fila['nombre']
    if fila['fk']:
        etiqueta += ' (FK)'
    return etiqueta


def ancho_elipse(texto: str) -> int:
    return min(250, max(112, int(len(texto) * 7.2) + 26))


def nombre_relacion(tabla: str, fila: dict) -> str:
    return (VERBOS_POR_TABLA.get((tabla, fila['nombre']))
            or VERBOS_RELACION.get(fila['nombre'])
            or 'relaciona')


def _solapa(a: tuple, b: tuple, margen: float = 8) -> bool:
    return (a[0] < b[0] + b[2] + margen and b[0] < a[0] + a[2] + margen
            and a[1] < b[1] + b[3] + margen and b[1] < a[1] + a[3] + margen)


def _ubicar_rombo(p1: tuple, p2: tuple, ocupados: list, desplazamiento: float = 0.0) -> tuple:
    """Busca el punto más cercano al punto medio que no pise nada.

    `desplazamiento` mueve el punto de partida en perpendicular al eje
    entidad→entidad: así dos relaciones del mismo par viajan por carriles
    distintos y sus cardinalidades no se confunden.
    """
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    largo = max((dx * dx + dy * dy) ** 0.5, 1.0)
    px, py = -dy / largo, dx / largo
    bx, by = mx + px * desplazamiento, my + py * desplazamiento
    candidatos = [(bx, by)]
    for r in (90, 150, 220, 300, 400, 520):
        for ux, uy in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, -1), (-1, 1), (1, 1)):
            candidatos.append((bx + ux * r, by + uy * r))
    for cx, cy in candidatos:
        caja = (cx - CHEN_DIAM_W / 2, cy - CHEN_DIAM_H / 2, CHEN_DIAM_W, CHEN_DIAM_H)
        if not any(_solapa(caja, o) for o in ocupados):
            return caja
    return (mx - CHEN_DIAM_W / 2, my - CHEN_DIAM_H / 2, CHEN_DIAM_W, CHEN_DIAM_H)


def chen_layout(tablas: dict) -> dict:
    orden = ordenar_tablas(tablas)

    # 1) celdas: atributos repartidos a izquierda y derecha de la entidad
    celdas = []
    for t in orden:
        filas = sorted(tablas[t]['filas'], key=lambda f: (not f['pk'], f['nombre']))
        mitad = (len(filas) + 1) // 2
        izq, der = filas[:mitad], filas[mitad:]
        w_izq = max((ancho_elipse(texto_atributo(f)) for f in izq), default=0)
        w_der = max((ancho_elipse(texto_atributo(f)) for f in der), default=0)
        alto_attrs = max(len(izq), len(der)) * CHEN_PITCH_ATRIBUTO
        w = w_izq + CHEN_GAP_ATRIBUTO + CHEN_ENT_W + CHEN_GAP_ATRIBUTO + w_der
        celdas.append({'tabla': t, 'izq': izq, 'der': der, 'w_izq': w_izq,
                       'w_der': w_der, 'w': w, 'h': max(alto_attrs, CHEN_ENT_H)})

    # 2) rejilla
    ncol = CHEN_COLUMNAS
    renglones = [celdas[i:i + ncol] for i in range(0, len(celdas), ncol)]
    col_w = [0] * ncol
    for ren in renglones:
        for j, c in enumerate(ren):
            col_w[j] = max(col_w[j], c['w'])
    xs = []
    x = 40
    for j in range(ncol):
        xs.append(x)
        x += col_w[j] + CHEN_GAP_COLUMNA

    entidades: dict = {}
    atributos: list = []
    ocupados: list = []
    y = 170
    for i_ren, ren in enumerate(renglones):
        alto_ren = max(c['h'] for c in ren)
        for j, c in enumerate(ren):
            cx = xs[j] + (col_w[j] - c['w']) / 2
            cy = y + (alto_ren - c['h']) / 2
            ent_x = cx + c['w_izq'] + CHEN_GAP_ATRIBUTO
            ent_y = cy + (c['h'] - CHEN_ENT_H) / 2
            entidades[c['tabla']] = {
                'x': ent_x, 'y': ent_y, 'w': CHEN_ENT_W, 'h': CHEN_ENT_H,
                'cx': ent_x + CHEN_ENT_W / 2, 'cy': ent_y + CHEN_ENT_H / 2,
                'col': j, 'row': i_ren,
            }
            ocupados.append((cx, cy, c['w'], c['h']))

            for lado, fs in (('izq', c['izq']), ('der', c['der'])):
                n = len(fs)
                y0 = entidades[c['tabla']]['cy'] - n * CHEN_PITCH_ATRIBUTO / 2
                for k, f in enumerate(fs):
                    w = ancho_elipse(texto_atributo(f))
                    ax = (ent_x - CHEN_GAP_ATRIBUTO - w) if lado == 'izq' \
                        else (ent_x + CHEN_ENT_W + CHEN_GAP_ATRIBUTO)
                    atributos.append({'tabla': c['tabla'], 'fila': f,
                                      'x': ax, 'y': y0 + k * CHEN_PITCH_ATRIBUTO,
                                      'w': w, 'h': CHEN_ELIPSE_H})
        y += alto_ren + CHEN_GAP_FILA

    # 3) rombos de relación, uno por FK, en el pasillo más cercano y con carril propio
    relaciones: list = []
    carriles: dict = {}
    for t in orden:
        for fila in tablas[t]['filas']:
            destino = fila['fk']
            if not destino or destino not in entidades:
                continue
            e1, e2 = entidades[t], entidades[destino]
            if e1['col'] != e2['col']:
                clave = ('h', min(e1['col'], e2['col']), max(e1['col'], e2['col']))
            else:
                clave = ('v', min(e1['row'], e2['row']), max(e1['row'], e2['row']))
            k = carriles.get(clave, 0)
            carriles[clave] = k + 1
            desplazamiento = 0.0 if k == 0 else 80.0 * ((k + 1) // 2) * (1 if k % 2 else -1)
            caja = _ubicar_rombo((e1['cx'], e1['cy']), (e2['cx'], e2['cy']),
                                 ocupados, desplazamiento)
            relaciones.append({
                'id': f"rel_{t}_{fila['nombre']}",
                'nombre': nombre_relacion(t, fila),
                'x': caja[0], 'y': caja[1], 'w': caja[2], 'h': caja[3],
                'origen': t, 'destino': destino,
                'card_origen': '1' if fila['o2o'] else 'N',
                'columna': fila['nombre'],
            })
            ocupados.append(caja)

    ancho = int(max(o[0] + o[2] for o in ocupados) + 80)
    alto = int(max(o[1] + o[3] for o in ocupados) + 80)
    return {'entidades': entidades, 'atributos': atributos, 'relaciones': relaciones,
            'ancho': max(ancho, 1200), 'alto': max(alto, 800)}


def chen_xml(tablas: dict, datos: dict, titulo: str) -> ET.ElementTree:
    mxfile = ET.Element('mxfile', {
        'host': 'jobdevs-er-generator',
        'agent': 'scripts/generate_er_drawio.py',
        'version': '24.0.0',
        'type': 'device',
    })
    diagrama = ET.SubElement(mxfile, 'diagram', {'id': 'er-chen-jobdevs', 'name': titulo})
    modelo = ET.SubElement(diagrama, 'mxGraphModel', {
        'dx': str(datos['ancho']), 'dy': str(datos['alto']), 'grid': '1', 'gridSize': '10',
        'guides': '1', 'tooltips': '1', 'connect': '1', 'arrows': '1', 'fold': '1',
        'page': '1', 'pageScale': '1', 'pageWidth': str(datos['ancho']),
        'pageHeight': str(datos['alto']), 'math': '0', 'shadow': '0',
    })
    raiz = ET.SubElement(modelo, 'root')
    ET.SubElement(raiz, 'mxCell', {'id': '0'})
    ET.SubElement(raiz, 'mxCell', {'id': '1', 'parent': '0'})

    n_attr = len(datos['atributos'])
    n_rel = len(datos['relaciones'])
    titulo_cell = ET.SubElement(raiz, 'mxCell', {
        'id': 'titulo', 'vertex': '1', 'parent': '1',
        'value': (f'<b>JobDevs — Diagrama Entidad-Relación (Chen)</b><br>'
                  f'<font style="font-size:10px" color="#666666">{len(tablas)} entidades · '
                  f'{n_attr} atributos · {n_rel} relaciones · generado desde los modelos Django</font>'),
        'style': 'text;html=1;align=left;verticalAlign=top;fontSize=14;whiteSpace=wrap;',
    })
    ET.SubElement(titulo_cell, 'mxGeometry', {
        'x': '40', 'y': '18', 'width': '1600', 'height': '52', 'as': 'geometry',
    })
    leyenda = ET.SubElement(raiz, 'mxCell', {
        'id': 'leyenda', 'vertex': '1', 'parent': '1',
        'value': ('<b>Rectángulo</b> entidad · <b>Elipse</b> atributo (nombre subrayado = clave primaria, '
                  '<b>(FK)</b> = columna foránea) · <b>Rombo</b> relación · <b>1 / N</b> cardinalidad '
                  '(N del lado que guarda la FK).<br>'
                  '<font color="#888888">Regenerar: '
                  '<code>.venv/bin/python scripts/generate_er_drawio.py --notacion chen</code></font>'),
        'style': ('text;html=1;align=left;verticalAlign=middle;fontSize=11;spacing=6;'
                  'whiteSpace=wrap;fillColor=#ffffff;strokeColor=#cccccc;'),
    })
    ET.SubElement(leyenda, 'mxGeometry', {
        'x': '40', 'y': '74', 'width': '1150', 'height': '56', 'as': 'geometry',
    })

    # --- entidades ---
    for t, e in datos['entidades'].items():
        app = tablas[t]['app']
        fill, stroke = COLORES.get(app, ('#ffffff', '#666666'))
        celda = ET.SubElement(raiz, 'mxCell', {
            'id': f'ent_{t}', 'value': f'<b>{t}</b>', 'vertex': '1', 'parent': '1',
            'style': (f'rounded=0;whiteSpace=wrap;html=1;fillColor={fill};'
                      f'strokeColor={stroke};fontSize=13;fontStyle=1;'),
        })
        ET.SubElement(celda, 'mxGeometry', {
            'x': str(e['x']), 'y': str(e['y']), 'width': str(e['w']),
            'height': str(e['h']), 'as': 'geometry',
        })

    # --- atributos ---
    for a in datos['atributos']:
        fila = a['fila']
        app = tablas[a['tabla']]['app']
        _, stroke = COLORES.get(app, ('#ffffff', '#666666'))
        etiqueta = texto_atributo(fila)
        if fila['fk']:
            etiqueta = etiqueta.replace(' (FK)', ' <font color="#6c8ebf">(FK)</font>')
        valor = f'<u><b>{etiqueta}</b></u>' if fila['pk'] else f'<b>{etiqueta}</b>'
        relleno = '#fdecea' if fila['pk'] else '#ffffff'
        celda = ET.SubElement(raiz, 'mxCell', {
            'id': f"atr_{a['tabla']}_{fila['nombre']}", 'value': valor, 'vertex': '1',
            'parent': '1',
            'style': (f'ellipse;whiteSpace=wrap;html=1;fillColor={relleno};'
                      f'strokeColor={stroke};fontSize=10;'),
        })
        ET.SubElement(celda, 'mxGeometry', {
            'x': str(a['x']), 'y': str(a['y']), 'width': str(a['w']),
            'height': str(a['h']), 'as': 'geometry',
        })
        arista = ET.SubElement(raiz, 'mxCell', {
            'id': f"ae_{a['tabla']}_{fila['nombre']}", 'edge': '1', 'parent': '1',
            'source': f"atr_{a['tabla']}_{fila['nombre']}", 'target': f"ent_{a['tabla']}",
            'style': 'endArrow=none;html=1;rounded=0;strokeColor=#999999;',
        })
        ET.SubElement(arista, 'mxGeometry', {'relative': '1', 'as': 'geometry'})

    # --- relaciones (rombos + cardinalidades) ---
    # puertos: si todas las líneas entran por el mismo punto del rectángulo se
    # apilan y no se distinguen. Se reparten por el perímetro de cada entidad.
    puertos: dict = {}

    def _lado(caja_origen, caja_destino, clave):
        """Lado del origen que mira al destino, y posición repartida en ese lado."""
        ox, oy = caja_origen[0] + caja_origen[2] / 2, caja_origen[1] + caja_origen[3] / 2
        dx = caja_destino[0] + caja_destino[2] / 2 - ox
        dy = caja_destino[1] + caja_destino[3] / 2 - oy
        if abs(dy) >= abs(dx):
            lado = 'top' if dy < 0 else 'bottom'
        else:
            lado = 'left' if dx < 0 else 'right'
        k = puertos.get((clave, lado), 0)
        puertos[(clave, lado)] = k + 1
        return lado, 0.15 + 0.7 * ((k % 6) / 5)

    def _estilo_puerto(prefijo, lado, pos):
        if lado == 'top':
            x, y = pos, 0.0
        elif lado == 'bottom':
            x, y = pos, 1.0
        elif lado == 'left':
            x, y = 0.0, pos
        else:
            x, y = 1.0, pos
        return f'{prefijo}X={x:.2f};{prefijo}Y={y:.2f};{prefijo}Dx=0;{prefijo}Dy=0;'

    for r in datos['relaciones']:
        celda = ET.SubElement(raiz, 'mxCell', {
            'id': r['id'], 'value': f"<b>{r['nombre']}</b>", 'vertex': '1', 'parent': '1',
            'style': ('rhombus;whiteSpace=wrap;html=1;fillColor=#fff2cc;'
                      'strokeColor=#d6b656;fontSize=10;'),
        })
        ET.SubElement(celda, 'mxGeometry', {
            'x': str(r['x']), 'y': str(r['y']), 'width': str(r['w']),
            'height': str(r['h']), 'as': 'geometry',
        })
        caja_rombo = (r['x'], r['y'], r['w'], r['h'])

        def _caja(tabla):
            e = datos['entidades'][tabla]
            return (e['x'], e['y'], e['w'], e['h'])

        caja_origen = _caja(r['origen'])
        caja_destino = _caja(r['destino'])

        for sufijo, origen, destino, card, puerto in (
                ('a', f"ent_{r['origen']}", r['id'], r['card_origen'],
                 _estilo_puerto('exit', *_lado(caja_origen, caja_rombo, f"ent_{r['origen']}"))
                 + _estilo_puerto('entry', *_lado(caja_rombo, caja_origen, f"{r['id']}_a"))),
                ('b', r['id'], f"ent_{r['destino']}", '1',
                 _estilo_puerto('exit', *_lado(caja_rombo, caja_destino, f"{r['id']}_b"))
                 + _estilo_puerto('entry', *_lado(caja_destino, caja_rombo, f"ent_{r['destino']}")))):
            arista = ET.SubElement(raiz, 'mxCell', {
                'id': f"{r['id']}_{sufijo}", 'value': card, 'edge': '1', 'parent': '1',
                'source': origen, 'target': destino,
                'style': ('edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;'
                          'jettySize=auto;html=1;endArrow=none;strokeColor=#555555;'
                          'fontSize=11;fontStyle=1;labelBackgroundColor=#ffffff;' + puerto),
            })
            # la cardinalidad va pegada a la entidad, no a mitad de la línea:
            # 0.15 en la arista entidad→rombo y 0.85 en rombo→entidad
            ET.SubElement(arista, 'mxGeometry', {
                'x': '0.15' if sufijo == 'a' else '0.85', 'relative': '1', 'as': 'geometry',
            })

    return ET.ElementTree(mxfile)


def validar_chen(arbol: ET.ElementTree, datos: dict) -> list[str]:
    problemas = validar(arbol, {})  # ids + referencias de aristas
    raiz = arbol.getroot()
    if raiz is None:
        return problemas + ['árbol XML sin raíz']

    cajas = []
    for a in datos['atributos']:
        cajas.append((f"atributo {a['tabla']}.{a['fila']['nombre']}", a['x'], a['y'], a['w'], a['h']))
    for t, e in datos['entidades'].items():
        cajas.append((f'entidad {t}', e['x'], e['y'], e['w'], e['h']))
    for r in datos['relaciones']:
        cajas.append((f"rombo {r['id']}", r['x'], r['y'], r['w'], r['h']))

    for i in range(len(cajas)):
        for j in range(i + 1, len(cajas)):
            if _solapa(cajas[i][1:], cajas[j][1:], margen=0):
                problemas.append(f'solape: {cajas[i][0]} <-> {cajas[j][0]}')
    return problemas


def validar(arbol: ET.ElementTree, tablas: dict) -> list[str]:
    problemas = []
    raiz = arbol.getroot()
    if raiz is None:
        return ['árbol XML sin raíz']
    ids = [c.get('id') or '' for c in raiz.iter('mxCell')]
    duplicados = {i for i in ids if ids.count(i) > 1}
    if duplicados:
        problemas.append(f'ids duplicados: {sorted(duplicados)}')

    existentes = set(ids)
    for arista in raiz.iter('mxCell'):
        if arista.get('edge') != '1':
            continue
        for extremo in ('source', 'target'):
            ref = arista.get(extremo)
            if ref not in existentes:
                problemas.append(f'arista {arista.get("id")} apunta a {extremo} inexistente: {ref}')

    # geometría: alto de cada tabla == cabecera + filas*alto_fila
    for t, info in tablas.items():
        celda = next((c for c in raiz.iter('mxCell') if c.get('id') == f't_{t}'), None)
        if celda is None:
            problemas.append(f'tabla {t} sin celda')
            continue
        geo = celda.find('mxGeometry')
        alto = float(geo.get('height') or 0) if geo is not None else -1.0
        esperado = ALTO_CABECERA + ALTO_FILA * len(info['filas'])
        if abs(alto - esperado) > 0.5:
            problemas.append(f'{t}: alto {alto} != esperado {esperado}')
    return problemas


def serializar(arbol: ET.ElementTree) -> bytes:
    """XML determinista (sin timestamps) para poder comparar con `--check`."""
    raiz = arbol.getroot()
    if raiz is None:
        raise ValueError('árbol XML sin raíz')
    ET.indent(arbol, space='  ')
    return ET.tostring(raiz, encoding='utf-8', xml_declaration=True)


def main() -> int:
    parser = argparse.ArgumentParser(description='Genera el ER de JobDevs en formato .drawio')
    parser.add_argument('-o', '--out', default=None,
                        help='ruta de salida (por defecto docs/ER_JOBDEVS.drawio para fisico '
                             'y docs/ER_JOBDEVS_chen.drawio para chen)')
    parser.add_argument('--notacion', choices=('fisico', 'chen'), default='fisico',
                        help='fisico = tablas con PK/FK dentro (default); '
                             'chen = entidades en rectángulo, atributos en elipse, relaciones en rombo')
    parser.add_argument('--con-auth', action='store_true',
                        help='incluye las tablas internas de django.contrib.auth '
                             '(grupos, permisos, contenttypes)')
    parser.add_argument('--titulo', default=None, help='nombre de la página del diagrama')
    parser.add_argument('--check', action='store_true',
                        help='no escribe: sale con código 1 si el archivo está desincronizado '
                             'respecto de los modelos (útil en CI)')
    args = parser.parse_args()

    tablas = recolectar(incluir_auth=args.con_auth)
    if args.notacion == 'chen':
        datos = chen_layout(tablas)
        arbol = chen_xml(tablas, datos, args.titulo or 'ER Chen')
        problemas = validar_chen(arbol, datos)
        resumen = (f"{len(datos['entidades'])} entidades, {len(datos['atributos'])} atributos, "
                   f"{len(datos['relaciones'])} relaciones")
        nombre_defecto = 'ER_JOBDEVS_chen.drawio'
    else:
        posiciones = layout(tablas)
        arbol = construir_xml(tablas, posiciones, args.titulo or 'Modelo ER')
        problemas = validar(arbol, tablas)
        n_filas = sum(len(t['filas']) for t in tablas.values())
        n_fks = sum(1 for t in tablas.values() for f in t['filas'] if f['fk'])
        resumen = f'{len(tablas)} tablas, {n_filas} columnas, {n_fks} FK'
        nombre_defecto = 'ER_JOBDEVS.drawio'

    if problemas:
        for p in problemas:
            print('ERROR:', p, file=sys.stderr)
        return 1

    salida = Path(args.out) if args.out else BASE_DIR / 'docs' / nombre_defecto
    contenido = serializar(arbol)

    if args.check:
        if not salida.exists():
            print(f'DESINCRONIZADO: no existe {salida}', file=sys.stderr)
            return 1
        actual = ET.parse(salida)
        if serializar(actual) != contenido:
            print(f'DESINCRONIZADO: {salida} no coincide con los modelos. '
                  f'Regenerar con: .venv/bin/python scripts/generate_er_drawio.py '
                  f'--notacion {args.notacion}', file=sys.stderr)
            return 1
        print(f'OK: {salida} está sincronizado con los modelos')
        return 0

    salida.parent.mkdir(parents=True, exist_ok=True)
    salida.write_bytes(contenido)

    print(f'{salida}  ({resumen})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
