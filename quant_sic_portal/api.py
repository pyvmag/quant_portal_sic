import frappe
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from frappe.utils import nowdate

SPREADSHEET_ID = "1jo9m4WLQ2k7AdqISUAzwpm0fer5gqvbmvVAob7pamRk"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
SERVICE_ACCOUNT_FILE = "/home/erpadmin/bench-jalsampada-portal/sites/credentials/google_sheets_new.json"


def clean_display(s):
    return str(s).strip().replace('\u200B', '')

def clean_header(s):
    return clean_display(s).lower()

def clean_numeric(s):
    return str(s).strip().replace('\u200B', '').replace(',', '')

def is_title_row(row):
    if 'values' not in row:
        return False
    for cell in row['values']:
        if cell:
            text_color = cell.get('userEnteredFormat', {}).get('textFormat', {}).get('foregroundColor', {})
            bg_color = cell.get('userEnteredFormat', {}).get('backgroundColor', {})
            is_white_text = (text_color.get('red', 0) > 0.9 and
                             text_color.get('green', 0) > 0.9 and
                             text_color.get('blue', 0) > 0.9)
            is_black_bg = (bg_color.get('red', 0) < 0.2 and
                           bg_color.get('green', 0) < 0.2 and
                           bg_color.get('blue', 0) < 0.2)
            if is_white_text and is_black_bg:
                return True
    return False

def get_title_value(row):
    if 'values' not in row:
        return ''
    for cell in row['values']:
        if cell:
            return cell.get('formattedValue', '') or ''
    return ''

def is_bold_row(row):
    if 'values' not in row:
        return False
    return any(
        cell.get('userEnteredFormat', {}).get('textFormat', {}).get('bold', False)
        for cell in row['values'] if cell
    )

def is_empty_row(row):
    if 'values' not in row:
        return True
    full_values = [cell.get('formattedValue') if cell else None for cell in row['values']]
    return all(v in (None, "") for v in full_values)

def is_yellow_row_with_total(row):
    if 'values' not in row:
        return False
    yellow_bg = any(
        (
            cell.get('userEnteredFormat', {}).get('backgroundColor', {}).get('red', 0) > 0.9 and
            cell.get('userEnteredFormat', {}).get('backgroundColor', {}).get('green', 0) > 0.9 and
            cell.get('userEnteredFormat', {}).get('backgroundColor', {}).get('blue', 0) < 0.2
        )
        for cell in row['values'] if cell
    )
    has_total = any('एकूण' in (cell.get('formattedValue', '') or '') for cell in row['values'])
    return yellow_bg and has_total

def find_date_with_red_text(sheet_data):
    for row in sheet_data:
        if 'values' not in row:
            continue
        for cell in row['values']:
            if cell:
                text_color = cell.get('userEnteredFormat', {}).get('textFormat', {}).get('foregroundColor', {})
                bg_color = cell.get('userEnteredFormat', {}).get('backgroundColor', {})
                # Red text: high red, low green/blue
                is_red = (text_color.get('red', 0) > 0.7 and
                          text_color.get('green', 0) < 0.3 and
                          text_color.get('blue', 0) < 0.3)
                # White background: high red, green, blue (or default white)
                is_white_bg = True # Assume white if not specified
                if 'backgroundColor' in cell.get('userEnteredFormat', {}):
                    is_white_bg = (bg_color.get('red', 0) > 0.9 and
                                   bg_color.get('green', 0) > 0.9 and
                                   bg_color.get('blue', 0) > 0.9)
                if is_red and is_white_bg:
                    return cell.get('formattedValue', '') or ''
    return 'N/A'

@frappe.whitelist()
def fetch_sheet_raw_data(sheet_name="Sheet2"):
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('sheets', 'v4', credentials=creds)
        # We use spreadsheets().get with includeGridData=True to get formatting (colors, bold)
        # which is required by is_title_row and is_yellow_row_with_total logic.
        sheet = service.spreadsheets().get(
            spreadsheetId=SPREADSHEET_ID,
            ranges=[f"{sheet_name}!A1:Z100"],
            includeGridData=True
        ).execute()

        # Extract the row data which contains formatting information
        sheet_obj = sheet['sheets'][0]
        data = sheet_obj['data'][0].get('rowData', [])
        merges = sheet_obj.get('merges', [])
                    
        return {"rowData": data, "merges": merges}
    except Exception as api_err:
        frappe.log_error(f"Google Sheets API error: {api_err}", "Water Level Fetch")
        return {"rowData": [], "merges": []}

def compute_kpis_for_table(table_rows, config):
    if not table_rows or len(table_rows) < 2:
        return {"total_categories": 0}
    category_lower = clean_header(config['categoryCol'])
    header_idx = -1
    for idx, row in enumerate(table_rows):
        row_lower = [clean_display(cell).lower() for cell in row]
        # Improved: Search for the full category column name substring in any cell of the row
        if any(category_lower in cell for cell in row_lower):
            header_idx = idx
            break
    if header_idx == -1:
        frappe.log("KPIs: Category column not found in any row")
        return {"total_categories": 0}
    header = [clean_header(h) for h in table_rows[header_idx]]
    category_idx = next((i for i, h in enumerate(header) if category_lower in h), -1)
    if category_idx == -1:
        frappe.log("KPIs: Category index not found in header")
        return {"total_categories": 0}
    data_rows = table_rows[header_idx + 1:]
    total_categories = 0
    kpis = {"total_categories": 0}
    for col in config['kpiCols']:
        col_key = f"total_{col.replace(' ', '_').lower()}"
        kpis[col_key] = 0.0
    for row in data_rows:
        if len(row) <= category_idx:
            continue
        category = clean_display(row[category_idx])
        if not category or category.lower() == 'एकूण':
            continue
        total_categories += 1
        for col in config['kpiCols']:
            col_lower = clean_header(col)
            col_idx = next((i for i, h in enumerate(header) if col_lower in h), -1)
            if col_idx != -1 and col_idx < len(row):
                try:
                    val_str = clean_numeric(row[col_idx])
                    val = float(val_str) if val_str else 0.0
                    col_key = f"total_{col.replace(' ', '_').lower()}"
                    kpis[col_key] += val
                except ValueError:
                    frappe.log(f"Non-numeric value in KPI col '{col}': {row[col_idx]}")
                    pass
    kpis["total_categories"] = total_categories
    frappe.log(f"KPIs computed: {kpis}")
    return kpis

def compute_group_kpis(table_rows, config, group_type='district'):
    if not table_rows or len(table_rows) < 2:
        frappe.log(f"{group_type} KPIs: No table rows or <2 rows")
        return {}
    header = [clean_header(h) for h in table_rows[0]]
    frappe.log(f"{group_type} KPIs header (first 5): {header[:5]}") # Debug: Log header
    # Standardize count column name across types
    if group_type == 'district2':
        count_col_name = 'प्रकल्पांची संख्या' # Specific for Table 2
    else:
        count_col_name = config['kpiCols'][0] if config['kpiCols'] else 'प्रकल्प संख्या'
    count_lower = clean_header(count_col_name)
    count_col_idx = next((i for i, h in enumerate(header) if count_lower in h), -1)
    if count_col_idx == -1 and group_type == 'district2':
        # Fallback for Table 2: try alternative search or fixed index
        count_col_idx = next((i for i, h in enumerate(header) if 'प्रकल्प' in h), -1)
        if count_col_idx == -1:
            count_col_idx = 2 # Changed to index 2
        frappe.log(f"{group_type} KPIs - Fallback to fixed count_col_idx=2 for Table 2")
    frappe.log(f"{group_type} KPIs - Searching for count_col '{count_col_name}' (lower: '{count_lower}'), found idx: {count_col_idx}") # Debug: Log count col search
    if count_col_idx == -1 and group_type != 'district2':
        frappe.log(f"{group_type.capitalize()} KPIs: Count column '{count_col_name}' not found in header: {header[:3]}")
        return {}
    groups = ['सांगली जिल्हा', 'सातारा जिल्हा', 'सोलापूर जिल्हा'] # Default; can be made dynamic if needed
    kpis = {}
    data_rows = table_rows[1:]
    frappe.log(f"{group_type} KPIs - Processing {len(data_rows)} data rows") # Debug: Log row count
    current_group = None
    for idx, row in enumerate(data_rows):
        row_str = ' '.join([clean_display(cell) for cell in row if clean_display(cell)])
        frappe.log(f"{group_type} KPIs - Row {idx} row_str: '{row_str[:100]}...'") # Debug: Log sample row_str
        if any(clean_display(g) in row_str for g in groups):
            current_group = next((g for g in groups if clean_display(g) in row_str), None)
            frappe.log(f"{group_type} KPIs - Set current_group: {current_group}") # Debug: Log group detection
        if current_group and current_group not in kpis:
            kpis[current_group] = {col: 0.0 for col in config['districtCols']}
        elif current_group and ('एकूण' in row_str or 'total' in row_str.lower()):
            current_group = None
            frappe.log(f"{group_type} KPIs - Reset current_group due to total row") # Debug: Log total reset
            continue
        if current_group:
            # For district2, dynamically find the numeric value in the row
            if group_type == 'district2':
                val = 0.0
                # For district2, specifically use index 2 (column C) for the count value
                if len(row) > 2:
                    try:
                        val_str = clean_numeric(row[2])
                        val = float(val_str) if val_str else 0.0
                    except ValueError:
                        val = 0.0
                # Match row to districtCols keywords
                for col in config['districtCols']:
                    if clean_display(col) in row_str:
                        frappe.log(f"{group_type} KPIs - Matching col '{col}' in row_str for group {current_group}") # Debug: Log col match
                        kpis[current_group][col] = val
                        frappe.log(f"{group_type} KPIs - Set {current_group}[{col}] = {val}") # Debug: Log value set
                        break
            else:
                # Original logic for other tables
                for col in config['districtCols']:
                    if clean_display(col) in row_str:
                        frappe.log(f"{group_type} KPIs - Matching col '{col}' in row_str for group {current_group}") # Debug: Log col match
                        if len(row) > count_col_idx:
                            try:
                                val_str = clean_numeric(row[count_col_idx])
                                val = float(val_str) if val_str else 0.0
                                kpis[current_group][col] = val
                                frappe.log(f"{group_type} KPIs - Set {current_group}[{col}] = {val}") # Debug: Log value set
                            except ValueError:
                                frappe.log(f"Non-numeric value in group KPI '{col}': {row[count_col_idx]}")
                            break
    # Compute totals
    for grp in kpis:
        kpis[grp]['Total'] = sum(kpis[grp].values())
    frappe.log(f"{group_type.capitalize()} KPIs computed: {kpis}")
    return kpis

def compute_group_pcts(table_rows, config):
    if not table_rows or len(table_rows) < 2:
        return {}
    header = [clean_header(h) for h in table_rows[0]]
    frappe.log(f"Group Pcts header: {' | '.join(header)}")
    # Find current and prev pct col indices with improved matching
    current_pct_term = clean_header(config['pctCol'])
    current_pct_idx = next((i for i, h in enumerate(header) if current_pct_term in h), -1)
    if current_pct_idx == -1:
        # Fallback matching for current pct
        current_pct_idx = next((i for i, h in enumerate(header) if 'उपयुक्त'.lower() in h and 'टक्केवारी'.lower() in h), -1)
    prev_pct_term = clean_header(config['secondPctCol'])
    prev_pct_idx = next((i for i, h in enumerate(header) if prev_pct_term in h), -1)
    if prev_pct_idx == -1:
        # Fallback matching for prev pct - changed to 'मागील' based on sheet
        prev_pct_idx = next((i for i, h in enumerate(header) if 'मागील'.lower() in h and 'टक्केवारी'.lower() in h), -1)
    frappe.log(f"Group Pcts - current_pct_idx: {current_pct_idx} ({header[current_pct_idx] if current_pct_idx != -1 else 'N/A'}), prev_pct_idx: {prev_pct_idx} ({header[prev_pct_idx] if prev_pct_idx != -1 else 'N/A'})")
    if current_pct_idx == -1:
        frappe.log(f"Group Pcts: Current pct column '{config['pctCol']}' not found in header: {header[:5]}")
        return {}
    if prev_pct_idx == -1:
        frappe.log(f"Group Pcts: Prev pct column '{config['secondPctCol']}' not found in header: {header[:5]}")
        return {}
    groups = ['सांगली जिल्हा', 'सातारा जिल्हा', 'सोलापूर जिल्हा']
    pcts = {}
    data_rows = table_rows[1:]
    current_group = None
    for row in data_rows:
        row_str = ' '.join([clean_display(cell) for cell in row if clean_display(cell)])
        if any(clean_display(g) in row_str for g in groups):
            current_group = next(g for g in groups if clean_display(g) in row_str)
            if current_group not in pcts:
                pcts[current_group] = {}
        elif current_group and ('एकूण' in row_str or 'total' in row_str.lower()):
            current_group = None
            continue
        if current_group:
            for col in config['districtCols']:
                if clean_display(col) in row_str:
                    try:
                        # Current pct
                        current_pct_str = clean_numeric(row[current_pct_idx])
                        current_pct_str = current_pct_str.replace('%', '').replace('(', '').replace(')', '')
                        current_val = float(current_pct_str) if current_pct_str else 0.0
                        pcts[current_group][f"{col.replace(' ', '_')}_current_pct"] = current_val
                        # Prev pct
                        prev_pct_str = clean_numeric(row[prev_pct_idx])
                        prev_pct_str = prev_pct_str.replace('%', '').replace('(', '').replace(')', '')
                        prev_val = float(prev_pct_str) if prev_pct_str else 0.0
                        pcts[current_group][f"{col.replace(' ', '_')}_prev_pct"] = prev_val
                    except ValueError:
                        frappe.log(f"Non-numeric pct value for '{col}': current={row[current_pct_idx] if len(row)>current_pct_idx else 'N/A'}, prev={row[prev_pct_idx] if len(row)>prev_pct_idx else 'N/A'}")
                    break
    # Compute average totals for district level double chart
    for grp in pcts:
        current_pcts_list = [pcts[grp][f"{col.replace(' ', '_')}_current_pct"] for col in config['districtCols'] if f"{col.replace(' ', '_')}_current_pct" in pcts[grp]]
        pcts[grp]['total_current_pct'] = sum(current_pcts_list) / len(current_pcts_list) if current_pcts_list else 0.0
        prev_pcts_list = [pcts[grp][f"{col.replace(' ', '_')}_prev_pct"] for col in config['districtCols'] if f"{col.replace(' ', '_')}_prev_pct" in pcts[grp]]
        pcts[grp]['total_prev_pct'] = sum(prev_pcts_list) / len(prev_pcts_list) if prev_pcts_list else 0.0
    frappe.log(f"Group Pcts computed: {pcts}")
    return pcts

def extract_chart_data(table_rows, config, table_num=1):
    if not table_rows or len(table_rows) < 2:
        return {"categories": [], "values": {}}
    # Find header row dynamically: the one containing the category column name
    category_lower = clean_header(config['categoryCol'])
    header_idx = -1
    for idx, row in enumerate(table_rows):
        row_lower = [clean_display(cell).lower() for cell in row]
        # Improved: Search for the full category column name substring in any cell of the row
        if any(category_lower in cell for cell in row_lower):
            header_idx = idx
            break
    if header_idx == -1:
        frappe.log(f"Chart data Table {table_num}: Category column not found")
        return {"categories": [], "values": {}}
    header = [clean_display(h) for h in table_rows[header_idx]] # Use clean_display, keep original case for logging
    frappe.log(f"Chart data Table {table_num} header: {' | '.join(header[:5])}...")
    # Category index with substring match on config column name
    category_idx = next((i for i, h in enumerate(header) if category_lower in clean_header(h)), -1)
    if category_idx == -1:
        frappe.log(f"Chart data Table {table_num}: Category index not found")
        return {"categories": [], "values": {}}
    cols_to_extract = config['kpiCols'] + ([config['pctCol']] if config.get('pctCol') else []) + ([config.get('secondPctCol')] if config.get('secondPctCol') else [])
    values = {f"{col.replace(' ', '_').lower()}": [] for col in cols_to_extract}
    data_rows = table_rows[header_idx + 1:]
    categories = []
    storage_values = []
    storage_col = config.get('storageCol', '')
    # Improved storage search: remove 'एकूण' for matching
    storage_search = clean_header(storage_col).replace('एकूण', '').strip() if storage_col else ''
    storage_idx = next((i for i, h in enumerate(header) if storage_search in clean_header(h)), -1) if storage_col else -1
    # Precompute column indices for efficiency and logging
    col_indices = {}
    for col in cols_to_extract:
        col_clean = clean_header(col)
        col_idx = next((i for i, h in enumerate(header) if col_clean in clean_header(h)), -1)
        if col_idx == -1 and col in [config.get('pctCol'), config.get('secondPctCol')]:
            if col == config['pctCol']:
                col_idx = next((i for i, h in enumerate(header) if 'उपयुक्त'.lower() in clean_header(h) and 'टक्केवारी'.lower() in clean_header(h)), -1)
            elif col == config['secondPctCol']:
                # Changed fallback to 'मागील' based on sheet
                col_idx = next((i for i, h in enumerate(header) if 'मागील'.lower() in clean_header(h) and 'टक्केवारी'.lower() in clean_header(h)), -1)
        col_indices[col] = col_idx
        if col in [config.get('pctCol'), config.get('secondPctCol')]:
            header_text = header[col_idx] if col_idx != -1 else 'Not found'
            frappe.log(f"Chart data Table {table_num} - Col '{col}' (key: {col.replace(' ', '_').lower()}) matched to idx {col_idx}, header: '{header_text}'")
    # Extract data in a single loop
    for row in data_rows:
        if len(row) <= category_idx:
            continue
        category = clean_display(row[category_idx])
        if not category or category.lower() == 'एकूण':
            continue
        categories.append(category)
        # Extract values for each column
        for col in cols_to_extract:
            col_idx = col_indices[col]
            if col_idx != -1 and col_idx < len(row):
                try:
                    val_str = clean_numeric(row[col_idx])
                    if col in [config.get('pctCol'), config.get('secondPctCol')]:
                        val_str = val_str.replace('%', '').replace('(', '').replace(')', '')
                    val = float(val_str) if val_str else 0.0
                except ValueError:
                    frappe.log(f"Non-numeric chart value for '{col}' in Table {table_num}: {row[col_idx]}")
                    val = 0.0
            else:
                val = 0.0
            values[f"{col.replace(' ', '_').lower()}"].append(val)
        # Compute storage value
        if storage_idx != -1 and storage_idx < len(row):
            try:
                val_str = clean_numeric(row[storage_idx])
                storage_val = float(val_str) if val_str else 0.0
            except ValueError:
                storage_val = 0.0
        else:
            storage_val = 0.0
        storage_values.append(storage_val)
    # Compute storage percentage if storageCol is provided
    total_storage = 0.0
    if storage_col and storage_values and len(storage_values) > 0:
        total_storage = sum(storage_values)
        storage_pct = [(v / total_storage * 100) if total_storage > 0 else 0 for v in storage_values]
        storage_pct_key = f"{storage_col.replace(' ', '_').lower()}_pct"
        values[storage_pct_key] = storage_pct
    frappe.log(f"Storage % computed for Table {table_num}: total={total_storage}, categories={len(categories)}")
    frappe.log(f"Chart data Table {table_num} extracted: {len(categories)} categories")
    frappe.log(f"Values keys: {list(values.keys())}, lengths: {[len(v) for v in values.values()]}")
    # Log sample values for pct columns
    pct_key = config['pctCol'].replace(' ', '_').lower()
    second_key = config['secondPctCol'].replace(' ', '_').lower()
    if pct_key in values:
        frappe.log(f"Sample pct values (first 3): {values[pct_key][:3]}")
    if second_key in values:
        frappe.log(f"Sample second pct values (first 3): {values[second_key][:3]}")
    return {"categories": categories, "values": values}

def extract_tables(sheet_data_obj):
    sheet_data = sheet_data_obj.get('rowData', [])
    merges = sheet_data_obj.get('merges', [])
    tables = []
    i = 0
    
    # Strategy 1: Title Row Based (Black Bg, White Text)
    while i < len(sheet_data):
        while i < len(sheet_data) and not is_title_row(sheet_data[i]):
            i += 1
        if i >= len(sheet_data):
            break
            
        title_row = sheet_data[i]
        title = get_title_value(title_row)
        i += 1
        
        while i < len(sheet_data) and is_empty_row(sheet_data[i]):
            i += 1
            
        header = None
        if i < len(sheet_data):
            header_row = sheet_data[i]
            header = [cell.get('formattedValue', '') or '' for cell in header_row.get('values', [])]
            i += 1
            
        if header:
            table_rows = [header]
            table_start = i - 1 # i was advanced after header
            while i < len(sheet_data):
                row = sheet_data[i]
                if is_title_row(row) or is_yellow_row_with_total(row):
                    if is_yellow_row_with_total(row):
                        table_rows.append([cell.get('formattedValue', '') or '' for cell in row.get('values', [])])
                        i += 1
                    break
                row_data = [cell.get('formattedValue', '') or '' for cell in row.get('values', [])]
                if any(row_data):
                    table_rows.append(row_data)
                i += 1
            
            # Trim trailing empties for Strategy 1
            max_cols = 0
            for r in table_rows:
                for idx, val in enumerate(r):
                    if str(val).strip(): max_cols = max(max_cols, idx + 1)
            table_rows = [r[:max_cols] for r in table_rows]
            
            tables.append({'title': title, 'rows': table_rows, 'start_row_index': table_start})

    # Strategy 2: If no tables found or some parts missed, try Content-Based (Sr. No.)
    if not tables:
        frappe.log("No formatting-based tables found. Trying content-based search (Sr. No.).")
        i = 3 # Skip report title rows (1-3)
        while i < len(sheet_data):
            row_vals = [str(cell.get('formattedValue', '') or '').strip().lower().replace('\n', ' ') for cell in sheet_data[i].get('values', [])]
            
            # Look for Row containing "Sr. No." or "अ.क्र."
            is_header = any(('sr.' in v and ('no.' in v or 'no' in v)) or ('अ' in v and 'क्र' in v) for v in row_vals)
            
            if is_header:
                start_of_header = i
                table_headers = []
                
                # Expand to find up to 3 rows of headers
                header_i = i
                while header_i < len(sheet_data) and header_i < i + 3:
                    row_data = [cell.get('formattedValue', '') or '' for cell in sheet_data[header_i].get('values', [])]
                    # Check if this row is already data (e.g. SR 1)
                    if header_i > i:
                        val0 = str(row_data[0]).strip()
                        if val0 and val0.isdigit():
                            break
                    table_headers.append(row_data)
                    header_i += 1
                
                i = header_i # Update data starting point
                
                table_rows = []
                # Collect data until we hit a clear break (2+ empty rows or next header)
                empty_count = 0
                while i < len(sheet_data):
                    row_data = [cell.get('formattedValue', '') or '' for cell in sheet_data[i].get('values', [])]
                    if not any(row_data):
                        empty_count += 1
                        if empty_count >= 2: break
                    else:
                        empty_count = 0
                        # Check if this row is another header
                        if any('sr.' in str(v).lower() and ('no.' in str(v).lower()) for v in row_data):
                            break
                        table_rows.append(row_data)
                    i += 1
                
                # Trim trailing empty columns from headers and rows
                max_cols = 0
                for r in table_headers:
                    for idx, val in enumerate(r):
                        if str(val).strip(): max_cols = max(max_cols, idx + 1)
                for r in table_rows:
                    for idx, val in enumerate(r):
                        if str(val).strip(): max_cols = max(max_cols, idx + 1)
                
                table_headers = [r[:max_cols] for r in table_headers]
                table_rows = [r[:max_cols] for r in table_rows]
                
                tables.append({
                    'title': f"Table {len(tables)+1}", 
                    'headers': table_headers, # Multi-level headers
                    'rows': table_rows,
                    'start_row_index': start_of_header # 0-based index in sheet
                })
            else:
                i += 1

    if not tables:
        frappe.log("Fallback to raw rows.")
        raw_rows = [[cell.get('formattedValue', '') or '' for cell in row['values']] for row in sheet_data if 'values' in row]
        tables = [{'title': 'Raw Data', 'headers': [raw_rows[0]] if raw_rows else [], 'rows': raw_rows[1:] if len(raw_rows)>1 else []}]
        
    return tables


@frappe.whitelist(allow_guest=True)
def run_test_py(config=None, sheet_name=None):
    try:
        # Parse config from request (default if none)
        default_config = {
            'categoryCol': 'तालुक्याचे नांव',
            'kpiCols': ['प्रकल्प संख्या'],
            'districtCols': ['मध्यम प्रकल्प', 'लघु प्रकल्प'],
            'pctCol': 'उपयुक्त साठा (द.ल.घ.फू.) टक्केवारी %',
            'secondPctCol': 'गतवर्षीच्या याच दिनांकाची टक्केवारी %',
            'storageCol': 'आजचा साठा एकूण'
        }
        if config:
            if isinstance(config, str):
                config = json.loads(config)
            # Validate config keys to prevent injection
            allowed_keys = list(default_config.keys())
            config = {k: v for k, v in config.items() if k in allowed_keys}
            default_config.update(config or {})
        config = default_config
        frappe.log(f"Using config: {config}")
        
        # Determine which sheet to fetch from
        target_sheet = sheet_name or "Sheet2"
        sheet_data_obj = fetch_sheet_raw_data(sheet_name=target_sheet)
        sheet_data = sheet_data_obj.get('rowData', [])
        frappe.log(f"Sheet data rows: {len(sheet_data)}") # Debug: Log sheet rows
        tables = extract_tables(sheet_data_obj)
        frappe.log(f"Extracted tables: {len(tables)}") # Debug log
        # Adjusting the sample logs to handle the new return structure
        if tables:
            first_table_rows = tables[0].get('rows', [])
            frappe.log(f"Table 1 rows sample: {first_table_rows[:2] if first_table_rows else 'No rows'}")
        
        date = find_date_with_red_text(sheet_data)
        # Compute KPIs with config. Note: Adjusting tables[0]['rows'] for Strategy 1 structure
        table1_data = tables[0].get('rows', []) if tables else []
        # If Strategy 1 was used, the header is inside 'rows'. If Strategy 2 was used, 'headers' is separate.
        # To maintain compatibility for compute functions, we'll prefix headers if separate.
        if tables and 'headers' in tables[0]:
            table1_full = tables[0]['headers'] + tables[0]['rows']
            table2_full = (tables[1]['headers'] + tables[1]['rows']) if len(tables) >= 2 else []
        else:
            table1_full = table1_data
            table2_full = tables[1].get('rows', []) if len(tables) >= 2 else []

        kpis = compute_kpis_for_table(table1_full, config) if tables else {"total_categories": 0}
        kpis_table1_districts = compute_group_kpis(table1_full, config, 'district1') if tables else {}
        kpis_table2 = compute_group_kpis(table2_full, config, 'district2') if len(tables) >= 2 else {}
        
        storage_pct = compute_group_pcts(table2_full, config) if len(tables) >= 2 else {}
        # Extract chart data with config
        chart_data = extract_chart_data(table1_full, config, 1) if tables else {"categories": [], "values": {}}
        chart_data2 = extract_chart_data(table2_full, config, 2) if len(tables) >= 2 else {"categories": [], "values": {}}
        return {
            "status": "ok",
            "message": {
                "tables": tables,
                "kpis": kpis,
                "kpis_table1_districts": kpis_table1_districts,
                "kpis_table2": kpis_table2,
                "date": date,
                "chart_data": chart_data,
                "chart_data2": chart_data2,
                "storage_pct": storage_pct
            }
        }
    except Exception as e:
        frappe.log(f"Error in run_test_py: {frappe.get_traceback()}", level="error")
        return {"status": "fail", "message": str(e)}

@frappe.whitelist(allow_guest=True)
def get_general_sheet_data(sheet_name="Flood Info"):
    """
    Generic function to fetch and extract tables from any sheet tab.
    Used for Flood Info and other dynamic pages.
    """
    try:
        sheet_data_obj = fetch_sheet_raw_data(sheet_name=sheet_name)
        sheet_data = sheet_data_obj.get('rowData', [])
        if not sheet_data:
            return {"status": "fail", "message": f"No data found in sheet '{sheet_name}'"}
            
        tables = extract_tables(sheet_data_obj)
        
        # Extract report header (first few rows before any table)
        report_header = []
        if len(sheet_data) >= 4:
            max_h_cols = 0
            temp_rows = []
            for i in range(4):
                row_cells = [cell.get('formattedValue', '') or '' for cell in sheet_data[i].get('values', [])]
                if any(row_cells):
                    temp_rows.append(row_cells)
                    for idx, val in enumerate(row_cells):
                        if str(val).strip(): max_h_cols = max(max_h_cols, idx + 1)
            
            # Trim header rows to match data width or at least remove trailing blanks
            for r in temp_rows:
                report_header.append(r[:max_h_cols])
        
        date = find_date_with_red_text(sheet_data)
        
        return {
            "status": "ok",
            "message": {
                "tables": tables,
                "date": date,
                "report_header": report_header,
                "merges": sheet_data_obj.get('merges', [])
            }
        }
    except Exception as e:
        frappe.log(f"Error in get_general_sheet_data: {frappe.get_traceback()}", level="error")
        return {"status": "fail", "message": str(e)}

@frappe.whitelist(allow_guest=True)
def get_visitor_stats(is_unique=False):
    """
    Returns visitor statistics. If is_unique is True, increments the counts.
    Uses direct SQL to bypass all Frappe caching mechanisms.
    """
    today = nowdate()
    if isinstance(is_unique, str):
        is_unique = is_unique.lower() == 'true'
    
    # helper to get global value via direct SQL
    def get_val(key):
        res = frappe.db.sql("SELECT defvalue FROM `tabDefaultValue` WHERE defkey=%s AND parent='__global' LIMIT 1", (key,))
        return res[0][0] if res else None

    # helper to set global value via direct SQL
    def set_val(key, val):
        if get_val(key) is not None:
            frappe.db.sql("UPDATE `tabDefaultValue` SET defvalue=%s WHERE defkey=%s AND parent='__global'", (str(val), key))
        else:
            # Create if missing
            from frappe.model.naming import make_autoname
            name = make_autoname('DefaultValue', 'hash')
            frappe.db.sql("""INSERT INTO `tabDefaultValue` (name, defkey, defvalue, parent, parenttype, parentfield) 
                             VALUES (%s, %s, %s, '__global', 'Control Panel', 'system_defaults')""", (name, key, str(val)))

    # Get values directly from DB
    total_visitors = int(get_val('total_visitors') or 0)
    today_visitors = int(get_val('today_visitors') or 0)
    last_visitor_date = get_val('last_visitor_date')
    
    # Reset today's count if it's a new day
    if last_visitor_date != today:
        today_visitors = 0
        set_val('last_visitor_date', today)
        set_val('today_visitors', 0)
        frappe.db.commit()
    
    if is_unique:
        total_visitors += 1
        today_visitors += 1
        set_val('total_visitors', total_visitors)
        set_val('today_visitors', today_visitors)
        frappe.db.commit()
        # Force clear the specific defaults cache as a safety measure
        frappe.cache().delete_value("defaults")
    
    return {
        "total_visitors": total_visitors,
        "today_visitors": today_visitors,
        "review_date": today
    }
