

import frappe
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import copy

SPREADSHEET_ID = "1uZMDUujtlQr_G5E720P0upyQJ2Pfwiu_m8DIorZZyvA"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SERVICE_ACCOUNT_FILE = "/home/erpadmin/bench-jalsampada-portal/sites/credentials/google_sheets.json"

SHEET_NAME = "sheet3"

CHART_HEADERS = [
    "सर्वोच्च न्यायालय",
    "उच्च न्यायालय",
    "दिवाणी न्यायालय",
    "अवमान याचिका",
    "मॅट",
    "इतर"
]

def is_kpi_color(cell):
    bg = cell.get('userEnteredFormat', {}).get('backgroundColor', {})
    red = bg.get('red', 0)
    green = bg.get('green', 0)
    blue = bg.get('blue', 1)
    return abs(red - 0.988) < 0.05 and abs(green - 0.898) < 0.05 and abs(blue - 0.804) < 0.05

def is_chart_color(cell):
    bg = cell.get('userEnteredFormat', {}).get('backgroundColor', {})
    red = bg.get('red', 0)
    green = bg.get('green', 0)
    blue = bg.get('blue', 1)
    return abs(red - 0.788) < 0.05 and abs(green - 0.855) < 0.05 and abs(blue - 0.973) < 0.05

def is_green_color(cell):
    bg = cell.get('userEnteredFormat', {}).get('backgroundColor', {})
    red = bg.get('red', 0)
    green = bg.get('green', 0)
    blue = bg.get('blue', 1)
    return abs(red - 0.576) < 0.05 and abs(green - 0.769) < 0.05 and abs(blue - 0.490) < 0.05

def is_yellow_cell(cell):
    if not cell:
        return False
    bg = cell.get('userEnteredFormat', {}).get('backgroundColor', {})
    red = bg.get('red', 0)
    green = bg.get('green', 0)
    blue = bg.get('blue', 1)
    return red > 0.9 and green > 0.9 and blue < 0.2

def get_full_row_data(row):
    if not row.get('values'):
        return []
    return [
        {
            'value': cell.get('formattedValue', '') if cell else '',
            'bg': cell.get('userEnteredFormat', {}).get('backgroundColor', {}) if cell else {}
        } for cell in row['values']
    ]

def get_headers_with_type(row):
    full_data = get_full_row_data(row)
    headers = []
    for idx, item in enumerate(full_data[2:], 2): # Skip first two columns (serial and labels)
        name = item['value'].strip()
        if name:
            cell = {'userEnteredFormat': {'backgroundColor': item['bg']}} # For color check
            header_type = None
            if is_kpi_color(cell):
                header_type = 'kpi'
            elif is_chart_color(cell):
                header_type = 'chart'
            elif is_green_color(cell):
                header_type = 'both'
            
            if name in CHART_HEADERS:
                header_type = 'chart' if header_type != 'kpi' else 'both'
            
            headers.append({'name': name, 'type': header_type, 'col_index': idx})
    return headers

def get_title(row):
    for cell in row.get('values', []):
        if cell and cell.get('formattedValue', '').strip():
            return cell['formattedValue'].strip()
    return 'Untitled'

def is_empty_row(row):
    if not row.get('values'):
        return True
    return all((not cell or not cell.get('formattedValue', '').strip()) for cell in row['values'])

def has_bold_row(row):
    if not row.get('values'):
        return False
    return any(
        cell and
        cell.get('userEnteredFormat', {}).get('textFormat', {}).get('bold', False) and
        cell.get('formattedValue', '').strip()
        for cell in row['values']
    )

def is_yellow_row(raw_row):
    if not raw_row.get('values'):
        return False
    return any(is_yellow_cell(cell) for cell in raw_row['values'] if cell)

def fetch_sheet_raw_data(sheet_name=SHEET_NAME):
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID,
        ranges=[sheet_name],
        includeGridData=True
    ).execute()
    return sheet['sheets'][0]['data'][0]['rowData']

def filter_empty_columns(headers_with_type, data_rows):
    """Filter out columns where all data is empty or zero"""
    if not data_rows or not headers_with_type:
        return headers_with_type, []
    
    valid_col_indices = []
    for col_info in headers_with_type:
        col_index = col_info['col_index']
        is_empty = True
        for row in data_rows:
            if len(row) > col_index:
                val = row[col_index]['value'].strip()
                if val and val != '0' and val != '0.0':
                    is_empty = False
                    break
        if not is_empty:
            valid_col_indices.append((col_info, col_index))
    
    filtered_headers = [col[0] for col in valid_col_indices]
    filtered_rows = []
    for row in data_rows:
        filtered_row = [row[0], row[1]] if len(row) > 1 else [row[0]]  # Keep serial and label
        for _, col_index in valid_col_indices:
            filtered_row.append(row[col_index] if len(row) > col_index else {'value': ''})
        filtered_rows.append(filtered_row)
    
    filtered_totals = None
    
    return filtered_headers, filtered_rows

def calculate_kpis(header_types, rows):
    kpis = []
    if not header_types or not rows:
        return kpis
    label_index = 1 
    for col_info in header_types:
        col_index = col_info['col_index']
        if col_info['type'] in ['kpi', 'both']:
            col_values = []
            for row in rows:
                if len(row) > label_index and row[label_index]['value'].strip():
                    if len(row) > col_index:
                        val = row[col_index]['value'].strip()
                        if val:
                            try:
                                num = float(val)
                                col_values.append(num)
                            except ValueError:
                                pass
            total_sum = sum(col_values)
            if col_values: 
                kpis.append({'label': col_info['name'], 'value': round(total_sum, 2)})
    return kpis

def prepare_charts(header_types, rows):
    charts = []
    if not header_types or not rows:
        return charts
    label_index = 1
    chart_types = ['bar', 'pie', 'doughnut']
    for i, col_info in enumerate(header_types):
        col_index = col_info['col_index']
        if col_info['type'] in ['chart', 'both'] or col_info['name'] in CHART_HEADERS:
            labels = []
            data = []
            for row in rows:
                if len(row) > label_index:
                    label_val = row[label_index]['value'].strip()
                    if label_val:
                        labels.append(label_val)
                        if len(row) > col_index:
                            val = row[col_index]['value'].strip()
                            try:
                                num = float(val)
                                data.append(num)
                            except ValueError:
                                data.append(0)
                        else:
                            data.append(0)
            if labels and data and len(labels) == len(data) and any(data): # Only if there's data
                chart_type = chart_types[i % len(chart_types)]
                charts.append({
                    'type': chart_type,
                    'label': f"{col_info['name']} चा आलेख (विभागानुसार)",
                    'labels': labels,
                    'data': data
                })
    return charts

@frappe.whitelist(allow_guest=True)
def run_test_py_demo():
    try:
        sheet_data = fetch_sheet_raw_data()
        frappe.log(f"Total rows in sheet: {len(sheet_data)}")
        tables = []
        i = 0
        while i < len(sheet_data):
            while i < len(sheet_data) and not has_bold_row(sheet_data[i]):
                i += 1
            if i >= len(sheet_data):
                break
            headers_with_type = get_headers_with_type(sheet_data[i])
            headers = [h['name'] for h in headers_with_type]
            header_index = i
            frappe.log(f"Header row at {i}: {headers}")
            i = header_index + 1
            title = 'Untitled Table'
            for j in range(header_index - 1, -1, -1):
                if not is_empty_row(sheet_data[j]):
                    title = get_title(sheet_data[j])
                    frappe.log(f"Title found at row {j}: {title}")
                    break
            data_rows = []
            while i < len(sheet_data):
                if has_bold_row(sheet_data[i]) or is_yellow_row(sheet_data[i]):
                    break
                full_row = get_full_row_data(sheet_data[i])
                row_is_yellow = any(is_yellow_cell({'userEnteredFormat': {'backgroundColor': item['bg']}}) for item in full_row)
                first_cell_empty = len(full_row) > 0 and not full_row[0]['value'].strip()
                if not row_is_yellow and not first_cell_empty and any(item['value'].strip() for item in full_row):
                    data_rows.append(full_row)
                i += 1
            totals = None
            if i < len(sheet_data) and is_yellow_row(sheet_data[i]):
                totals = get_full_row_data(sheet_data[i])
                i += 1
            
            filtered_headers_with_type, filtered_data_rows = filter_empty_columns(headers_with_type, data_rows)
            filtered_headers = [h['name'] for h in filtered_headers_with_type]
            if totals:
                filtered_totals = [totals[0], totals[1]] if len(totals) > 1 else [totals[0]]
                for h in filtered_headers_with_type:
                    col_index = h['col_index']
                    filtered_totals.append(totals[col_index] if len(totals) > col_index else {'value': ''})
            else:
                filtered_totals = None
            
            kpis = calculate_kpis(filtered_headers_with_type, filtered_data_rows)
            charts = prepare_charts(filtered_headers_with_type, filtered_data_rows)
            table = {
                'title': title,
                'headers': filtered_headers,
                'header_types': filtered_headers_with_type,
                'rows': filtered_data_rows,
                'totals': filtered_totals,
                'kpis': kpis,
                'charts': charts
            }
            tables.append(table)
        frappe.log(f"Total tables: {len(tables)}")
        return {
            "status": "ok",
            "message": tables
        }
    except Exception as e:
        frappe.log(f"Error: {str(e)}")
        import traceback
        frappe.log(traceback.format_exc())
        return {"status": "fail", "message": str(e)}