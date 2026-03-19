import frappe
import json
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

# Google Sheets Configuration
SPREADSHEET_ID = "1uZMDUujtlQr_G5E720P0upyQJ2Pfwiu_m8DIorZZyvA"
SHEET_NAME = "Pani Vapar 2"
SERVICE_ACCOUNT_FILE = "/home/erpadmin/bench-jalsampada-portal/sites/credentials/google_sheets.json"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]


@frappe.whitelist(allow_guest=True)
def get_sheet_data():
    """
    Public API endpoint to fetch data from Google Sheet 'Pani Vapar 2'.
    Detects header row by orange background (#ff9900).
    Returns structured JSON for frontend table display.
    """
    try:
        # Authenticate with service account
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)

        # Define range (adjust if you have more rows/columns)
        a1_range = f"'{SHEET_NAME}'!A1:ZZ1000"

        # Fetch raw values using spreadsheets.values.get (simple and reliable)
        values_result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=a1_range
        ).execute()

        values = values_result.get('values', [])
        if not values:
            return {"success": False, "error": "No data found in the sheet."}

        # Fetch formatting using spreadsheets.get with correct fields mask
        # We request: backgroundColor, bold, foregroundColor (for red text), and formattedValue (per cell)
        fields_mask = (
            "sheets(data(rowData(values("
            "effectiveFormat(backgroundColor,textFormat(bold,foregroundColor)),"
            "formattedValue"
            ")),startRow,startColumn))"
        )

        format_result = service.spreadsheets().get(
            spreadsheetId=SPREADSHEET_ID,
            ranges=a1_range,
            fields=fields_mask,
            includeGridData=True  # Required to get rowData when using ranges
        ).execute()

        sheets = format_result.get('sheets', [])
        if not sheets or not sheets[0].get('data'):
            return {"success": False, "error": "Could not retrieve formatting data."}

        data_grid = sheets[0]['data'][0]
        row_data = data_grid.get('rowData', [])
        start_row = data_grid.get('startRow', 0)

        # Build grid of formatted values (fallback if needed)
        formatted_grid = []
        for i, row in enumerate(row_data):
            if i + start_row >= len(values) + start_row:
                break
            formatted_row = []
            cells = row.get('values', [])
            for cell in cells:
                formatted_row.append(cell.get('formattedValue', ''))
            formatted_grid.append(formatted_row)

        # Pad rows to uniform columns
        max_cols = max(len(row) for row in values) if values else 0
        padded_values = [row + [''] * (max_cols - len(row)) for row in values]
        padded_formatted = [row + [''] * (max_cols - len(row)) for row in formatted_grid]

        # Detect header row by #ff9900 background (RGB: 1.0, 0.6, 0.0)
        header_row_idx = 0  # fallback
        for i, row in enumerate(row_data):
            if 'values' not in row:
                continue
            cells = row['values']
            if not cells:
                continue

            bg_matches = []
            for cell in cells:
                fmt = cell.get('effectiveFormat', {})
                bg = fmt.get('backgroundColor', {})
                r = bg.get('red', 0)
                g = bg.get('green', 0)
                b = bg.get('blue', 0)

                if abs(r - 1.0) < 0.01 and abs(g - 0.6) < 0.01 and abs(b - 0.0) < 0.01:
                    bg_matches.append(True)
                elif cell.get('formattedValue'):  # cell has content but wrong bg
                    bg_matches.append(False)

            if bg_matches and all(bg_matches):
                header_row_idx = i
                break

        # Extract parts
        headers = padded_values[header_row_idx]
        title_rows = padded_values[:header_row_idx]  # rows above header (e.g., main title with red bg)
        data_rows = padded_values[header_row_idx + 1:]  # data below header

        return {
            "success": True,
            "data": {
                "title_rows": title_rows,
                "headers": headers,
                "rows": data_rows
            }
        }

    except Exception as e:
        frappe.log_error(message=frappe.get_traceback(), title="Pani Vapar Sheet Error")
        return {
            "success": False,
            "error": f"Failed to fetch sheet data: {str(e)}"
        }


@frappe.whitelist(allow_guest=True)
def get_tender_json():
    return get_sheet_data()