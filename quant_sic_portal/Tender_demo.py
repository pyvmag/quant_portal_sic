import frappe
import logging
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SPREADSHEET_ID = "1uZMDUujtlQr_G5E720P0upyQJ2Pfwiu_m8DIorZZyvA"
SERVICE_ACCOUNT_FILE = "/home/erpadmin/bench-jalsampada-portal/sites/credentials/google_sheets.json"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

logger = logging.getLogger(__name__)

def fetch_sheet_data(sheet_name, max_rows=100, max_cols=26, header_row_idx=None):
    try:
        credentials = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=credentials)
        range_name = f"{sheet_name}!A1:Z{max_rows}"
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name
        ).execute()
        values = result.get('values', [])
        if not values:
            return {'success': True, 'headers': [], 'rows': [], 'total_rows': 0, 'total_columns': 0}

        for row in values:
            if len(row) < max_cols:
                row.extend([''] * (max_cols - len(row)))

        if header_row_idx is None:
            header_row_idx = next((i for i, row in enumerate(values) if any(cell.strip() for cell in row)), None)
            if header_row_idx is None:
                return {'success': True, 'headers': [], 'rows': [], 'total_rows': 0, 'total_columns': 0}
        else:
            if isinstance(header_row_idx, str) and header_row_idx.lower() == 'null':
                header_row_idx = next((i for i, row in enumerate(values) if any(cell.strip() for cell in row)), None)
                if header_row_idx is None:
                    return {'success': True, 'headers': [], 'rows': [], 'total_rows': 0, 'total_columns': 0}
            else:
                if isinstance(header_row_idx, str):
                    header_row_idx = int(header_row_idx)
                if header_row_idx >= len(values):
                    return {'success': True, 'headers': [], 'rows': [], 'total_rows': 0, 'total_columns': 0}

        headers = values[header_row_idx]
        headers = [cell.strip() if cell else '' for cell in headers]
        while headers and not headers[-1]:
            headers.pop()
        num_cols = len(headers)

        start_data_idx = header_row_idx + 1
        data_rows = []
        for row_idx in range(start_data_idx, len(values)):
            row = values[row_idx]
            if len(row) < num_cols:
                row = row + [''] * (num_cols - len(row))
            if any(cell.strip() for cell in row[:num_cols]):
                data_rows.append(row[:num_cols])

        return {'success': True, 'headers': headers, 'rows': data_rows,
                'total_rows': len(data_rows), 'total_columns': num_cols}

    except Exception as e:
        logger.error(f"fetch_sheet_data failed for {sheet_name}: {str(e)}", exc_info=True)
        return {'success': False, 'error': str(e)}

@frappe.whitelist(allow_guest=True)
def get_tender_json(sheet_name="Tender", header_row_idx=None, max_rows=50, max_cols=26):
    try:
        if header_row_idx == 'null':
            header_row_idx = None

        if sheet_name == "Tender" and header_row_idx is None:
            header_row_idx = 0
            max_rows = 50
        elif sheet_name == "Tender2" and header_row_idx is None:
            header_row_idx = 2
            max_rows = 50
        elif sheet_name == "Sheet_pdf" and header_row_idx is None:
            header_row_idx = None
            max_rows = 100
        else:
            max_rows = max_rows or 100

        max_rows = int(max_rows)
        max_cols = int(max_cols)

        data = fetch_sheet_data(sheet_name, max_rows, max_cols, header_row_idx)
        frappe.response['data'] = data
        frappe.response['type'] = 'json'
        frappe.response['http_status_code'] = 200
        frappe.local.response.headers = {
            'Content-Type': 'application/json; charset=utf-8',
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0'
        }
        return data

    except Exception as e:
        logger.error(f"get_tender_json error for {sheet_name}: {str(e)}", exc_info=True)
        error_response = {'success': False, 'error': str(e)}
        frappe.response['data'] = error_response
        frappe.response['type'] = 'json'
        frappe.response['http_status_code'] = 200
        return error_response
