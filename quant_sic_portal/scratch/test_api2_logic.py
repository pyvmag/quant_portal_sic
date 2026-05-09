
import sys
import os
import json

# Add the project directory to sys.path to import our module
sys.path.append("/home/erpadmin/bench-jalsampada-portal/apps/quant_sic_portal")

# Mock frappe BEFORE any other imports
class MockFrappe:
    def whitelist(self, **kwargs):
        def decorator(f):
            return f
        return decorator
    def log(self, msg):
        print(f"LOG: {msg}")
    def throw(self, msg):
        raise Exception(msg)

mock_frappe = MockFrappe()
sys.modules['frappe'] = mock_frappe

from quant_sic_portal.api2 import run_test_py_demo

def test():
    result = run_test_py_demo()
    # Filter out big data for readability
    if "message" in result:
        for table in result["message"]:
            if "rows" in table:
                print(f"Table: {table.get('title')}")
                print(f"Number of rows: {len(table['rows'])}")
                print(f"Totals: {table.get('totals') is not None}")
                if table.get('totals'):
                    print(f"Totals Data: {[c.get('value') for c in table['totals']]}")
    else:
        print(json.dumps(result, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test()
