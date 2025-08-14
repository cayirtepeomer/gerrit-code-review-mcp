#!/usr/bin/env python3
"""
Docker integration tests for Gerrit MCP Server
Tests Docker build, container startup, and runtime behavior
"""

import os
import subprocess
import tempfile
import time
from pathlib import Path

import pytest


class TestDockerIntegration:
    """Test Docker container build and runtime behavior"""

    @pytest.fixture(scope="class")
    def project_root(self):
        """Get the project root directory"""
        return Path(__file__).parent.parent

    @pytest.fixture(scope="class")
    def test_env_file(self, project_root):
        """Create a temporary test environment file"""
        test_env_content = """# Test environment file for Gerrit Code Review MCP Server
# This is for testing the server startup only - not for actual Gerrit connection

GERRIT_HOST=test.gerrit.example.com
GERRIT_USER=test-user
GERRIT_HTTP_PASSWORD=test-password
GERRIT_EXCLUDED_PATTERNS=\\.pbxproj$,\\.xcworkspace$,node_modules/,\\.lock$
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write(test_env_content)
            return f.name

    def test_docker_build(self, project_root):
        """Test that Docker image builds successfully"""
        result = subprocess.run(
            ["docker", "build", "-t", "gerrit-mcp-test", "."],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, f"Docker build failed: {result.stderr}"
        # Docker build output goes to stderr in newer versions
        build_output = result.stdout + result.stderr
        assert (
            "Successfully built" in build_output
            or "Successfully tagged" in build_output
            or "naming to docker.io/library/gerrit-mcp-test done" in build_output
        )

    def test_container_startup(self, project_root, test_env_file):
        """Test container startup behavior with timeout"""
        # MCP servers expect stdio communication and will exit without input
        result = subprocess.run(
            [
                "timeout",
                "10s",
                "docker",
                "run",
                "--rm",
                "--env-file",
                test_env_file,
                "gerrit-mcp-test",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        # Timeout is expected since MCP servers wait for stdin
        # Check that the server started properly before timing out (message may be in stderr)
        output = result.stdout + result.stderr
        assert (
            "Starting Gerrit Review MCP server" in output
        ), f"MCP server startup message not found in output: {result.stdout} {result.stderr}"

    def test_container_logs_no_errors(self, project_root, test_env_file):
        """Test that container startup doesn't produce error messages"""
        result = subprocess.run(
            [
                "timeout",
                "5s",
                "docker",
                "run",
                "--rm",
                "--env-file",
                test_env_file,
                "gerrit-mcp-test",
            ],
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        # Check for common error patterns
        error_patterns = ["error", "exception", "failed", "traceback"]
        output_lower = result.stdout.lower() + result.stderr.lower()

        for pattern in error_patterns:
            assert (
                pattern not in output_lower
            ), f"Found error pattern '{pattern}' in container output: {result.stdout} {result.stderr}"

    def test_interactive_mode(self, project_root, test_env_file):
        """Test container in interactive mode with brief input"""
        # Send "exit" command to test interactive mode
        result = subprocess.run(
            [
                "timeout",
                "5s",
                "docker",
                "run",
                "--rm",
                "-i",
                "--env-file",
                test_env_file,
                "gerrit-mcp-test",
            ],
            input="exit\n",
            cwd=project_root,
            capture_output=True,
            text=True,
        )

        # Should start successfully (timeout expected)
        output = result.stdout + result.stderr
        assert (
            "Starting Gerrit Review MCP server" in output
        ), f"Interactive mode test failed: {result.stdout} {result.stderr}"

    def teardown_class(self):
        """Clean up test Docker image"""
        try:
            subprocess.run(
                ["docker", "rmi", "gerrit-mcp-test"],
                capture_output=True,
                check=False,  # Don't fail if image doesn't exist
            )
        except Exception:
            pass  # Ignore cleanup errors


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
