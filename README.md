# Jira Worklog Extractor for ZYN Project

This tool extracts worklogs from Jira for the ZYN project, filtered by ERP Activity. It includes all issues linked to epics that match the filter criteria.

## Features

- Finds all issues with specific ERP Activity value
- Identifies epics and includes all issues within those epics
- Includes all issues linked to matched issues
- Extracts worklogs with detailed information
- Exports results to CSV
- Generates summary statistics by author

## Setup

### 1. Install Requirements

```bash
pip install requests
```

### 2. Configure Jira Connection

Update the configuration in `config.json` or directly in `extract_worklogs.py`:

- **JIRA_URL**: Your Jira instance URL (e.g., `https://yourcompany.atlassian.net`)
- **JIRA_EMAIL**: Your Jira email address
- **JIRA_API_TOKEN**: Your Jira API token ([Create one here](https://id.atlassian.com/manage-profile/security/api-tokens))
- **PROJECT_KEY**: The Jira project key (default: `ZYN`)
- **ERP_ACTIVITY_FILTER**: The ERP Activity value to filter by (default: `ProjectTask-00000007118797`)
- **CUSTOM_FIELD_ERP_ACTIVITY**: The custom field ID for ERP Activity

### 3. Find Your Custom Field ID

To find the custom field ID for "ERP Activity":

1. Go to Jira and view any issue
2. Open browser developer tools (F12)
3. Go to Network tab
4. Reload the page
5. Find the API call to `/rest/api/3/issue/[ISSUE-KEY]`
6. Look in the response for your field name and note the field ID (e.g., `customfield_10234`)
7. Update `CUSTOM_FIELD_ERP_ACTIVITY` in the script

## Usage

### Basic Usage

```bash
python extract_worklogs.py
```

### Using Configuration File

To load settings from `config.json`, modify the script to read from the config file:

```python
import json

with open('config.json', 'r') as f:
    config = json.load(f)

extractor = JiraWorklogExtractor(
    config['jira_url'],
    config['jira_email'],
    config['jira_api_token']
)
```

## Output

The script generates:

1. **Console Output**: Progress updates and summary statistics
2. **CSV File**: Detailed worklog entries with columns:
   - `issue_key`: Jira issue key
   - `author`: Name of person who logged time
   - `author_email`: Email of author
   - `time_spent`: Time in human-readable format (e.g., "2h 30m")
   - `time_spent_hours`: Time in hours (decimal)
   - `started`: When the work was started
   - `comment`: Worklog comment

### Example Output

```
Searching for issues with ERP Activity = ProjectTask-00000007118797...
Found 5 direct matches
Found 2 epics: ['ZYN-123', 'ZYN-456']
Finding issues in epic ZYN-123...
  Added 15 issues from epic
Finding issues in epic ZYN-456...
  Added 8 issues from epic
Finding linked issues...
Total issues collected: 32

Extracting worklogs from 32 issues...
  Progress: 10/32
  Progress: 20/32
  Progress: 30/32
Total worklogs extracted: 156

============================================================
SUMMARY REPORT
============================================================
Total hours logged: 245.50
Total worklog entries: 156

Breakdown by author:
------------------------------------------------------------
John Smith                       89.25 hours  (45 entries)
Jane Doe                         67.50 hours  (38 entries)
Bob Johnson                      55.75 hours  (42 entries)
Alice Williams                   33.00 hours  (31 entries)
```

## How It Works

The extractor follows this process:

1. **Find Direct Matches**: Searches for all issues in the ZYN project where the ERP Activity field equals `ProjectTask-00000007118797`

2. **Identify Epics**: From the direct matches, identifies which issues are epics

3. **Expand Epics**: For each epic found, retrieves all issues that belong to that epic

4. **Find Linked Issues**: For all collected issues, finds any linked issues (blocks, relates to, etc.)

5. **Extract Worklogs**: Retrieves all worklog entries from the complete set of issues

6. **Generate Reports**: Creates a summary and exports detailed data to CSV

## Customization

### Filter by Date Range

Add date filtering to the worklog extraction:

```python
def extract_worklogs(self, issue_keys, start_date=None, end_date=None):
    # Filter worklogs by date
    if start_date:
        started_datetime = datetime.fromisoformat(worklog['started'].replace('Z', '+00:00'))
        if started_datetime < start_date:
            continue
```

### Export to Excel

Install `openpyxl` and add Excel export:

```bash
pip install openpyxl pandas
```

```python
import pandas as pd

df = pd.DataFrame(worklogs)
df.to_excel('worklogs.xlsx', index=False)
```

## Troubleshooting

### Authentication Error
- Verify your API token is correct
- Ensure your email matches your Jira account

### Custom Field Not Found
- Double-check the custom field ID
- Ensure you have permission to view the field

### No Issues Found
- Verify the ERP Activity value is correct
- Check that issues exist with this value in Jira

## License

MIT License
