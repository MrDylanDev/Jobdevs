#!/usr/bin/env python3
"""Genera libros Excel derivados de la documentación canónica de JobDevs.

No sustituye los Markdown fuente. Los libros se regeneran desde:
- docs/MATRIZ_REGLAS_NEGOCIO.md
- docs/ESTADO_VERIFICACION_ACTUAL.md
"""
from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
RULES_SOURCE = DOCS / "MATRIZ_REGLAS_NEGOCIO.md"
VERIFICATION_SOURCE = DOCS / "ESTADO_VERIFICACION_ACTUAL.md"
RULES_OUTPUT = DOCS / "MATRIZ_REGLAS_NEGOCIO_JOBDEVS.xlsx"
VERIFICATION_OUTPUT = DOCS / "ESTADO_VERIFICACION_ACTUAL_JOBDEVS.xlsx"

NAVY = "162842"
BLUE = "28639A"
PALE = "E8F2FA"
GREEN = "D9EAD3"
AMBER = "FCE5CD"
RED = "F4CCCC"
GRAY = "D9E1F2"
THIN = Side(style="thin", color="D9E2F3")
STATUS_VALUES = [
    "Documentada",
    "Implementada localmente",
    "Prueba focalizada",
    "Parcial",
    "Pendiente de decisión",
    "Pendiente de aceptación",
    "Pendiente de despliegue",
    "Brecha",
]
EXECUTION_VALUES = ["Pendiente", "En curso", "Aprobada", "Con observaciones", "Bloqueada", "No aplica"]


def table_row(line: str) -> list[str]:
    return [value.strip() for value in line.strip().strip("|").split("|")]


def clean(text: str) -> str:
    return re.sub(r"`([^`]*)`", r"\1", text).replace("**", "").strip()


def add_title(ws, title: str, subtitle: str, width: int) -> None:
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=width)
    cell = ws.cell(1, 1, title)
    cell.font = Font(bold=True, color="FFFFFF", size=16)
    cell.fill = PatternFill("solid", fgColor=NAVY)
    cell.alignment = Alignment(horizontal="left", vertical="center")
    ws.row_dimensions[1].height = 28
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=width)
    cell = ws.cell(2, 1, subtitle)
    cell.font = Font(italic=True, color="40556D")
    cell.fill = PatternFill("solid", fgColor=PALE)
    cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[2].height = 34


def style_table(ws, start_row: int, end_row: int, end_col: int, name: str) -> None:
    for cell in ws[start_row]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor=BLUE)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    for row in ws.iter_rows(min_row=start_row + 1, max_row=end_row, max_col=end_col):
        for cell in row:
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(bottom=THIN)
    ref = f"A{start_row}:{chr(64 + end_col)}{end_row}"
    table = Table(displayName=name, ref=ref)
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True)
    ws.add_table(table)
    ws.freeze_panes = f"A{start_row + 1}"
    ws.auto_filter.ref = ref


def parse_rules() -> tuple[list[list[str]], list[list[str]]]:
    domain = ""
    rules: list[list[str]] = []
    gaps: list[list[str]] = []
    for line in RULES_SOURCE.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            domain = line[3:].strip()
            continue
        if not line.startswith("|"):
            continue
        cols = table_row(line)
        if cols[0].startswith("RN-"):
            if cols[0] == "RN-USR" or cols[0].startswith("RN-") and len(cols) == 8:
                rules.append([domain, *map(clean, cols)])
        elif cols[0].startswith("BR-RN-") and len(cols) == 3:
            gaps.append(list(map(clean, cols)))
    return rules, gaps


def parse_verification() -> tuple[list[list[str]], list[list[str]]]:
    cycle: list[list[str]] = []
    checks: list[list[str]] = []
    mode = ""
    for line in VERIFICATION_SOURCE.read_text(encoding="utf-8").splitlines():
        if line == "## Identificación del ciclo":
            mode = "cycle"
            continue
        if line == "## Matriz a completar":
            mode = "checks"
            continue
        if line.startswith("## "):
            mode = ""
            continue
        if not line.startswith("|"):
            continue
        cols = table_row(line)
        if not cols or set(cols[0]) == {"-"}:
            continue
        if mode == "cycle" and len(cols) == 2 and cols[0] != "Campo":
            cycle.append([clean(cols[0]), clean(cols[1])])
        elif mode == "checks" and len(cols) == 5 and cols[0] != "Verificación":
            checks.append(list(map(clean, cols)))
    return cycle, checks


def rules_workbook() -> None:
    rules, gaps = parse_rules()
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Reglas"
    headers = [
        "Dominio", "ID", "Regla normativa", "Actor y precondición", "Resultado o rechazo",
        "Implementación autoritativa", "Prueba relacionada", "Origen", "Estado y límite",
        "Estado de seguimiento", "Prioridad", "Responsable", "Última revisión", "Observaciones",
    ]
    add_title(
        ws,
        "Matriz de reglas de negocio — seguimiento",
        "Derivado de docs/MATRIZ_REGLAS_NEGOCIO.md. El Markdown es la fuente canónica; no editar este Excel como sustituto.",
        len(headers),
    )
    ws.append([])
    ws.append(headers)
    for row in rules:
        source_status = row[-1]
        tracking = "Brecha" if source_status.startswith("Brecha") else (
            "Parcial" if source_status.startswith("Parcial") else "Implementada localmente"
        )
        ws.append([*row, tracking, "", "", "", ""])
    style_table(ws, 4, 3 + len(rules) + 1, len(headers), "ReglasNegocio")
    widths = [25, 16, 55, 35, 45, 42, 36, 26, 50, 27, 14, 22, 17, 38]
    for idx, width in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + idx)].width = width
    status_validation = DataValidation(type="list", formula1="'Listas'!$A$2:$A$9", allow_blank=True)
    ws.add_data_validation(status_validation)
    status_validation.add(f"J5:J{4 + len(rules)}")
    ws.conditional_formatting.add(
        f"J5:J{4 + len(rules)}", FormulaRule(formula=['J5="Brecha"'], fill=PatternFill("solid", fgColor=RED))
    )
    ws.conditional_formatting.add(
        f"J5:J{4 + len(rules)}", FormulaRule(formula=['J5="Parcial"'], fill=PatternFill("solid", fgColor=AMBER))
    )

    gaps_ws = wb.create_sheet("Brechas")
    gap_headers = ["ID", "Brecha o decisión", "Cierre requerido", "Prioridad", "Responsable", "Estado", "Fecha objetivo", "Evidencia"]
    add_title(
        gaps_ws,
        "Brechas y decisiones pendientes",
        "Derivado de la sección 13 de docs/MATRIZ_REGLAS_NEGOCIO.md. Completar responsables, fechas y evidencia sin alterar el origen.",
        len(gap_headers),
    )
    gaps_ws.append([])
    gaps_ws.append(gap_headers)
    for gap in gaps:
        gaps_ws.append([*gap, "", "", "Pendiente", "", ""])
    style_table(gaps_ws, 4, 3 + len(gaps) + 1, len(gap_headers), "BrechasReglas")
    for idx, width in enumerate([16, 66, 65, 15, 24, 22, 18, 42], 1):
        gaps_ws.column_dimensions[chr(64 + idx)].width = width
    gap_validation = DataValidation(type="list", formula1='"Pendiente,En curso,Bloqueada,Cerrada"', allow_blank=False)
    gaps_ws.add_data_validation(gap_validation)
    gap_validation.add(f"F5:F{4 + len(gaps)}")

    summary = wb.create_sheet("Resumen", 0)
    add_title(summary, "Resumen de reglas de negocio", "Indicadores derivados; se recalculan al abrir en Excel o LibreOffice.", 4)
    summary.append([])
    summary.append(["Indicador", "Valor", "", ""])
    summary.append(["Reglas documentadas", len(rules), "", ""])
    summary.append(["Brechas registradas", len(gaps), "", ""])
    summary.append(["Dominios", len({row[0] for row in rules}), "", ""])
    summary.append([])
    summary.append(["Estado de seguimiento", "Cantidad", "", ""])
    for status in STATUS_VALUES:
        summary.append([status, f'=COUNTIF(Reglas!$J$5:$J${4 + len(rules)},A{summary.max_row + 1})', "", ""])
    style_table(summary, 4, 7, 2, "ResumenReglas")
    for row in range(9, summary.max_row + 1):
        summary.cell(row, 1).alignment = Alignment(wrap_text=True)
    summary.column_dimensions["A"].width = 32
    summary.column_dimensions["B"].width = 18
    summary.freeze_panes = "A5"

    lists = wb.create_sheet("Listas")
    lists.append(["Estados de seguimiento"])
    for status in STATUS_VALUES:
        lists.append([status])
    lists.sheet_state = "hidden"
    wb.save(RULES_OUTPUT)


def verification_workbook() -> None:
    cycle, checks = parse_verification()
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Verificaciones"
    headers = [
        "Verificación", "Comando o entorno", "Resultado actual", "Código de salida", "Evidencia",
        "Estado de seguimiento", "Fecha de ejecución", "Rama", "Commit", "Responsable", "Observaciones",
    ]
    add_title(
        ws,
        "Estado de verificación actual — registro operativo",
        "Derivado de docs/ESTADO_VERIFICACION_ACTUAL.md. Registrar cada ejecución con checkout, entorno, comando y salida real.",
        len(headers),
    )
    ws.append([])
    ws.append(headers)
    for check in checks:
        current = check[2]
        status = "Pendiente" if current.startswith(("Pendiente", "No ejecutado", "No verificada")) else "Con observaciones"
        ws.append([*check, status, "", "", "", "", ""])
    style_table(ws, 4, 3 + len(checks) + 1, len(headers), "RegistroVerificaciones")
    for idx, width in enumerate([33, 38, 35, 18, 40, 24, 20, 28, 18, 24, 45], 1):
        ws.column_dimensions[chr(64 + idx)].width = width
    validation = DataValidation(type="list", formula1="'Listas'!$A$2:$A$7", allow_blank=False)
    ws.add_data_validation(validation)
    validation.add(f"F5:F{4 + len(checks)}")
    ws.conditional_formatting.add(
        f"F5:F{4 + len(checks)}", FormulaRule(formula=['F5="Bloqueada"'], fill=PatternFill("solid", fgColor=RED))
    )
    ws.conditional_formatting.add(
        f"F5:F{4 + len(checks)}", FormulaRule(formula=['F5="Aprobada"'], fill=PatternFill("solid", fgColor=GREEN))
    )

    cycle_ws = wb.create_sheet("Ciclo actual")
    add_title(cycle_ws, "Identificación del ciclo", "Datos de contexto derivados de docs/ESTADO_VERIFICACION_ACTUAL.md.", 2)
    cycle_ws.append([])
    cycle_ws.append(["Campo", "Valor"])
    for row in cycle:
        cycle_ws.append(row)
    style_table(cycle_ws, 4, 3 + len(cycle) + 1, 2, "DatosCiclo")
    cycle_ws.column_dimensions["A"].width = 32
    cycle_ws.column_dimensions["B"].width = 80

    summary = wb.create_sheet("Resumen", 0)
    add_title(summary, "Resumen de verificación", "Indicadores derivados del registro operativo; no sustituyen evidencia de ejecución.", 2)
    summary.append([])
    summary.append(["Indicador", "Valor"])
    summary.append(["Verificaciones registradas", len(checks)])
    for status in EXECUTION_VALUES:
        summary.append([status, f'=COUNTIF(Verificaciones!$F$5:$F${4 + len(checks)},A{summary.max_row + 1})'])
    style_table(summary, 4, 4 + len(EXECUTION_VALUES), 2, "ResumenVerificacion")
    summary.column_dimensions["A"].width = 30
    summary.column_dimensions["B"].width = 18

    instructions = wb.create_sheet("Instrucciones")
    add_title(instructions, "Uso del registro", "Reglas de evidencia para no confundir documentación, pruebas locales, aceptación y despliegue.", 2)
    instructions.append([])
    for item in [
        "Cada fila representa una verificación independiente; no combinar ejecuciones solapadas.",
        "Registrar rama, commit, fecha, responsable, entorno y salida real antes de marcar Aprobada.",
        "Una prueba local no equivale a aceptación de producto ni a evidencia de despliegue.",
        "No sustituir el Markdown canónico: al cerrar un ciclo, trasladar resultados resumidos a docs/ESTADO_VERIFICACION_ACTUAL.md.",
        "Conservar enlaces o rutas de logs, capturas y reportes en la columna Evidencia.",
    ]:
        instructions.append(["•", item])
    instructions.column_dimensions["A"].width = 5
    instructions.column_dimensions["B"].width = 115
    for row in instructions.iter_rows(min_row=4, max_row=instructions.max_row, max_col=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    instructions.freeze_panes = "A4"

    lists = wb.create_sheet("Listas")
    lists.append(["Estados de seguimiento"])
    for status in EXECUTION_VALUES:
        lists.append([status])
    lists.sheet_state = "hidden"
    wb.save(VERIFICATION_OUTPUT)


def main() -> None:
    rules_workbook()
    verification_workbook()
    print(f"{RULES_OUTPUT}: generado")
    print(f"{VERIFICATION_OUTPUT}: generado")


if __name__ == "__main__":
    main()
