[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/cayirtepeomer-gerrit-code-review-mcp-badge.png)](https://mseep.ai/app/cayirtepeomer-gerrit-code-review-mcp)

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
export GERRIT_HOST="gerrit.example.com"  # Your Gerrit server hostname
export GERRIT_USER="your-username"       # Your Gerrit username
export GERRIT_HTTP_PASSWORD="your-http-password"  # Your Gerrit HTTP password
```

Or create a `.env` file:
```
GERRIT_HOST=gerrit.example.com
GERRIT_USER=your-username
GERRIT_HTTP_PASSWORD=your-http-password
```

2. Generate HTTP password:
- Log into your Gerrit web interface
- Go to Settings > HTTP Credentials
- Generate new password
- Copy the password to your environment or .env file

## MCP Configuration

To use this MCP server with Cursor, you need to add its configuration to your `~/.cursor/mcp.json` file. Here's the required configuration:

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
1. Verify your HTTP password is correctly set
2. Check GERRIT_HOST setting
3. Ensure HTTPS access is enabled on Gerrit server
4. Test connection using curl:
   ```bash
   curl -u "username:http-password" https://your-gerrit-host/a/changes/
   ```
5. Verify Gerrit access permissions for your account

## License

This project is licensed under the MIT License.

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request
