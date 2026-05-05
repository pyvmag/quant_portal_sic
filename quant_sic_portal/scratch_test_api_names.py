import frappe

def test_api_names():
    names = [
        "quant_sic_portal.api.get_general_sheet_data",
        "sicsangli.api.get_general_sheet_data"
    ]
    for name in names:
        try:
            print(f"Testing {name}...")
            # Try to resolve the method
            frappe.get_attr(name)
            print(f"SUCCESS: {name} found.")
        except Exception as e:
            print(f"FAILED: {name} - {e}")

if __name__ == "__main__":
    test_api_names()
