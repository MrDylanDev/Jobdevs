"""Genera el diagrama UML de casos de uso del Desarrollador en JobDevs.

No modifica el diagrama original de Descargas. Reutiliza el maquetador de
casos de uso de Empresa: ambos roles comparten la misma notación y estilo.
"""
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

from generate_empresa_usecase_drawio import add_page

BASE = Path(__file__).resolve().parents[1]
OUTPUT = BASE / 'docs' / 'DESARROLLADOR_JOBDEVS.drawio'

# Cada caso corresponde a una ruta accesible por un desarrollador o a datos
# mostrados en su dashboard (postulaciones, contratos, estadísticas, historial).
PAGES = [
    ('01 - Cuenta y búsqueda de proyectos', [
        ('Registrarse como desarrollador', 'Cuenta'),
        ('Iniciar sesión', 'Cuenta'),
        ('Recuperar contraseña', 'Cuenta'),
        ('Cerrar sesión', 'Cuenta'),
        ('Actualizar perfil profesional', 'Perfil'),
        ('Solicitar verificación SENA', 'Perfil'),
        ('Consultar estadísticas personales', 'Perfil'),
        ('Consultar calificación y reseñas recibidas', 'Perfil'),
        ('Explorar proyectos disponibles', 'Proyectos'),
        ('Buscar y filtrar proyectos', 'Proyectos'),
        ('Consultar detalle de proyecto y empresa', 'Proyectos'),
        ('Añadir o quitar proyecto de favoritos', 'Proyectos'),
        ('Consultar proyectos favoritos', 'Proyectos'),
        ('Postularse a un proyecto', 'Postulaciones'),
    ]),
    ('02 - Contratos y trabajo', [
        ('Consultar postulaciones vigentes', 'Postulaciones'),
        ('Consultar historial de postulaciones', 'Postulaciones'),
        ('Consultar contrato digital', 'Contratos'),
        ('Firmar contrato digital como desarrollador', 'Contratos'),
        ('Activar contratación con ambas firmas', 'Contratos'),
        ('Consultar contratos vigentes', 'Contratos'),
        ('Consultar historial de contratos', 'Contratos'),
        ('Consultar proyectos activos y sus hitos', 'Proyectos'),
        ('Consultar avances del proyecto', 'Avances'),
        ('Registrar avance y subir evidencia', 'Avances'),
        ('Proponer o responder cancelación justificada', 'Contratos'),
        ('Consultar proyectos finalizados', 'Proyectos'),
        ('Continuar trabajo mediante proyecto sucesor', 'Proyectos'),
        ('Calificar a la empresa', 'Perfil'),
    ]),
    ('03 - Mensajería y disputas', [
        ('Comunicarse con la empresa', 'Mensajes'),
        ('Comunicarse con administración', 'Mensajes'),
        ('Participar en chat grupal del proyecto', 'Mensajes'),
        ('Consultar bandeja de entrada', 'Mensajes'),
        ('Consultar mensajes enviados', 'Mensajes'),
        ('Consultar notificaciones', 'Notificaciones'),
        ('Marcar notificaciones como leídas', 'Notificaciones'),
        ('Limpiar notificaciones', 'Notificaciones'),
        ('Abrir disputa de un contrato activo', 'Disputas'),
        ('Consultar disputa y entrar a la sala', 'Disputas'),
        ('Aportar y consultar evidencia privada', 'Disputas'),
        ('Enviar mensaje en disputa', 'Disputas'),
        ('Consultar historial de disputas', 'Disputas'),
    ]),
]


def serialize():
    root = ET.Element('mxfile', {
        'host': 'jobdevs-usecase-generator',
        'agent': 'scripts/generate_desarrollador_usecase_drawio.py',
        'version': '24.0.0', 'type': 'device',
    })
    for number, (title, cases) in enumerate(PAGES, 1):
        add_page(root, number, title, cases, actor='Desarrollador',
                 slug='desarrollador', spread_actor_ports=True)
    ET.indent(root, space='  ')
    return ET.tostring(root, encoding='utf-8', xml_declaration=True)


def main():
    parser = argparse.ArgumentParser(description='Genera los casos de uso de Desarrollador')
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
