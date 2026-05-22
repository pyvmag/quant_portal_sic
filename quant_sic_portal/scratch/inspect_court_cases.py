from quant_sic_portal.api2 import fetch_sheet_raw_data, is_header_row, get_full_row_data, get_headers_with_type

def inspect():
    try:
        rows = fetch_sheet_raw_data()
        print(f"Total rows fetched: {len(rows)}")
        for idx, row in enumerate(rows[:40]):
            full_row = get_full_row_data(row)
            row_text = "".join([item['value'] for item in full_row]).strip()
            if row_text:
                is_hdr = is_header_row(row)
                headers = get_headers_with_type(row)
                print(f"Row {idx}: is_header={is_hdr}, text='{row_text}', headers_count={len(headers)}")
                # Print bold and color details for each cell
                for c_idx, cell in enumerate(row.get('values', [])):
                    if cell and cell.get('formattedValue'):
                        val = cell.get('formattedValue')
                        bold = cell.get('userEnteredFormat', {}).get('textFormat', {}).get('bold', False)
                        bg = cell.get('userEnteredFormat', {}).get('backgroundColor', {})
                        print(f"  Cell {c_idx}: '{val}', bold={bold}, bg={bg}")
    except Exception as e:
        import traceback
        traceback.print_exc()
