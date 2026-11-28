"""Convierte el catálogo revisado de casos de prueba a un Excel ejecutable.

Uso: /usr/bin/python3 scripts/generate_test_cases_xlsx.py
Fuente: docs/CASOS_DE_PRUEBA.md y docs/TRAZABILIDAD_REQUISITOS.md.
"""
import argparse
import re
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.workbook.properties import CalcProperties
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'docs' / 'CASOS_DE_PRUEBA.md'
REQUIREMENTS = ROOT / 'docs' / 'TRAZABILIDAD_REQUISITOS.md'
DEST = ROOT / 'docs' / 'CASOS_DE_PRUEBA_JOBDEVS.xlsx'
RF_PATTERN = re.compile(r'^RF(?:-N\d+| \d+\.\d+\.\d+)$')
NAVY, BLUE, PALE = '162842', '28639A', 'E8F2FA'


def parse_table(line):
    if not line.startswith('|') or not line.endswith('|'):
        raise ValueError(f'Fila Markdown inválida: {line}')
    return [part.strip() for part in line[1:-1].split('|')]


def source_cases():
    rows = {'rf': [], 'negative': [], 'e2e': [], 'rnf': []}
    section = None
    module = ''
    for line in SOURCE.read_text(encoding='utf-8').splitlines():
        if line.startswith('## 3.'):
            section = 'rf'
        elif line.startswith('## 4.'):
            section = 'negative'
        elif line.startswith('## 5.'):
            section = 'e2e'
        elif line.startswith('## 6.'):
            section = None
        elif line.startswith('## 8.'):
            section = 'rnf'
        if section == 'rf' and line.startswith('### '):
            module = line[4:]
        if not line.startswith(('| CP-', '| NEG-', '| E2E-')):
            continue
        columns = parse_table(line)
        if section == 'rf' and line.startswith('| CP-'):
            if len(columns) != 6 or not RF_PATTERN.fullmatch(columns[1]):
                raise ValueError(f'Caso RF mal formado: {line}')
            rows['rf'].append((module, *columns))
        elif section == 'negative' and line.startswith('| NEG-'):
            if len(columns) != 6:
                raise ValueError(f'Caso negativo mal formado: {line}')
            rows['negative'].append(tuple(columns))
        elif section == 'e2e' and line.startswith('| E2E-'):
            if len(columns) != 4:
                raise ValueError(f'Paso E2E mal formado: {line}')
            rows['e2e'].append(tuple(columns))
        elif section == 'rnf' and line.startswith('| CP-RNF-'):
            if len(columns) != 6 or not re.fullmatch(r'RNF-\d+', columns[1]):
                raise ValueError(f'Caso RNF mal formado: {line}')
            rows['rnf'].append(tuple(columns))
    expected = set(re.findall(
        r'\| \*\*(RF(?:-N\d+| \d+\.\d+\.\d+))\*\*',
        REQUIREMENTS.read_text(encoding='utf-8'),
    ))
    ids = [item[1] for item in rows['rf']]
    found = [item[2] for item in rows['rf']]
    if len(ids) != len(set(ids)) or len(found) != len(set(found)) or set(found) != expected:
        raise ValueError(f'Cobertura incorrecta: faltan {expected - set(found)}, sobran {set(found) - expected}')
    if len(rows['negative']) != 15 or len(rows['e2e']) != 8:
        raise ValueError('El número de escenarios negativos/E2E difiere del catálogo')
    if len({x[0] for x in rows['negative']}) != 15 or len({x[0] for x in rows['e2e']}) != 8:
        raise ValueError('IDs negativos/E2E duplicados')
    expected_rnf = set(re.findall(
        r'^\| (RNF-\d+) \|', REQUIREMENTS.read_text(encoding='utf-8'), re.M,
    ))
    rnf_ids = [row[1] for row in rows['rnf']]
    if len(rnf_ids) != len(set(rnf_ids)) or set(rnf_ids) != expected_rnf:
        raise ValueError(f'RNF sin caso: {expected_rnf - set(rnf_ids)}')
    return rows


def role(rf, precondition):
    """Roles de ejecución: el pre-requisito textual sigue siendo la fuente detallada."""
    specified = {
        'RF 1.1.2': 'Visitante',
        'RF 1.2.1': 'Visitante',
        'RF 1.4.1': 'Empresa / Desarrollador / Administrador',
        'RF 1.4.2': 'Usuario registrado',
        'RF 1.4.3': 'Usuario autenticado',
        'RF 1.4.4': 'Usuario registrado',
        'RF 4.3.1': 'Empresa',
        'RF 4.3.2': 'Administrador',
        'RF 5.3.2': 'Empresa / Desarrollador',
        'RF 5.3.3': 'Empresa / Desarrollador',
        'RF 6.1.1': 'Empresa / Desarrollador',
        'RF 6.1.2': 'Empresa / Desarrollador',
        'RF 6.1.3': 'Empresa / Desarrollador',
        'RF 6.2.1': 'Participantes autorizados',
        'RF 6.2.2': 'Desarrollador / Empresa',
        'RF 6.3.1': 'Destinatario autenticado',
        'RF 6.3.2': 'Empresa / Desarrollador',
        'RF 8.1.1': 'Empresa',
        'RF 8.1.2': 'Operador / tarea periódica',
        'RF 8.2.1': 'Empresa / Desarrollador',
        'RF 8.2.2': 'Empresa / Desarrollador',
        'RF 8.3.1': 'Empresa / Desarrollador',
        'RF 9.1.1': 'Desarrollador',
        'RF 9.1.2': 'Administrador / Desarrollador',
        'RF 9.2.1': 'Empresa / Administrador',
        'RF 9.2.2': 'Visitante / Empresa',
        'RF 10.1.1': 'Empresa / Desarrollador',
        'RF 10.1.2': 'Administrador / Partes',
        'RF 10.2.1': 'Empresa / Desarrollador / Administrador',
        'RF 10.2.2': 'Administrador',
    }
    specified.update(dict(zip(
        [f'RF-N{i:02d}' for i in range(1, 32)],
        ['Empresa / Desarrollador', 'Empresa', 'Administrador', 'Administrador',
         'Desarrollador / Visitante', 'Empresa / Desarrollador', 'Operador',
         'Empresa / Desarrollador', 'Empresa', 'Administrador / Desarrollador',
         'Empresa / Administrador', 'Desarrollador / Administrador',
         'Titular / Administrador', 'Empresa / Desarrollador', 'Empresa',
         'Administrador', 'Partes / Administrador', 'Administrador / Partes',
         'Destinatario autenticado', 'Participante de sala',
         'Empresa / Desarrollador', 'Remitente autenticado', 'Desarrollador',
         'Administrador', 'Administrador', 'Administrador', 'Administrador',
         'Operador', 'Empresa / Administrador', 'Administrador', 'Operador'],
        strict=True,
    )))
    if rf in specified:
        return specified[rf]
    explicit = []
    for token, label in [('EMP-A', 'Empresa'), ('EMP-B', 'Empresa'),
                         ('DEV-A', 'Desarrollador'), ('DEV-B', 'Desarrollador'),
                         ('ADM-A', 'Administrador'), ('ANON', 'Visitante')]:
        if token in precondition and label not in explicit:
            explicit.append(label)
    if explicit:
        return ' / '.join(explicit)
    if rf.startswith(('RF 1.3.', 'RF 7.')):
        return 'Administrador'
    if rf.startswith(('RF 3.1.', 'RF 4.1.', 'RF 5.2.2')):
        return 'Desarrollador'
    if rf.startswith(('RF 2.', 'RF 3.2.', 'RF 3.3.', 'RF 3.4.', 'RF 4.2.', 'RF 5.2.1')):
        return 'Empresa'
    return 'Según precondición'


def setup_sheet(ws, title, subtitle, headings, widths, table_name):
    ws.sheet_view.showGridLines = False
    count = len(headings)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=count)
    ws.cell(1, 1, title)
    ws.cell(1, 1).font = Font(name='Aptos Display', size=19, bold=True, color='FFFFFF')
    ws.cell(1, 1).fill = PatternFill('solid', fgColor=NAVY)
    ws.row_dimensions[1].height = 34
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=count)
    ws.cell(2, 1, subtitle)
    ws.cell(2, 1).font = Font(name='Aptos', size=10, italic=True, color='37506A')
    ws.cell(2, 1).fill = PatternFill('solid', fgColor=PALE)
    ws.row_dimensions[2].height = 31
    for col, value in enumerate(headings, 1):
        cell = ws.cell(4, col, value)
        cell.font = Font(name='Aptos', bold=True, color='FFFFFF')
        cell.fill = PatternFill('solid', fgColor=BLUE)
        cell.alignment = Alignment(vertical='center', wrap_text=True)
        ws.column_dimensions[get_column_letter(col)].width = widths[col - 1]
    ws.row_dimensions[4].height = 32
    ws.freeze_panes = 'D5'
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = '1:4'
    ws.sheet_properties.outlinePr.summaryBelow = True
    return table_name


def fill_sheet(ws, records, headers, widths, name, subtitle):
    setup_sheet(ws, ws.title, subtitle, headers, widths, name)
    for idx, row in enumerate(records, start=5):
        for col, value in enumerate(row, 1):
            cell = ws.cell(idx, col, value)
            cell.font = Font(name='Aptos', size=10, color='263B50')
            cell.alignment = Alignment(vertical='top', wrap_text=True)
            if idx % 2:
                cell.fill = PatternFill('solid', fgColor='F5F9FD')
        ws.row_dimensions[idx].height = 52
    end = 4 + len(records)
    ref = f'A4:{get_column_letter(len(headers))}{end}'
    tab = Table(displayName=name, ref=ref)
    tab.tableStyleInfo = TableStyleInfo(name='TableStyleMedium2', showRowStripes=True)
    ws.add_table(tab)
    ws.auto_filter.ref = ref
    ws.print_options.horizontalCentered = True
    ws.page_setup.orientation = 'landscape'
    ws.page_setup.paperSize = ws.PAPERSIZE_A3
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    status_col = headers.index('Estado') + 1
    col = get_column_letter(status_col)
    validation = DataValidation(type='list', formula1='"No ejecutado,Pasó,Falló,Bloqueado"')
    validation.error = 'Selecciona una opción de la lista'
    validation.errorTitle = 'Estado inválido'
    validation.showErrorMessage = True
    ws.add_data_validation(validation)
    validation.add(f'{col}5:{col}{end}')
    for text, color in [('Pasó', 'DBF3E6'), ('Falló', 'FFE0DE'),
                        ('Bloqueado', 'FFF2CE'), ('No ejecutado', 'E7ECF2')]:
        ws.conditional_formatting.add(
            f'{col}5:{col}{end}',
            CellIsRule(operator='equal', formula=[f'"{text}"'],
                       fill=PatternFill('solid', fgColor=color)),
        )
    return end


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, default=DEST,
                        help='salida nueva si existe un registro de ejecución previo')
    parser.add_argument('--force', action='store_true',
                        help='sobrescribe el Excel existente (pierde resultados manuales)')
    args = parser.parse_args()
    if args.out.exists() and not args.force:
        parser.error(f'{args.out} ya existe; no se sobrescribe el registro de ejecución')
    data = source_cases()
    wb = Workbook()
    summary = wb.active
    summary.title = 'Resumen'
    rf_ws = wb.create_sheet('Casos RF')
    neg_ws = wb.create_sheet('Negativos')
    e2e_ws = wb.create_sheet('Flujo E2E')
    rnf_ws = wb.create_sheet('Casos RNF')
    guide = wb.create_sheet('Guía y datos')
    summary.sheet_view.showGridLines = guide.sheet_view.showGridLines = False

    tracking = ['Estado', 'Resultado observado', 'Evidencia / enlace',
                'Defecto / incidencia', 'Ejecutor', 'Fecha', 'Entorno', 'Versión / commit']
    rf_rows = [
        (case, rf, module, role(rf, pre), priority, pre, action, expected,
         'No ejecutado', '', '', '', '', '', '', '')
        for module, case, rf, priority, pre, action, expected in data['rf']
    ]
    negative_rows = [
        (case, rf, role(rf.split(',')[0], pre), priority, pre, action, expected,
         'No ejecutado', '', '', '', '', '', '', '')
        for case, rf, priority, pre, action, expected in data['negative']
    ]
    e2e_rows = [
        (case, actor, action, expected, 'No ejecutado', '', '', '', '', '', '', '')
        for case, actor, action, expected in data['e2e']
    ]
    rnf_actors = {
        'RNF-03': 'Tres roles', 'RNF-04': 'Visitante / tres roles',
        'RNF-10': 'Operador', 'RNF-12': 'Tres roles / navegador',
        'RNF-14': 'Operador', 'RNF-21': 'Administrador',
    }
    rnf_rows = [
        (case, rnf, rnf_actors[rnf], priority, pre, action, expected,
         'No ejecutado', '', '', '', '', '', '', '')
        for case, rnf, priority, pre, action, expected in data['rnf']
    ]
    fill_sheet(rf_ws, rf_rows,
        ['Caso', 'Requisito', 'Módulo', 'Rol / actor', 'Prioridad',
         'Precondición / datos', 'Acción / pasos', 'Resultado esperado'] + tracking,
        [17, 18, 38, 24, 12, 48, 61, 66, 19, 55, 40, 28, 22, 18, 26, 24],
        'CasosRF', f'{len(rf_rows)} IDs de la matriz interna. NO es cobertura de la fuente externa: ver AUDITORIA_FUENTES_REQUISITOS.md.')
    fill_sheet(neg_ws, negative_rows,
        ['Caso', 'RF relacionados', 'Rol / actor', 'Prioridad',
         'Precondición / datos', 'Acción / pasos', 'Resultado esperado'] + tracking,
        [17, 37, 28, 12, 52, 62, 68, 19, 55, 40, 28, 22, 18, 26, 24],
        'CasosNegativos', '15 pruebas adversariales y de frontera; sin ejecución manual registrada.')
    fill_sheet(e2e_ws, e2e_rows,
        ['Paso', 'Actor', 'Acción / pasos', 'Comprobación esperada'] + tracking,
        [17, 29, 76, 77, 19, 55, 40, 28, 22, 18, 26, 24],
        'PasosE2E', '8 pasos de un flujo integral; E2E-08 usa una contratación distinta a la ya finalizada.')
    fill_sheet(rnf_ws, rnf_rows,
        ['Caso', 'Requisito RNF', 'Rol / actor', 'Prioridad',
         'Precondición / datos', 'Acción / pasos', 'Resultado esperado'] + tracking,
        [17, 18, 28, 12, 55, 72, 78, 19, 55, 40, 28, 22, 18, 26, 24],
        'CasosRNF', '6 RNF priorizados de 38 documentados; 32 sin caso propio; no ejecutados.')

    summary.merge_cells('A1:H1')
    summary['A1'] = 'JOBDEVS  |  CASOS DE PRUEBA'
    summary['A1'].font = Font(name='Aptos Display', size=20, bold=True, color='FFFFFF')
    summary['A1'].fill = PatternFill('solid', fgColor=NAVY)
    summary.row_dimensions[1].height = 38
    for col in 'ABCDEFGH':
        summary.column_dimensions[col].width = 24
    overview = [
        ('Fuente', 'docs/CASOS_DE_PRUEBA.md'),
        ('IDs en matriz interna', len(data['rf'])),
        ('Fuente externa', '97 enumerados (66 base + 31 extensiones); declara 99'),
        ('Diferencia pendiente', '12 IDs base solo externos, 14 solo internos; ver AUDITORIA_FUENTES_REQUISITOS.md'),
        ('Casos RF', len(data['rf'])),
        ('Casos RNF separados', len(data['rnf'])),
        ('Casos negativos', len(data['negative'])),
        ('Pasos de flujo E2E', len(data['e2e'])),
        ('Pruebas manuales', 'NO EJECUTADAS — registrar resultado por fila'),
        ('Suite local, sin E2E', '1242 aprobadas, 1 omitida (commit 1b7a2ac); resultado separado'),
        ('Motor para concurrencia', 'PostgreSQL: no validar locks usando SQLite'),
    ]
    for row_idx, (label, value) in enumerate(overview, 3):
        summary.cell(row_idx, 1, label).font = Font(bold=True, color=NAVY)
        summary.merge_cells(start_row=row_idx, start_column=2, end_row=row_idx, end_column=8)
        summary.cell(row_idx, 2, value)
        summary.cell(row_idx, 2).alignment = Alignment(wrap_text=True, vertical='center')
        summary.row_dimensions[row_idx].height = 29
    summary['A15'] = 'Seguimiento manual (se recalcula al abrir en Excel/LibreOffice)'
    summary['A15'].font = Font(bold=True, color=BLUE)
    for i, (sheet, end, state_col) in enumerate([
        ('Casos RF', 4 + len(rf_rows), 'I'),
        ('Negativos', 4 + len(negative_rows), 'H'),
        ('Flujo E2E', 4 + len(e2e_rows), 'E'),
        ('Casos RNF', 4 + len(rnf_rows), 'H'),
    ], 17):
        summary.cell(i, 1, sheet)
        summary.cell(i, 2, f'=COUNTA(\'{sheet}\'!A5:A{end})')
        for j, state in enumerate(['No ejecutado', 'Pasó', 'Falló', 'Bloqueado'], 3):
            summary.cell(i, j, f'=COUNTIF(\'{sheet}\'!{state_col}5:{state_col}{end},"{state}")')
    for i, name in enumerate(['Hoja', 'Total', 'No ejecutado', 'Pasó', 'Falló', 'Bloqueado'], 1):
        summary.cell(16, i, name).font = Font(bold=True, color='FFFFFF')
        summary.cell(16, i).fill = PatternFill('solid', fgColor=BLUE)
    summary.freeze_panes = 'B17'

    guide_rows = [
        ('Alcance', 'Este libro es un catálogo editable de diseño y ejecución; ningún caso manual está marcado como pasado.'),
        ('Trazabilidad', '99 IDs internos, NO 99 certificados frente a la fuente externa: 12 IDs solo externos y 14 solo internos. Ver docs/AUDITORIA_FUENTES_REQUISITOS.md.'),
        ('RNF', '6 casos priorizados de los 38 RNF de MatrizRNF.md; los otros 32 siguen sin caso propio.'),
        ('Estados', 'Cambiar Estado con el menú desplegable y completar Observado, Evidencia, Defecto, Ejecutor, Fecha, Entorno y Versión.'),
        ('P0 / P1 / P2', 'P0: seguridad/integridad; P1: flujo principal; P2: presentación/datos auxiliares.'),
        ('EMP-A / EMP-B', 'Empresa propietaria verificada / empresa ajena; usar cuentas ficticias separadas.'),
        ('DEV-A / DEV-B', 'Desarrollador SENA habilitado / desarrollador ajeno; usar cuentas ficticias.'),
        ('ADM-A / ANON', 'Administrador / usuario sin sesión.'),
        ('Estados de proyecto', 'Preparar publicado, en_desarrollo, en_disputa y finalizado; cupos libres/agotados.'),
        ('Entorno', 'Base de datos aislada; correo de prueba. No usar producción ni datos reales.'),
        ('Concurrencia', 'Ejecutar en PostgreSQL para comprobar bloqueos de filas; no inferir de SQLite.'),
        ('Flujo E2E', 'El paso E2E-08 requiere otra contratación activa distinta de la ya finalizada.'),
        ('Automatización', 'Las pruebas automáticas existentes NO son ejecución de las filas manuales; verificar test exacto antes de enlazarlo.'),
        ('Criterio de salida', 'Primero resolver IDs discordantes con responsable del producto; luego P0/P1 y E2E ejecutados en entornos declarados.'),
    ]
    guide.column_dimensions['A'].width = 27
    guide.column_dimensions['B'].width = 125
    guide.append(['Concepto', 'Instrucción / dato'])
    guide['A1'].font = guide['B1'].font = Font(color='FFFFFF', bold=True)
    guide['A1'].fill = guide['B1'].fill = PatternFill('solid', fgColor=NAVY)
    for label, value in guide_rows:
        guide.append([label, value])
        guide.cell(guide.max_row, 2).alignment = Alignment(wrap_text=True, vertical='center')
        guide.row_dimensions[guide.max_row].height = 34
    guide.freeze_panes = 'B2'

    wb.calculation = CalcProperties(calcMode='auto', fullCalcOnLoad=True)
    wb.save(args.out)
    print(f'{args.out}: {len(rf_rows)} RF, {len(rnf_rows)} RNF, '
          f'{len(negative_rows)} negativos, {len(e2e_rows)} E2E')


if __name__ == '__main__':
    main()
