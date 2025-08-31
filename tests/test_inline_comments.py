#!/usr/bin/env python3
"""
Unit tests for inline comments functionality in the Gerrit MCP Server.

Tests the new inline comments retrieval feature added to fetch_gerrit_change.
"""

import pytest
from unittest.mock import Mock, patch

# Import the modules we're testing
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server import fetch_gerrit_change


class TestInlineComments:
    """Test inline comments functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        context = Mock()
        return context

    @pytest.fixture
    def sample_change_info(self):
        """Sample change info response from Gerrit API."""
        return {
            "id": "test~master~I1234567890abcdef",
            "project": "test",
            "branch": "master",
            "change_id": "I1234567890abcdef",
            "subject": "Test change",
            "status": "NEW",
            "current_revision": "abc123def456",
            "revisions": {
                "abc123def456": {
                    "kind": "REWORK",
                    "_number": 1,
                    "files": {
                        "test.cpp": {
                            "lines_inserted": 5,
                            "lines_deleted": 2
                        }
                    }
                },
                "def456abc123": {
                    "kind": "REWORK",
                    "_number": 2,
                    "files": {
                        "test.cpp": {
                            "lines_inserted": 7,
                            "lines_deleted": 3
                        }
                    }
                }
            }
        }

    @pytest.fixture
    def sample_inline_comments(self):
        """Sample inline comments response from Gerrit API."""
        return {
            "test.cpp": [
                {
                    "author": {
                        "_account_id": 1000001,
                        "name": "Test Reviewer",
                        "email": "test.reviewer@example.com",
                        "username": "test_reviewer"
                    },
                    "id": "comment_id_123",
                    "line": 42,
                    "message": "Consider using std::find_if() here",
                    "updated": "2025-08-18 10:00:00.000000000",
                    "unresolved": True
                }
            ]
        }

    @pytest.fixture
    def sample_diff_info(self):
        """Sample diff info response from Gerrit API."""
        return {
            "meta_a": {
                "name": "test.cpp",
                "content_type": "text/x-c++src",
                "lines": 100
            },
            "meta_b": {
                "name": "test.cpp", 
                "content_type": "text/x-c++src",
                "lines": 103
            },
            "change_type": "MODIFIED",
            "content": [
                {
                    "ab": ["line 1", "line 2"]
                },
                {
                    "a": ["old line"],
                    "b": ["new line"]
                }
            ]
        }

    @patch('server.make_gerrit_rest_request')
    def test_fetch_change_with_inline_comments_success(
        self,
        mock_request,
        mock_context,
        sample_change_info,
        sample_inline_comments,
        sample_diff_info
    ):
        """Test successful retrieval of change with inline comments."""
        # Mock the API responses - change info, diff info, then comments
        mock_request.side_effect = [
            sample_change_info,  # First call for change info
            sample_diff_info,    # Second call for file diff
            sample_inline_comments  # Third call for inline comments
        ]

        # Call the function directly with comments enabled
        result = fetch_gerrit_change(mock_context, "12345", include_comments=True)

        # Verify the result structure
        assert "change_info" in result
        assert "inline_comments" in result
        assert result["inline_comments"] == sample_inline_comments
        
        # Verify comments API was called
        comments_call_found = False
        for call in mock_request.call_args_list:
            if "comments" in call[0][1]:
                comments_call_found = True
                break
        assert comments_call_found, "Comments API should have been called"

    @patch('server.make_gerrit_rest_request')
    def test_fetch_change_with_comments_disabled(
        self,
        mock_request,
        mock_context,
        sample_change_info,
        sample_diff_info
    ):
        """Test fetching change with inline comments disabled."""
        # Mock the API responses - only change info and diff, no comments call
        mock_request.side_effect = [
            sample_change_info,  # First call for change info
            sample_diff_info     # Second call for file diff
        ]

        # Call the function with include_comments=False
        result = fetch_gerrit_change(mock_context, "12345", include_comments=False)

        # Verify the result structure - should have empty inline_comments
        assert "change_info" in result
        assert "inline_comments" in result
        assert result["inline_comments"] == {}
        
        # Verify comments API was NOT called
        comments_call_found = False
        for call in mock_request.call_args_list:
            if "comments" in call[0][1]:
                comments_call_found = True
                break
        assert not comments_call_found, "Comments API should NOT have been called"

    @patch('server.make_gerrit_rest_request')
    def test_fetch_change_default_behavior_no_comments(
        self,
        mock_request,
        mock_context,
        sample_change_info,
        sample_diff_info
    ):
        """Test that the default behavior is to NOT include comments."""
        # Mock the API responses - only change info and diff, no comments call
        mock_request.side_effect = [
            sample_change_info,  # First call for change info
            sample_diff_info     # Second call for file diff
        ]

        # Call the function with default parameters (should not include comments)
        result = fetch_gerrit_change(mock_context, "12345")

        # Verify the result structure - should have empty inline_comments
        assert "change_info" in result
        assert "inline_comments" in result
        assert result["inline_comments"] == {}
        
        # Verify comments API was NOT called
        comments_call_found = False
        for call in mock_request.call_args_list:
            if "comments" in call[0][1]:
                comments_call_found = True
                break
        assert not comments_call_found, "Comments API should NOT have been called by default"

    @patch('server.make_gerrit_rest_request')
    def test_fetch_change_with_comments_enabled_explicitly(
        self,
        mock_request,
        mock_context,
        sample_change_info,
        sample_inline_comments,
        sample_diff_info
    ):
        """Test fetching change with inline comments explicitly enabled."""
        # Mock the API responses
        mock_request.side_effect = [
            sample_change_info,
            sample_diff_info,
            sample_inline_comments
        ]

        # Call the function with include_comments=True (explicit)
        result = fetch_gerrit_change(mock_context, "12345", include_comments=True)

        # Verify the result structure
        assert "change_info" in result
        assert "inline_comments" in result
        assert result["inline_comments"] == sample_inline_comments

    @patch('server.make_gerrit_rest_request')
    def test_fetch_change_inline_comments_api_failure(
        self,
        mock_request,
        mock_context,
        sample_change_info,
        sample_diff_info
    ):
        """Test handling of inline comments API failure."""
        # Mock the API responses - change info and diff succeed, comments fail
        def side_effect(*args, **kwargs):
            if "comments" in args[1]:
                raise Exception("API Error: Comments endpoint failed")
            elif "diff" in args[1]:
                return sample_diff_info
            else:
                return sample_change_info

        mock_request.side_effect = side_effect

        # Call the function with comments enabled - should not raise exception
        result = fetch_gerrit_change(mock_context, "12345", include_comments=True)

        # Verify the result structure - should have empty inline_comments
        assert "change_info" in result
        assert "inline_comments" in result
        assert result["inline_comments"] == {}

    @patch('server.make_gerrit_rest_request')
    @patch('server.logger')
    def test_inline_comments_logging_on_failure(
        self, 
        mock_logger, 
        mock_request, 
        mock_context, 
        sample_change_info,
        sample_diff_info
    ):
        """Test that inline comments API failures are properly logged."""
        # Mock the API responses - change info and diff succeed, comments fail
        def side_effect(*args, **kwargs):
            if "comments" in args[1]:
                raise Exception("Network timeout")
            elif "diff" in args[1]:
                return sample_diff_info
            else:
                return sample_change_info

        mock_request.side_effect = side_effect

        # Call the function with comments enabled
        fetch_gerrit_change(mock_context, "12345", include_comments=True)

        # Verify that a warning was logged
        mock_logger.warning.assert_called_once()
        warning_call = mock_logger.warning.call_args[0][0]
        assert "Failed to fetch inline comments for change 12345" in warning_call
        assert "Network timeout" in warning_call

    def test_inline_comments_structure_validation(self, sample_inline_comments):
        """Test that inline comments have the expected structure."""
        # Verify the structure of our sample data
        assert isinstance(sample_inline_comments, dict)
        
        for file_path, comments in sample_inline_comments.items():
            assert isinstance(file_path, str)
            assert isinstance(comments, list)
            
            for comment in comments:
                # Required fields
                assert "author" in comment
                assert "id" in comment
                assert "message" in comment
                assert "updated" in comment
                
                # Author structure
                author = comment["author"]
                assert "_account_id" in author
                assert "name" in author
                assert "email" in author
                
                # Optional fields that might be present
                if "line" in comment:
                    assert isinstance(comment["line"], int)
                if "unresolved" in comment:
                    assert isinstance(comment["unresolved"], bool)


class TestInlineCommentsIntegration:
    """Integration tests for inline comments functionality."""

    @pytest.fixture
    def mock_context(self):
        """Create a mock MCP context."""
        context = Mock()
        return context

    @pytest.fixture
    def sample_change_info(self):
        """Sample change info response from Gerrit API."""
        return {
            "id": "test~master~I1234567890abcdef",
            "project": "test",
            "branch": "master",
            "change_id": "I1234567890abcdef",
            "subject": "Test change",
            "status": "NEW",
            "current_revision": "abc123def456",
            "revisions": {
                "abc123def456": {
                    "kind": "REWORK",
                    "_number": 1,
                    "files": {
                        "test.cpp": {
                            "lines_inserted": 5,
                            "lines_deleted": 2
                        }
                    }
                }
            }
        }

    @pytest.fixture
    def sample_inline_comments(self):
        """Sample inline comments response from Gerrit API."""
        return {
            "test.cpp": [
                {
                    "author": {
                        "_account_id": 1000001,
                        "name": "Test Reviewer",
                        "email": "test.reviewer@example.com",
                        "username": "test_reviewer"
                    },
                    "id": "comment_id_123",
                    "line": 42,
                    "message": "Consider using std::find_if() here",
                    "updated": "2025-08-18 10:00:00.000000000",
                    "unresolved": True
                }
            ]
        }

    @pytest.fixture
    def sample_diff_info(self):
        """Sample diff info response from Gerrit API."""
        return {
            "meta_a": {"name": "test.cpp", "content_type": "text/x-c++src", "lines": 100},
            "meta_b": {"name": "test.cpp", "content_type": "text/x-c++src", "lines": 103},
            "change_type": "MODIFIED",
            "content": [{"ab": ["line 1", "line 2"]}, {"a": ["old line"], "b": ["new line"]}]
        }

    @patch('server.make_gerrit_rest_request')
    def test_real_world_comment_structure(
        self, 
        mock_request, 
        mock_context, 
        sample_change_info, 
        sample_inline_comments,
        sample_diff_info
    ):
        """Test with a structure similar to real Gerrit inline comments."""
        # Based on the actual structure we saw from change 30701
        real_world_change = {
            "id": "example-project~feature-branch~I1234567890abcdef1234567890abcdef12345678",
            "project": "example-project",
            "branch": "feature-branch",
            "change_id": "I1234567890abcdef1234567890abcdef12345678",
            "subject": "Example Issue: Fix memory management in component lifecycle",
            "status": "MERGED",
            "current_revision": "abc123def456789012345678901234567890abcd",
            "revisions": {
                "abc123def456789012345678901234567890abcd": {
                    "kind": "REWORK",
                    "_number": 1,
                    "files": {
                        "src/components/example_component.cpp": {
                            "lines_inserted": 9,
                            "lines_deleted": 9
                        }
                    }
                }
            }
        }

        real_world_comments = {
            "src/components/example_component.cpp": [
                {
                    "author": {
                        "_account_id": 1000010,
                        "name": "John Reviewer",
                        "email": "john.reviewer@example.com",
                        "username": "jreviewer"
                    },
                    "id": "1c02a99d_36313d4d",
                    "line": 245,
                    "range": {
                        "start_line": 235,
                        "start_character": 0,
                        "end_line": 245,
                        "end_character": 7
                    },
                    "updated": "2025-08-18 01:16:55.830000000",
                    "message": "[0] You could have changed this to std::find_if()",
                    "unresolved": True
                }
            ]
        }

        # Mock the API responses
        mock_request.side_effect = [
            real_world_change, 
            sample_diff_info,  # Mock diff for the cpp file
            real_world_comments
        ]

        # Call the function with comments enabled
        result = fetch_gerrit_change(mock_context, "12345", include_comments=True)

        # Verify the result
        assert "inline_comments" in result
        
        comments = result["inline_comments"]
        assert "src/components/example_component.cpp" in comments
        
        cpp_comments = comments["src/components/example_component.cpp"]
        assert len(cpp_comments) == 1
        
        comment = cpp_comments[0]
        assert comment["author"]["name"] == "John Reviewer"
        assert comment["line"] == 245
        assert "std::find_if()" in comment["message"]
        assert comment["unresolved"] is True


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])