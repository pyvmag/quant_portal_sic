import frappe
import json

def debug_flood_info_2():
    from quant_sic_portal.api import fetch_sheet_raw_data
    sheet_name = "Flood Info 2"
    raw_data_obj = fetch_sheet_raw_data(sheet_name=sheet_name)
    raw_data = raw_data_obj.get('rowData', [])
    
    print(f"Fetched {len(raw_data)} rows from {sheet_name}")
    for i, row in enumerate(raw_data[:40]): # First 40 rows
        cells = [cell.get('formattedValue', '') or '' for cell in row.get('values', [])]
        print(f"Row {i+1}: {cells}")

if __name__ == "__main__":
    debug_flood_info_2()
