"""
Extract worklogs from Jira ZYN project filtered by ERP Activity.
Includes all issues linked to epics that match the filter.
"""

import requests
from requests.auth import HTTPBasicAuth
import json
from datetime import datetime
from collections import defaultdict
import csv
from pathlib import Path

# Version
VERSION = "1.0.0"

# Configuration
JIRA_URL = "https://your-jira-instance.atlassian.net"  # Update this
JIRA_EMAIL = "your-email@example.com"  # Update this
JIRA_API_TOKEN = "your-api-token-here"  # Update this - Get from https://id.atlassian.com/manage-profile/security/api-tokens
PROJECT_KEY = "ZYN"
ERP_ACTIVITY_FILTER = "ProjectTask-00000007118797"
LOG_LEVEL = 1  # 1 = standard, 2 = debug (shows [DEBUG] messages)

class JiraWorklogExtractor:
    def __init__(self, jira_url, api_token):
        self.jira_url = jira_url.rstrip('/')
        self.api_token = api_token
        self.headers = {
            "Accept": "application/json",
            "Authorization": f"Bearer {api_token}"
        }

    def search_issues(self, jql, fields=None, max_results=100):
        """Search for issues using JQL"""
        url = f"{self.jira_url}/rest/api/2/search"
        all_issues = []
        start_at = 0

        if fields is None:
            fields = ["summary", "issuetype", "status", "issuelinks"]

        while True:
            params = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": max_results,
                "fields": ",".join(fields)
            }

            if LOG_LEVEL >= 2:
                print(f"\n[DEBUG] API Call: GET {url}")
                print(f"[DEBUG] JQL: {jql}")
                print(f"[DEBUG] Parameters: {params}")
                print(f"[DEBUG] Headers: {self.headers}")

            response = requests.get(url, headers=self.headers, params=params)

            if LOG_LEVEL >= 2:
                print(f"[DEBUG] Response Status: {response.status_code}")

            if response.status_code != 200:
                if LOG_LEVEL >= 2:
                    print(f"[DEBUG] Response Body: {response.text[:500]}")

            response.raise_for_status()
            data = response.json()

            batch_size = len(data['issues'])
            all_issues.extend(data['issues'])

            if LOG_LEVEL >= 2:
                print(f"[DEBUG] Retrieved {batch_size} issues (total so far: {len(all_issues)}/{data['total']})")
            else:
                print(f"  Fetching issues: {len(all_issues)}/{data['total']}")

            if start_at + max_results >= data['total']:
                break
            start_at += max_results

        return all_issues

    def get_epic_issues(self, epic_key):
        """Get all issues in an epic"""
        print(f"  Searching for issues in epic {epic_key}...")
        jql = f'project = {PROJECT_KEY} AND "Epic Link" = {epic_key}'
        return self.search_issues(jql)

    def get_linked_issues(self, issue_key):
        """Get all issues linked to a given issue"""
        url = f"{self.jira_url}/rest/api/2/issue/{issue_key}"
        params = {"fields": "issuelinks"}

        if LOG_LEVEL >= 2:
            print(f"\n[DEBUG] Getting linked issues for {issue_key}")
            print(f"[DEBUG] API Call: GET {url}")

        response = requests.get(url, headers=self.headers, params=params)

        if LOG_LEVEL >= 2:
            print(f"[DEBUG] Response Status: {response.status_code}")

        if response.status_code != 200:
            if LOG_LEVEL >= 2:
                print(f"[DEBUG] Response Body: {response.text[:500]}")

        response.raise_for_status()
        data = response.json()

        linked_issues = []
        issue_links = data.get('fields', {}).get('issuelinks', [])

        for link in issue_links:
            if 'outwardIssue' in link:
                linked_issues.append(link['outwardIssue']['key'])
            if 'inwardIssue' in link:
                linked_issues.append(link['inwardIssue']['key'])

        if linked_issues and LOG_LEVEL >= 2:
            print(f"[DEBUG] Found {len(linked_issues)} linked issues: {', '.join(linked_issues)}")

        return linked_issues

    def get_worklogs(self, issue_key):
        """Get all worklogs for an issue"""
        url = f"{self.jira_url}/rest/api/2/issue/{issue_key}/worklog"

        if LOG_LEVEL >= 2:
            print(f"[DEBUG] Getting worklogs for {issue_key}")

        response = requests.get(url, headers=self.headers)

        if LOG_LEVEL >= 2:
            print(f"[DEBUG] Response Status: {response.status_code}")

        if response.status_code != 200:
            if LOG_LEVEL >= 2:
                print(f"[DEBUG] Response Body: {response.text[:500]}")

        response.raise_for_status()
        data = response.json()

        worklogs = data.get('worklogs', [])
        if worklogs and LOG_LEVEL >= 2:
            print(f"[DEBUG] Found {len(worklogs)} worklog(s) for {issue_key}")

        return worklogs

    def find_issues_by_erp_activity(self):
        """Find all issues with ERP Activity filter"""
        jql = f'project = {PROJECT_KEY} AND "ERP Activity" ~ "{ERP_ACTIVITY_FILTER}"'
        return self.search_issues(jql)

    def get_subtasks(self, issue_key):
        """Get all subtasks for an issue"""
        url = f"{self.jira_url}/rest/api/2/issue/{issue_key}"
        params = {"fields": "subtasks"}

        if LOG_LEVEL >= 2:
            print(f"\n[DEBUG] Getting subtasks for {issue_key}")

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        data = response.json()

        subtasks = data.get('fields', {}).get('subtasks', [])
        subtask_keys = [subtask['key'] for subtask in subtasks]

        if subtask_keys and LOG_LEVEL >= 2:
            print(f"[DEBUG] Found {len(subtask_keys)} subtask(s): {', '.join(subtask_keys)}")

        return subtask_keys

    def collect_all_related_issues(self):
        """
        Collect all issues related to the ERP Activity:
        1. Direct matches
        2. Issues linked to epics
        3. Issues linked to any matched issue
        4. Sub-tasks of all collected issues
        """
        print(f"\n{'='*70}")
        print(f"STARTING ISSUE COLLECTION")
        print(f"{'='*70}")
        print(f'Searching for issues with "ERP Activity" ~ "{ERP_ACTIVITY_FILTER}"...')

        # Step 1: Find all issues matching the ERP Activity
        direct_issues = self.find_issues_by_erp_activity()
        print(f"\n[STEP 1 COMPLETE] Found {len(direct_issues)} direct matches")

        all_issue_keys = set()
        epic_keys = []

        # Collect direct issue keys and identify epics
        print("\n[STEP 2] Analyzing direct matches for epics...")
        for issue in direct_issues:
            issue_key = issue['key']
            all_issue_keys.add(issue_key)
            print(f"  - {issue_key}")

            issue_type = issue['fields'].get('issuetype', {}).get('name', '')
            if issue_type == 'Epic':
                epic_keys.append(issue_key)

        print(f"\n[STEP 2 COMPLETE] Found {len(epic_keys)} epics: {epic_keys}")

        # Step 2: Get all issues linked to epics
        if epic_keys:
            print(f"\n[STEP 3] Getting issues from epics...")
            for epic_key in epic_keys:
                print(f"\n  Processing epic {epic_key}...")
                epic_issues = self.get_epic_issues(epic_key)
                before_count = len(all_issue_keys)
                for issue in epic_issues:
                    all_issue_keys.add(issue['key'])
                after_count = len(all_issue_keys)
                print(f"  [EPIC COMPLETE] Added {after_count - before_count} new issues from epic {epic_key}")
            print(f"\n[STEP 3 COMPLETE] Total issues after epic expansion: {len(all_issue_keys)}")
        else:
            print(f"\n[STEP 3 SKIPPED] No epics found")

        # Step 3: Get all linked issues
        print(f"\n[STEP 4] Finding linked issues (checking {len(all_issue_keys)} issues)...")
        initial_keys = list(all_issue_keys)
        linked_count = 0
        for i, issue_key in enumerate(initial_keys, 1):
            if i % 20 == 0:
                print(f"  Progress: {i}/{len(initial_keys)} issues checked, {linked_count} new links found")
            linked = self.get_linked_issues(issue_key)
            for linked_key in linked:
                if linked_key.startswith(PROJECT_KEY):
                    if linked_key not in all_issue_keys:
                        all_issue_keys.add(linked_key)
                        linked_count += 1

        print(f"\n[STEP 4 COMPLETE] Added {linked_count} new linked issues")

        # Step 4: Get all subtasks
        print(f"\n[STEP 5] Finding subtasks (checking {len(all_issue_keys)} issues)...")
        initial_keys_for_subtasks = list(all_issue_keys)
        subtask_count = 0
        for i, issue_key in enumerate(initial_keys_for_subtasks, 1):
            if i % 20 == 0:
                print(f"  Progress: {i}/{len(initial_keys_for_subtasks)} issues checked, {subtask_count} subtasks found")
            subtasks = self.get_subtasks(issue_key)
            for subtask_key in subtasks:
                if subtask_key not in all_issue_keys:
                    all_issue_keys.add(subtask_key)
                    subtask_count += 1

        print(f"\n[STEP 5 COMPLETE] Added {subtask_count} new subtasks")
        print(f"\n{'='*70}")
        print(f"ISSUE COLLECTION COMPLETE: {len(all_issue_keys)} total issues")
        print(f"{'='*70}\n")
        return sorted(all_issue_keys)

    def get_issue_metadata(self, issue_key):
        """Get issue type, epic link, and summary for an issue"""
        url = f"{self.jira_url}/rest/api/2/issue/{issue_key}"
        params = {"fields": "issuetype,customfield_10014,summary"}  # customfield_10014 is typically Epic Link

        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        data = response.json()

        return {
            'issue_type': data.get('fields', {}).get('issuetype', {}).get('name', 'Unknown'),
            'epic_link': data.get('fields', {}).get('customfield_10014', ''),
            'summary': data.get('fields', {}).get('summary', '')
        }

    def extract_worklogs(self, issue_keys):
        """Extract worklogs from all issues"""
        all_worklogs = []
        issue_metadata_cache = {}

        print(f"\nExtracting worklogs from {len(issue_keys)} issues...")
        for i, issue_key in enumerate(issue_keys, 1):
            if i % 10 == 0:
                print(f"  Progress: {i}/{len(issue_keys)} issues processed")

            try:
                # Get issue metadata
                if issue_key not in issue_metadata_cache:
                    issue_metadata_cache[issue_key] = self.get_issue_metadata(issue_key)

                metadata = issue_metadata_cache[issue_key]

                worklogs = self.get_worklogs(issue_key)
                if worklogs and LOG_LEVEL >= 1:
                    print(f"    {issue_key}: Found {len(worklogs)} worklog(s)")
                for worklog in worklogs:
                    # Handle comment field - can be string, dict, or None
                    comment = ''
                    if worklog.get('comment'):
                        comment_field = worklog['comment']
                        if isinstance(comment_field, str):
                            comment = comment_field
                        elif isinstance(comment_field, dict):
                            # Jira Atlassian Document Format
                            try:
                                content = comment_field.get('content', [])
                                if content and len(content) > 0:
                                    first_block = content[0]
                                    if isinstance(first_block, dict):
                                        block_content = first_block.get('content', [])
                                        if block_content and len(block_content) > 0:
                                            text_node = block_content[0]
                                            if isinstance(text_node, dict):
                                                comment = text_node.get('text', '')
                            except (KeyError, IndexError, AttributeError):
                                comment = str(comment_field)

                    all_worklogs.append({
                        'issue_key': issue_key,
                        'issue_type': metadata['issue_type'],
                        'epic_link': metadata['epic_link'],
                        'summary': metadata['summary'],
                        'worklog_id': worklog['id'],
                        'author': worklog['author'].get('displayName', 'Unknown'),
                        'author_email': worklog['author'].get('emailAddress', ''),
                        'time_spent': worklog.get('timeSpent', ''),
                        'time_spent_seconds': worklog.get('timeSpentSeconds', 0),
                        'started': worklog.get('started', ''),
                        'comment': comment
                    })
            except Exception as e:
                print(f"  Error extracting worklogs from {issue_key}: {e}")

        print(f"\nTotal worklogs extracted: {len(all_worklogs)}")
        return all_worklogs

    def export_to_csv(self, worklogs, filename='worklogs_export.csv'):
        """Export worklogs to CSV"""
        if not worklogs:
            print("No worklogs to export")
            return

        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['issue_key', 'summary', 'issue_type', 'epic_link', 'author', 'author_email', 'time_spent',
                         'time_spent_hours', 'started', 'comment']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for worklog in worklogs:
                writer.writerow({
                    'issue_key': worklog['issue_key'],
                    'summary': worklog['summary'],
                    'issue_type': worklog['issue_type'],
                    'epic_link': worklog['epic_link'],
                    'author': worklog['author'],
                    'author_email': worklog['author_email'],
                    'time_spent': worklog['time_spent'],
                    'time_spent_hours': round(worklog['time_spent_seconds'] / 3600, 2),
                    'started': worklog['started'],
                    'comment': worklog['comment']
                })

        print(f"Worklogs exported to {filename}")

    def generate_summary(self, worklogs):
        """Generate summary statistics"""
        if not worklogs:
            print("No worklogs to summarize")
            return

        # Summary by author
        by_author = defaultdict(lambda: {'hours': 0, 'entries': 0})
        total_seconds = 0

        for worklog in worklogs:
            author = worklog['author']
            seconds = worklog['time_spent_seconds']
            by_author[author]['hours'] += seconds / 3600
            by_author[author]['entries'] += 1
            total_seconds += seconds

        print("\n" + "="*60)
        print("SUMMARY REPORT")
        print("="*60)
        print(f"Total hours logged: {total_seconds / 3600:.2f}")
        print(f"Total worklog entries: {len(worklogs)}")
        print("\nBreakdown by author:")
        print("-"*60)

        for author, stats in sorted(by_author.items(), key=lambda x: x[1]['hours'], reverse=True):
            print(f"{author:30s} {stats['hours']:8.2f} hours  ({stats['entries']} entries)")

    def export_to_html(self, worklogs, filename='worklogs_report.html'):
        """Export worklogs to an interactive HTML report"""
        if not worklogs:
            print("No worklogs to export")
            return

        # Calculate summary statistics
        by_author = defaultdict(lambda: {'hours': 0, 'entries': 0, 'worklogs': []})
        by_issue = defaultdict(lambda: {'hours': 0, 'entries': 0, 'authors': set(), 'issue_type': '', 'epic_link': '', 'summary': ''})
        total_seconds = 0

        for worklog in worklogs:
            author = worklog['author']
            issue_key = worklog['issue_key']
            seconds = worklog['time_spent_seconds']

            by_author[author]['hours'] += seconds / 3600
            by_author[author]['entries'] += 1
            by_author[author]['worklogs'].append(worklog)

            by_issue[issue_key]['hours'] += seconds / 3600
            by_issue[issue_key]['entries'] += 1
            by_issue[issue_key]['authors'].add(author)
            by_issue[issue_key]['issue_type'] = worklog['issue_type']
            by_issue[issue_key]['epic_link'] = worklog['epic_link']
            by_issue[issue_key]['summary'] = worklog['summary']

            total_seconds += seconds

        total_hours = total_seconds / 3600

        # Sort data
        authors_sorted = sorted(by_author.items(), key=lambda x: x[1]['hours'], reverse=True)
        issues_sorted = sorted(by_issue.items(), key=lambda x: x[1]['hours'], reverse=True)

        # Generate HTML
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jira Worklog Report - {PROJECT_KEY}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }}

        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            overflow: hidden;
        }}

        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            text-align: center;
        }}

        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            font-weight: 600;
        }}

        .header .subtitle {{
            font-size: 1.1em;
            opacity: 0.9;
        }}

        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            padding: 40px;
            background: #f8f9fa;
        }}

        .stat-card {{
            background: white;
            padding: 25px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.2s;
        }}

        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}

        .stat-card .number {{
            font-size: 2.5em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}

        .stat-card .label {{
            color: #666;
            font-size: 0.9em;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}

        .section {{
            padding: 40px;
        }}

        .section-title {{
            font-size: 1.8em;
            margin-bottom: 25px;
            color: #333;
            padding-bottom: 10px;
            border-bottom: 3px solid #667eea;
        }}

        .chart-container {{
            margin-bottom: 40px;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            background: white;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            border-radius: 8px;
            overflow: hidden;
        }}

        thead {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }}

        th {{
            padding: 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }}

        td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}

        tbody tr:hover {{
            background: #f8f9fa;
        }}

        tbody tr:last-child td {{
            border-bottom: none;
        }}

        .progress-bar {{
            background: #e9ecef;
            height: 25px;
            border-radius: 12px;
            overflow: hidden;
            margin-top: 5px;
        }}

        .progress-fill {{
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            height: 100%;
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            padding: 0 10px;
            color: white;
            font-size: 0.85em;
            font-weight: 600;
        }}

        .details-toggle {{
            background: #667eea;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9em;
            transition: background 0.2s;
        }}

        .details-toggle:hover {{
            background: #764ba2;
        }}

        .worklog-details {{
            display: none;
            margin-top: 15px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            border-left: 4px solid #667eea;
        }}

        .worklog-details.active {{
            display: block;
        }}

        .worklog-entry {{
            background: white;
            padding: 12px;
            margin-bottom: 10px;
            border-radius: 4px;
            font-size: 0.9em;
        }}

        .worklog-entry:last-child {{
            margin-bottom: 0;
        }}

        .worklog-meta {{
            color: #666;
            font-size: 0.85em;
            margin-bottom: 5px;
        }}

        .worklog-comment {{
            color: #333;
            margin-top: 5px;
            font-style: italic;
        }}

        .footer {{
            background: #2d3748;
            color: white;
            padding: 20px 40px;
            text-align: center;
            font-size: 0.9em;
        }}

        @media print {{
            body {{
                background: white;
            }}
            .details-toggle {{
                display: none;
            }}
            .worklog-details {{
                display: block !important;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Jira Worklog Report</h1>
            <div class="subtitle">Project: {PROJECT_KEY}</div>
            <div class="subtitle">Version: {VERSION}</div>
            <div class="subtitle">Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="number">{total_hours:.1f}</div>
                <div class="label">Total Hours</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(worklogs)}</div>
                <div class="label">Total Entries</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(by_author)}</div>
                <div class="label">Contributors</div>
            </div>
            <div class="stat-card">
                <div class="number">{len(by_issue)}</div>
                <div class="label">Issues</div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">Hours by Author</h2>
            <table>
                <thead>
                    <tr>
                        <th>Author</th>
                        <th>Hours</th>
                        <th>Entries</th>
                        <th>% of Total</th>
                        <th>Distribution</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
"""

        for i, (author, stats) in enumerate(authors_sorted):
            percentage = (stats['hours'] / total_hours * 100) if total_hours > 0 else 0
            html += f"""
                    <tr>
                        <td><strong>{author}</strong></td>
                        <td>{stats['hours']:.2f}h</td>
                        <td>{stats['entries']}</td>
                        <td>{percentage:.1f}%</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {percentage}%">
                                    {percentage:.1f}%
                                </div>
                            </div>
                        </td>
                        <td>
                            <button class="details-toggle" onclick="toggleDetails('author-{i}')">
                                View Details
                            </button>
                        </td>
                    </tr>
                    <tr>
                        <td colspan="6" style="padding: 0; border: none;">
                            <div id="author-{i}" class="worklog-details">
"""

            for worklog in sorted(stats['worklogs'], key=lambda x: x['started'], reverse=True):
                comment = worklog['comment'] if worklog['comment'] else 'No comment'
                epic_display = f" • Epic: {worklog['epic_link']}" if worklog['epic_link'] else ''
                html += f"""
                                <div class="worklog-entry">
                                    <div class="worklog-meta">
                                        <strong>{worklog['issue_key']}</strong> ({worklog['issue_type']}) •
                                        {worklog['time_spent']} •
                                        {worklog['started'][:10]}{epic_display}
                                    </div>
                                    <div class="worklog-comment">{comment}</div>
                                </div>
"""

            html += """
                            </div>
                        </td>
                    </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2 class="section-title">Hours by Issue</h2>
            <table>
                <thead>
                    <tr>
                        <th>Issue Key</th>
                        <th>Summary</th>
                        <th>Type</th>
                        <th>Epic Link</th>
                        <th>Hours</th>
                        <th>Entries</th>
                        <th>Contributors</th>
                        <th>% of Total</th>
                        <th>Distribution</th>
                    </tr>
                </thead>
                <tbody>
"""

        for issue_key, stats in issues_sorted:
            percentage = (stats['hours'] / total_hours * 100) if total_hours > 0 else 0
            contributors = ', '.join(sorted(stats['authors']))
            epic_link = stats['epic_link'] if stats['epic_link'] else '-'
            summary = stats['summary'] if stats['summary'] else '-'
            html += f"""
                    <tr>
                        <td><strong>{issue_key}</strong></td>
                        <td>{summary}</td>
                        <td>{stats['issue_type']}</td>
                        <td>{epic_link}</td>
                        <td>{stats['hours']:.2f}h</td>
                        <td>{stats['entries']}</td>
                        <td>{contributors}</td>
                        <td>{percentage:.1f}%</td>
                        <td>
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: {percentage}%">
                                    {percentage:.1f}%
                                </div>
                            </div>
                        </td>
                    </tr>
"""

        html += f"""
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2 class="section-title">All Worklog Entries</h2>
            <table>
                <thead>
                    <tr>
                        <th>Issue</th>
                        <th>Summary</th>
                        <th>Type</th>
                        <th>Epic Link</th>
                        <th>Author</th>
                        <th>Date</th>
                        <th>Time Spent</th>
                        <th>Comment</th>
                    </tr>
                </thead>
                <tbody>
"""

        for worklog in sorted(worklogs, key=lambda x: x['started'], reverse=True):
            comment = worklog['comment'][:100] + '...' if len(worklog['comment']) > 100 else worklog['comment']
            comment = comment if comment else 'No comment'
            epic_link = worklog['epic_link'] if worklog['epic_link'] else '-'
            summary = worklog['summary'][:50] + '...' if len(worklog['summary']) > 50 else worklog['summary']
            summary = summary if summary else '-'
            html += f"""
                    <tr>
                        <td><strong>{worklog['issue_key']}</strong></td>
                        <td>{summary}</td>
                        <td>{worklog['issue_type']}</td>
                        <td>{epic_link}</td>
                        <td>{worklog['author']}</td>
                        <td>{worklog['started'][:10]}</td>
                        <td>{worklog['time_spent']}</td>
                        <td>{comment}</td>
                    </tr>
"""

        html += """
                </tbody>
            </table>
        </div>

        <div class="footer">
            Generated by Jira Worklog Extractor
        </div>
    </div>

    <script>
        function toggleDetails(id) {
            const element = document.getElementById(id);
            element.classList.toggle('active');
        }
    </script>
</body>
</html>
"""

        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"HTML report exported to {filename}")


def main():
    # Initialize extractor
    extractor = JiraWorklogExtractor(JIRA_URL, JIRA_API_TOKEN)

    # Collect all related issues
    issue_keys = extractor.collect_all_related_issues()

    if not issue_keys:
        print("No issues found matching the criteria")
        return

    # Extract worklogs
    worklogs = extractor.extract_worklogs(issue_keys)

    # Generate summary
    extractor.generate_summary(worklogs)

    # Create output directory if it doesn't exist
    from pathlib import Path
    output_dir = Path('output')
    output_dir.mkdir(exist_ok=True)

    # Export to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_filename = output_dir / f'zyn_worklogs_{timestamp}.csv'
    extractor.export_to_csv(worklogs, str(csv_filename))

    # Export to HTML
    html_filename = output_dir / f'zyn_worklogs_{timestamp}.html'
    extractor.export_to_html(worklogs, str(html_filename))

    print(f"\nDone! Results exported:")
    print(f"  - CSV: {csv_filename}")
    print(f"  - HTML Report: {html_filename}")


if __name__ == "__main__":
    main()
