---
"gerrit-review-mcp": minor
---

Add inline-comments retrieval support to the fetch_gerrit_change tool

- Add optional `include_comments` parameter to `fetch_gerrit_change()` function (defaults to `True`)
- Fetch inline comments from Gerrit's `/comments` REST API endpoint
- Response now includes `inline_comments` field with comment data
- Backward compatible with graceful error handling
- Includes comprehensive test coverage (7 test cases)