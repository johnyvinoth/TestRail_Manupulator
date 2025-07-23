"""
This script retrieves specified TestRail test cases from a given Test Run
and displays their details in a formatted table. It handles TestRail API
authentication, processes TestRail IDs (removing 'C' prefix),
maps numerical status codes to human-readable labels, and identifies
any requested test cases that were not found in the API response.
"""

import requests
import json
import base64
import warnings

from requests.packages.urllib3.exceptions import InsecureRequestWarning

warnings.filterwarnings("ignore", category=InsecureRequestWarning)

# --- Configuration Variables ---
TESTRALL_API_URL = "https://testrail.j2noc.com/"
PROJECT_ID = 26
SUITE_ID = 241
SECTION_ID = 8498
RUN_ID = 24822
RAW_CASE_IDS_STRING = ("C89683,C116612,C89682,C89622") # Updated example IDs
USERNAME = "qaautomation@consensus.com"
API_KEY = "testrail"

# --- Mapping Dictionaries (Hardcoded for simplicity, could be fetched via API as well) ---
automation_status_map = {
    1: 'Pending',
    2: 'In Progress',
    3: 'In Review',
    4: 'Rejected',
    5: 'Automated'
}

priority_id_map = {
    1: 'P4',
    2: 'P3',
    3: 'P2',
    4: 'P1'
}

# --- API Endpoint Comments (Retained as per request) ---
# api_endpoint = f"{TESTRALL_API_URL}index.php?/api/v2/get_cases/{PROJECT_ID}&suite_id={SUITE_ID}&case_ids={case_ids_str}"
# api_endpoint = f"{TESTRALL_API_URL}index.php?/api/v2/get_cases/{PROJECT_ID}&suite_id={SUITE_ID}" # To get all the test cases in a TestSuite using the Suite ID, but its fetching only 99 records due to Testrail limation
# if we need records beyond fetched records in that suite, need to find a workaround.


# ==============================================================================
# --- Reusable Functions ---
# ==============================================================================

def get_api_headers(username: str, api_key: str) -> dict:
    """
    Generates the necessary HTTP headers for TestRail API authentication.
    """
    credentials = f"{username}:{api_key}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    return {
        "Content-Type": "application/json",
        "Authorization": f"Basic {encoded_credentials}"
    }

def process_raw_case_ids(raw_ids_string: str) -> set[int]:
    """
    Parses a comma-separated string of TestRail IDs, removes 'C' prefixes,
    and returns a set of integer IDs for efficient lookup.
    """
    individual_raw_ids = [id.strip() for id in raw_ids_string.split(',')]
    return set(int(id[1:]) if id.startswith('C') else int(id) for id in individual_raw_ids)

def fetch_testrail_data(url: str, headers: dict) -> dict | None:
    """
    Fetches data from the specified TestRail API endpoint.
    Handles HTTP errors and JSON decoding errors.
    """
    try:
        response = requests.get(url, headers=headers, verify=False)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"An HTTP error occurred during API fetch: {e}")
        if response is not None:
            print(f"Response status code: {response.status_code}")
            print(f"Response content: {response.text}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response from API: {e}")
        if response is not None:
            print(f"Non-JSON response content: {response.text}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during API fetch: {e}")
        return None

def prepare_table_data(
    api_response_tests: list[dict],
    requested_case_ids: set[int],
    automation_map: dict,
    priority_map: dict
) -> tuple[list[dict], set[int]]:
    """
    Filters API response data, maps numerical IDs to display values,
    and prepares a list of dictionaries suitable for table printing.
    Also returns a set of found case IDs.
    """
    table_rows = []
    found_case_ids = set()

    for test_data in api_response_tests:
        # Check if the item is a dict and its case_id is in our requested set
        if isinstance(test_data, dict) and test_data.get("case_id") in requested_case_ids:
            found_case_ids.add(test_data["case_id"]) # Add to found set

            # Map automation status
            automation_status_id = test_data.get('custom_tc_automation_status')
            automation_status_display = automation_map.get(automation_status_id, str(automation_status_id))

            # Map priority
            priority_id = test_data.get('priority_id')
            priority_display = priority_map.get(priority_id, str(priority_id))

            # Handle review comments (already string or "None")
            review_comments_value = test_data.get('custom_tc_reviewcomments')
            review_comments_display = str(review_comments_value if review_comments_value is not None else "None")

            table_rows.append({
                "ID": str(test_data.get('case_id', 'N/A')),
                "Priority": priority_display,
                "Automation Status": automation_status_display,
                "Review Comments": review_comments_display,
                "Title": str(test_data.get('title', 'N/A')),
            })
    return table_rows, found_case_ids

def print_formatted_table(table_data: list[dict]):
    """
    Prints a list of dictionaries as a neatly formatted table.
    """
    if not table_data:
        print("No data to display in the table.")
        return

    # Determine dynamic column widths
    column_widths = {
        "ID": max(len(str(row["ID"])) for row in table_data),
        "Priority": max(len(str(row["Priority"])) for row in table_data),
        "Automation Status": max(len(str(row["Automation Status"])) for row in table_data),
        "Review Comments": max(len(str(row["Review Comments"])) for row in table_data),
        "Title": max(len(str(row["Title"])) for row in table_data)
    }

    # Ensure header width is accommodated
    for col_name in column_widths:
        column_widths[col_name] = max(column_widths[col_name], len(col_name))

    # Construct header format string
    header_order = ["ID", "Priority", "Automation Status", "Review Comments", "Title"]
    header_format_parts = [f"{{:<{column_widths[col_name]}}}" for col_name in header_order]
    header_format = " | ".join(header_format_parts)

    # Print header
    print(f"Found {len(table_data)} cases matching your criteria.")
    print(header_format.format(*header_order))

    # Print separator line
    total_width = sum(column_widths.values()) + (len(header_order) - 1) * 3 # N columns, N-1 separators
    print("-" * total_width)

    # Print rows
    for row in table_data:
        print(header_format.format(
            row["ID"],
            row["Priority"],
            row["Automation Status"],
            row["Review Comments"],
            row["Title"]
        ))

def print_unmatched_ids(requested_ids: set[int], found_ids: set[int], run_id: int):
    """
    Prints a list of requested case IDs that were not found in the API response.
    """
    unmatched_case_ids = requested_ids - found_ids
    if unmatched_case_ids:
        print("\n--- Unmatched Case IDs ---")
        print(f"The following requested TestRail Case IDs were not found in Run {run_id}:")
        print(f"{sorted(list(unmatched_case_ids))}")
    else:
        print("\nAll requested TestRail Case IDs were found in the API response.")

# ==============================================================================
# --- Main Script Execution ---
# ==============================================================================

if __name__ == "__main__":
    # 1. Prepare API Headers
    api_headers = get_api_headers(USERNAME, API_KEY)

    # 2. Process Raw Case IDs String
    requested_case_ids_set = process_raw_case_ids(RAW_CASE_IDS_STRING)

    # 3. Define API Endpoint for Test Run
    current_api_endpoint = f"{TESTRALL_API_URL}index.php?/api/v2/get_tests/{RUN_ID}"

    # 4. Fetch TestRail Data
    cases_data_response = fetch_testrail_data(current_api_endpoint, api_headers)

    if cases_data_response and 'tests' in cases_data_response and isinstance(cases_data_response['tests'], list):
        # 5. Filter and Prepare Table Data
        # Note: SECTION_ID filtering is currently NOT applied here directly,
        # as the original problem indicated get_tests doesn't have a direct section_id filter.
        # If section_id filtering is crucial and cases can span multiple sections in the run,
        # you'd need to add 'and case.get("section_id") == SECTION_ID' in prepare_table_data
        # as a secondary filter.
        table_rows_data, found_ids_in_response = prepare_table_data(
            cases_data_response['tests'],
            requested_case_ids_set,
            automation_status_map,
            priority_id_map
        )

        # 6. Print Formatted Table
        print_formatted_table(table_rows_data)

        # 7. Print Unmatched IDs
        print_unmatched_ids(requested_case_ids_set, found_ids_in_response, RUN_ID)

    else:
        print("Initial API response did not contain a valid list of 'tests' or was empty.")
        # If fetch_testrail_data already printed error, no need to duplicate here
        # but could add more specific checks if cases_data_response is None or malformed.
# test