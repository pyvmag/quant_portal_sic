import frappe
import json

def debug_sheet_rows():
    from quant_sic_portal.api import fetch_sheet_raw_data
    sheet_name = "Flood Info 1"
    raw_data = fetch_sheet_raw_data(sheet_name=sheet_name)
    
    for i, row in enumerate(raw_data):
        cells = [cell.get('formattedValue', '') or '' for cell in row.get('values', [])]
        print(f"Row {i+1}: {cells}")

if __name__ == "__main__":
    debug_sheet_rows()
