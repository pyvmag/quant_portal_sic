import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json

SPREADSHEET_ID = "1jo9m4WLQ2k7AdqISUAzwpm0fer5gqvbmvVAob7pamRk"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = "/home/erpadmin/bench-jalsampada-portal/sites/credentials/google_sheets_new.json"

def inspect_aexp():
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        sheet = service.spreadsheets().get(
            spreadsheetId=SPREADSHEET_ID,
            ranges=["Aexp"],
            includeGridData=True
        ).execute()
        
        sheet_obj = sheet['sheets'][0]
        data = sheet_obj['data'][0].get('rowData', [])
        
        print("Number of rows in Aexp:", len(data))
        for i in range(min(10, len(data))):
            row_vals = [cell.get('formattedValue', '') if cell else '' for cell in data[i].get('values', [])]
            print(f"Row {i}: {row_vals}")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    inspect_aexp()
