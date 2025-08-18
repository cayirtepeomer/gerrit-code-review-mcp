---
"gerrit-review-mcp": patch
---

Migrate Docker integration tests from subprocess to testcontainers-python

- Replace subprocess-based Docker commands with the Testcontainers for Python library.
- Add testcontainers>=3.7.0 for improved container lifecycle management.
- Implement function-scoped fixtures for better test isolation.
- Add automatic container and image cleanup via context managers.
- Improve cross-platform compatibility by removing a Linux-specific timeout dependency.
- Enhance error handling with structured container logs and proper wait strategies.
- Add comprehensive health checks using wait_for_logs() with a configurable timeout.
- Modernize tests/test_docker_integration.py to the Testcontainers-based implementation.
- Update .gitignore to exclude the .roo/ AI assistant rules directory.
- Add pytest configuration and Docker availability checks for better CI/CD integration.
- Implement configurable timeouts and delays via environment variables for test reliability.
- Fix packaging configuration to exclude non-runtime files from wheel distribution.
- Replace deprecated pkg_resources with modern importlib.metadata for version checking.
- Add comprehensive testing documentation with environment variable configuration.
- Improve test robustness with fallback strategies for container environment validation.