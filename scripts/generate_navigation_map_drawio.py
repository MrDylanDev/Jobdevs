#!/usr/bin/env python3
"""Genera el mapa de navegación de JobDevs desde un inventario revisable.

El mapa describe pantallas y transiciones de UX, no todas las APIs ni cada
acción POST. Las rutas y guards se documentan en docs/MAPA_NAVEGACION.md.
"""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "MAPA_NAVEGACION_JOBDEVS.drawio"

COLORS = {
    "publica": ("#E8EDFF", "#6D83BA"),
    "empresa": ("#E4F3EB", "#639D7B"),
    "desarrollador": ("#E2F0FD", "#608AB0"),
    "admin": ("#F6EBFF", "#9674AE"),
    "shared": ("#FFF2DB", "#B99456"),
    "state": ("#FFE8E8", "#BA6868"),
}

# A page has named lanes. Every flow is a sequence: (node label, semantic kind).
PAGES = [
    (
        "01 - Acceso público y entrada por rol", "Visitante", "publica",
        [
            ("Descubrimiento", [
                [("Inicio público", "publica"), ("Catálogo de proyectos", "publica"), ("Detalle de proyecto / empresa", "publica")],
            ]),
            ("Cuenta", [
                [("Inicio público", "publica"), ("Registro", "publica"), ("Elegir empresa o desarrollador", "state"), ("Crear cuenta y perfil inicial", "publica"), ("Dashboard del rol", "shared")],
                [("Inicio de sesión", "publica"), ("Validar cuenta activa", "state"), ("Dashboard según rol", "shared")],
                [("Recuperar contraseña", "publica"), ("Restablecer con token", "publica"), ("Inicio de sesión", "publica")],
            ]),
        ],
    ),
    (
        "02 - Navegación de Empresa", "Empresa", "empresa",
        [
            ("Perfil y verificación", [
                [("Dashboard empresa", "empresa"), ("Perfil de empresa", "empresa"), ("Solicitar verificación", "empresa"), ("Volver al dashboard", "empresa")],
            ]),
            ("Ofertas y candidatos", [
                [("Dashboard: Mis ofertas", "empresa"), ("Crear / editar proyecto", "empresa"), ("Publicar o reabrir postulaciones", "empresa"), ("Postulaciones recibidas", "empresa"), ("Comparar 2–4 candidatos", "empresa"), ("Iniciar negociación", "state")],
                [("Dashboard: Mis ofertas", "empresa"), ("Desactivar oferta", "state"), ("Historial", "empresa")],
            ]),
            ("Contrato y ejecución", [
                [("Negociación", "state"), ("Contrato digital", "shared"), ("Firma de empresa", "empresa"), ("Esperar / verificar firma del desarrollador", "state"), ("Contrato activo", "shared")],
                [("Dashboard: En desarrollo", "empresa"), ("Hitos y equipos", "empresa"), ("Avances pendientes", "empresa"), ("Aprobar o rechazar avance", "empresa"), ("Finalización y valoración", "empresa"), ("Proyecto sucesor si continúa el trabajo", "state")],
            ]),
            ("Soporte y excepciones", [
                [("Centro de chat / mensajes", "empresa"), ("Chat directo o grupal", "shared"), ("Notificaciones", "shared")],
                [("Contrato activo", "shared"), ("Proponer o responder cancelación", "state"), ("Confirmación bilateral o mediación", "state"), ("Disputa y evidencia privada", "state")],
            ]),
        ],
    ),
    (
        "03 - Navegación de Desarrollador", "Desarrollador", "desarrollador",
        [
            ("Perfil y descubrimiento", [
                [("Dashboard desarrollador", "desarrollador"), ("Perfil profesional", "desarrollador"), ("Solicitar verificación SENA", "desarrollador"), ("Volver al dashboard", "desarrollador")],
                [("Dashboard: Explorar", "desarrollador"), ("Buscar y filtrar proyectos", "desarrollador"), ("Detalle de proyecto y empresa", "desarrollador"), ("Guardar favorito o postularse", "desarrollador")],
            ]),
            ("Postulación y contrato", [
                [("Postulación enviada", "state"), ("Ver postulaciones vigentes", "desarrollador"), ("Negociación", "state"), ("Contrato digital", "shared"), ("Firma del desarrollador", "desarrollador"), ("Contrato activo tras ambas firmas", "state")],
                [("Dashboard: Favoritos", "desarrollador"), ("Explorar proyectos", "desarrollador"), ("Detalle / postulación", "desarrollador")],
            ]),
            ("Trabajo y cierre", [
                [("Dashboard: Proyectos activos", "desarrollador"), ("Consultar hitos", "desarrollador"), ("Registrar avance", "desarrollador"), ("Adjuntar evidencia opcional", "desarrollador"), ("Revisión de empresa", "state")],
                [("Proyecto finalizado", "state"), ("Calificar empresa", "desarrollador"), ("Historial de contratos y valoraciones", "desarrollador"), ("Proyecto sucesor si procede", "state")],
            ]),
            ("Soporte y excepciones", [
                [("Centro de chat / bandeja", "desarrollador"), ("Chat directo o grupal", "shared"), ("Notificaciones", "shared")],
                [("Contrato activo", "shared"), ("Proponer o responder cancelación", "state"), ("Confirmación bilateral o mediación", "state"), ("Disputa y evidencia privada", "state")],
            ]),
        ],
    ),
    (
        "04 - Navegación de Administrador", "Administrador", "admin",
        [
            ("Supervisión", [
                [("Dashboard administrador", "admin"), ("Métricas y alertas", "admin"), ("Usuarios", "admin"), ("Crear, editar, activar, suspender o eliminar", "admin")],
                [("Dashboard administrador", "admin"), ("Proyectos", "admin"), ("Explorar y supervisar", "admin"), ("Regularizar cierre histórico", "admin"), ("Crear sucesor sin reactivar el original", "state")],
            ]),
            ("Verificación y configuración", [
                [("Dashboard: Verificación empresas", "admin"), ("Revisar documentos", "admin"), ("Aprobar, rechazar o pedir soporte", "admin")],
                [("Dashboard: Verificación desarrolladores", "admin"), ("Gestionar fichas y excepciones SENA", "admin"), ("Resolver solicitud", "admin")],
                [("Dashboard: Configuración", "admin"), ("Plazo global de negociación (1–30)", "admin"), ("Auditar el cambio", "state")],
            ]),
            ("Mediación y evidencia", [
                [("Solicitudes de cancelación", "admin"), ("Revisar causal y evidencia", "admin"), ("Confirmar, rechazar o escalar", "state")],
                [("Disputas", "admin"), ("Sala de mediación", "admin"), ("Consultar evidencia privada", "admin"), ("Resolver y emitir dictamen", "state")],
            ]),
            ("Control operativo", [
                [("Auditoría de cambios", "admin"), ("Chats y logs técnicos", "admin"), ("Reportes CSV / impresión", "admin")],
                [("Notificaciones", "admin"), ("Depuración", "admin"), ("Volver al dashboard", "admin")],
            ]),
        ],
    ),
    (
        "05 - Flujos transversales y guardas", "Reglas de transición", "shared",
        [
            ("Contratación", [
                [("Proyecto con vacante", "shared"), ("Postulación", "shared"), ("Negociación: cupo reservado", "state"), ("Contrato borrador", "shared"), ("Primera firma: no activa", "state"), ("Segunda firma", "state"), ("Contrato activo", "shared")],
            ]),
            ("Ejecución y cierre", [
                [("Contrato activo", "shared"), ("Hitos", "shared"), ("Avance con descripción / evidencia", "shared"), ("Revisión de empresa", "state"), ("Último hito aprobado", "state"), ("Proyecto y contrato finalizados", "state"), ("Valoraciones posteriores", "shared")],
                [("Proyecto y contrato finalizados", "state"), ("Continuación requerida", "state"), ("Nuevo proyecto sucesor vinculado", "shared")],
            ]),
            ("Cancelación y mediación", [
                [("Contrato activo", "shared"), ("Solicitud con causal", "state"), ("Acuerdo / respuesta de contraparte", "state"), ("Cancelar sin sanción o continuar", "state")],
                [("Desacuerdo, inactividad o fuerza mayor", "state"), ("Abrir mediación", "state"), ("Congelar proyecto y cupo", "state"), ("Evidencia privada", "state"), ("Dictamen administrativo", "state"), ("Continuidad, terminación o sanción", "state")],
            ]),
            ("Guardas", [
                [("Ruta pública", "publica"), ("Autenticación", "state"), ("Rol + objeto + estado", "state"), ("Pantalla o acción autorizada", "shared")],
                [("Ruta denegada / estado inválido", "state"), ("Error, redirección o 403", "state")],
            ]),
        ],
    ),
]


def vertex(root, ident, label, style, x, y, width, height):
    cell = ET.SubElement(root, "mxCell", {"id": ident, "value": label, "style": style, "vertex": "1", "parent": "1"})
    ET.SubElement(cell, "mxGeometry", {"x": str(x), "y": str(y), "width": str(width), "height": str(height), "as": "geometry"})


def edge(root, ident, source, target, dashed=False):
    style = "endArrow=blockThin;endFill=1;html=1;rounded=0;strokeColor=#718499;strokeWidth=1.5;"
    if dashed:
        style += "dashed=1;"
    cell = ET.SubElement(root, "mxCell", {"id": ident, "edge": "1", "parent": "1", "source": source, "target": target, "style": style})
    ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})


def node_style(kind: str) -> str:
    fill, stroke = COLORS[kind]
    shape = "hexagon" if kind == "state" else "rounded=1"
    return (
        f"{shape};whiteSpace=wrap;html=1;align=center;verticalAlign=middle;"
        f"fillColor={fill};strokeColor={stroke};fontColor=#1D2D3C;fontSize=13;strokeWidth=2;spacing=8;"
    )


def build_page(mxfile, page_num, title, actor, actor_kind, lanes):
    flow_count = sum(len(flows) for _, flows in lanes)
    max_steps = max(len(flow) for _, flows in lanes for flow in flows)
    width = max(1800, 470 + max_steps * 245)
    height = max(1650, 260 + flow_count * 180)
    diagram = ET.SubElement(mxfile, "diagram", {"id": f"navigation-{page_num}", "name": title})
    graph = ET.SubElement(diagram, "mxGraphModel", {
        "dx": str(width), "dy": str(height), "grid": "1", "gridSize": "10", "guides": "1", "tooltips": "1",
        "connect": "1", "arrows": "1", "page": "1", "pageScale": "1", "pageWidth": str(width), "pageHeight": str(height), "math": "0", "shadow": "0",
    })
    root = ET.SubElement(graph, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    vertex(root, f"title-{page_num}", f"<b>JobDevs · Mapa de navegación</b><br>{title}", "text;html=1;align=left;verticalAlign=middle;fontSize=24;fontColor=#243449;", 40, 24, width - 280, 65)
    vertex(root, f"legend-{page_num}", "Rectángulo: pantalla o módulo · Hexágono: estado, guarda o transición de negocio · Flecha: navegación/avance", "text;html=1;align=left;verticalAlign=middle;fontSize=11;fontColor=#506176;", 40, 90, width - 280, 35)
    vertex(root, f"actor-{page_num}", actor, "shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;html=1;fontSize=16;fontStyle=1;strokeColor=#34465B;", 62, height // 2 - 70, 80, 115)
    vertex(root, f"boundary-{page_num}", "<b>JobDevs</b>", "rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacing=18;fontSize=16;fontColor=#506176;fillColor=#FFFFFF;strokeColor=#718499;strokeWidth=2;", 190, 145, width - 250, height - 190)

    y = 185
    node_counter = 0
    for lane, flows in lanes:
        lane_height = max(150, len(flows) * 145 + 45)
        vertex(root, f"lane-{page_num}-{node_counter}", lane.upper(), "text;html=1;align=left;verticalAlign=middle;fontSize=12;fontStyle=1;fontColor=#506176;", 225, y + 10, 180, 28)
        flow_y = y + 40
        for flow in flows:
            previous = None
            x = 430
            for step, kind in flow:
                ident = f"node-{page_num}-{node_counter}"
                vertex(root, ident, step, node_style(kind), x, flow_y, 205, 72)
                if previous:
                    edge(root, f"edge-{page_num}-{node_counter}", previous, ident)
                else:
                    edge(root, f"actor-edge-{page_num}-{node_counter}", f"actor-{page_num}", ident, dashed=True)
                previous = ident
                node_counter += 1
                x += 245
            flow_y += 100
        y += lane_height


def serialize() -> bytes:
    mxfile = ET.Element("mxfile", {"host": "jobdevs-navigation-generator", "agent": "scripts/generate_navigation_map_drawio.py", "version": "24.0.0", "type": "device"})
    for index, (title, actor, kind, lanes) in enumerate(PAGES, 1):
        build_page(mxfile, index, title, actor, kind, lanes)
    tree = ET.ElementTree(mxfile)
    ET.indent(tree, space="  ")
    return ET.tostring(mxfile, encoding="utf-8", xml_declaration=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Genera el mapa de navegación de JobDevs")
    parser.add_argument("--check", action="store_true", help="comprueba que el archivo es determinista y actual")
    parser.add_argument("-o", "--out", type=Path, default=OUTPUT)
    args = parser.parse_args()
    content = serialize()
    if args.check:
        if not args.out.exists() or args.out.read_bytes() != content:
            parser.exit(1, f"DESINCRONIZADO: {args.out}\n")
        print(f"OK: {args.out}")
        return
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(content)
    total_flows = sum(sum(len(flows) for _, flows in lanes) for _, _, _, lanes in PAGES)
    print(f"{args.out}: {len(PAGES)} páginas, {total_flows} flujos")


if __name__ == "__main__":
    main()
