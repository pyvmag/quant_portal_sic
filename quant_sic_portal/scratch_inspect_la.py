
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import json

SPREADSHEET_ID = "1jo9m4WLQ2k7AdqISUAzwpm0fer5gqvbmvVAob7pamRk"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SERVICE_ACCOUNT_FILE = "/home/erpadmin/bench-jalsampada-portal/sites/credentials/google_sheets_new.json"

def inspect_la():
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID,
        ranges=["LA!A1:Z20"],
        includeGridData=True
    ).execute()
    
    rows = sheet['sheets'][0]['data'][0].get('rowData', [])
    for i, row in enumerate(rows):
        vals = [cell.get('formattedValue', '') for cell in row.get('values', [])]
        print(f"Row {i}: {vals}")

if __name__ == "__main__":
    inspect_la()
