from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SPREADSHEET_ID = "1jo9m4WLQ2k7AdqISUAzwpm0fer5gqvbmvVAob7pamRk"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = "/home/erpadmin/bench-jalsampada-portal/sites/credentials/google_sheets_new.json"

def list_sheets():
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        spreadsheet = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        sheets = [sheet['properties']['title'] for sheet in spreadsheet['sheets']]
        print("Sheets found:", sheets)
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    list_sheets()
