"""Genera el diagrama UML de casos de uso de Empresa, sin tocar Descargas."""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]
OUTPUT = BASE / 'docs' / 'EMPRESA_JOBDEVS.drawio'

# Acciones visibles para el rol empresa: rutas de usuarios, proyectos,
# postulaciones, contrataciones, avances, disputas, mensajes y notificaciones.
PAGES = [
    ('01 - Cuenta y proyectos', [
        ('Registrarse como empresa', 'Cuenta'),
        ('Iniciar sesión', 'Cuenta'),
        ('Recuperar contraseña', 'Cuenta'),
        ('Cerrar sesión', 'Cuenta'),
        ('Actualizar perfil de empresa', 'Perfil'),
        ('Solicitar verificación de empresa', 'Perfil'),
        ('Consultar reputación de la empresa', 'Perfil'),
        ('Publicar proyecto y definir vacantes', 'Proyectos'),
        ('Editar proyecto publicado', 'Proyectos'),
        ('Reabrir plazo de postulación autorizado', 'Proyectos'),
        ('Retirar oferta o desactivar proyecto', 'Proyectos'),
        ('Crear y eliminar hitos', 'Proyectos'),
        ('Crear y eliminar equipos', 'Proyectos'),
        ('Finalizar proyecto y crear sucesor vinculado', 'Proyectos'),
        ('Calificar desarrolladores', 'Proyectos'),
        ('Consultar historial de proyectos', 'Proyectos'),
    ]),
    ('02 - Candidatos, contratos y avances', [
        ('Consultar postulaciones recibidas', 'Postulaciones'),
        ('Filtrar y revisar candidatos', 'Postulaciones'),
        ('Comparar de 2 a 4 candidatos', 'Postulaciones'),
        ('Rechazar postulación', 'Postulaciones'),
        ('Iniciar negociación', 'Postulaciones'),
        ('Consultar y editar contrato digital', 'Contratos'),
        ('Firmar contrato digital como empresa', 'Contratos'),
        ('Activar contratación con ambas firmas', 'Contratos'),
        ('Consultar desarrolladores contratados', 'Contratos'),
        ('Consultar detalle de contratación', 'Contratos'),
        ('Proponer o responder cancelación justificada', 'Contratos'),
        ('Consultar avances y progreso de hitos', 'Avances'),
        ('Aceptar avance o evidencia', 'Avances'),
        ('Rechazar avance o evidencia', 'Avances'),
    ]),
    ('03 - Comunicación y disputas', [
        ('Comunicarse con desarrolladores', 'Mensajes'),
        ('Comunicarse con administración', 'Mensajes'),
        ('Participar en chat grupal del proyecto', 'Mensajes'),
        ('Consultar bandeja de mensajes', 'Mensajes'),
        ('Consultar mensajes enviados', 'Mensajes'),
        ('Consultar notificaciones', 'Notificaciones'),
        ('Marcar notificaciones como leídas', 'Notificaciones'),
        ('Limpiar notificaciones', 'Notificaciones'),
        ('Abrir disputa de un proyecto propio', 'Disputas'),
        ('Consultar disputa y entrar a la sala', 'Disputas'),
        ('Aportar y consultar evidencia privada', 'Disputas'),
        ('Enviar mensaje en disputa', 'Disputas'),
        ('Consultar historial de disputas', 'Disputas'),
    ]),
]

COLORS = {
    'Cuenta': ('#e8edff', '#6d83ba'),
    'Perfil': ('#e6f4f3', '#5b9b93'),
    'Proyectos': ('#e4f3eb', '#639d7b'),
    'Postulaciones': ('#fff2db', '#b99456'),
    'Contratos': ('#f6ebff', '#9674ae'),
    'Avances': ('#e2f0fd', '#608ab0'),
    'Mensajes': ('#eef4e5', '#82a064'),
    'Notificaciones': ('#e9efff', '#6a87bf'),
    'Disputas': ('#ffe8e8', '#ba6868'),
}


def vertex(root, ident, label, style, x, y, width, height):
    cell = ET.SubElement(root, 'mxCell', {
        'id': ident, 'value': label, 'style': style, 'vertex': '1', 'parent': '1',
    })
    ET.SubElement(cell, 'mxGeometry', {
        'x': str(x), 'y': str(y), 'width': str(width),
        'height': str(height), 'as': 'geometry',
    })


def add_page(mxfile, number, title, cases, actor='Empresa', slug='empresa',
             spread_actor_ports=False):
    height = max(1360, 320 + 94 * len(cases))
    diagram = ET.SubElement(mxfile, 'diagram', {'id': f'{slug}-{number}', 'name': title})
    graph = ET.SubElement(diagram, 'mxGraphModel', {
        'dx': '1460', 'dy': str(height), 'grid': '1', 'gridSize': '10',
        'guides': '1', 'tooltips': '1', 'connect': '1', 'arrows': '1',
        'page': '1', 'pageScale': '1', 'pageWidth': '1460',
        'pageHeight': str(height), 'math': '0', 'shadow': '0',
    })
    root = ET.SubElement(graph, 'root')
    ET.SubElement(root, 'mxCell', {'id': '0'})
    ET.SubElement(root, 'mxCell', {'id': '1', 'parent': '0'})
    vertex(root, f'title-{number}', f'<b>JobDevs · {actor}</b><br>{title}',
           'text;html=1;align=left;verticalAlign=middle;fontSize=24;fontColor=#243449;',
           55, 28, 1120, 70)
    vertex(root, f'boundary-{number}', '<b>JobDevs</b>',
           'rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;'
           'spacing=18;fontSize=16;fontColor=#506176;fillColor=#ffffff;'
           'strokeColor=#718499;strokeWidth=2;', 420, 135, 985, height - 200)
    vertex(root, f'actor-{number}', actor,
           'shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;'
           'html=1;fontSize=17;fontStyle=1;strokeColor=#34465b;',
           114, height // 2 - 80, 82, 120)
    for i, (label, area) in enumerate(cases):
        y = 216 + i * 94
        fill, stroke = COLORS[area]
        ident = f'use-{number}-{i}'
        exit_y = (f'{(i + 1) / (len(cases) + 1):.3f}'
                  if spread_actor_ports else '0.5')
        vertex(root, ident, label,
               'ellipse;whiteSpace=wrap;html=1;align=center;verticalAlign=middle;'
               f'fillColor={fill};strokeColor={stroke};fontColor=#1d2d3c;'
               'fontSize=15;strokeWidth=2;spacing=10;', 665, y, 615, 62)
        edge = ET.SubElement(root, 'mxCell', {
            'id': f'association-{number}-{i}', 'edge': '1', 'parent': '1',
            'source': f'actor-{number}', 'target': ident,
            'style': 'endArrow=none;startArrow=none;html=1;rounded=0;'
                     f'strokeColor=#9aabba;strokeWidth=1;exitX=1;exitY={exit_y};'
                     'exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;',
        })
        ET.SubElement(edge, 'mxGeometry', {'relative': '1', 'as': 'geometry'})
        vertex(root, f'area-{number}-{i}', area.upper(),
               'text;html=1;align=right;verticalAlign=middle;fontSize=10;'
               'fontColor=#667789;', 510, y + 16, 130, 30)


def serialize():
    mxfile = ET.Element('mxfile', {
        'host': 'jobdevs-usecase-generator',
        'agent': 'scripts/generate_empresa_usecase_drawio.py',
        'version': '24.0.0', 'type': 'device',
    })
    for number, (title, cases) in enumerate(PAGES, 1):
        add_page(mxfile, number, title, cases, spread_actor_ports=True)
    ET.indent(mxfile, space='  ')
    return ET.tostring(mxfile, encoding='utf-8', xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(description='Genera los casos de uso de Empresa')
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
