#!/usr/bin/env python3
"""Genera cinco diagramas de secuencia de los flujos críticos de JobDevs."""
from __future__ import annotations

import argparse
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "SECUENCIAS_JOBDEVS.drawio"

PAGES = [
    (
        "01 - Negociación y contratación con doble firma",
        ["Empresa", "UI / navegador", "Vista de negociación", "BD / transacción", "Notificaciones", "Desarrollador"],
        [
            (0, 1, "Selecciona candidatura e inicia negociación", "call"),
            (1, 2, "POST /postulaciones/iniciar-negociacion/<id>/", "call"),
            (2, 3, "Valida rol, titularidad, estado y cupo; bloquea proyecto/postulación", "call"),
            (3, 2, "Reserva cupo: postulación=en_negociacion; plazo congelado; crea contrato", "return"),
            (2, 4, "Crea avisos de negociación y firma pendiente", "call"),
            (4, 5, "Notifica negociación y plazo para revisar/firma", "call"),
            (2, 1, "Responde OK; abre chat/contrato", "return"),
            (0, 1, "Edita términos y firma como empresa", "call"),
            (1, 2, "POST /contrataciones/contrato-digital/<id>/firmar/", "call"),
            (2, 3, "Guarda primera firma y snapshot/hash; NO activa", "call"),
            (5, 1, "Revisa contrato y firma", "call"),
            (1, 2, "POST firma del desarrollador", "call"),
            (2, 3, "Valida segunda firma y activa contratación atómicamente", "call"),
            (3, 4, "Notifica contrato activo a las partes", "call"),
        ],
        ["La primera firma nunca activa el contrato.", "La activación requiere ambas firmas, reserva válida y transacción exitosa."],
    ),
    (
        "02 - Registro y revisión de avance",
        ["Desarrollador", "UI / navegador", "Vista de avances", "BD / transacción", "Notificaciones", "Empresa"],
        [
            (0, 1, "Abre proyecto activo y formulario de avance", "call"),
            (1, 2, "POST /avances/registrar/<proyecto_id>/", "call"),
            (2, 3, "Verifica desarrollador contratado, proyecto activo e hito pendiente", "call"),
            (2, 2, "Valida descripción obligatoria y URL/archivo opcionales", "self"),
            (2, 3, "Crea avance pendiente; hito=en_revision", "call"),
            (3, 4, "Crea aviso para empresa", "call"),
            (4, 5, "Notifica avance pendiente de revisión", "call"),
            (5, 1, "Revisa avance y elige aceptar/rechazar", "call"),
            (1, 2, "POST /avances/revisar/<avance_id>/", "call"),
            (2, 3, "Bloquea avance/proyecto y revalida estado", "call"),
            (3, 2, "Aceptar: avance aceptado, hito completado; rechazar: hito pendiente", "return"),
            (2, 3, "Si es último hito: finaliza proyecto y contratos", "call"),
            (3, 4, "Notifica decisión al desarrollador", "call"),
        ],
        ["Un rechazo exige comentario y devuelve el hito a pendiente.", "La aprobación del último hito dispara el cierre transaccional."],
    ),
    (
        "03 - Cancelación justificada y mediación",
        ["Parte solicitante", "UI / navegador", "Servicio de cancelación", "BD / transacción", "Contraparte", "Administrador"],
        [
            (0, 1, "Propone cancelación con causal y datos requeridos", "call"),
            (1, 2, "POST /contrataciones/cancelar/<id>/", "call"),
            (2, 3, "Valida contrato, actor, causal, evidencia/declaración", "call"),
            (3, 2, "Crea solicitud pendiente; no libera cupo ni cancela", "return"),
            (2, 4, "Notifica solicitud a contraparte", "call"),
            (4, 1, "Confirma o rechaza según causal", "call"),
            (1, 2, "POST /contrataciones/cancelaciones/<id>/resolver/", "call"),
            (2, 3, "Confirma acuerdo o conserva solicitud para revisión", "call"),
            (0, 1, "Ante desacuerdo/fuerza mayor/inactividad abre mediación", "call"),
            (1, 2, "POST /disputas/abrir/<proyecto_id>/", "call"),
            (2, 3, "Crea disputa; congela contrato/proyecto y conserva cupo", "call"),
            (3, 5, "Notifica expediente y evidencia privada", "call"),
            (5, 2, "Revisa evidencia y emite dictamen", "call"),
            (2, 3, "Resuelve: continuidad, terminación o sanción", "call"),
        ],
        ["Solicitud o silencio no cancelan automáticamente.", "La evidencia privada se descarga solo tras autorización por expediente."],
    ),
    (
        "04 - Cierre irreversible y proyecto sucesor",
        ["Empresa", "UI / navegador", "Revisión / servicio", "BD / transacción", "Desarrolladores", "Administrador"],
        [
            (0, 1, "Aprueba avance final", "call"),
            (1, 2, "POST revisión de avance", "call"),
            (2, 3, "Marca último hito completado y verifica que no queden pendientes", "call"),
            (3, 2, "Finaliza proyecto y contratos; registra historial/auditoría", "return"),
            (2, 4, "Notifica cierre y habilita valoraciones posteriores", "call"),
            (0, 1, "Crea proyecto sucesor si continúa el trabajo", "call"),
            (1, 2, "Acción autorizada desde el flujo de cierre", "call"),
            (2, 3, "Crea nuevo proyecto vinculado al original", "call"),
            (3, 2, "Preserva proyecto/contratos originales como finalizados", "return"),
            (5, 2, "Regulariza cierre histórico solo con evidencia", "call"),
            (2, 3, "Registra fecha, actor, motivo y referencia de evidencia", "call"),
        ],
        ["No existe reactivación del proyecto finalizado para continuar trabajo.", "Las valoraciones se realizan después del cierre real."],
    ),
    (
        "05 - Solicitud y resolución de verificación",
        ["Empresa o desarrollador", "UI / navegador", "Vista de verificación", "BD / almacenamiento", "Administrador", "Notificaciones"],
        [
            (0, 1, "Completa perfil y solicitud de verificación", "call"),
            (1, 2, "POST /empresa/verificacion/ o /desarrollador/verificacion/", "call"),
            (2, 3, "Valida rol, datos y documento de soporte", "call"),
            (3, 2, "Persiste solicitud y estado pendiente", "return"),
            (2, 5, "Notifica solicitud al panel administrativo", "call"),
            (4, 1, "Abre panel, revisa datos y documento autorizado", "call"),
            (1, 2, "POST resolver verificación", "call"),
            (2, 3, "Guarda aprobar, rechazar o solicitar soporte", "call"),
            (3, 5, "Notifica resultado al titular", "call"),
            (5, 0, "Muestra badge/estado actualizado", "return"),
        ],
        ["La revisión documental no prueba por sí sola consulta externa a RUES/Cámara.", "El acceso al documento de soporte se autoriza por rol y perfil."],
    ),
]


def vertex(root, ident, value, style, x, y, w, h):
    cell = ET.SubElement(root, "mxCell", {"id": ident, "value": value, "style": style, "vertex": "1", "parent": "1"})
    ET.SubElement(cell, "mxGeometry", {"x": str(x), "y": str(y), "width": str(w), "height": str(h), "as": "geometry"})


def message(root, ident, source, target, label, y, source_x, target_x, kind):
    if kind == "self":
        cell = ET.SubElement(root, "mxCell", {"id": ident, "value": label, "edge": "1", "parent": "1", "style": "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=blockThin;strokeColor=#536B84;fontSize=11;labelBackgroundColor=#FFFFFF;"})
        geo = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
        ET.SubElement(geo, "mxPoint", {"x": str(source_x + 74), "y": str(y), "as": "sourcePoint"})
        ET.SubElement(geo, "mxPoint", {"x": str(source_x + 130), "y": str(y + 22), "as": "targetPoint"})
        return
    dashed = "dashed=1;" if kind == "return" else ""
    # Puntos explícitos: cada mensaje conserva su propia altura temporal.
    cell = ET.SubElement(root, "mxCell", {"id": ident, "value": label, "edge": "1", "parent": "1", "style": f"edgeStyle=none;rounded=0;html=1;endArrow=blockThin;strokeColor=#536B84;fontSize=11;labelBackgroundColor=#FFFFFF;{dashed}"})
    geo = ET.SubElement(cell, "mxGeometry", {"relative": "1", "as": "geometry"})
    ET.SubElement(geo, "mxPoint", {"x": str(source_x), "y": str(y), "as": "sourcePoint"})
    ET.SubElement(geo, "mxPoint", {"x": str(target_x), "y": str(y), "as": "targetPoint"})


def build_page(mxfile, page_no, title, participants, events, notes):
    width = max(1800, 260 + len(participants) * 270)
    height = max(1600, 300 + len(events) * 72 + len(notes) * 75)
    d = ET.SubElement(mxfile, "diagram", {"id": f"seq-{page_no}", "name": title})
    graph = ET.SubElement(d, "mxGraphModel", {"dx": str(width), "dy": str(height), "grid": "1", "gridSize": "10", "guides": "1", "tooltips": "1", "connect": "1", "arrows": "1", "page": "1", "pageScale": "1", "pageWidth": str(width), "pageHeight": str(height), "math": "0", "shadow": "0"})
    root = ET.SubElement(graph, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    vertex(root, f"title-{page_no}", f"<b>JobDevs · Diagrama de secuencia</b><br>{title}", "text;html=1;align=left;verticalAlign=middle;fontSize=23;fontColor=#243449;", 45, 20, width - 90, 66)
    xs=[]
    for i, name in enumerate(participants):
        x=100 + i*270; xs.append(x+85)
        vertex(root, f"p-{page_no}-{i}", name, "rounded=1;whiteSpace=wrap;html=1;align=center;verticalAlign=middle;fillColor=#E8F2FA;strokeColor=#5B88A5;fontSize=13;fontStyle=1;", x, 112, 170, 52)
        vertex(root, f"life-{page_no}-{i}", "", "shape=line;strokeColor=#9AAABB;dashed=1;", x+84, 164, 1, height-340)
    y=210
    for index, (src, dst, label, kind) in enumerate(events):
        message(root, f"m-{page_no}-{index}", f"p-{page_no}-{src}", f"p-{page_no}-{dst}", label, y, xs[src], xs[dst], kind)
        y += 72
    note_y=height - 110
    for i, note in enumerate(notes):
        vertex(root, f"note-{page_no}-{i}", note, "shape=note;whiteSpace=wrap;html=1;align=left;verticalAlign=middle;fillColor=#FFF2CC;strokeColor=#B99456;fontSize=11;spacing=8;", 80+i*(width-200)//len(notes), note_y, (width-260)//len(notes), 70)


def serialize() -> bytes:
    mxfile=ET.Element("mxfile", {"host":"jobdevs-sequence-generator", "agent":"scripts/generate_sequence_diagrams.py", "version":"24.0.0", "type":"device"})
    for i, (title, participants, events, notes) in enumerate(PAGES, 1):
        build_page(mxfile, i, title, participants, events, notes)
    tree=ET.ElementTree(mxfile)
    ET.indent(tree, space="  ")
    return ET.tostring(mxfile, encoding="utf-8", xml_declaration=True)


def main():
    parser=argparse.ArgumentParser(description="Genera diagramas de secuencia críticos de JobDevs")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("-o", "--out", type=Path, default=OUTPUT)
    args=parser.parse_args()
    content=serialize()
    if args.check:
        if not args.out.exists() or args.out.read_bytes()!=content:
            parser.exit(1, f"DESINCRONIZADO: {args.out}\n")
        print(f"OK: {args.out}")
        return
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(content)
    print(f"{args.out}: {len(PAGES)} páginas")

if __name__ == "__main__":
    main()
