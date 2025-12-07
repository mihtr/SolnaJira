# CLAUDE.md

**Version: 1.2.0**

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

### Five-Stage Collection Process

The `JiraWorklogExtractor` class implements a comprehensive issue collection strategy:

1. **Direct Match** (`find_issues_by_erp_activity`): Uses JQL to find all issues where the ERP Activity custom field matches the filter value

2. **Epic Expansion** (`get_epic_issues`): Identifies epics from direct matches, then collects ALL issues within those epics using the "Epic Link" field

3. **Linked Issues** (`get_linked_issues`): For all collected issues, follows issue links (blocks, relates to, etc.) to capture the full scope of related work

4. **Sub-tasks** (`get_subtasks`): For all collected issues, retrieves any sub-tasks to ensure complete coverage of work items

This ensures comprehensive worklog extraction across the entire project scope, including all related work and sub-tasks.

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
  - Smart Insights & Recommendations with AI-powered pattern detection
  - Interactive Chart.js visualizations (pie charts, bar charts, time series)
  - Hours by author with expandable details
  - Hours by issue breakdown with epic names and parent links
  - Complete worklog entries table with issue type, epic names, and parent links
  - Visual progress bars and percentage distributions
  - Sortable and filterable tables
  - Compact font sizing for detailed tables

## Modifying Filters

To change the ERP Activity filter or project:
- `ERP_ACTIVITY_FILTER`: The value to filter on (line 19)
- `PROJECT_KEY`: The Jira project key (line 18)

The script searches using JQL: `project = {PROJECT_KEY} AND "ERP Activity" ~ "{ERP_ACTIVITY_FILTER}"`

## Key Features

- **Configurable logging**: Set `LOG_LEVEL = 2` to see detailed API calls, JQL queries, and responses
- **Enhanced issue metadata**: Automatically fetches issue type, epic name, parent link, team, components, labels, and product items
- **Epic names display**: Shows human-readable epic names instead of keys (e.g., "SelfService backend for Zynergy (Invoice)" instead of "ZYN-48067")
- **Parent link tracking**: Displays parent links of epics with clickable names
- **Robust comment parsing**: Handles both plain text and Atlassian Document Format comments
- **Interactive HTML reports**:
  - Smart Insights with 8 pattern detection algorithms (Gini coefficient, Z-score, bottleneck detection)
  - 5 interactive Chart.js charts (team distribution pie, top contributors bar, component/product charts, time series)
  - Sortable and filterable tables with column-specific filters
  - Compact table styling for better information density
  - Click "View Details" on any author to see their individual worklog entries
- **Five-stage collection**: Ensures comprehensive coverage by expanding epics, following links, and including sub-tasks
- **Performance optimized**: Parallel processing, caching, and efficient API calls
