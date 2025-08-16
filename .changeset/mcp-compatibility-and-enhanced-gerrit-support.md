---
"gerrit-review-mcp": patch
---

Fix MCP 1.12.4 compatibility and add enhanced Gerrit support

- Fix FastMCP constructor parameter change from 'description' to 'instructions' for MCP 1.12.4+ compatibility
- Add support for both standard and path-based Gerrit URL formats (e.g., gerrit.example.com vs gerrit.example.com/r)
- Implement dual authentication support (HTTP password for newer Gerrit, login password fallback for older instances)
- Change authentication method from HTTPDigestAuth to HTTPBasicAuth for better compatibility
- Add RooCode support alongside existing Cursor integration in MCP configuration documentation
- Add comprehensive HTTP credentials authentication troubleshooting for LDAP/OAuth environments
- Include gitBasicAuthPolicy configuration guidance for Gerrit administrators
- Add comprehensive Docker testing infrastructure with pytest integration
- Include environment configuration templates for easier setup
- Improve error messages with troubleshooting guidance for different Gerrit versions
- Remove debug logging statements for cleaner production code and improved maintainability
- Format code with Black and isort to follow project style guidelines
- Update .gitignore to include pytest cache directory