import frappe
import logging
from functools import lru_cache
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SPREADSHEET_ID = "1uZMDUujtlQr_G5E720P0upyQJ2Pfwiu_m8DIorZZyvA"
SHEET_NAME = "Tender"
SERVICE_ACCOUNT_FILE = "/home/erpadmin/bench-jalsampada-portal/sites/credentials/google_sheets.json"

SCOPES = ("https://www.googleapis.com/auth/spreadsheets.readonly",)

MAX_ROWS = 50
MAX_COLS = 26

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_sheets_service():
    creds = Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds, cache_discovery=False)

def pad_row(row, length):
    row = row or []
    return row[:length] if len(row) >= length else row + [''] * (length - len(row))

def fetch_sheet_data():
    try:
        service = get_sheets_service()
        range_name = f"{SHEET_NAME}!A1:Z{MAX_ROWS}"

        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=range_name,
            valueRenderOption="FORMATTED_VALUE"
        ).execute()

        values = result.get("values", [])
        if not values:
            return {
                "success": True,
                "headers": [],
                "rows": [],
                "total_rows": 0,
                "total_columns": 0
            }

        headers = pad_row(values[0], MAX_COLS)

        data_rows = []
        for row in values[1:]:
            if any(str(cell).strip() for cell in row):
                data_rows.append(pad_row(row, MAX_COLS))

        return {
            "success": True,
            "headers": headers,
            "rows": data_rows,
            "total_rows": len(data_rows),
            "total_columns": len(headers)
        }

    except Exception as e:
        logger.exception("fetch_sheet_data failed")
        return {"success": False, "error": str(e)}

@frappe.whitelist(allow_guest=True)
def get_tender_json():
    data = fetch_sheet_data()

    frappe.response["data"] = data
    frappe.response["type"] = "json"
    frappe.response["http_status_code"] = 200
    frappe.local.response.headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
    }

    return data

@frappe.whitelist(allow_guest=True)
def get_ongoing_tender_json():
    SPREADSHEET_ID_ONGOING = "1jo9m4WLQ2k7AdqISUAzwpm0fer5gqvbmvVAob7pamRk"
    SERVICE_ACCOUNT_FILE_ONGOING = "/home/erpadmin/bench-jalsampada-portal/sites/credentials/google_sheets_new.json"
    try:
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE_ONGOING,
            scopes=SCOPES
        )
        service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        range_name = "'Ongoing Tender'!A1:Z100"
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID_ONGOING,
            range=range_name,
            valueRenderOption="FORMATTED_VALUE"
        ).execute()
        values = result.get("values", [])
        
        header_row_idx = -1
        for i, row in enumerate(values):
            if row and any("अ. क्र." in str(cell) for cell in row):
                header_row_idx = i
                break
        
        if header_row_idx == -1:
             for i, row in enumerate(values):
                 if any(str(cell).strip() for cell in row):
                     header_row_idx = i
                     break
        
        if header_row_idx == -1:
            return {"success": False, "error": "No data found"}
            
        headers = values[header_row_idx]
        rows = [row for row in values[header_row_idx+1:] if any(str(cell).strip() for cell in row)]
        
        data = {
            "success": True,
            "headers": headers,
            "rows": rows
        }
        frappe.response["data"] = data
        return data
    except Exception as e:
        return {"success": False, "error": str(e)}
