import frappe
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

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
        data = sheet['sheets'][0]['data'][0].get('rowData', [])
        
        # Debug: Print the raw data around row 46 for verification
        for i, row in enumerate(data):
            if i >= 44 and i <= 47:  # Rows 45-48
                cells = row.get('values', [])
                first_cell = cells[0].get('formattedValue', '') if cells else ''
                print(f"DEBUG Row {i+1}: {first_cell}")
                    
        return data
    except Exception as api_err:
        frappe.log_error(f"Google Sheets API error: {api_err}", "Water Level Fetch")
        # Do not raise; return empty to allow graceful fail
        return []

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

def extract_tables(sheet_data):
    tables = []
    i = 0
    table_num = 1
    while i < len(sheet_data) and table_num <= 2: # Limit to 2 tables
        while i < len(sheet_data) and not is_title_row(sheet_data[i]):
            i += 1
        if i >= len(sheet_data):
            break
        title_row = sheet_data[i]
        title = get_title_value(title_row)
        frappe.log(f"Found title for Table {table_num} at row {i}: {title}")
        i += 1 # Skip title row
        while i < len(sheet_data) and is_empty_row(sheet_data[i]):
            i += 1
        # Find header as first non-empty row (more robust than bold)
        header = None
        while i < len(sheet_data) and header is None:
            if not is_empty_row(sheet_data[i]):
                header_row = sheet_data[i]
                header = [cell.get('formattedValue', '') or '' for cell in header_row['values']]
                frappe.log(f"Found header for Table {table_num} at row {i}: {header[:3]}...")
                i += 1
            else:
                i += 1
        if header is None:
            frappe.log(f"No header found after title for Table {table_num}")
            continue
        # Collect data rows until yellow total
        table_rows = [header] # Include header as first row
        while i < len(sheet_data):
            row = sheet_data[i]
            if is_yellow_row_with_total(row):
                total_row = [cell.get('formattedValue', '') or '' for cell in row['values']]
                table_rows.append(total_row)
                frappe.log(f"Found total row for Table {table_num} at row {i}, ending table")
                break
            row_data = [cell.get('formattedValue', '') or '' for cell in row['values']]
            if any(row_data): # Add non-empty rows
                table_rows.append(row_data)
            i += 1
        tables.append({
            'title': title,
            'rows': table_rows
        })
        frappe.log(f"Table {table_num}: {len(table_rows)} rows")
        table_num += 1
        i += 1 # Skip to next potential table
    if len(tables) == 0:
        frappe.log("No tables detected - falling back to raw rows split")
        # Fallback: split raw rows into two dummy tables
        raw_rows = [[cell.get('formattedValue', '') or '' for cell in row['values']] for row in sheet_data if 'values' in row]
        mid_point = len(raw_rows) // 2
        tables = [
            {'title': 'Table 1 (Fallback)', 'rows': raw_rows[:mid_point]},
            {'title': 'Table 2 (Fallback)', 'rows': raw_rows[mid_point:]}
        ]
    # Add title to check if using fallback
    for table in tables:
        if 'Fallback' in table['title']:
            print(f"DEBUG: Using fallback table: {table['title']}")
    return tables

@frappe.whitelist(allow_guest=True)
def run_test_py(config=None):
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
        sheet_data = fetch_sheet_raw_data()
        frappe.log(f"Sheet data rows: {len(sheet_data)}") # Debug: Log sheet rows
        tables = extract_tables(sheet_data)
        frappe.log(f"Extracted tables: {len(tables)}") # Debug log
        frappe.log(f"Table 1 rows sample: {tables[0]['rows'][:2] if tables else 'No tables'}") # Debug: Log Table 1 sample
        frappe.log(f"Table 2 rows sample: {tables[1]['rows'][:2] if len(tables) >= 2 else 'No Table 2'}") # Debug: Log Table 2 sample
        date = find_date_with_red_text(sheet_data)
        # Compute KPIs with config
        kpis = compute_kpis_for_table(tables[0]['rows'], config) if tables else {"total_categories": 0}
        kpis_table1_districts = compute_group_kpis(tables[0]['rows'], config, 'district1') if tables else {}
        kpis_table2 = compute_group_kpis(tables[1]['rows'], config, 'district2') if len(tables) >= 2 else {}
        frappe.log(f"kpis_table2 computed: {kpis_table2}") # Debug: Log final kpis_table2
        storage_pct = compute_group_pcts(tables[1]['rows'], config) if len(tables) >= 2 else {}
        # Extract chart data with config
        chart_data = extract_chart_data(tables[0]['rows'], config, 1) if tables else {"categories": [], "values": {}}
        chart_data2 = extract_chart_data(tables[1]['rows'], config, 2) if len(tables) >= 2 else {"categories": [], "values": {}}
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