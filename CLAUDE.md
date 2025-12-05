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
- CSV file: `zyn_worklogs_<timestamp>.csv`
- HTML report: `zyn_worklogs_<timestamp>.html` with interactive visualizations

## Configuration

Before running, update these values in `extract_worklogs.py:15-20`:

- **JIRA_URL**: Jira instance URL
- **JIRA_EMAIL**: User email (not currently used with Bearer auth)
- **JIRA_API_TOKEN**: API token from https://id.atlassian.com/manage-profile/security/api-tokens
- **PROJECT_KEY**: The Jira project key (default: "ZYN")
- **ERP_ACTIVITY_FILTER**: The value to filter on (e.g., "ProjectTask-00000007118797")
- **LOG_LEVEL**: 1 = standard output, 2 = debug output with [DEBUG] messages

The `config.json` file exists as a template but is not currently used by the script.

## Architecture

### Three-Stage Collection Process

The `JiraWorklogExtractor` class implements a comprehensive issue collection strategy:

1. **Direct Match** (`find_issues_by_erp_activity`): Uses JQL to find all issues where the ERP Activity custom field matches the filter value

2. **Epic Expansion** (`get_epic_issues`): Identifies epics from direct matches, then collects ALL issues within those epics using the "Epic Link" field

3. **Linked Issues** (`get_linked_issues`): For all collected issues, follows issue links (blocks, relates to, etc.) to capture the full scope of related work

This ensures comprehensive worklog extraction across the entire project scope, not just direct matches.

### API Integration

- Uses Jira REST API v2 with Bearer token authentication
- Implements pagination for large result sets (`search_issues` method)
- All API calls use `requests.raise_for_status()` for error handling
- Debug logging available for all API calls when `LOG_LEVEL = 2`

### Worklog Extraction

The `extract_worklogs` method:
- Fetches issue metadata (type, epic link) for each issue
- Iterates through all collected issue keys
- Calls `/rest/api/2/issue/{key}/worklog` for each issue
- Parses comment structure handling both string and Atlassian Document Format
- Handles errors gracefully to continue processing remaining issues
- Caches issue metadata to avoid duplicate API calls

### Output Generation

- `generate_summary`: Aggregates hours by author using `defaultdict`
- `export_to_csv`: Writes structured CSV with issue type, epic link, and worklog details
- `export_to_html`: Generates interactive HTML report with:
  - Summary dashboard with key metrics
  - Hours by author with expandable details
  - Hours by issue breakdown
  - Complete worklog entries table with issue type and epic link columns
  - Visual progress bars and percentage distributions

## Modifying Filters

To change the ERP Activity filter or project:
- `ERP_ACTIVITY_FILTER`: The value to filter on (line 19)
- `PROJECT_KEY`: The Jira project key (line 18)

The script searches using JQL: `project = {PROJECT_KEY} AND "ERP Activity" ~ "{ERP_ACTIVITY_FILTER}"`

## Key Features

- **Configurable logging**: Set `LOG_LEVEL = 2` to see detailed API calls, JQL queries, and responses
- **Issue metadata**: Automatically fetches issue type and epic link for each worklog
- **Robust comment parsing**: Handles both plain text and Atlassian Document Format comments
- **Interactive HTML reports**: Click "View Details" on any author to see their individual worklog entries
- **Three-stage collection**: Ensures comprehensive coverage by expanding epics and following links
