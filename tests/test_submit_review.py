#!/usr/bin/env python3
"""Tests for review submission utilities."""

from types import SimpleNamespace

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from server import (
    build_review_comments,
    submit_gerrit_review,
)


class TestBuildReviewComments:
    """Validate comment payload transformation logic."""

    def test_empty_comments_returns_empty_mapping(self):
        assert build_review_comments(None) == {}
        assert build_review_comments([]) == {}

    def test_comment_payload_structure(self):
        comments = [
            {"path": "a/file.py", "line": 12, "message": "Fix this"},
            {"path": "a/file.py", "line": 18, "message": "Another"},
            {"path": "b/file.py", "message": "File level"},
        ]

        expected = {
            "a/file.py": [
                {"line": 12, "message": "Fix this"},
                {"line": 18, "message": "Another"},
            ],
            "b/file.py": [
                {"message": "File level"},
            ],
        }

        assert build_review_comments(comments) == expected

    def test_invalid_comment_raises_value_error(self):
        with pytest.raises(ValueError):
            build_review_comments([{"message": "Missing path"}])

    def test_invalid_line_value_raises_value_error(self):
        with pytest.raises(ValueError) as exc_info:
            build_review_comments([
                {"path": "file.py", "line": 0, "message": "Nope"}
            ])
        assert "line" in str(exc_info.value)

    def test_invalid_range_value_raises_value_error(self):
        with pytest.raises(ValueError) as exc_info:
            build_review_comments([
                {"path": "file.py", "range": "oops", "message": "Nope"}
            ])
        assert "range" in str(exc_info.value)


class TestSubmitGerritReview:
    """Ensure review submissions are orchestrated correctly."""

    def _dummy_ctx(self):
        return SimpleNamespace(request_context=SimpleNamespace(lifespan_context=None))

    def test_submit_review_uses_current_revision(self, monkeypatch):
        calls = []

        def fake_make_request(ctx, endpoint, *, method="GET", params=None, json_payload=None):
            calls.append((endpoint, method, json_payload))
            if method == "GET":
                return {
                    "current_revision": "rev123",
                    "revisions": {
                        "rev123": {"_number": 1}
                    },
                }
            return {"labels": {"Code-Review": 1}}

        monkeypatch.setattr("server.make_gerrit_rest_request", fake_make_request)

        result = submit_gerrit_review(
            self._dummy_ctx(),
            change_id="12345",
            message="Looks good",
            labels={"Code-Review": 1},
            comments=[{"path": "a/file.py", "message": "Nice"}],
        )

        assert result["revision"] == "rev123"
        assert len(calls) == 2
        assert calls[1][1] == "POST"
        assert calls[1][2]["labels"] == {"Code-Review": 1}

    def test_submit_review_patchset_not_found(self, monkeypatch):
        def fake_make_request(ctx, endpoint, *, method="GET", params=None, json_payload=None):
            return {
                "current_revision": "rev123",
                "revisions": {
                    "rev123": {"_number": 1}
                },
            }

        monkeypatch.setattr("server.make_gerrit_rest_request", fake_make_request)

        with pytest.raises(ValueError) as exc_info:
            submit_gerrit_review(
                self._dummy_ctx(),
                change_id="12345",
                patchset_number="999",
                message="Test",
            )

        assert "Patchset 999 not found" in str(exc_info.value)

    def test_submit_review_requires_payload(self):
        with pytest.raises(ValueError):
            submit_gerrit_review(self._dummy_ctx(), change_id="12345")

    def test_submit_review_respects_notify(self, monkeypatch):
        captured_payload = {}

        def fake_make_request(ctx, endpoint, *, method="GET", params=None, json_payload=None):
            if method == "GET":
                return {
                    "current_revision": "rev123",
                    "revisions": {
                        "rev123": {"_number": 1}
                    },
                }
            captured_payload.update(json_payload or {})
            return {}

        monkeypatch.setattr("server.make_gerrit_rest_request", fake_make_request)

        submit_gerrit_review(
            self._dummy_ctx(),
            change_id="12345",
            message="Test",
            notify="OWNER_REVIEWERS",
        )

        assert captured_payload.get("notify") == "OWNER_REVIEWERS"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
