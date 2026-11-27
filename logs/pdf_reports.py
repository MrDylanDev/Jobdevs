import io
from html import escape
from pathlib import Path

import pymupdf
from django.conf import settings
from django.http import HttpResponse
from django.utils import timezone


_DARK_BG = (0.06, 0.10, 0.16)
_SENA_GREEN = (0.22, 0.66, 0.00)  # Verde institucional SENA (#39A900)
_ACCENT_TEAL = (0.06, 0.73, 0.51)
_MUTED = (0.42, 0.47, 0.54)
_BORDER = (0.85, 0.88, 0.92)
_WHITE = (1, 1, 1)

_BASE_CSS = """
body {
    font-family: sans-serif;
    font-size: 8.5pt;
    color: #1e293b;
    margin: 0;
    padding: 0;
}
.meta-bar {
    background-color: #f8fafc;
    border: 0.7pt solid #e2e8f0;
    padding: 7pt 10pt;
    margin-bottom: 12pt;
    font-size: 8pt;
    color: #475569;
}
.meta-bar b {
    color: #0f172a;
}
table.kpi-grid {
    width: 100%;
    border-collapse: separate;
    border-spacing: 6pt 0;
    margin: 0 -6pt 14pt -6pt;
}
table.kpi-grid td {
    background-color: #f8fafc;
    border: 0.7pt solid #dbe3ec;
    border-top: 2.5pt solid #39A900;
    padding: 8pt 10pt;
    vertical-align: top;
}
.kpi-label {
    font-size: 7.5pt;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.3pt;
    margin-bottom: 3pt;
}
.kpi-value {
    font-size: 16pt;
    font-weight: bold;
    color: #0f172a;
    margin-bottom: 2pt;
}
.kpi-sub {
    font-size: 7pt;
    color: #64748b;
}
h2.section-title {
    font-size: 10.5pt;
    color: #0f172a;
    margin: 12pt 0 6pt 0;
    padding-bottom: 3pt;
    border-bottom: 1pt solid #39A900;
}
table.data-table {
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 12pt;
    font-size: 8pt;
}
table.data-table th {
    background-color: #0f1a29;
    color: #ffffff;
    font-weight: bold;
    text-align: left;
    padding: 6pt 6pt;
    border: 0.5pt solid #0f1a29;
}
table.data-table td {
    padding: 5.5pt 6pt;
    border: 0.5pt solid #dbe3ec;
    vertical-align: top;
    color: #1e293b;
}
table.data-table tr.alt td {
    background-color: #f8fafc;
}
.num {
    text-align: right;
    white-space: nowrap;
}
.center {
    text-align: center;
}
.badge {
    display: inline-block;
    padding: 1.5pt 5pt;
    font-size: 7pt;
    font-weight: bold;
    border: 0.5pt solid #cbd5e1;
    background-color: #f1f5f9;
    color: #334155;
}
.badge-ok {
    background-color: #ecfdf5;
    border-color: #a7f3d0;
    color: #065f46;
}
.badge-info {
    background-color: #eff6ff;
    border-color: #bfdbfe;
    color: #1e40af;
}
.badge-warn {
    background-color: #fffbeb;
    border-color: #fde68a;
    color: #92400e;
}
.badge-danger {
    background-color: #fef2f2;
    border-color: #fecaca;
    color: #991b1b;
}
.empty-box {
    border: 0.7pt solid #dbe3ec;
    background-color: #f8fafc;
    padding: 14pt;
    text-align: center;
    color: #64748b;
    font-size: 8.5pt;
}
table.signatures {
    width: 100%;
    border-collapse: separate;
    border-spacing: 24pt 0;
    margin: 22pt -24pt 0 -24pt;
}
table.signatures td {
    width: 50%;
    padding-top: 26pt;
    border-top: 0.8pt solid #475569;
    text-align: center;
    font-size: 8pt;
    color: #334155;
}
.sig-role {
    font-size: 7pt;
    color: #64748b;
}
"""


def _logo_path():
    base = Path(getattr(settings, 'BASE_DIR', Path.cwd()))
    for candidate in (
        base / 'static' / 'IMG' / 'Logo.jpg',
        base / 'static' / 'IMG' / 'admin_soporte.png',
    ):
        if candidate.exists():
            return str(candidate)
    return None


def _draw_header_footer(doc, codigo, titulo, subtitulo, usuario_gen, fecha_gen, landscape):
    page_w = 842 if landscape else 595
    page_h = 595 if landscape else 842
    margin_x = 34
    logo = _logo_path()
    total_pages = len(doc)

    for idx, page in enumerate(doc, start=1):
        # Encabezado institucional
        page.draw_rect(pymupdf.Rect(0, 0, page_w, 76), color=_DARK_BG, fill=_DARK_BG)
        page.draw_rect(pymupdf.Rect(0, 72, page_w, 76), color=_SENA_GREEN, fill=_SENA_GREEN)

        text_x = margin_x
        if logo:
            try:
                page.insert_image(pymupdf.Rect(margin_x, 14, margin_x + 44, 58), filename=logo, keep_proportion=True)
                text_x = margin_x + 54
            except Exception:
                pass

        page.insert_text((text_x, 26), "SERVICIO NACIONAL DE APRENDIZAJE — SENA · PLATAFORMA JOBDEVS", fontsize=8, fontname="helv", color=_ACCENT_TEAL)
        page.insert_text((text_x, 45), titulo, fontsize=14, fontname="helv", color=_WHITE)
        page.insert_text((text_x, 60), subtitulo, fontsize=8.5, fontname="helv", color=(0.78, 0.83, 0.89))

        # Bloque derecho de código y fecha
        right_x = page_w - margin_x - 155
        page.insert_text((right_x, 28), f"Código: {codigo}", fontsize=8.5, fontname="helv", color=_WHITE)
        page.insert_text((right_x, 42), f"Fecha: {fecha_gen}", fontsize=8, fontname="helv", color=(0.78, 0.83, 0.89))
        page.insert_text((right_x, 56), f"Emisor: @{usuario_gen}", fontsize=8, fontname="helv", color=(0.78, 0.83, 0.89))

        # Pie de página institucional
        page.draw_line((margin_x, page_h - 32), (page_w - margin_x, page_h - 32), color=_BORDER, width=0.8)
        page.insert_text(
            (margin_x, page_h - 17),
            "JobDevs · Gestión Académica y Vinculación Productiva SENA · Documento generado automáticamente",
            fontsize=7.5,
            fontname="helv",
            color=_MUTED,
        )
        page.insert_text(
            (page_w - margin_x - 68, page_h - 17),
            f"Página {idx} de {total_pages}",
            fontsize=7.5,
            fontname="helv",
            color=_MUTED,
        )


def _render_story_pdf(body_html, codigo, titulo, subtitulo, usuario_gen, filename, landscape=True):
    page_w = 842 if landscape else 595
    page_h = 595 if landscape else 842
    margin_x = 34
    mediabox = pymupdf.Rect(0, 0, page_w, page_h)
    body_rect = pymupdf.Rect(margin_x, 90, page_w - margin_x, page_h - 44)

    html = f"<html><body>{body_html}</body></html>"
    story = pymupdf.Story(html=html, user_css=_BASE_CSS)

    buf = io.BytesIO()
    writer = pymupdf.DocumentWriter(buf)
    more = 1
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(body_rect)
        story.draw(dev)
        writer.end_page()
    writer.close()

    doc = pymupdf.open(stream=buf.getvalue(), filetype='pdf')
    fecha_gen = timezone.localtime(timezone.now()).strftime('%d/%m/%Y %H:%M')
    _draw_header_footer(doc, codigo, titulo, subtitulo, usuario_gen, fecha_gen, landscape)

    pdf_bytes = doc.tobytes()
    doc.close()
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def _badge_estado_html(valor):
    texto = escape(str(valor or ''))
    low = texto.lower()
    cls = 'badge'
    if 'public' in low or ('activ' in low and 'inactiv' not in low) or 'finaliz' in low:
        cls = 'badge badge-ok'
    elif 'desarrollo' in low or 'proceso' in low:
        cls = 'badge badge-info'
    elif 'cancel' in low or 'suspend' in low:
        cls = 'badge badge-danger'
    elif 'pend' in low or 'alta' in low:
        cls = 'badge badge-warn'
    return f'<span class="{cls}">{texto}</span>'


def _signature_block_html(usuario_gen):
    return (
        '<table class="signatures"><tr>'
        f'<td><b>@{escape(usuario_gen)}</b><br><span class="sig-role">Administrador de Plataforma · JobDevs</span></td>'
        '<td><b>Vo. Bo. Coordinación Académica / SENA</b><br><span class="sig-role">Validación Institucional</span></td>'
        '</tr></table>'
    )


def render_reporte_mensual_pdf(mes_texto, usuario_gen, usuarios, proyectos, contrataciones, desglose_roles, desglose_proyectos):
    kpis_html = (
        '<table class="kpi-grid"><tr>'
        f'<td><div class="kpi-label">Usuarios registrados</div><div class="kpi-value">{usuarios}</div><div class="kpi-sub">Nuevas cuentas en el período</div></td>'
        f'<td><div class="kpi-label">Proyectos publicados</div><div class="kpi-value">{proyectos}</div><div class="kpi-sub">Necesidades tecnológicas creadas</div></td>'
        f'<td><div class="kpi-label">Contrataciones realizadas</div><div class="kpi-value">{contrataciones}</div><div class="kpi-sub">Vinculaciones formalizadas</div></td>'
        '</tr></table>'
    )

    def _tabla_resumen(titulo_sec, col1, filas):
        rows_html = []
        for idx, (label, count) in enumerate(filas):
            cls = ' class="alt"' if idx % 2 == 1 else ''
            rows_html.append(f'<tr{cls}><td>{escape(str(label))}</td><td class="num"><b>{count}</b></td></tr>')
        return (
            f'<h2 class="section-title">{escape(titulo_sec)}</h2>'
            '<table class="data-table">'
            f'<thead><tr><th>{escape(col1)}</th><th class="num" style="width:110pt;">Cantidad</th></tr></thead>'
            f'<tbody>{"".join(rows_html)}</tbody></table>'
        )

    meta_html = (
        f'<div class="meta-bar"><b>Período evaluado:</b> {escape(mes_texto)} &nbsp;|&nbsp; '
        f'<b>Alcance:</b> Actividad consolidada de usuarios, proyectos y contrataciones en la plataforma JobDevs.</div>'
    )

    body_html = (
        meta_html
        + kpis_html
        + _tabla_resumen('1. Desglose de Usuarios Registrados por Rol', 'Rol de Usuario', desglose_roles)
        + _tabla_resumen('2. Desglose de Proyectos Publicados por Estado', 'Estado del Proyecto', desglose_proyectos)
        + _signature_block_html(usuario_gen)
    )

    return _render_story_pdf(
        body_html=body_html,
        codigo='JD-REP-MENS',
        titulo=f'Reporte Mensual Ejecutivo ({mes_texto})',
        subtitulo='Indicadores consolidados de gestión institucional',
        usuario_gen=usuario_gen,
        filename=f'reporte_mensual_{mes_texto}.pdf',
        landscape=False,
    )


def render_reporte_tabla_pdf(
    codigo,
    titulo,
    subtitulo,
    usuario_gen,
    filtros_texto,
    kpis,
    encabezados,
    filas,
    filename,
    numeric_cols=(),
    badge_cols=(),
):
    meta_html = (
        f'<div class="meta-bar"><b>Filtros aplicados:</b> {escape(filtros_texto or "Sin filtros (registro completo)")} '
        f'&nbsp;|&nbsp; <b>Total de registros:</b> {len(filas)}</div>'
    )

    kpi_cells = []
    for label, value, sub in kpis:
        kpi_cells.append(
            f'<td><div class="kpi-label">{escape(str(label))}</div>'
            f'<div class="kpi-value">{escape(str(value))}</div>'
            f'<div class="kpi-sub">{escape(str(sub))}</div></td>'
        )
    kpis_html = f'<table class="kpi-grid"><tr>{"".join(kpi_cells)}</tr></table>' if kpi_cells else ''

    if not filas:
        table_html = '<div class="empty-box">No se encontraron registros para los criterios seleccionados.</div>'
    else:
        th_cells = []
        for idx, col in enumerate(encabezados):
            cls = ' class="num"' if idx in numeric_cols else ''
            th_cells.append(f'<th{cls}>{escape(str(col))}</th>')

        body_rows = []
        for r_idx, fila in enumerate(filas):
            tr_cls = ' class="alt"' if r_idx % 2 == 1 else ''
            tds = []
            for c_idx, val in enumerate(fila):
                if c_idx in badge_cols:
                    tds.append(f'<td>{_badge_estado_html(val)}</td>')
                elif c_idx in numeric_cols:
                    tds.append(f'<td class="num">{escape("" if val is None else str(val))}</td>')
                else:
                    tds.append(f'<td>{escape("" if val is None else str(val))}</td>')
            body_rows.append(f'<tr{tr_cls}>{"".join(tds)}</tr>')

        table_html = (
            '<table class="data-table">'
            f'<thead><tr>{"".join(th_cells)}</tr></thead>'
            f'<tbody>{"".join(body_rows)}</tbody></table>'
        )

    body_html = meta_html + kpis_html + table_html + _signature_block_html(usuario_gen)

    return _render_story_pdf(
        body_html=body_html,
        codigo=codigo,
        titulo=titulo,
        subtitulo=subtitulo,
        usuario_gen=usuario_gen,
        filename=filename,
        landscape=True,
    )
