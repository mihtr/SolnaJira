# Jira Worklog Extractor for ZYN Project

**Version: 1.0.0**

This tool extracts worklogs from Jira for the ZYN project, filtered by ERP Activity. It includes all issues linked to epics that match the filter criteria.

## Features

- Finds all issues with specific ERP Activity value using JQL
- Identifies epics and includes all issues within those epics
- Includes all issues linked to matched issues
- Collects all sub-tasks of matched issues
- Extracts worklogs with detailed information including issue type, epic links, and summary
- Exports results to CSV and interactive HTML reports
- Generates summary statistics by author and issue
- Bearer token authentication
- Environment variable configuration support (.env file)
- Command-line interface with flexible options
- Visual progress bars with tqdm
- Configurable log levels (standard/debug)
- Comprehensive five-stage collection process

## Setup

### 1. Install Requirements

```bash
pip install -r requirements.txt
```

This will install:
- `requests` - HTTP library for Jira API
- `python-dotenv` - Environment variable management
- `tqdm` - Progress bar visualization

### 2. Configure Jira Connection

There are three ways to configure the tool (in order of precedence):

#### Option A: Command-Line Arguments (Highest Priority)
```bash
python extract_worklogs.py --jira-url https://jira.example.com --jira-token YOUR_TOKEN --project ZYN
```

#### Option B: Environment Variables (.env file)
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your values:
   ```env
   JIRA_URL=https://your-jira-instance.atlassian.net
   JIRA_EMAIL=your-email@example.com
   JIRA_API_TOKEN=your-api-token-here
   PROJECT_KEY=ZYN
   ERP_ACTIVITY_FILTER=ProjectTask-00000007118797
   LOG_LEVEL=1
   ```

3. Get your API token from: [https://id.atlassian.com/manage-profile/security/api-tokens](https://id.atlassian.com/manage-profile/security/api-tokens)

#### Option C: Environment Variables (System-level)
Set environment variables in your shell:
```bash
export JIRA_URL=https://your-jira-instance.atlassian.net
export JIRA_API_TOKEN=your-token-here
```

## Usage

### Basic Usage

```bash
# Use configuration from .env file
python extract_worklogs.py
```

### Command-Line Options

```bash
# Show help
python extract_worklogs.py --help

# Override project and ERP activity
python extract_worklogs.py --project ZYN --erp-activity ProjectTask-00000007118797

# Debug mode with detailed API logging
python extract_worklogs.py --log-level 2

# Custom output directory
python extract_worklogs.py --output-dir ./reports

# Export only CSV (skip HTML)
python extract_worklogs.py --format csv

# Export only HTML (skip CSV)
python extract_worklogs.py --format html

# Show version
python extract_worklogs.py --version
```

### Available Arguments

| Argument | Short | Description | Default |
|----------|-------|-------------|---------|
| `--project` | `-p` | Project key | From env or `ZYN` |
| `--erp-activity` | `-e` | ERP Activity filter | From env |
| `--jira-url` | | Jira instance URL | From env |
| `--jira-token` | | Jira API token | From env |
| `--output-dir` | `-o` | Output directory | `./output` |
| `--log-level` | `-l` | Log level (1=standard, 2=debug) | `1` |
| `--format` | `-f` | Output format (csv/html/both) | `both` |
| `--version` | `-v` | Show version | |
| `--help` | `-h` | Show help message | |

The script will:
1. Search for issues using the specified ERP Activity filter
2. Expand epics to include all child issues
3. Find all linked issues
4. Collect all sub-tasks
5. Extract worklogs from all collected issues
6. Generate CSV and HTML reports

## Output

The script generates:

1. **Console Output**: Progress updates with visual progress bars and summary statistics

2. **CSV File** (`<project>_worklogs_<timestamp>.csv`): Detailed worklog entries with columns:
   - `issue_key`: Jira issue key
   - `summary`: Issue summary/title
   - `issue_type`: Issue type (Story, Task, Bug, Epic, Sub-task, etc.)
   - `epic_link`: Epic this issue belongs to
   - `author`: Name of person who logged time
   - `author_email`: Email of author
   - `time_spent`: Time in human-readable format (e.g., "2h 30m")
   - `time_spent_hours`: Time in hours (decimal)
   - `started`: When the work was started
   - `comment`: Worklog comment

3. **HTML Report** (`<project>_worklogs_<timestamp>.html`): Interactive report with:
   - Summary dashboard with total hours, entries, contributors, and issues
   - Hours by Author with expandable detail views showing individual worklogs
   - Hours by Issue with summary, type, epic link, and contributor breakdown
   - Complete worklog entries table with all fields
   - Visual progress bars and percentage distributions
   - Professional styling with gradient header and responsive design

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

## Configuration

### Log Levels

Set `LOG_LEVEL` in the script to control output verbosity:

- `LOG_LEVEL = 1` (Standard): Shows progress and summary information
- `LOG_LEVEL = 2` (Debug): Shows all API calls, JQL queries, headers, and response details with `[DEBUG]` prefix

### Authentication

The script uses Bearer token authentication with the Jira REST API v2. Ensure your API token has sufficient permissions to:
- Read issues in the project
- Access custom fields
- View worklogs

## Architecture

### Three-Stage Collection Process

1. **Direct Match**: Uses JQL to find all issues where "ERP Activity" matches the filter value
2. **Epic Expansion**: Identifies epics from direct matches, then collects ALL issues within those epics
3. **Linked Issues**: For all collected issues, follows issue links to capture the full scope of related work

This ensures comprehensive worklog extraction across the entire project scope.

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
