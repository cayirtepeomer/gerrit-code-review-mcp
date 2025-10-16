import os
import json
import logging
import re
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass
from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from urllib.parse import quote
from pathlib import Path
import requests

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context

from config import create_auth_handler, get_password

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

@dataclass
class GerritContext:
    host: str
    user: str
    http_password: Optional[str] = None
    verify_ssl: Union[bool, str] = True


def resolve_ssl_verification_setting() -> Union[bool, str]:
    """Resolve SSL verification behaviour based on environment configuration."""
    ssl_verify_env = os.getenv("GERRIT_SSL_VERIFY")
    ca_bundle_env = os.getenv("GERRIT_CA_BUNDLE")

    # Explicit CA bundle takes precedence when provided
    if ca_bundle_env:
        ca_bundle_clean = ca_bundle_env.strip()
        if not ca_bundle_clean:
            raise ValueError(
                "GERRIT_CA_BUNDLE is set but empty after trimming whitespace. "
                "Please provide a valid certificate bundle path or unset the variable."
            )
        ca_path = Path(ca_bundle_clean).expanduser()
        if not (ca_path.exists() and ca_path.is_file()):
            raise ValueError(
                f"Configured GERRIT_CA_BUNDLE path '{ca_path}' does not exist. "
                "Please provide a valid certificate bundle path or unset the variable."
            )
        return str(ca_path)

    if ssl_verify_env is None:
        return True

    normalized_value = ssl_verify_env.strip().lower()
    if normalized_value in {"1", "true", "yes", "on"}:
        return True
    if normalized_value in {"0", "false", "no", "off"}:
        logger.warning("TLS verification disabled via GERRIT_SSL_VERIFY. Use with caution.")
        return False

    # Allow specifying a direct CA bundle path via GERRIT_SSL_VERIFY
    potential_path = Path(ssl_verify_env.strip()).expanduser()
    if potential_path.exists() and potential_path.is_file():
        return str(potential_path)

    raise ValueError(
        "Invalid GERRIT_SSL_VERIFY value. Provide true/false or a path to a CA bundle."
    )

def make_gerrit_rest_request(ctx: Context, endpoint: str) -> Dict[str, Any]:
    """Make a REST API request to Gerrit and handle the response"""
    gerrit_ctx = ctx.request_context.lifespan_context
    
    if not gerrit_ctx.http_password:
        logger.error("HTTP password not set in context")
        raise ValueError("HTTP password not set. Please set GERRIT_HTTP_PASSWORD in your environment.")
        
    # Ensure endpoint starts with 'a/' for authenticated requests
    if not endpoint.startswith('a/'):
        endpoint = f'a/{endpoint}'
    
    url = f"https://{gerrit_ctx.host}/{endpoint}"
    
    auth = create_auth_handler(gerrit_ctx.user, gerrit_ctx.http_password)
    
    try:
        headers = {
            'Accept': 'application/json',
            'User-Agent': 'GerritReviewMCP/1.0'
        }
        
        response = requests.get(url, auth=auth, headers=headers, verify=gerrit_ctx.verify_ssl)
        
        if response.status_code == 401:
            raise Exception("Authentication failed. Please check your Gerrit HTTP password in your account settings.")
            
        response.raise_for_status()
        
        # Remove Gerrit's XSSI prefix if present
        content = response.text
        if content.startswith(")]}'"):
            content = content[4:]
            
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {str(e)}")
            raise Exception(f"Failed to parse Gerrit response as JSON: {str(e)}")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"REST request failed: {str(e)}")
        response = getattr(e, "response", None)
        if response is not None:
            logger.error(f"Response status: {response.status_code}")
        raise Exception(f"Failed to make Gerrit REST API request: {str(e)}")


@asynccontextmanager
async def gerrit_lifespan(server: FastMCP) -> AsyncIterator[GerritContext]:
    """Manage Gerrit connection details"""
    host = os.getenv("GERRIT_HOST", "")
    user = os.getenv("GERRIT_USER", "")
    
    # Log simple error if user includes protocol in GERRIT_HOST
    if host.startswith(('http://', 'https://')):
        logger.warning("GERRIT_HOST should not include protocol; stripping scheme.")
        host = re.sub(r'^https?://', '', host).rstrip('/')
    
    if not all([host, user]):
        logger.error("Missing required environment variables:")
        if not host: logger.error("- GERRIT_HOST not set")
        if not user: logger.error("- GERRIT_USER not set")
        raise ValueError(
            "Missing required environment variables: GERRIT_HOST, GERRIT_USER. "
            "Please set these in your environment or .env file."
        )

    # Get the appropriate password based on authentication method
    try:
        password = get_password()
    except ValueError as e:
        logger.error(f"Password configuration error: {str(e)}")
        raise

    verify_ssl = resolve_ssl_verification_setting()

    ctx = GerritContext(host=host, user=user, http_password=password, verify_ssl=verify_ssl)
    try:
        yield ctx
    finally:
        pass


# Create MCP server
mcp = FastMCP(
    "Gerrit Review",
    lifespan=gerrit_lifespan,
    dependencies=["python-dotenv", "requests"]
)

@mcp.tool()
def fetch_gerrit_change(ctx: Context, change_id: str, patchset_number: Optional[str] = None, include_comments: bool = False) -> Dict[str, Any]:
    """
    Fetch a Gerrit change and its contents.
    
    Args:
        change_id: The Gerrit change ID to fetch
        patchset_number: Optional patchset number to fetch (defaults to latest)
        include_comments: Optional boolean to include inline comments (defaults to False)
    Returns:
        Dict containing the raw change information including files and diffs
    """
    # Get change details using REST API with all required information
    change_endpoint = f"a/changes/{change_id}/detail?o=CURRENT_REVISION&o=CURRENT_COMMIT&o=MESSAGES&o=DETAILED_LABELS&o=DETAILED_ACCOUNTS&o=ALL_REVISIONS&o=ALL_COMMITS&o=ALL_FILES&o=COMMIT_FOOTERS"
    change_info = make_gerrit_rest_request(ctx, change_endpoint)
    
    if not change_info:
        raise ValueError(f"Change {change_id} not found")
        
    # Extract project and ref information
    project = change_info.get("project")
    if not project:
        raise ValueError("Project information not found in change")
        
    # Get the target patchset
    current_revision = change_info.get("current_revision")
    revisions = change_info.get("revisions", {})
    
    if patchset_number:
        # Find specific patchset
        target_revision = None
        for rev, rev_info in revisions.items():
            if str(rev_info.get("_number")) == str(patchset_number):
                target_revision = rev
                break
        if not target_revision:
            available_patchsets = sorted([str(info.get("_number")) for info in revisions.values()])
            raise ValueError(f"Patchset {patchset_number} not found. Available patchsets: {', '.join(available_patchsets)}")
    else:
        # Use current revision
        target_revision = current_revision
    
    if not target_revision or target_revision not in revisions:
        raise ValueError("Revision information not found")

    revision_info = revisions[target_revision]
    
    # Process each file with configurable filtering
    processed_files = []
    excluded_files = []
    
    # Get exclusion patterns from environment or use defaults
    excluded_patterns_str = os.getenv("GERRIT_EXCLUDED_PATTERNS", "")
    if excluded_patterns_str:
        excluded_patterns = [pattern.strip() for pattern in excluded_patterns_str.split(",") if pattern.strip()]
    else:
        excluded_patterns = []
    
    for file_path, file_info in revision_info.get("files", {}).items():
        if file_path == "/COMMIT_MSG":
            continue
        
        # Check if file should be excluded based on patterns only
        should_exclude = False
        exclude_reason = ""
        
        # Check for excluded patterns
        for pattern in excluded_patterns:
            if re.search(pattern, file_path):
                should_exclude = True
                exclude_reason = f"Excluded pattern: {pattern}"
                break
        
        if should_exclude:
            excluded_files.append({
                "path": file_path,
                "status": file_info.get("status", "MODIFIED"),
                "lines_inserted": file_info.get("lines_inserted", 0),
                "lines_deleted": file_info.get("lines_deleted", 0),
                "size_delta": file_info.get("size_delta", 0),
                "exclude_reason": exclude_reason
            })
            continue
            
        # Get the diff for this file
        encoded_path = quote(file_path, safe='')
        diff_endpoint = f"a/changes/{change_id}/revisions/{target_revision}/files/{encoded_path}/diff"
        diff_info = make_gerrit_rest_request(ctx, diff_endpoint)
        
        file_data = {
            "path": file_path,
            "status": file_info.get("status", "MODIFIED"),
            "lines_inserted": file_info.get("lines_inserted", 0),
            "lines_deleted": file_info.get("lines_deleted", 0),
            "size_delta": file_info.get("size_delta", 0),
            "diff": diff_info
        }
        processed_files.append(file_data)
    
    # Fetch inline comments for the target revision (if requested)
    inline_comments = {}
    if include_comments:
        try:
            comments_endpoint = f"a/changes/{change_id}/revisions/{target_revision}/comments"
            inline_comments = make_gerrit_rest_request(ctx, comments_endpoint)
        except Exception as e:
            logger.warning(f"Failed to fetch inline comments for change {change_id}: {str(e)}")
            inline_comments = {}
    
    # Return the complete change information
    result = {
        "change_info": change_info,
        "project": project,
        "revision": target_revision,
        "patchset": revision_info,
        "files": processed_files,
        "inline_comments": inline_comments
    }
    
    if excluded_files:
        result["excluded_large_files"] = excluded_files
        result["_note"] = f"Excluded {len(excluded_files)} large files to prevent infinite loops. Use fetch_patchset_diff for specific large files."
    
    return result


@mcp.tool()
def fetch_patchset_diff(ctx: Context, change_id: str, base_patchset: str, target_patchset: str, file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch differences between two patchsets of a Gerrit change.
    
    Args:
        change_id: The Gerrit change ID
        base_patchset: The base patchset number to compare from
        target_patchset: The target patchset number to compare to
        file_path: Optional specific file path to get diff for. If not provided, returns diffs for all changed files.
    Returns:
        Dict containing the diff information between the patchsets
    """
    # First get the revision info for both patchsets
    change_endpoint = f"a/changes/{change_id}/detail?o=ALL_REVISIONS&o=ALL_FILES"
    change_info = make_gerrit_rest_request(ctx, change_endpoint)
    
    if not change_info:
        raise ValueError(f"Change {change_id} not found")
    
    revisions = change_info.get("revisions", {})
    
    # Find revision hashes for both patchsets
    base_revision = None
    target_revision = None
    for rev, rev_info in revisions.items():
        if str(rev_info.get("_number")) == str(base_patchset):
            base_revision = rev
        if str(rev_info.get("_number")) == str(target_patchset):
            target_revision = rev
            
    if not base_revision or not target_revision:
        available_patchsets = sorted([str(info.get("_number")) for info in revisions.values()])
        raise ValueError(f"Patchset(s) not found. Available patchsets: {', '.join(available_patchsets)}")

    # Get the diff between revisions using Gerrit's comparison endpoint
    diff_endpoint = f"a/changes/{change_id}/revisions/{target_revision}/files"
    if base_revision:
        diff_endpoint += f"?base={base_revision}"
    
    files_diff = make_gerrit_rest_request(ctx, diff_endpoint)
    
    # Process the files that actually changed
    changed_files = {}
    for file_path, file_info in files_diff.items():
        if file_path == "/COMMIT_MSG":
            continue
            
        if file_info.get("status") != "SAME":  # Only include files that actually changed
            # Get detailed diff for this file
            encoded_path = quote(file_path, safe='')
            file_diff_endpoint = f"a/changes/{change_id}/revisions/{target_revision}/files/{encoded_path}/diff"
            if base_revision:
                file_diff_endpoint += f"?base={base_revision}"
            diff_info = make_gerrit_rest_request(ctx, file_diff_endpoint)
            
            changed_files[file_path] = {
                "status": file_info.get("status", "MODIFIED"),
                "lines_inserted": file_info.get("lines_inserted", 0),
                "lines_deleted": file_info.get("lines_deleted", 0),
                "size_delta": file_info.get("size_delta", 0),
                "diff": diff_info
            }
    
    return {
        "base_revision": base_revision,
        "target_revision": target_revision,
        "base_patchset": base_patchset,
        "target_patchset": target_patchset,
        "files": changed_files
    }

if __name__ == "__main__":
    try:
        logger.info("Starting Gerrit Review MCP server")
        # Initialize and run the server
        mcp.run(transport='stdio')
    except Exception as e:
        logger.error(f"Failed to start MCP server: {str(e)}")
        raise
