
import sys
import os
import json

# Add the project directory to sys.path to import our module
sys.path.append("/home/erpadmin/bench-jalsampada-portal/apps/quant_sic_portal")

from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SPREADSHEET_ID = "1uZMDUujtlQr_G5E720P0upyQJ2Pfwiu_m8DIorZZyvA"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
SERVICE_ACCOUNT_FILE = "/home/erpadmin/bench-jalsampada-portal/sites/credentials/google_sheets.json"
SHEET_NAME = "sheet3"

def fetch_sheet_raw_data(sheet_name=SHEET_NAME):
    creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    sheet = service.spreadsheets().get(
        spreadsheetId=SPREADSHEET_ID,
        ranges=[sheet_name],
        includeGridData=True
    ).execute()
    return sheet['sheets'][0]['data'][0]['rowData']

def test_debug():
    data = fetch_sheet_raw_data()
    print(f"Total rows: {len(data)}")
    
    for i in range(20, 40):
        if i >= len(data): break
        row = data[i]
        values = []
        is_bold = []
        is_yellow = []
        
        if 'values' in row:
            for cell in row['values']:
                val = cell.get('formattedValue', '')
                values.append(val)
                bold = cell.get('userEnteredFormat', {}).get('textFormat', {}).get('bold', False)
                is_bold.append(bold)
                
                bg = cell.get('userEnteredFormat', {}).get('backgroundColor', {})
                r = bg.get('red', 0)
                g = bg.get('green', 0)
                b = bg.get('blue', 0)
                yellow = (r > 0.9 and g > 0.9 and b < 0.2)
                is_yellow.append(yellow)
        
        print(f"Row {i+1}: {values}")
        print(f"Bold {i+1}: {any(is_bold)}")
        print(f"Yellow {i+1}: {any(is_yellow)}")
        print("-" * 20)

if __name__ == "__main__":
    test_debug()
