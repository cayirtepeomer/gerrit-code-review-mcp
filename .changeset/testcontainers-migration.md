---
"gerrit-review-mcp": patch
---

Migrate Docker integration tests from subprocess to testcontainers-python

- Replace subprocess-based Docker commands with testcontainers-python library
- Add testcontainers>=3.7.0 dependency for improved container lifecycle management
- Implement function-scoped fixtures for better test isolation
- Add automatic container and image cleanup with context managers
- Improve cross-platform compatibility by removing Linux-specific timeout dependency
- Enhance error handling with structured container logs and proper wait strategies
- Add comprehensive health checks using wait_for_logs() with timeout configuration
- Modernize test_docker_integration.py with testcontainers implementation
- Update .gitignore to exclude .roo/ AI assistant rules directory