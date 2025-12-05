# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Purpose

This repository contains a Jira worklog extraction tool for the ZYN project. It extracts time-logged hours from Jira issues filtered by a custom "ERP Activity" field, with comprehensive collection that includes:
- Direct issue matches
- All issues within matched epics
- All issues linked to any matched issue

## Running the Tool

```bash
# Install dependencies
pip install -r requirements.txt

# Run the extractor
python extract_worklogs.py
```

The script outputs:
- Console summary with total hours and breakdown by author
- CSV file: `zyn_worklogs_<ERP_ACTIVITY>_<timestamp>.csv`

## Configuration

Before running, update these values in `extract_worklogs.py:14-19`:

- **JIRA_URL**: Jira instance URL
- **JIRA_EMAIL**: User email
- **JIRA_API_TOKEN**: API token from https://id.atlassian.com/manage-profile/security/api-tokens
- **CUSTOM_FIELD_ERP_ACTIVITY**: Custom field ID for "ERP Activity" (find via browser DevTools on Jira issue API response at `/rest/api/3/issue/[KEY]`)

The `config.json` file exists as a template but is not currently used by the script.

## Architecture

### Three-Stage Collection Process

The `JiraWorklogExtractor` class implements a comprehensive issue collection strategy:

1. **Direct Match** (`find_issues_by_erp_activity`): Uses JQL to find all issues where the ERP Activity custom field matches the filter value

2. **Epic Expansion** (`get_epic_issues`): Identifies epics from direct matches, then collects ALL issues within those epics using the "Epic Link" field

3. **Linked Issues** (`get_linked_issues`): For all collected issues, follows issue links (blocks, relates to, etc.) to capture the full scope of related work

This ensures comprehensive worklog extraction across the entire project scope, not just direct matches.

### API Integration

- Uses Jira REST API v3 with Basic Auth (email + API token)
- Implements pagination for large result sets (`search_issues` method)
- All API calls use `requests.raise_for_status()` for error handling

### Worklog Extraction

The `extract_worklogs` method:
- Iterates through all collected issue keys
- Calls `/rest/api/3/issue/{key}/worklog` for each issue
- Parses nested comment structure from Jira's Atlassian Document Format
- Handles errors gracefully to continue processing remaining issues

### Output Generation

- `generate_summary`: Aggregates hours by author using `defaultdict`
- `export_to_csv`: Writes structured CSV with hours converted from seconds to decimal format

## Custom Field Discovery

The ERP Activity field is a Jira custom field. To find the field ID:
1. Open any Jira issue in browser
2. Open DevTools (F12) → Network tab
3. Reload page and find `/rest/api/3/issue/[KEY]` request
4. Search response JSON for "ERP Activity" to find the `customfield_XXXXX` ID
5. Update `CUSTOM_FIELD_ERP_ACTIVITY` constant

## Modifying Filters

To change the ERP Activity filter or project:
- `ERP_ACTIVITY_FILTER`: The value to filter on (line 18)
- `PROJECT_KEY`: The Jira project key (line 17)

To add date filtering, modify `extract_worklogs` to filter worklogs by the `started` field.
