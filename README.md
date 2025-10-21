# Gerrit Review MCP Server

[![smithery badge](https://smithery.ai/badge/@cayirtepeomer/gerrit-code-review-mcp)](https://smithery.ai/server/@cayirtepeomer/gerrit-code-review-mcp)

This MCP server provides integration with Gerrit code review system, allowing AI assistants to review code changes and their details through a simple interface.

## Features

The server provides a streamlined toolset for code review:

### Fetch Change Details
```python
fetch_gerrit_change(change_id: str, patchset_number: Optional[str] = None)
```
- Fetches complete change information including files and patch sets
- Shows detailed diff information for each modified file
- Displays file changes, insertions, and deletions
- Supports reviewing specific patch sets
- Returns comprehensive change details including:
  - Project and branch information
  - Author and reviewer details
  - Comments and review history
  - File modifications with diff content
  - Current patch set information

### Compare Patchset Differences
```python
fetch_patchset_diff(change_id: str, base_patchset: str, target_patchset: str, file_path: Optional[str] = None)
```
- Compare differences between two patchsets of a change
- View specific file differences or all changed files
- Analyze code modifications across patchset versions
- Track evolution of changes through review iterations

### Example Usage

Review a complete change:
```python
# Fetch latest patchset of change 23824
change = fetch_gerrit_change("23824")
```

Compare specific patchsets:
```python
# Compare differences between patchsets 1 and 2 for change 23824
diff = fetch_patchset_diff("23824", "1", "2")
```

View specific file changes:
```python
# Get diff for a specific file between patchsets
file_diff = fetch_patchset_diff("23824", "1", "2", "path/to/file.swift")
```

## Prerequisites

- Python 3.10 or higher (Python 3.11 recommended)
- Gerrit HTTP access credentials
- HTTP password generated from Gerrit settings
- Access to the `mcp[cli]` package repository (private package)

## Installation

### Installing via Smithery

To install gerrit-code-review-mcp for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@cayirtepeomer/gerrit-code-review-mcp):

```bash
npx -y @smithery/cli install @cayirtepeomer/gerrit-code-review-mcp --client claude
```

### Manual Installation
1. Clone this repository:
```bash
git clone <repository-url>
cd gerrit-review-mcp
```

2. Create and activate a virtual environment:
```bash
# For macOS/Linux:
python -m venv .venv
source .venv/bin/activate

# For Windows:
python -m venv .venv
.venv\Scripts\activate
```

3. Install this package in editable mode with its dependencies:
```bash
pip install -e .
```

## Configuration

1. Set up environment variables:
```bash
export GERRIT_HOST="gerrit.example.com"  # Your Gerrit server hostname (without https://)
export GERRIT_USER="your-username"       # Your Gerrit account username
export GERRIT_HTTP_PASSWORD="your-http-password"  # Generated HTTP password from Gerrit Settings > HTTP Credentials
export GERRIT_EXCLUDED_PATTERNS="\.pbxproj$,\.xcworkspace$,node_modules/"  # Optional: regex patterns for files to exclude from reviews
# Optional TLS configuration for custom or self-signed certificates
export GERRIT_SSL_VERIFY="true"              # Set to 'false' to skip TLS verification in constrained environments
export GERRIT_CA_BUNDLE="/path/to/ca.pem"    # Optional custom CA bundle path used when verification stays enabled
# Note: If both are set, GERRIT_CA_BUNDLE takes precedence and verification stays enabled using that bundle.
```

Or create a `.env` file:
```
GERRIT_HOST=gerrit.example.com
GERRIT_USER=your-username
GERRIT_HTTP_PASSWORD=your-http-password
GERRIT_EXCLUDED_PATTERNS=\.pbxproj$,\.xcworkspace$,node_modules/
GERRIT_SSL_VERIFY=true
GERRIT_CA_BUNDLE=/path/to/ca.pem
# If both are set, the CA bundle wins.
```

2. Generate HTTP password:
- Log into your Gerrit web interface
- Go to Settings > HTTP Credentials
- Generate new password
- Copy the password to your environment or .env file

3. Configure file exclusions (optional):
- Set `GERRIT_EXCLUDED_PATTERNS` to exclude specific file types from change reviews
- Use comma-separated regex patterns (e.g., `\.pbxproj$,\.xcworkspace$,node_modules/`)
- Leave empty or unset to use default exclusions
- This helps prevent infinite loops with large files

## MCP Configuration

To use this MCP server with Cursor or RooCode, you need to add its configuration to your `~/.cursor/mcp.json` or `.roo/mcp.json` file. Here's the required configuration:

```json
{
  "mcpServers": {
    "gerrit-review-mcp": {
      "command": "/path/to/your/workspace/gerrit-code-review-mcp/.venv/bin/python",
      "args": [
        "/path/to/your/workspace/gerrit-code-review-mcp/server.py",
        "--transport",
        "stdio"
      ],
      "cwd": "/path/to/your/workspace/gerrit-code-review-mcp",
      "env": {
        "PYTHONPATH": "/path/to/your/workspace/gerrit-code-review-mcp",
        "VIRTUAL_ENV": "/path/to/your/workspace/gerrit-code-review-mcp/.venv",
        "PATH": "/path/to/your/workspace/gerrit-code-review-mcp/.venv/bin:/usr/local/bin:/usr/bin:/bin"
      },
      "stdio": true
    }
  }
}
```

Replace `/path/to/your/workspace` with your actual workspace path. For example, if your project is in `/Users/username/projects/gerrit-code-review-mcp`, use that path instead.

Make sure all paths in the configuration point to:
- Your virtual environment's Python interpreter
- The project's `server.py` file
- The correct working directory
- The virtual environment's bin directory in the PATH

## Implementation Details

The server uses Gerrit REST API to interact with Gerrit, providing:
- Fast and reliable change information retrieval
- Secure authentication using HTTP digest auth
- Support for various Gerrit REST endpoints
- Clean and maintainable codebase
- HTTPS encryption for secure communication

## Troubleshooting

If you encounter connection issues:
1. Verify your HTTP password is correctly set in `GERRIT_HTTP_PASSWORD`
2. Check `GERRIT_HOST` setting (hostname only, without https://)
3. Ensure HTTPS access is enabled on Gerrit server
4. Test connection using curl with the `/a/` prefix for authenticated API calls:
   ```bash
   curl -u "your-username:your-http-password" https://your-gerrit-server.com/a/changes/?q=status:open
   ```
5. Verify Gerrit access permissions for your account

### HTTP Credentials Authentication Issues

If you're having trouble with authentication, check your Gerrit config for `gitBasicAuthPolicy = HTTP` (or `HTTP_LDAP`).

### Working with Self-Signed Certificates

- `GERRIT_SSL_VERIFY=false` disables TLS verification when Gerrit uses an internally issued certificate lacking required Subject Alternative Name (SAN) entries.
- Provide a custom certificate bundle via `GERRIT_CA_BUNDLE=/path/to/ca.pem` to keep verification enabled while trusting a private CA.
- Treat disabled verification as a temporary workaround until a certificate with matching SANs is issued for the Gerrit hostnames you access.

## License

This project is licensed under the MIT License.

## Testing

This project includes comprehensive Docker integration tests using testcontainers-python for reliable cross-platform testing.

### Running Tests

To run the full test suite:
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run all tests
pytest

# Run only integration tests
pytest -m integration

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=. --cov-report=html
```

### Test Environment Variables

The following environment variables can be used to configure test behavior:

- `TEST_STARTUP_TIMEOUT`: Container startup timeout in seconds (default: 30)
- `TEST_LOGS_SETTLE_DELAY`: Delay before checking logs in seconds (default: 0)
- `DOCKER_HOST`: Docker daemon host for remote Docker (optional)

Example:
```bash
# Run tests with custom timeouts
TEST_STARTUP_TIMEOUT=60 TEST_LOGS_SETTLE_DELAY=1 pytest tests/test_docker_integration.py -v
```

### Docker Requirements

Docker integration tests require:
- Docker daemon running and accessible
- Docker socket available at `/var/run/docker.sock` (Linux/macOS) or `DOCKER_HOST` set
- Sufficient permissions to build and run containers

Tests will be automatically skipped if Docker is not available.

### CI/CD Integration

For CI/CD environments, ensure:
- Docker-in-Docker (DinD) service is available
- Docker socket is mounted or `DOCKER_HOST` is configured
- Sufficient timeout values are set for slower environments

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run the test suite to ensure everything works
5. Submit a pull request
