---
"gerrit-review-mcp": patch
---

Migrate Docker integration tests from subprocess to testcontainers-python

**Core Migration:**
- Replace subprocess-based Docker commands with the Testcontainers for Python library
- Add testcontainers>=3.7.0 dependency for improved container lifecycle management
- Implement function-scoped fixtures with automatic cleanup via context managers
- Improve cross-platform compatibility by removing Linux-specific timeout dependency

**Testing Enhancements:**
- Add comprehensive health checks using wait_for_logs() with configurable timeouts
- Implement a robust Docker daemon availability check using docker ping instead of file detection
- Use command arrays for container exec operations with proper exit-code validation
- Add fallback strategies for container environment validation and error handling

**Code Quality & Configuration:**
- Replace deprecated pkg_resources with modern importlib.metadata for version checking
- Enhance requests version parsing using a PEP 440–aware strategy (packaging.version) with a regex fallback
- Fix packaging configuration to exclude non-runtime files from wheel distribution
- Add pytest configuration and comprehensive testing documentation
- Update .gitignore to exclude coverage files and AI assistant rules directory