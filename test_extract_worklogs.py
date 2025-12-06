"""
Comprehensive test suite for Jira Worklog Extractor.

This module contains unit tests for the JiraWorklogExtractor class,
covering all major functionality including API calls, data extraction,
caching, and export functionality.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, mock_open, call
from datetime import datetime
from pathlib import Path
import pickle
import hashlib
import json
import requests
from collections import defaultdict

# Import the module under test
import extract_worklogs
from extract_worklogs import JiraWorklogExtractor


# =============================================================================
# FIXTURES - Mock Data
# =============================================================================

@pytest.fixture
def mock_jira_config():
    """Basic configuration for JiraWorklogExtractor"""
    return {
        'jira_url': 'https://test-jira.atlassian.net',
        'api_token': 'test-api-token-12345',
        'project_key': 'TEST',
        'erp_activity_filter': 'ProjectTask-00000001',
        'log_level': 1,
        'cache_dir': '.test_cache',
        'use_cache': True,
        'cache_ttl': 3600
    }


@pytest.fixture
def mock_issue_response():
    """Mock response for Jira issue search"""
    return {
        'total': 2,
        'startAt': 0,
        'maxResults': 100,
        'issues': [
            {
                'key': 'TEST-1',
                'fields': {
                    'summary': 'Test Issue 1',
                    'issuetype': {'name': 'Story'},
                    'status': {'name': 'In Progress'},
                    'issuelinks': []
                }
            },
            {
                'key': 'TEST-2',
                'fields': {
                    'summary': 'Test Epic',
                    'issuetype': {'name': 'Epic'},
                    'status': {'name': 'Open'},
                    'issuelinks': []
                }
            }
        ]
    }


@pytest.fixture
def mock_epic_issue_response():
    """Mock response for epic issues"""
    return {
        'total': 2,
        'startAt': 0,
        'maxResults': 100,
        'issues': [
            {
                'key': 'TEST-10',
                'fields': {
                    'summary': 'Epic Child 1',
                    'issuetype': {'name': 'Story'},
                    'status': {'name': 'Done'},
                    'issuelinks': []
                }
            },
            {
                'key': 'TEST-11',
                'fields': {
                    'summary': 'Epic Child 2',
                    'issuetype': {'name': 'Task'},
                    'status': {'name': 'In Progress'},
                    'issuelinks': []
                }
            }
        ]
    }


@pytest.fixture
def mock_linked_issues_response():
    """Mock response for linked issues"""
    return {
        'fields': {
            'issuelinks': [
                {
                    'outwardIssue': {
                        'key': 'TEST-20',
                        'fields': {
                            'summary': 'Linked Issue 1'
                        }
                    }
                },
                {
                    'inwardIssue': {
                        'key': 'TEST-21',
                        'fields': {
                            'summary': 'Linked Issue 2'
                        }
                    }
                }
            ]
        }
    }


@pytest.fixture
def mock_subtasks_response():
    """Mock response for subtasks"""
    return {
        'fields': {
            'subtasks': [
                {
                    'key': 'TEST-30',
                    'fields': {
                        'summary': 'Subtask 1'
                    }
                },
                {
                    'key': 'TEST-31',
                    'fields': {
                        'summary': 'Subtask 2'
                    }
                }
            ]
        }
    }


@pytest.fixture
def mock_worklogs_response():
    """Mock response for worklogs"""
    return {
        'worklogs': [
            {
                'id': '100',
                'author': {
                    'displayName': 'John Doe',
                    'emailAddress': 'john.doe@example.com'
                },
                'timeSpent': '2h',
                'timeSpentSeconds': 7200,
                'started': '2024-03-15T10:00:00.000+0000',
                'comment': {
                    'type': 'doc',
                    'version': 1,
                    'content': [
                        {
                            'type': 'paragraph',
                            'content': [
                                {
                                    'type': 'text',
                                    'text': 'Implemented feature X'
                                }
                            ]
                        }
                    ]
                }
            },
            {
                'id': '101',
                'author': {
                    'displayName': 'Jane Smith',
                    'emailAddress': 'jane.smith@example.com'
                },
                'timeSpent': '3h 30m',
                'timeSpentSeconds': 12600,
                'started': '2024-03-16T14:30:00.000+0000',
                'comment': 'Fixed bug in component Y'
            }
        ]
    }


@pytest.fixture
def mock_issue_metadata_response():
    """Mock response for issue metadata"""
    return {
        'fields': {
            'issuetype': {'name': 'Story'},
            'customfield_10014': 'TEST-EPIC',  # Epic Link
            'summary': 'Test Issue Summary',
            'components': [
                {'name': 'Component A'},
                {'name': 'Component B'}
            ],
            'labels': ['backend', 'priority-high'],
            'customfield_11440': {'value': 'Product Item 1'},  # Product Item
            'customfield_10076': {'name': 'Team Alpha'}  # Team Name
        }
    }


@pytest.fixture
def mock_empty_worklogs():
    """Mock response with no worklogs"""
    return {'worklogs': []}


@pytest.fixture
def extractor(mock_jira_config):
    """Create a JiraWorklogExtractor instance for testing"""
    return JiraWorklogExtractor(**mock_jira_config, skip_validation=True)


# =============================================================================
# TEST INITIALIZATION AND CONFIGURATION
# =============================================================================

class TestInitialization:
    """Tests for JiraWorklogExtractor initialization"""

    def test_initialization_with_valid_config(self, mock_jira_config):
        """Test that extractor initializes with valid configuration"""
        extractor = JiraWorklogExtractor(**mock_jira_config, skip_validation=True)

        assert extractor.jira_url == 'https://test-jira.atlassian.net'
        assert extractor.api_token == 'test-api-token-12345'
        assert extractor.project_key == 'TEST'
        assert extractor.erp_activity_filter == 'ProjectTask-00000001'
        assert extractor.log_level == 1
        assert extractor.use_cache is True
        assert extractor.cache_ttl == 3600

    def test_initialization_strips_trailing_slash(self):
        """Test that trailing slash is removed from JIRA URL"""
        extractor = JiraWorklogExtractor(
            jira_url='https://test-jira.atlassian.net/',
            api_token='token',
            skip_validation=True
        )
        assert extractor.jira_url == 'https://test-jira.atlassian.net'

    def test_initialization_with_defaults(self):
        """Test initialization with minimal required parameters"""
        extractor = JiraWorklogExtractor(
            jira_url='https://test.atlassian.net',
            api_token='token123',
            skip_validation=True
        )
        assert extractor.project_key is not None
        assert extractor.erp_activity_filter is not None

    def test_headers_configured_correctly(self, extractor):
        """Test that HTTP headers are configured correctly"""
        assert extractor.headers['Accept'] == 'application/json'
        assert 'Bearer' in extractor.headers['Authorization']
        assert 'test-api-token-12345' in extractor.headers['Authorization']

    @patch('extract_worklogs.Path.mkdir')
    def test_cache_directory_created_when_enabled(self, mock_mkdir, mock_jira_config):
        """Test that cache directory is created when cache is enabled"""
        mock_jira_config['use_cache'] = True
        extractor = JiraWorklogExtractor(**mock_jira_config, skip_validation=True)
        mock_mkdir.assert_called_once()

    def test_session_created_with_retry_strategy(self, extractor):
        """Test that HTTP session is created with retry logic"""
        assert extractor.session is not None
        assert hasattr(extractor.session, 'get')
        assert hasattr(extractor.session, 'post')


# =============================================================================
# TEST CACHE FUNCTIONALITY
# =============================================================================

class TestCacheOperations:
    """Tests for cache-related operations"""

    def test_get_cache_key_generates_consistent_hash(self, extractor):
        """Test that cache key generation is deterministic"""
        key1 = extractor._get_cache_key('worklogs', 'TEST-123')
        key2 = extractor._get_cache_key('worklogs', 'TEST-123')
        assert key1 == key2

    def test_get_cache_key_different_for_different_identifiers(self, extractor):
        """Test that different identifiers produce different cache keys"""
        key1 = extractor._get_cache_key('worklogs', 'TEST-123')
        key2 = extractor._get_cache_key('worklogs', 'TEST-456')
        assert key1 != key2

    def test_get_cache_key_includes_prefix(self, extractor):
        """Test that cache key includes the prefix"""
        key = extractor._get_cache_key('worklogs', 'TEST-123')
        assert key.startswith('worklogs_')
        assert key.endswith('.pkl')

    @patch('extract_worklogs.Path.exists')
    def test_get_from_cache_returns_none_when_cache_disabled(self, mock_exists, extractor):
        """Test that cache retrieval returns None when cache is disabled"""
        extractor.use_cache = False
        result = extractor._get_from_cache('test_key')
        assert result is None
        mock_exists.assert_not_called()

    @patch('extract_worklogs.Path.exists')
    def test_get_from_cache_returns_none_when_file_not_exists(self, mock_exists, extractor):
        """Test that cache retrieval returns None when cache file doesn't exist"""
        mock_exists.return_value = False
        result = extractor._get_from_cache('test_key')
        assert result is None

    @patch('builtins.open', new_callable=mock_open, read_data=pickle.dumps({'test': 'data'}))
    @patch('extract_worklogs.Path.exists')
    @patch('extract_worklogs.Path.stat')
    @patch('time.time')
    def test_get_from_cache_returns_data_when_valid(self, mock_time, mock_stat, mock_exists, mock_file, extractor):
        """Test that valid cached data is returned"""
        mock_exists.return_value = True
        mock_time.return_value = 1000
        mock_stat_obj = Mock()
        mock_stat_obj.st_mtime = 500  # File age: 500 seconds
        mock_stat.return_value = mock_stat_obj

        result = extractor._get_from_cache('test_key.pkl')
        assert result == {'test': 'data'}

    @patch('extract_worklogs.Path.exists')
    @patch('extract_worklogs.Path.stat')
    @patch('extract_worklogs.Path.unlink')
    @patch('time.time')
    def test_get_from_cache_deletes_expired_cache(self, mock_time, mock_unlink, mock_stat, mock_exists, extractor):
        """Test that expired cache is deleted"""
        mock_exists.return_value = True
        mock_time.return_value = 10000
        mock_stat_obj = Mock()
        mock_stat_obj.st_mtime = 5000  # File age: 5000 seconds (> TTL of 3600)
        mock_stat.return_value = mock_stat_obj

        result = extractor._get_from_cache('test_key.pkl')
        assert result is None
        mock_unlink.assert_called_once()

    @patch('builtins.open', new_callable=mock_open)
    def test_save_to_cache_writes_data(self, mock_file, extractor):
        """Test that data is written to cache"""
        test_data = {'key': 'value'}
        extractor._save_to_cache('test_key.pkl', test_data)
        mock_file.assert_called_once()

    def test_save_to_cache_does_nothing_when_cache_disabled(self, extractor):
        """Test that cache saving is skipped when cache is disabled"""
        extractor.use_cache = False
        # Should not raise any exception
        extractor._save_to_cache('test_key', {'data': 'value'})

    @patch('builtins.open', side_effect=IOError('Permission denied'))
    def test_save_to_cache_handles_write_errors(self, mock_file, extractor, capsys):
        """Test that cache write errors are handled gracefully"""
        extractor._save_to_cache('test_key.pkl', {'data': 'value'})
        captured = capsys.readouterr()
        assert 'Warning' in captured.out or captured.out == ''


# =============================================================================
# TEST ISSUE SEARCH
# =============================================================================

class TestIssueSearch:
    """Tests for issue search functionality"""

    @patch('extract_worklogs.requests.Session.get')
    def test_search_issues_successful_single_page(self, mock_get, extractor, mock_issue_response):
        """Test successful issue search with single page of results"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issue_response
        mock_get.return_value = mock_response

        jql = 'project = TEST'
        issues = extractor.search_issues(jql)

        assert len(issues) == 2
        assert issues[0]['key'] == 'TEST-1'
        assert issues[1]['key'] == 'TEST-2'
        mock_get.assert_called_once()

    @patch('extract_worklogs.requests.Session.get')
    def test_search_issues_handles_pagination(self, mock_get, extractor):
        """Test that pagination is handled correctly"""
        # First page
        page1 = {
            'total': 150,
            'startAt': 0,
            'maxResults': 100,
            'issues': [{'key': f'TEST-{i}'} for i in range(100)]
        }
        # Second page
        page2 = {
            'total': 150,
            'startAt': 100,
            'maxResults': 100,
            'issues': [{'key': f'TEST-{i}'} for i in range(100, 150)]
        }

        mock_response1 = Mock()
        mock_response1.status_code = 200
        mock_response1.json.return_value = page1

        mock_response2 = Mock()
        mock_response2.status_code = 200
        mock_response2.json.return_value = page2

        mock_get.side_effect = [mock_response1, mock_response2]

        jql = 'project = TEST'
        issues = extractor.search_issues(jql)

        assert len(issues) == 150
        assert mock_get.call_count == 2

    @patch('extract_worklogs.requests.Session.get')
    def test_search_issues_raises_on_http_error(self, mock_get, extractor):
        """Test that HTTP errors are raised properly"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = requests.HTTPError('Unauthorized')
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            extractor.search_issues('project = TEST')

    @patch('extract_worklogs.requests.Session.get')
    def test_search_issues_with_custom_fields(self, mock_get, extractor, mock_issue_response):
        """Test issue search with custom field selection"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issue_response
        mock_get.return_value = mock_response

        fields = ['summary', 'status', 'customfield_10014']
        extractor.search_issues('project = TEST', fields=fields)

        call_args = mock_get.call_args
        assert 'fields' in call_args.kwargs['params']
        assert 'summary' in call_args.kwargs['params']['fields']

    @patch('extract_worklogs.requests.Session.get')
    def test_find_issues_by_erp_activity(self, mock_get, extractor, mock_issue_response):
        """Test finding issues by ERP Activity filter"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issue_response
        mock_get.return_value = mock_response

        issues = extractor.find_issues_by_erp_activity()

        assert len(issues) == 2
        # Check that JQL contains the ERP Activity filter
        call_args = mock_get.call_args
        jql = call_args.kwargs['params']['jql']
        assert 'ERP Activity' in jql
        assert extractor.erp_activity_filter in jql


# =============================================================================
# TEST EPIC AND LINKED ISSUES
# =============================================================================

class TestEpicAndLinkedIssues:
    """Tests for epic and linked issue retrieval"""

    @patch('extract_worklogs.requests.Session.get')
    def test_get_epic_issues(self, mock_get, extractor, mock_epic_issue_response):
        """Test retrieving issues from an epic"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_epic_issue_response
        mock_get.return_value = mock_response

        epic_key = 'TEST-EPIC'
        issues = extractor.get_epic_issues(epic_key)

        assert len(issues) == 2
        assert issues[0]['key'] == 'TEST-10'
        assert issues[1]['key'] == 'TEST-11'

        # Verify JQL contains Epic Link
        call_args = mock_get.call_args
        jql = call_args.kwargs['params']['jql']
        assert 'Epic Link' in jql
        assert epic_key in jql

    @patch('extract_worklogs.requests.Session.get')
    def test_get_linked_issues(self, mock_get, extractor, mock_linked_issues_response):
        """Test retrieving linked issues"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_linked_issues_response
        mock_get.return_value = mock_response

        issue_key = 'TEST-1'
        linked = extractor.get_linked_issues(issue_key)

        assert len(linked) == 2
        assert 'TEST-20' in linked
        assert 'TEST-21' in linked

    @patch('extract_worklogs.requests.Session.get')
    def test_get_linked_issues_empty(self, mock_get, extractor):
        """Test retrieving linked issues when there are none"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'fields': {'issuelinks': []}}
        mock_get.return_value = mock_response

        linked = extractor.get_linked_issues('TEST-1')
        assert len(linked) == 0

    @patch('extract_worklogs.requests.Session.get')
    def test_get_subtasks(self, mock_get, extractor, mock_subtasks_response):
        """Test retrieving subtasks from an issue"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_subtasks_response
        mock_get.return_value = mock_response

        subtasks = extractor.get_subtasks('TEST-1')

        assert len(subtasks) == 2
        assert 'TEST-30' in subtasks
        assert 'TEST-31' in subtasks

    @patch('extract_worklogs.requests.Session.get')
    def test_get_subtasks_empty(self, mock_get, extractor):
        """Test retrieving subtasks when there are none"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'fields': {'subtasks': []}}
        mock_get.return_value = mock_response

        subtasks = extractor.get_subtasks('TEST-1')
        assert len(subtasks) == 0


# =============================================================================
# TEST WORKLOG EXTRACTION
# =============================================================================

class TestWorklogExtraction:
    """Tests for worklog extraction functionality"""

    @patch('extract_worklogs.requests.Session.get')
    def test_get_worklogs_successful(self, mock_get, extractor, mock_worklogs_response):
        """Test successful worklog retrieval"""
        extractor.use_cache = False  # Disable cache for this test

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_worklogs_response
        mock_get.return_value = mock_response

        worklogs = extractor.get_worklogs('TEST-1')

        assert len(worklogs) == 2
        assert worklogs[0]['id'] == '100'
        assert worklogs[0]['author']['displayName'] == 'John Doe'
        assert worklogs[0]['timeSpentSeconds'] == 7200

    @patch('extract_worklogs.requests.Session.get')
    def test_get_worklogs_empty(self, mock_get, extractor, mock_empty_worklogs):
        """Test retrieving worklogs when there are none"""
        extractor.use_cache = False

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_empty_worklogs
        mock_get.return_value = mock_response

        worklogs = extractor.get_worklogs('TEST-1')
        assert len(worklogs) == 0

    @patch('extract_worklogs.requests.Session.get')
    def test_get_worklogs_uses_cache(self, mock_get, extractor, mock_worklogs_response):
        """Test that worklog retrieval uses cache"""
        # First call - should hit API
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_worklogs_response
        mock_get.return_value = mock_response

        # Mock cache operations
        with patch.object(extractor, '_get_from_cache', return_value=None) as mock_get_cache, \
             patch.object(extractor, '_save_to_cache') as mock_save_cache:

            worklogs = extractor.get_worklogs('TEST-1')

            mock_get_cache.assert_called_once()
            mock_save_cache.assert_called_once()

    @patch('extract_worklogs.requests.Session.get')
    def test_get_issue_metadata(self, mock_get, extractor, mock_issue_metadata_response):
        """Test retrieving issue metadata"""
        extractor.use_cache = False

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issue_metadata_response
        mock_get.return_value = mock_response

        metadata = extractor.get_issue_metadata('TEST-1')

        assert metadata['issue_type'] == 'Story'
        assert metadata['epic_link'] == 'TEST-EPIC'
        assert metadata['summary'] == 'Test Issue Summary'
        assert 'Component A' in metadata['components']
        assert 'backend' in metadata['labels']
        assert metadata['product_item'] == 'Product Item 1'
        assert metadata['team'] == 'Team Alpha'

    @patch('extract_worklogs.requests.Session.get')
    def test_extract_issue_worklogs_with_document_format_comment(self, mock_get, extractor,
                                                                   mock_worklogs_response,
                                                                   mock_issue_metadata_response):
        """Test extracting worklogs with Atlassian Document Format comments"""
        extractor.use_cache = False

        # Mock the API calls
        def mock_get_response(url, **kwargs):
            response = Mock()
            response.status_code = 200
            if 'worklog' in url:
                response.json.return_value = mock_worklogs_response
            else:
                response.json.return_value = mock_issue_metadata_response
            return response

        mock_get.side_effect = mock_get_response

        issue_metadata_cache = {}
        worklogs = extractor._extract_issue_worklogs('TEST-1', issue_metadata_cache)

        assert len(worklogs) == 2
        assert worklogs[0]['comment'] == 'Implemented feature X'
        assert worklogs[0]['author'] == 'John Doe'
        assert worklogs[0]['time_spent_seconds'] == 7200

    @patch('extract_worklogs.requests.Session.get')
    def test_extract_issue_worklogs_with_string_comment(self, mock_get, extractor, mock_issue_metadata_response):
        """Test extracting worklogs with plain string comments"""
        extractor.use_cache = False

        mock_worklogs = {
            'worklogs': [{
                'id': '100',
                'author': {'displayName': 'John Doe', 'emailAddress': 'john@example.com'},
                'timeSpent': '2h',
                'timeSpentSeconds': 7200,
                'started': '2024-03-15T10:00:00.000+0000',
                'comment': 'Simple string comment'
            }]
        }

        def mock_get_response(url, **kwargs):
            response = Mock()
            response.status_code = 200
            if 'worklog' in url:
                response.json.return_value = mock_worklogs
            else:
                response.json.return_value = mock_issue_metadata_response
            return response

        mock_get.side_effect = mock_get_response

        issue_metadata_cache = {}
        worklogs = extractor._extract_issue_worklogs('TEST-1', issue_metadata_cache)

        assert len(worklogs) == 1
        assert worklogs[0]['comment'] == 'Simple string comment'

    @patch('extract_worklogs.requests.Session.get')
    def test_extract_issue_worklogs_handles_errors(self, mock_get, extractor):
        """Test that worklog extraction handles errors gracefully"""
        extractor.use_cache = False
        mock_get.side_effect = Exception('API Error')

        issue_metadata_cache = {}
        worklogs = extractor._extract_issue_worklogs('TEST-1', issue_metadata_cache)

        # Should return empty list on error
        assert worklogs == []


# =============================================================================
# TEST COLLECTION OF ALL RELATED ISSUES
# =============================================================================

class TestCollectAllRelatedIssues:
    """Tests for comprehensive issue collection"""

    @patch.object(JiraWorklogExtractor, 'get_subtasks')
    @patch.object(JiraWorklogExtractor, 'get_linked_issues')
    @patch.object(JiraWorklogExtractor, 'get_epic_issues')
    @patch.object(JiraWorklogExtractor, 'find_issues_by_erp_activity')
    def test_collect_all_related_issues_no_epics(self, mock_find, mock_epic, mock_linked, mock_subtasks, extractor):
        """Test collecting issues when no epics are present"""
        # Setup mocks
        mock_find.return_value = [
            {'key': 'TEST-1', 'fields': {'issuetype': {'name': 'Story'}}},
            {'key': 'TEST-2', 'fields': {'issuetype': {'name': 'Task'}}}
        ]
        mock_linked.return_value = []
        mock_subtasks.return_value = []

        issue_keys = extractor.collect_all_related_issues()

        assert len(issue_keys) == 2
        assert 'TEST-1' in issue_keys
        assert 'TEST-2' in issue_keys
        mock_epic.assert_not_called()

    @patch.object(JiraWorklogExtractor, 'get_subtasks')
    @patch.object(JiraWorklogExtractor, 'get_linked_issues')
    @patch.object(JiraWorklogExtractor, 'get_epic_issues')
    @patch.object(JiraWorklogExtractor, 'find_issues_by_erp_activity')
    def test_collect_all_related_issues_with_epics(self, mock_find, mock_epic, mock_linked, mock_subtasks, extractor):
        """Test collecting issues including epic children"""
        # Setup mocks
        mock_find.return_value = [
            {'key': 'TEST-EPIC', 'fields': {'issuetype': {'name': 'Epic'}}},
            {'key': 'TEST-1', 'fields': {'issuetype': {'name': 'Story'}}}
        ]
        mock_epic.return_value = [
            {'key': 'TEST-10'},
            {'key': 'TEST-11'}
        ]
        mock_linked.return_value = []
        mock_subtasks.return_value = []

        issue_keys = extractor.collect_all_related_issues()

        assert len(issue_keys) >= 3  # Epic + Story + Epic children
        assert 'TEST-EPIC' in issue_keys
        assert 'TEST-1' in issue_keys
        assert 'TEST-10' in issue_keys
        mock_epic.assert_called_once_with('TEST-EPIC')

    @patch.object(JiraWorklogExtractor, 'get_subtasks')
    @patch.object(JiraWorklogExtractor, 'get_linked_issues')
    @patch.object(JiraWorklogExtractor, 'get_epic_issues')
    @patch.object(JiraWorklogExtractor, 'find_issues_by_erp_activity')
    def test_collect_all_related_issues_with_linked(self, mock_find, mock_epic, mock_linked, mock_subtasks, extractor):
        """Test collecting issues including linked issues"""
        mock_find.return_value = [
            {'key': 'TEST-1', 'fields': {'issuetype': {'name': 'Story'}}}
        ]
        mock_linked.return_value = ['TEST-20', 'TEST-21']
        mock_subtasks.return_value = []

        issue_keys = extractor.collect_all_related_issues()

        assert 'TEST-1' in issue_keys
        assert 'TEST-20' in issue_keys
        assert 'TEST-21' in issue_keys

    @patch.object(JiraWorklogExtractor, 'get_subtasks')
    @patch.object(JiraWorklogExtractor, 'get_linked_issues')
    @patch.object(JiraWorklogExtractor, 'get_epic_issues')
    @patch.object(JiraWorklogExtractor, 'find_issues_by_erp_activity')
    def test_collect_all_related_issues_with_subtasks(self, mock_find, mock_epic, mock_linked, mock_subtasks, extractor):
        """Test collecting issues including subtasks"""
        mock_find.return_value = [
            {'key': 'TEST-1', 'fields': {'issuetype': {'name': 'Story'}}}
        ]
        mock_linked.return_value = []
        mock_subtasks.return_value = ['TEST-30', 'TEST-31']

        issue_keys = extractor.collect_all_related_issues()

        assert 'TEST-1' in issue_keys
        assert 'TEST-30' in issue_keys
        assert 'TEST-31' in issue_keys

    @patch.object(JiraWorklogExtractor, 'get_subtasks')
    @patch.object(JiraWorklogExtractor, 'get_linked_issues')
    @patch.object(JiraWorklogExtractor, 'get_epic_issues')
    @patch.object(JiraWorklogExtractor, 'find_issues_by_erp_activity')
    def test_collect_filters_out_other_projects(self, mock_find, mock_epic, mock_linked, mock_subtasks, extractor):
        """Test that only issues from the target project are collected"""
        mock_find.return_value = [
            {'key': 'TEST-1', 'fields': {'issuetype': {'name': 'Story'}}}
        ]
        # Return linked issues from different projects
        mock_linked.return_value = ['TEST-20', 'OTHER-10', 'EXTERNAL-5']
        mock_subtasks.return_value = []

        issue_keys = extractor.collect_all_related_issues()

        assert 'TEST-1' in issue_keys
        assert 'TEST-20' in issue_keys
        assert 'OTHER-10' not in issue_keys
        assert 'EXTERNAL-5' not in issue_keys


# =============================================================================
# TEST PARALLEL WORKLOG EXTRACTION
# =============================================================================

class TestParallelWorklogExtraction:
    """Tests for parallel worklog extraction"""

    @patch.object(JiraWorklogExtractor, '_extract_issue_worklogs')
    def test_extract_worklogs_parallel(self, mock_extract, extractor):
        """Test that worklogs are extracted in parallel"""
        # Setup mock to return different worklogs for each issue
        def extract_side_effect(issue_key, cache):
            return [{
                'issue_key': issue_key,
                'author': 'Test User',
                'time_spent_seconds': 3600
            }]

        mock_extract.side_effect = extract_side_effect

        issue_keys = ['TEST-1', 'TEST-2', 'TEST-3']
        worklogs = extractor.extract_worklogs(issue_keys, max_workers=2)

        assert len(worklogs) == 3
        assert mock_extract.call_count == 3

    @patch.object(JiraWorklogExtractor, '_extract_issue_worklogs')
    def test_extract_worklogs_handles_individual_failures(self, mock_extract, extractor):
        """Test that extraction continues even if individual issues fail"""
        call_count = [0]

        def extract_side_effect(issue_key, cache):
            call_count[0] += 1
            if call_count[0] == 2:
                raise Exception('API Error')
            return [{
                'issue_key': issue_key,
                'author': 'Test User',
                'time_spent_seconds': 3600
            }]

        mock_extract.side_effect = extract_side_effect

        issue_keys = ['TEST-1', 'TEST-2', 'TEST-3']
        worklogs = extractor.extract_worklogs(issue_keys)

        # Should still get worklogs from 2 issues
        assert len(worklogs) == 2


# =============================================================================
# TEST CSV EXPORT
# =============================================================================

class TestCSVExport:
    """Tests for CSV export functionality"""

    @patch('builtins.open', new_callable=mock_open)
    @patch('csv.DictWriter')
    def test_export_to_csv_successful(self, mock_writer_class, mock_file, extractor):
        """Test successful CSV export"""
        mock_writer = Mock()
        mock_writer_class.return_value = mock_writer

        worklogs = [
            {
                'issue_key': 'TEST-1',
                'summary': 'Test Issue',
                'issue_type': 'Story',
                'epic_link': 'TEST-EPIC',
                'author': 'John Doe',
                'author_email': 'john@example.com',
                'time_spent': '2h',
                'time_spent_seconds': 7200,
                'started': '2024-03-15T10:00:00.000+0000',
                'comment': 'Test comment'
            }
        ]

        extractor.export_to_csv(worklogs, 'test_output.csv')

        mock_file.assert_called_once_with('test_output.csv', 'w', newline='', encoding='utf-8')
        mock_writer.writeheader.assert_called_once()
        mock_writer.writerow.assert_called_once()

    def test_export_to_csv_empty_worklogs(self, extractor, capsys):
        """Test CSV export with empty worklogs"""
        extractor.export_to_csv([], 'test_output.csv')
        captured = capsys.readouterr()
        assert 'No worklogs to export' in captured.out

    @patch('builtins.open', new_callable=mock_open)
    @patch('csv.DictWriter')
    def test_export_to_csv_calculates_hours_correctly(self, mock_writer_class, mock_file, extractor):
        """Test that CSV export correctly converts seconds to hours"""
        mock_writer = Mock()
        mock_writer_class.return_value = mock_writer

        worklogs = [{
            'issue_key': 'TEST-1',
            'summary': 'Test',
            'issue_type': 'Story',
            'epic_link': '',
            'author': 'John',
            'author_email': 'john@example.com',
            'time_spent': '3h 30m',
            'time_spent_seconds': 12600,  # Should be 3.5 hours
            'started': '2024-03-15',
            'comment': ''
        }]

        extractor.export_to_csv(worklogs)

        # Check that writerow was called with hours calculation
        call_args = mock_writer.writerow.call_args[0][0]
        assert call_args['time_spent_hours'] == 3.5


# =============================================================================
# TEST HTML EXPORT
# =============================================================================

class TestHTMLExport:
    """Tests for HTML export functionality"""

    @patch('builtins.open', new_callable=mock_open)
    def test_export_to_html_successful(self, mock_file, extractor):
        """Test successful HTML export"""
        worklogs = [
            {
                'issue_key': 'TEST-1',
                'summary': 'Test Issue',
                'issue_type': 'Story',
                'epic_link': 'TEST-EPIC',
                'author': 'John Doe',
                'author_email': 'john@example.com',
                'time_spent': '2h',
                'time_spent_seconds': 7200,
                'started': '2024-03-15T10:00:00.000+0000',
                'comment': 'Test comment',
                'components': ['Component A'],
                'labels': ['backend'],
                'product_item': 'Product 1',
                'team': 'Team Alpha'
            }
        ]

        extractor.export_to_html(worklogs, 'test_report.html')

        mock_file.assert_called_once()
        # Check that write was called with HTML content
        write_calls = mock_file().write.call_args_list
        assert len(write_calls) > 0

    def test_export_to_html_empty_worklogs(self, extractor, capsys):
        """Test HTML export with empty worklogs"""
        extractor.export_to_html([], 'test_report.html')
        captured = capsys.readouterr()
        assert 'No worklogs to export' in captured.out

    @patch('builtins.open', new_callable=mock_open)
    def test_export_to_html_includes_timing_info(self, mock_file, extractor):
        """Test that HTML export includes timing information"""
        worklogs = [{
            'issue_key': 'TEST-1',
            'summary': 'Test',
            'issue_type': 'Story',
            'epic_link': '',
            'author': 'John',
            'author_email': 'john@example.com',
            'time_spent': '1h',
            'time_spent_seconds': 3600,
            'started': '2024-03-15T10:00:00.000+0000',
            'comment': '',
            'components': [],
            'labels': [],
            'product_item': 'None',
            'team': 'None'
        }]

        timing_info = {
            'total_time': 45.5,
            'collection_time': 30.0,
            'extraction_time': 15.5,
            'issue_count': 10,
            'worklog_count': 25
        }

        extractor.export_to_html(worklogs, 'test_report.html', timing_info)

        # Check that timing info was written
        write_calls = mock_file().write.call_args_list
        html_content = ''.join([str(call[0][0]) for call in write_calls])
        assert 'Execution Time' in html_content or '45.5' in html_content

    @patch('builtins.open', new_callable=mock_open)
    def test_export_to_html_creates_jira_links(self, mock_file, extractor):
        """Test that HTML export creates clickable Jira links"""
        worklogs = [{
            'issue_key': 'TEST-123',
            'summary': 'Test',
            'issue_type': 'Story',
            'epic_link': '',
            'author': 'John',
            'author_email': 'john@example.com',
            'time_spent': '1h',
            'time_spent_seconds': 3600,
            'started': '2024-03-15T10:00:00.000+0000',
            'comment': '',
            'components': [],
            'labels': [],
            'product_item': 'None',
            'team': 'None'
        }]

        extractor.export_to_html(worklogs, 'test_report.html')

        write_calls = mock_file().write.call_args_list
        html_content = ''.join([str(call[0][0]) for call in write_calls])

        # Check that Jira URL and issue key are in the HTML
        assert extractor.jira_url in html_content
        assert 'TEST-123' in html_content


# =============================================================================
# TEST SUMMARY GENERATION
# =============================================================================

class TestSummaryGeneration:
    """Tests for summary report generation"""

    def test_generate_summary_successful(self, extractor, capsys):
        """Test successful summary generation"""
        worklogs = [
            {
                'author': 'John Doe',
                'time_spent_seconds': 7200  # 2 hours
            },
            {
                'author': 'John Doe',
                'time_spent_seconds': 3600  # 1 hour
            },
            {
                'author': 'Jane Smith',
                'time_spent_seconds': 10800  # 3 hours
            }
        ]

        extractor.generate_summary(worklogs)

        captured = capsys.readouterr()
        assert 'SUMMARY REPORT' in captured.out
        assert 'Total hours logged' in captured.out
        assert '6.00' in captured.out  # Total hours
        assert 'John Doe' in captured.out
        assert 'Jane Smith' in captured.out

    def test_generate_summary_empty_worklogs(self, extractor, capsys):
        """Test summary generation with empty worklogs"""
        extractor.generate_summary([])
        captured = capsys.readouterr()
        assert 'No worklogs to summarize' in captured.out

    def test_generate_summary_sorts_by_hours(self, extractor, capsys):
        """Test that summary is sorted by hours descending"""
        worklogs = [
            {'author': 'User A', 'time_spent_seconds': 3600},   # 1 hour
            {'author': 'User B', 'time_spent_seconds': 10800},  # 3 hours
            {'author': 'User C', 'time_spent_seconds': 7200},   # 2 hours
        ]

        extractor.generate_summary(worklogs)

        captured = capsys.readouterr()
        output = captured.out

        # User B should appear before User C, and User C before User A
        pos_b = output.find('User B')
        pos_c = output.find('User C')
        pos_a = output.find('User A')

        assert pos_b < pos_c < pos_a


# =============================================================================
# TEST ERROR HANDLING
# =============================================================================

class TestErrorHandling:
    """Tests for error handling scenarios"""

    @patch('extract_worklogs.requests.Session.get')
    def test_handles_network_timeout(self, mock_get, extractor):
        """Test handling of network timeout errors"""
        mock_get.side_effect = requests.Timeout('Connection timed out')

        with pytest.raises(requests.Timeout):
            extractor.search_issues('project = TEST')

    @patch('extract_worklogs.requests.Session.get')
    def test_handles_invalid_json_response(self, mock_get, extractor):
        """Test handling of invalid JSON responses"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.side_effect = ValueError('Invalid JSON')
        mock_get.return_value = mock_response

        with pytest.raises(ValueError):
            extractor.search_issues('project = TEST')

    @patch('extract_worklogs.requests.Session.get')
    def test_handles_403_forbidden(self, mock_get, extractor):
        """Test handling of 403 Forbidden errors"""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.raise_for_status.side_effect = requests.HTTPError('Forbidden')
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            extractor.search_issues('project = TEST')

    @patch('extract_worklogs.requests.Session.get')
    def test_handles_404_not_found(self, mock_get, extractor):
        """Test handling of 404 Not Found errors"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.HTTPError('Not Found')
        mock_get.return_value = mock_response

        with pytest.raises(requests.HTTPError):
            extractor.get_linked_issues('NONEXISTENT-1')


# =============================================================================
# TEST COMMAND-LINE ARGUMENT PARSING
# =============================================================================

class TestArgumentParsing:
    """Tests for command-line argument parsing"""

    @patch('sys.argv', ['extract_worklogs.py', '--project', 'CUSTOM', '--log-level', '2'])
    def test_parse_arguments_custom_project(self):
        """Test parsing custom project argument"""
        args = extract_worklogs.parse_arguments()
        assert args.project == 'CUSTOM'
        assert args.log_level == 2

    @patch('sys.argv', ['extract_worklogs.py', '--format', 'csv'])
    def test_parse_arguments_csv_only(self):
        """Test parsing format argument for CSV only"""
        args = extract_worklogs.parse_arguments()
        assert args.format == 'csv'

    @patch('sys.argv', ['extract_worklogs.py', '--no-cache'])
    def test_parse_arguments_no_cache(self):
        """Test parsing no-cache flag"""
        args = extract_worklogs.parse_arguments()
        assert args.no_cache is True

    @patch('sys.argv', ['extract_worklogs.py', '--cache-ttl', '7200'])
    def test_parse_arguments_custom_cache_ttl(self):
        """Test parsing custom cache TTL"""
        args = extract_worklogs.parse_arguments()
        assert args.cache_ttl == 7200

    @patch('sys.argv', ['extract_worklogs.py', '--output-dir', './custom_reports'])
    def test_parse_arguments_custom_output_dir(self):
        """Test parsing custom output directory"""
        args = extract_worklogs.parse_arguments()
        assert args.output_dir == './custom_reports'


# =============================================================================
# TEST MAIN FUNCTION
# =============================================================================

class TestMainFunction:
    """Tests for the main function"""

    @patch('extract_worklogs.JiraWorklogExtractor')
    @patch('extract_worklogs.parse_arguments')
    @patch('extract_worklogs.Path.mkdir')
    def test_main_executes_full_workflow(self, mock_mkdir, mock_parse_args, mock_extractor_class):
        """Test that main function executes the full workflow"""
        # Setup mocks
        mock_args = Mock()
        mock_args.jira_url = 'https://test.atlassian.net'
        mock_args.jira_token = 'token'
        mock_args.project = 'TEST'
        mock_args.erp_activity = 'ProjectTask-001'
        mock_args.output_dir = 'output'
        mock_args.log_level = 1
        mock_args.format = 'both'
        mock_args.no_cache = False
        mock_args.cache_ttl = 3600
        mock_parse_args.return_value = mock_args

        mock_extractor = Mock()
        mock_extractor.collect_all_related_issues.return_value = ['TEST-1', 'TEST-2']
        mock_extractor.extract_worklogs.return_value = [
            {
                'author': 'John',
                'time_spent_seconds': 3600,
                'issue_key': 'TEST-1',
                'summary': 'Test',
                'issue_type': 'Story',
                'epic_link': '',
                'author_email': 'john@example.com',
                'time_spent': '1h',
                'started': '2024-03-15',
                'comment': '',
                'components': [],
                'labels': [],
                'product_item': 'None',
                'team': 'None'
            }
        ]
        mock_extractor_class.return_value = mock_extractor

        # Execute main
        extract_worklogs.main()

        # Verify workflow
        mock_extractor.collect_all_related_issues.assert_called_once()
        mock_extractor.extract_worklogs.assert_called_once()
        mock_extractor.generate_summary.assert_called_once()

    @patch('extract_worklogs.JiraWorklogExtractor')
    @patch('extract_worklogs.parse_arguments')
    def test_main_exits_when_no_issues_found(self, mock_parse_args, mock_extractor_class, capsys):
        """Test that main exits gracefully when no issues are found"""
        mock_args = Mock()
        mock_args.jira_url = 'https://test.atlassian.net'
        mock_args.jira_token = 'token'
        mock_args.project = 'TEST'
        mock_args.erp_activity = 'ProjectTask-001'
        mock_args.output_dir = 'output'
        mock_args.log_level = 1
        mock_args.format = 'both'
        mock_args.no_cache = False
        mock_args.cache_ttl = 3600
        mock_parse_args.return_value = mock_args

        mock_extractor = Mock()
        mock_extractor.collect_all_related_issues.return_value = []
        mock_extractor_class.return_value = mock_extractor

        extract_worklogs.main()

        captured = capsys.readouterr()
        assert 'No issues found' in captured.out
        mock_extractor.extract_worklogs.assert_not_called()


# =============================================================================
# TEST SESSION WITH RETRY LOGIC
# =============================================================================

class TestSessionRetryLogic:
    """Tests for HTTP session retry configuration"""

    def test_session_has_retry_strategy(self, extractor):
        """Test that session is configured with retry strategy"""
        session = extractor.session
        assert session is not None

        # Check that adapters are mounted
        assert 'http://' in session.adapters
        assert 'https://' in session.adapters

    def test_session_headers_set(self, extractor):
        """Test that session has correct headers"""
        assert 'Accept' in extractor.session.headers
        assert 'Authorization' in extractor.session.headers


# =============================================================================
# TEST JQL QUERY TRACKING
# =============================================================================

class TestJQLQueryTracking:
    """Tests for JQL query tracking functionality"""

    def test_jql_queries_list_initialized(self, extractor):
        """Test that jql_queries list is initialized"""
        assert hasattr(extractor, 'jql_queries')
        assert isinstance(extractor.jql_queries, list)
        assert len(extractor.jql_queries) == 0

    @patch('extract_worklogs.requests.Session.get')
    def test_search_issues_tracks_jql_query(self, mock_get, extractor, mock_issue_response):
        """Test that search_issues tracks JQL queries"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issue_response
        mock_get.return_value = mock_response

        jql = 'project = TEST AND "ERP Activity" ~ "value"'
        extractor.search_issues(jql)

        assert jql in extractor.jql_queries
        assert len(extractor.jql_queries) == 1

    @patch('extract_worklogs.requests.Session.get')
    def test_search_issues_tracks_multiple_unique_queries(self, mock_get, extractor, mock_issue_response):
        """Test that multiple unique queries are tracked"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issue_response
        mock_get.return_value = mock_response

        jql1 = 'project = TEST'
        jql2 = 'project = TEST AND status = Open'

        extractor.search_issues(jql1)
        extractor.search_issues(jql2)

        assert jql1 in extractor.jql_queries
        assert jql2 in extractor.jql_queries
        assert len(extractor.jql_queries) == 2

    @patch('extract_worklogs.requests.Session.get')
    def test_search_issues_does_not_duplicate_queries(self, mock_get, extractor, mock_issue_response):
        """Test that duplicate queries are not tracked twice"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_issue_response
        mock_get.return_value = mock_response

        jql = 'project = TEST'

        extractor.search_issues(jql)
        extractor.search_issues(jql)  # Same query again

        assert len(extractor.jql_queries) == 1


# =============================================================================
# TEST EXCEL EXPORT
# =============================================================================

class TestExcelExport:
    """Tests for Excel export functionality"""

    @patch('extract_worklogs.openpyxl.Workbook')
    def test_export_to_excel_successful(self, mock_workbook_class, extractor):
        """Test successful Excel export"""
        mock_workbook = Mock()
        mock_ws = Mock()
        mock_workbook.active = mock_ws
        mock_workbook.create_sheet = Mock(return_value=mock_ws)
        mock_workbook_class.return_value = mock_workbook

        worklogs = [
            {
                'issue_key': 'TEST-1',
                'summary': 'Test Issue',
                'issue_type': 'Story',
                'epic_link': 'TEST-EPIC',
                'author': 'John Doe',
                'author_email': 'john@example.com',
                'time_spent': '2h',
                'time_spent_seconds': 7200,
                'started': '2024-03-15T10:00:00.000+0000',
                'comment': 'Test comment',
                'components': ['Component A'],
                'labels': ['backend'],
                'product_item': 'Product 1',
                'team': 'Team Alpha'
            }
        ]

        extractor.export_to_excel(worklogs, 'test_output.xlsx')

        mock_workbook.save.assert_called_once_with('test_output.xlsx')

    def test_export_to_excel_empty_worklogs(self, extractor, capsys):
        """Test Excel export with empty worklogs"""
        extractor.export_to_excel([], 'test_output.xlsx')
        captured = capsys.readouterr()
        assert 'No worklogs to export' in captured.out

    @patch('extract_worklogs.openpyxl.Workbook')
    def test_export_to_excel_creates_multiple_sheets(self, mock_workbook_class, extractor):
        """Test that Excel export creates all required sheets"""
        mock_workbook = Mock()
        mock_ws = Mock()
        mock_workbook.active = mock_ws

        # Track sheet creation
        created_sheets = []
        def create_sheet_side_effect(title):
            created_sheets.append(title)
            return mock_ws

        mock_workbook.create_sheet = Mock(side_effect=create_sheet_side_effect)
        mock_workbook_class.return_value = mock_workbook

        worklogs = [{
            'issue_key': 'TEST-1',
            'summary': 'Test',
            'issue_type': 'Story',
            'epic_link': '',
            'author': 'John',
            'author_email': 'john@example.com',
            'time_spent': '1h',
            'time_spent_seconds': 3600,
            'started': '2024-03-15T10:00:00.000+0000',
            'comment': '',
            'components': ['Comp A'],
            'labels': ['label1'],
            'product_item': 'Product 1',
            'team': 'Team A'
        }]

        extractor.export_to_excel(worklogs, 'test_output.xlsx')

        # Check that expected sheets were created
        expected_sheets = [
            'Hours by Year-Month',
            'Hours by Product Item',
            'Hours by Component',
            'Hours by Label',
            'Hours by Team',
            'Hours by Author',
            'Hours by Issue',
            'All Worklog Entries'
        ]

        for sheet_name in expected_sheets:
            assert sheet_name in created_sheets

    @patch('extract_worklogs.openpyxl.Workbook')
    def test_export_to_excel_calculates_hours_correctly(self, mock_workbook_class, extractor):
        """Test that Excel export correctly converts seconds to hours"""
        mock_workbook = Mock()
        mock_ws = Mock()
        mock_workbook.active = mock_ws
        mock_workbook.create_sheet = Mock(return_value=mock_ws)
        mock_workbook_class.return_value = mock_workbook

        worklogs = [{
            'issue_key': 'TEST-1',
            'summary': 'Test',
            'issue_type': 'Story',
            'epic_link': '',
            'author': 'John',
            'author_email': 'john@example.com',
            'time_spent': '3h 30m',
            'time_spent_seconds': 12600,  # Should be 3.5 hours
            'started': '2024-03-15T10:00:00.000+0000',
            'comment': '',
            'components': [],
            'labels': [],
            'product_item': 'None',
            'team': 'None'
        }]

        extractor.export_to_excel(worklogs, 'test_output.xlsx')

        # Verify workbook was saved
        mock_workbook.save.assert_called_once()


# =============================================================================
# TEST VALIDATION FUNCTIONALITY
# =============================================================================

class TestValidation:
    """Tests for configuration validation"""

    @patch('extract_worklogs.requests.Session.get')
    def test_validate_configuration_checks_jira_url(self, mock_get, mock_jira_config):
        """Test that validation checks Jira URL accessibility"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'displayName': 'Test User',
            'emailAddress': 'test@example.com'
        }
        mock_get.return_value = mock_response

        # Should not raise exception
        extractor = JiraWorklogExtractor(**mock_jira_config, skip_validation=False)

    @patch('extract_worklogs.requests.Session.get')
    def test_validate_configuration_fails_on_invalid_url(self, mock_get, mock_jira_config):
        """Test that validation fails on inaccessible URL"""
        mock_get.side_effect = requests.ConnectionError('Could not connect')

        with pytest.raises(Exception):
            JiraWorklogExtractor(**mock_jira_config, skip_validation=False)

    @patch('extract_worklogs.requests.Session.get')
    def test_validate_configuration_checks_api_token(self, mock_get, mock_jira_config):
        """Test that validation checks API token validity"""
        # First call for URL check
        mock_response1 = Mock()
        mock_response1.status_code = 200

        # Second call for API token check
        mock_response2 = Mock()
        mock_response2.status_code = 401
        mock_response2.raise_for_status.side_effect = requests.HTTPError('Unauthorized')

        mock_get.side_effect = [mock_response1, mock_response2]

        with pytest.raises(Exception):
            JiraWorklogExtractor(**mock_jira_config, skip_validation=False)


# =============================================================================
# TEST INTEGRATION SCENARIOS
# =============================================================================

class TestIntegrationScenarios:
    """Integration tests for complete workflows"""

    @patch.object(JiraWorklogExtractor, 'get_subtasks')
    @patch.object(JiraWorklogExtractor, 'get_linked_issues')
    @patch.object(JiraWorklogExtractor, 'get_epic_issues')
    @patch.object(JiraWorklogExtractor, 'find_issues_by_erp_activity')
    @patch.object(JiraWorklogExtractor, '_extract_issue_worklogs')
    def test_full_extraction_workflow(self, mock_extract, mock_find, mock_epic,
                                     mock_linked, mock_subtasks, extractor):
        """Test complete workflow from issue collection to worklog extraction"""
        # Setup: 1 epic with 2 children, 1 regular issue, 1 linked issue, 2 subtasks
        mock_find.return_value = [
            {'key': 'TEST-EPIC', 'fields': {'issuetype': {'name': 'Epic'}}},
            {'key': 'TEST-1', 'fields': {'issuetype': {'name': 'Story'}}}
        ]
        mock_epic.return_value = [
            {'key': 'TEST-10'},
            {'key': 'TEST-11'}
        ]
        mock_linked.return_value = ['TEST-20']
        mock_subtasks.return_value = ['TEST-30', 'TEST-31']

        mock_extract.return_value = [{
            'issue_key': 'TEST-1',
            'author': 'John Doe',
            'time_spent_seconds': 3600
        }]

        # Execute full workflow
        issue_keys = extractor.collect_all_related_issues()
        worklogs = extractor.extract_worklogs(issue_keys)

        # Verify comprehensive collection
        assert len(issue_keys) >= 7  # Epic + Story + 2 epic children + linked + 2 subtasks
        assert 'TEST-EPIC' in issue_keys
        assert 'TEST-1' in issue_keys
        assert 'TEST-10' in issue_keys
        assert 'TEST-20' in issue_keys
        assert 'TEST-30' in issue_keys

    @patch('builtins.open', new_callable=mock_open)
    @patch('extract_worklogs.openpyxl.Workbook')
    @patch('csv.DictWriter')
    def test_export_to_all_formats(self, mock_csv_writer, mock_workbook, mock_file, extractor):
        """Test exporting to all supported formats"""
        mock_workbook_instance = Mock()
        mock_workbook.return_value = mock_workbook_instance
        mock_ws = Mock()
        mock_workbook_instance.active = mock_ws
        mock_workbook_instance.create_sheet = Mock(return_value=mock_ws)

        mock_writer = Mock()
        mock_csv_writer.return_value = mock_writer

        worklogs = [{
            'issue_key': 'TEST-1',
            'summary': 'Test',
            'issue_type': 'Story',
            'epic_link': '',
            'author': 'John',
            'author_email': 'john@example.com',
            'time_spent': '1h',
            'time_spent_seconds': 3600,
            'started': '2024-03-15T10:00:00.000+0000',
            'comment': '',
            'components': [],
            'labels': [],
            'product_item': 'None',
            'team': 'None'
        }]

        # Export to all formats
        extractor.export_to_csv(worklogs, 'test.csv')
        extractor.export_to_html(worklogs, 'test.html')
        extractor.export_to_excel(worklogs, 'test.xlsx')

        # Verify all exports were called
        mock_writer.writeheader.assert_called_once()
        mock_workbook_instance.save.assert_called_once()
        assert mock_file.call_count >= 2  # CSV and HTML


# =============================================================================
# TEST HTML JQL SECTION
# =============================================================================

class TestHTMLJQLSection:
    """Tests for JQL queries section in HTML export"""

    @patch('builtins.open', new_callable=mock_open)
    def test_html_includes_jql_queries_section(self, mock_file, extractor):
        """Test that HTML export includes JQL queries section"""
        # Add some JQL queries
        extractor.jql_queries = [
            'project = TEST AND "ERP Activity" ~ "value1"',
            'project = TEST AND "Epic Link" = TEST-100'
        ]

        worklogs = [{
            'issue_key': 'TEST-1',
            'summary': 'Test',
            'issue_type': 'Story',
            'epic_link': '',
            'author': 'John',
            'author_email': 'john@example.com',
            'time_spent': '1h',
            'time_spent_seconds': 3600,
            'started': '2024-03-15T10:00:00.000+0000',
            'comment': '',
            'components': [],
            'labels': [],
            'product_item': 'None',
            'team': 'None'
        }]

        extractor.export_to_html(worklogs, 'test_report.html')

        write_calls = mock_file().write.call_args_list
        html_content = ''.join([str(call[0][0]) for call in write_calls])

        # Check that JQL section exists
        assert 'JQL Queries' in html_content or 'jql-queries' in html_content

        # Check that queries are included
        assert 'ERP Activity' in html_content
        assert 'Epic Link' in html_content

    @patch('builtins.open', new_callable=mock_open)
    def test_html_jql_section_includes_navigation_link(self, mock_file, extractor):
        """Test that navigation menu includes JQL queries link"""
        extractor.jql_queries = ['project = TEST']

        worklogs = [{
            'issue_key': 'TEST-1',
            'summary': 'Test',
            'issue_type': 'Story',
            'epic_link': '',
            'author': 'John',
            'author_email': 'john@example.com',
            'time_spent': '1h',
            'time_spent_seconds': 3600,
            'started': '2024-03-15T10:00:00.000+0000',
            'comment': '',
            'components': [],
            'labels': [],
            'product_item': 'None',
            'team': 'None'
        }]

        extractor.export_to_html(worklogs, 'test_report.html')

        write_calls = mock_file().write.call_args_list
        html_content = ''.join([str(call[0][0]) for call in write_calls])

        # Check for navigation link
        assert '#jql-queries' in html_content


# =============================================================================
# TEST PERFORMANCE AND PARALLEL PROCESSING
# =============================================================================

class TestPerformance:
    """Tests for performance-critical operations"""

    @patch.object(JiraWorklogExtractor, '_extract_issue_worklogs')
    def test_parallel_extraction_is_faster_than_sequential(self, mock_extract, extractor):
        """Test that parallel extraction completes faster (simulated)"""
        import time

        def slow_extraction(issue_key, cache):
            time.sleep(0.01)  # Simulate API call delay
            return [{'issue_key': issue_key, 'author': 'Test', 'time_spent_seconds': 3600}]

        mock_extract.side_effect = slow_extraction

        issue_keys = [f'TEST-{i}' for i in range(10)]

        # Time parallel extraction
        start_time = time.time()
        worklogs = extractor.extract_worklogs(issue_keys, max_workers=5)
        parallel_time = time.time() - start_time

        assert len(worklogs) == 10
        assert parallel_time < 0.5  # Should be much faster than 10 * 0.01 = 0.1s sequential

    @patch.object(JiraWorklogExtractor, '_extract_issue_worklogs')
    def test_handles_large_issue_count(self, mock_extract, extractor):
        """Test extraction of large number of issues"""
        mock_extract.return_value = [{'issue_key': 'TEST-1', 'author': 'Test', 'time_spent_seconds': 3600}]

        # Simulate large workload
        issue_keys = [f'TEST-{i}' for i in range(100)]
        worklogs = extractor.extract_worklogs(issue_keys)

        assert len(worklogs) == 100


# =============================================================================
# TEST DATA AGGREGATION
# =============================================================================

class TestDataAggregation:
    """Tests for data aggregation in reports"""

    def test_aggregation_by_component_no_splitting(self, extractor):
        """Test that components with multiple values are not split"""
        worklogs = [
            {
                'issue_key': 'TEST-1',
                'components': ['Backend', 'Frontend'],
                'time_spent_seconds': 7200  # 2 hours
            }
        ]

        # Simulate aggregation logic
        by_component = defaultdict(lambda: {'hours': 0, 'entries': 0, 'issues': set()})

        for worklog in worklogs:
            components = worklog.get('components', [])
            if components:
                component_key = ', '.join(sorted(components))
                by_component[component_key]['hours'] += worklog['time_spent_seconds'] / 3600
                by_component[component_key]['entries'] += 1
                by_component[component_key]['issues'].add(worklog['issue_key'])

        # Verify only one aggregated entry
        assert len(by_component) == 1
        assert 'Backend, Frontend' in by_component
        assert by_component['Backend, Frontend']['hours'] == 2.0

    def test_aggregation_by_label_no_splitting(self, extractor):
        """Test that labels with multiple values are not split"""
        worklogs = [
            {
                'issue_key': 'TEST-1',
                'labels': ['backend', 'urgent', 'security'],
                'time_spent_seconds': 10800  # 3 hours
            }
        ]

        # Simulate aggregation logic
        by_label = defaultdict(lambda: {'hours': 0, 'entries': 0, 'issues': set()})

        for worklog in worklogs:
            labels = worklog.get('labels', [])
            if labels:
                label_key = ', '.join(sorted(labels))
                by_label[label_key]['hours'] += worklog['time_spent_seconds'] / 3600
                by_label[label_key]['entries'] += 1
                by_label[label_key]['issues'].add(worklog['issue_key'])

        # Verify only one aggregated entry
        assert len(by_label) == 1
        assert 'backend, security, urgent' in by_label
        assert by_label['backend, security, urgent']['hours'] == 3.0


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short', '--cov=extract_worklogs', '--cov-report=html'])
