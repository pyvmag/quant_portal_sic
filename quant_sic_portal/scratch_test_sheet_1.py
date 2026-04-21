import frappe
import json

def test_sheet_data():
    from quant_sic_portal.api import fetch_sheet_raw_data, extract_tables
    
    sheet_name = "Flood Info 1"
    raw_data = fetch_sheet_raw_data(sheet_name=sheet_name)
    print(f"Fetched {len(raw_data)} rows from {sheet_name}")
    
    tables = extract_tables(raw_data)
    print(f"Extracted {len(tables)} tables")
    
    for i, table in enumerate(tables):
        print(f"\nTable {i+1}: {table['title']}")
        print(f"Rows: {len(table['rows'])}")
        if table['rows']:
            print(f"Header: {table['rows'][0][:5]}")
            if len(table['rows']) > 1:
                print(f"First Data Row: {table['rows'][1][:5]}")

if __name__ == "__main__":
    test_sheet_data()
