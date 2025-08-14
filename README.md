# Gerrit Code Review MCP Server for RooCode

This directory contains the Gerrit Code Review MCP Server installation for RooCode. This MCP server provides integration with Gerrit code review systems, allowing AI assistants to review code changes and their details.

## Features

- **Fetch Change Details**: Extract and display complete change information including files and patch sets
- **Compare Patch Set Differences**: Analyze differences between two or more patch sets
- **Integration Capabilities**: Seamlessly integrate with mainstream code review tools and CI/CD pipelines

## Installation Status

✅ **Installed and Configured**

The MCP server has been successfully:
- Cloned from the official repository
- Built as a Docker image (`gerrit-code-review-mcp`)
- Configured for RooCode integration
- Set up with proper environment templates

## Configuration

### 1. Environment Setup

Copy the environment template and configure your Gerrit settings:

```bash
cd /home/atmp/data/dev-tools-1/mcp/gerrit
cp .env.template .env
```

Edit the `.env` file with your actual Gerrit server details:

```bash
# Your Gerrit server hostname (without https://)
GERRIT_HOST=your-gerrit-server.com

# Your Gerrit username
GERRIT_USER=your-username

# Your Gerrit HTTP password (generate from Settings > HTTP Credentials)
GERRIT_HTTP_PASSWORD=your-http-password

# Optional: File patterns to exclude from reviews
GERRIT_EXCLUDED_PATTERNS=\.pbxproj$,\.xcworkspace$,node_modules/,\.lock$
```

### 2. Generate Gerrit HTTP Password

1. Log into your Gerrit web interface
2. Go to **Settings > HTTP Credentials**
3. Generate a new password
4. Copy the password to your `.env` file

### 3. MCP Server Configuration

The MCP server is configured to run via Docker with the following configuration:

```json
{
  "mcpServers": {
    "gerrit-code-review-mcp": {
      "command": "docker",
      "args": [
        "run", "--rm", "-i",
        "--env-file", "/home/atmp/data/dev-tools-1/mcp/gerrit/.env",
        "gerrit-code-review-mcp"
      ],
      "cwd": "/home/atmp/data/dev-tools-1/mcp/gerrit",
      "stdio": true
    }
  }
}
```

## Usage

### Starting the Server

Use the provided startup script:

```bash
cd /home/atmp/data/dev-tools-1/mcp/gerrit
./start-server.sh
```

The script will:
- Check if the `.env` file exists
- Verify the Docker image is available
- Start the MCP server with proper configuration

### Available Tools

Once connected, the MCP server provides these tools:

#### `fetch_gerrit_change`
```python
fetch_gerrit_change(change_id: str, patchset_number: Optional[str] = None)
```
- Fetches complete change information including files and patch sets
- Shows detailed diff information for each modified file
- Supports reviewing specific patch sets

#### `fetch_patchset_diff`
```python
fetch_patchset_diff(change_id: str, base_patchset: str, target_patchset: str, file_path: Optional[str] = None)
```
- Compare differences between two patchsets of a change
- View specific file differences or all changed files
- Track evolution of changes through review iterations

### Example Usage

```python
# Fetch latest patchset of change 23824
change = fetch_gerrit_change("23824")

# Compare differences between patchsets 1 and 2
diff = fetch_patchset_diff("23824", "1", "2")

# Get diff for a specific file between patchsets
file_diff = fetch_patchset_diff("23824", "1", "2", "path/to/file.swift")
```

## Troubleshooting

### Connection Issues

If you encounter connection issues:

1. **Verify HTTP password**: Check that your Gerrit HTTP password is correctly set in `.env`
2. **Check GERRIT_HOST**: Ensure the hostname is correct (without `https://`)
3. **Test connection**: Use curl to test your credentials:
   ```bash
   curl -u "username:http-password" https://your-gerrit-host/a/changes/
   ```
4. **Verify permissions**: Ensure your Gerrit account has access to the projects you want to review

### Docker Issues

If the Docker image is not found:
```bash
cd /home/atmp/data/dev-tools-1/mcp/gerrit
docker build -t gerrit-code-review-mcp .
```

### Environment File Missing

If you get an error about missing `.env` file:
```bash
cp .env.template .env
# Then edit .env with your actual Gerrit settings
```

## File Structure

```
mcp/gerrit/
├── README.md              # This file
├── config.json           # MCP server configuration
├── .env.template         # Environment variables template
├── start-server.sh       # Startup script
├── server.py            # Main MCP server code
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
└── pyproject.toml      # Python project configuration
```

## Technical Details

- **Language**: Python 3.11
- **Framework**: FastMCP (Model Context Protocol)
- **Container**: Docker-based deployment
- **Authentication**: HTTP Digest Auth with Gerrit
- **API**: Gerrit REST API integration

## Security Notes

- The `.env` file contains sensitive credentials - never commit it to version control
- HTTP passwords should be generated specifically for API access
- The MCP server runs in an isolated Docker container
- All communication with Gerrit uses HTTPS encryption

## Support

For issues specific to this installation, check:
1. Docker container logs: `docker logs <container-id>`
2. Gerrit server connectivity
3. Environment variable configuration
4. Gerrit account permissions

For upstream issues, refer to the original repository:
https://github.com/cayirtepeomer/gerrit-code-review-mcp
