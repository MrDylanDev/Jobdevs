"""Genera un diagrama UML de casos de uso del administrador de JobDevs.

El archivo original de Descargas no se modifica. Páginas separadas mantienen
legibles las asociaciones y conservan un único actor por página.
"""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUTPUT = BASE / 'docs' / 'ADMIN_JOBDEVS.drawio'

# Cada elemento es (nombre del caso, área funcional). Los casos amplios del
# dibujo original se desglosan solamente donde existe una acción comprobada.
PAGES = [
    ('01 - Usuarios y proyectos', [
        ('Iniciar sesión', 'Acceso'),
        ('Cerrar sesión', 'Acceso'),
        ('Consultar y filtrar usuarios', 'Usuarios'),
        ('Crear usuario', 'Usuarios'),
        ('Editar usuario', 'Usuarios'),
        ('Activar o suspender usuario', 'Usuarios'),
        ('Eliminar usuario', 'Usuarios'),
        ('Supervisar proyectos y sus avances', 'Proyectos'),
        ('Explorar catálogo de proyectos', 'Proyectos'),
        ('Consultar alertas de inactividad', 'Proyectos'),
        ('Crear proyecto sucesor sin reactivar el original', 'Proyectos'),
        ('Regularizar cierre histórico con evidencia', 'Proyectos'),
        ('Gestionar categorías de solución', 'Proyectos'),
    ]),
    ('02 - Verificación y mediación', [
        ('Revisar solicitud de verificación de empresa', 'Verificación'),
        ('Aprobar, rechazar o pedir documento a empresa', 'Verificación'),
        ('Revisar solicitud de verificación de desarrollador', 'Verificación'),
        ('Aprobar, rechazar o pedir documento a desarrollador', 'Verificación'),
        ('Consultar documentos de soporte', 'Verificación'),
        ('Registrar ficha SENA', 'SENA'),
        ('Activar o desactivar ficha SENA', 'SENA'),
        ('Autorizar excepción de ficha SENA', 'SENA'),
        ('Revocar excepción de ficha SENA', 'SENA'),
        ('Consultar disputa y entrar a la sala', 'Disputas'),
        ('Enviar mensaje en disputa', 'Disputas'),
        ('Resolver disputa y emitir dictamen', 'Disputas'),
        ('Revisar solicitudes de cancelación', 'Disputas'),
        ('Configurar plazo global de negociación', 'Configuración'),
    ]),
    ('03 - Comunicación y control', [
        ('Consultar métricas y estadísticas globales', 'Análisis'),
        ('Consultar rankings y reseñas', 'Análisis'),
        ('Consultar historial de estados y auditoría sensible', 'Auditoría'),
        ('Auditar altas, cambios, bajas y acciones masivas', 'Auditoría'),
        ('Auditar chats', 'Auditoría'),
        ('Consultar logs técnicos', 'Auditoría'),
        ('Generar reportes CSV', 'Reportes'),
        ('Consultar vista imprimible de reportes', 'Reportes'),
        ('Consultar notificaciones', 'Notificaciones'),
        ('Depurar notificaciones antiguas', 'Notificaciones'),
        ('Enviar mensajes de soporte', 'Comunicación'),
    ]),
]

COLORS = {
    'Acceso': ('#e8edff', '#6d83ba'), 'Usuarios': ('#e2f0fd', '#608ab0'),
    'Proyectos': ('#e4f3eb', '#639d7b'), 'Verificación': ('#fff0dc', '#bd864b'),
    'SENA': ('#f6ebff', '#9674ae'), 'Disputas': ('#ffe8e8', '#ba6868'),
    'Análisis': ('#e6f4f3', '#5b9b93'), 'Auditoría': ('#f1eaff', '#8774ae'),
    'Reportes': ('#fff2db', '#b99456'), 'Notificaciones': ('#e9efff', '#6a87bf'),
    'Comunicación': ('#eef4e5', '#82a064'),
    'Configuración': ('#e6f4f3', '#5b9b93'),
}


def vertex(root, ident, value, style, x, y, w, h):
    cell = ET.SubElement(root, 'mxCell', {
        'id': ident, 'value': value, 'style': style, 'vertex': '1', 'parent': '1',
    })
    ET.SubElement(cell, 'mxGeometry', {
        'x': str(x), 'y': str(y), 'width': str(w), 'height': str(h), 'as': 'geometry',
    })
    return cell


def build_page(mxfile, number, title, cases):
    height = max(1360, 320 + 94 * len(cases))
    diagram = ET.SubElement(mxfile, 'diagram', {'id': f'admin-{number}', 'name': title})
    graph = ET.SubElement(diagram, 'mxGraphModel', {
        'dx': '1460', 'dy': str(height), 'grid': '1', 'gridSize': '10',
        'guides': '1', 'tooltips': '1', 'connect': '1', 'arrows': '1',
        'page': '1', 'pageScale': '1', 'pageWidth': '1460',
        'pageHeight': str(height), 'math': '0', 'shadow': '0',
    })
    root = ET.SubElement(graph, 'root')
    ET.SubElement(root, 'mxCell', {'id': '0'})
    ET.SubElement(root, 'mxCell', {'id': '1', 'parent': '0'})
    vertex(root, f'title-{number}', f'<b>JobDevs · Administrador</b><br>{title}',
           'text;html=1;align=left;verticalAlign=middle;fontSize=24;fontColor=#243449;',
           55, 28, 1120, 70)
    vertex(root, f'boundary-{number}', '<b>JobDevs</b>',
           'rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;'
           'spacing=18;fontSize=16;fontColor=#506176;fillColor=#ffffff;strokeColor=#718499;'
           'strokeWidth=2;', 420, 135, 985, height - 200)
    # El contorno se añade antes de los casos, para que las asociaciones no tapen texto.
    y_actor = height // 2 - 80
    vertex(root, f'actor-{number}', 'Administrador',
           'shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;'
           'html=1;fontSize=17;fontStyle=1;strokeColor=#34465b;',
           114, y_actor, 82, 120)
    start_y = 216
    for i, (label, area) in enumerate(cases):
        y = start_y + i * 94
        fill, stroke = COLORS[area]
        ident = f'use-{number}-{i}'
        vertex(root, ident, label,
               'ellipse;whiteSpace=wrap;html=1;align=center;verticalAlign=middle;'
               f'fillColor={fill};strokeColor={stroke};fontColor=#1d2d3c;'
               'fontSize=15;strokeWidth=2;spacing=10;', 665, y, 615, 62)
        # Cada asociación usa un puerto del actor distinto para evitar un abanico ilegible.
        edge = ET.SubElement(root, 'mxCell', {
            'id': f'association-{number}-{i}', 'edge': '1', 'parent': '1',
            'source': f'actor-{number}', 'target': ident,
            'style': 'endArrow=none;startArrow=none;html=1;rounded=0;'
                     f'strokeColor=#9aabba;strokeWidth=1;exitX=1;exitY={(i + 1) / (len(cases) + 1):.3f};'
                     'exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;',
        })
        ET.SubElement(edge, 'mxGeometry', {'relative': '1', 'as': 'geometry'})
        vertex(root, f'area-{number}-{i}', area.upper(),
               'text;html=1;align=right;verticalAlign=middle;fontSize=10;'
               'fontColor=#667789;', 510, y + 16, 130, 30)
    return graph


def serialize():
    mxfile = ET.Element('mxfile', {
        'host': 'jobdevs-usecase-generator', 'agent': 'scripts/generate_admin_usecase_drawio.py',
        'version': '24.0.0', 'type': 'device',
    })
    for number, (title, cases) in enumerate(PAGES, 1):
        build_page(mxfile, number, title, cases)
    tree = ET.ElementTree(mxfile)
    ET.indent(tree, space='  ')
    return ET.tostring(mxfile, encoding='utf-8', xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(description='Genera el diagrama UML del administrador')
    parser.add_argument('--check', action='store_true', help='comprueba sin escribir')
    parser.add_argument('-o', '--out', type=Path, default=OUTPUT)
    args = parser.parse_args()
    content = serialize()
    if args.check:
        if not args.out.exists() or args.out.read_bytes() != content:
            parser.exit(1, f'DESINCRONIZADO: {args.out}\n')
        print(f'OK: {args.out}')
        return
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(content)
    print(f'{args.out}: {len(PAGES)} páginas, {sum(len(c) for _, c in PAGES)} casos de uso')


if __name__ == '__main__':
    main()
