import time
from datetime import datetime
import requests
# from requests.packages.urllib3.exceptions import InsecureRequestWarning

from atlassian import Confluence
import matplotlib.pyplot as plt
from urllib3.exceptions import InsecureRequestWarning

import testrail

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
# TestRail API credentials
TESTRAIL_API_URL = "http://testrail.j2noc.com/"
TESTRAIL_USERNAME = "qaautomation@consensus.com"
TESTRAIL_PASSWORD = "testrail"
TESTRAIL_API_KEY = "JSde97eZq0BwULvavOjQ-QboLXzwqyynzgHvuD1Z."

# Confluence API credentials
CONFLUENCE_API_URL = "https://yourconfluenceurl.com"
CONFLUENCE_USERNAME = "vinoth.xavier@consensus.com"
CONFLUENCE_API_KEY = "your_api_key"
CONFLUENCE_SPACE_KEY = "your_space_key"
CONFLUENCE_PAGE_TITLE = "Automated Test Report"

TESTRAIL = testrail.APIClient(TESTRAIL_API_URL)
TESTRAIL.password=TESTRAIL_API_KEY
TESTRAIL.user=TESTRAIL_USERNAME

ROJECT_ID = "P1"  # Integer ID of target project

# Filters to be applied when using 'get_runs' and 'get_plans'
# The suite_id value is used for projects which have multiple suites enabled
# Value should be set to None if filter will not be applied
# offset is not included here since it is handled elsewhere
# created_before and created_after are handled in the next code block
FILTERS = {'suite_id': "S7",  # This is REQUIRED if your project is running in multi-suite mode
           'created_by': None,  # Integer ID of user
           'is_completed': None,  # 0 for active, 1 for completed
           'limit': None,  # Integer between 1 and 249
           'milestone_id': None  # Integer ID of milestone
           }


# Fetch test data from TestRail
def fetch_testrail_data(testRunId):
    headers = {
        "Content-Type": "application/json",
        # "Authorization": f"Bearer {TESTRAIL_API_KEY}"
    }
    project_id = 1
    # url = TESTRAIL_API_URL + "index.php?/api/v2/get_case/" + testRunId
    url = TESTRAIL_API_URL + f"index.php?/api/v2/get_cases/{project_id}&suite_id={testRunId}"

    try:
        response = requests.get(url, auth=(TESTRAIL_USERNAME, TESTRAIL_PASSWORD), headers=headers, verify=False)
        response.raise_for_status()  # This will raise an HTTPError if the HTTP request returned an unsuccessful status code.
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")  # Output the specific error
        print(f"Response content: {response.content}")  # Output the response content to see any additional information
    except Exception as err:
        print(f"An error occurred: {err}    ")
def make_api_get_request(uri):
    too_many_requests = False
    while not too_many_requests:
        try:
            response = TESTRAIL.send_get(uri)
            return response
        except testrail.APIError as error:
            error_string = str(error)
            if 'Retry after' in error_string:
                # Parse retry after x seconds
                retry_after = error_string.split('Retry after ')[1]
                retry_after = retry_after.split(' ', 1)[0]
                retry_after = int(retry_after)
                print('Pause for %x seconds' % retry_after)
                time.sleep(retry_after)
                too_many_requests = True
            else:
                raise Exception('Unexpected API Error: %s' % error_string)


# Process the test data
def process_testrail_data(data):
    report_count = {
        "Automated": 0,
        "AutomationBacklog": 0,
        "Manual": 0,
        "UI_Mobile_Backlog": 0,
    }
    for test in data:
        if test["custom_automation_status"] == "Automated":
            report_count["Automated"] += 1
        elif test["custom_automation_status"] == "AutomationBacklog":
            report_count["AutomationBacklog"] += 1
        elif test["custom_automation_status"] == "Manual":
            report_count["Manual"] += 1
        elif test["custom_automation_status"] == "UI_Mobile_Backlog":
            report_count["UI_Mobile_Backlog"] += 1
    return report_count


# Create the chart
def create_chart(report_count, width=400, height=200):
    categories = [
        "Automated",
        "AutomationBacklog",
        "Manual",
        "UI_Mobile_Backlog",
    ]
    counts = [report_count[cat] for cat in categories if report_count[cat] != 0]
    labels = [cat for cat in categories if report_count[cat] != 0]

    fig, ax = plt.subplots()
    ax.pie(counts, labels=labels, autopct='%1.1f%%', startangle=90)
    ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    global graph_filename
    graph_filename = "test_report_chart.png"
    plt.savefig(graph_filename)
    plt.close()


# Upload the chart and report to Confluence
def upload_to_confluence():
    confluence = Confluence(
        url=CONFLUENCE_API_URL,
        username=CONFLUENCE_USERNAME,
        password=CONFLUENCE_API_KEY
    )

    page_id = confluence.get_page_id(CONFLUENCE_SPACE_KEY, CONFLUENCE_PAGE_TITLE)
    if not page_id:
        raise Exception(f"Confluence page '{CONFLUENCE_PAGE_TITLE}' not found in space '{CONFLUENCE_SPACE_KEY}'.")

    with open(graph_filename, 'rb') as file:
        attachment = confluence.attach_file(file, page_id)

    page_body = f"""
    <h1>Automated Test Report</h1>
    <p>Here is the summary of the test report:</p>
    <ac:image ac:height="200" ac:width="400">
        <ri:attachment ri:filename="{graph_filename}" />
    </ac:image>
    """

    confluence.update_page(
        page_id=page_id,
        title=CONFLUENCE_PAGE_TITLE,
        body=page_body
    )


if __name__ == "__main__":
    testRunId = "C20523"  # Replace with the ID of your test run in TestRail
    # test_data = fetch_testrail_data(testRunId)
    # report_count = process_testrail_data(test_data)
    URI="get_tests/" + testRunId
make_api_get_request(URI)
# create_chart(report_count)
# upload_to_confluence()
