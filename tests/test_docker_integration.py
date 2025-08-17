#!/usr/bin/env python3
"""
Docker integration tests for Gerrit MCP Server using testcontainers
Tests Docker build, container startup, and runtime behavior with testcontainers-python
"""

import os
import tempfile
import time
from pathlib import Path
from typing import Generator

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs


class TestDockerIntegrationTestcontainers:
    """Test Docker container build and runtime behavior using testcontainers"""

    @pytest.fixture(scope="class")
    def project_root(self) -> Path:
        """Get the project root directory"""
        return Path(__file__).parent.parent

    @pytest.fixture(scope="class")
    def test_env_file(self, project_root: Path) -> Generator[str, None, None]:
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
            temp_file_path = f.name
        
        try:
            yield temp_file_path
        finally:
            # Clean up the temporary file
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    @pytest.fixture(scope="function")
    def gerrit_mcp_container(self, project_root: Path, test_env_file: str) -> Generator[DockerContainer, None, None]:
        """Build and provide a Gerrit MCP container using testcontainers"""
        # First, build the Docker image using the Docker client
        image_tag = "gerrit-mcp-testcontainers:latest"
        
        # Create a temporary container to get the Docker client
        temp_container = DockerContainer("hello-world")
        docker_client = temp_container.get_docker_client()
        
        # Build the image from Dockerfile
        image, build_logs = docker_client.build(
            path=str(project_root),
            dockerfile="Dockerfile",
            tag=image_tag,
            rm=True
        )
        
        try:
            # Create container from the built image
            container = DockerContainer(image_tag)
            
            # Set environment variables from the test env file
            with open(test_env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        container = container.with_env(key, value)
            
            # Start the container
            with container:
                yield container
        finally:
            # Clean up the built image
            try:
                docker_client.client.images.remove(image_tag, force=True)
            except Exception:
                pass  # Ignore cleanup errors

    def test_container_build_and_startup(self, gerrit_mcp_container: DockerContainer):
        """Test that container builds and starts successfully"""
        # Container should be running
        assert gerrit_mcp_container.get_container_host_ip() is not None
        
        # Wait for the startup message in logs
        try:
            wait_for_logs(
                gerrit_mcp_container, 
                "Starting Gerrit Review MCP server",
                timeout=10
            )
        except Exception as e:
            # Get logs for debugging if startup message not found
            logs = gerrit_mcp_container.get_logs()
            pytest.fail(f"Startup message not found in logs. Container logs: {logs}")

    def test_container_logs_no_errors(self, gerrit_mcp_container: DockerContainer):
        """Test that container startup doesn't produce error messages"""
        # Wait a moment for any potential errors to appear
        time.sleep(2)
        
        logs = gerrit_mcp_container.get_logs()
        logs_text = logs[0].decode('utf-8') + logs[1].decode('utf-8')  # stdout + stderr
        
        # Check for common error patterns
        error_patterns = ["error", "exception", "failed", "traceback"]
        logs_lower = logs_text.lower()
        
        for pattern in error_patterns:
            assert pattern not in logs_lower, f"Found error pattern '{pattern}' in container logs: {logs_text}"

    def test_container_environment_variables(self, gerrit_mcp_container: DockerContainer):
        """Test that environment variables are properly set in the container"""
        # Execute a command to check environment variables
        result = gerrit_mcp_container.exec("env")
        env_output = result.output.decode('utf-8')
        
        # Check that our test environment variables are present
        assert "GERRIT_HOST=test.gerrit.example.com" in env_output
        assert "GERRIT_USER=test-user" in env_output
        assert "GERRIT_HTTP_PASSWORD=test-password" in env_output

    def test_container_python_environment(self, gerrit_mcp_container: DockerContainer):
        """Test that Python environment is properly configured"""
        # Check Python version
        result = gerrit_mcp_container.exec("python --version")
        python_version = result.output.decode('utf-8').strip()
        assert "Python 3." in python_version
        
        # Check that required packages are installed
        result = gerrit_mcp_container.exec("pip list")
        pip_output = result.output.decode('utf-8')
        
        # Check for key dependencies
        assert "mcp" in pip_output.lower()
        assert "requests" in pip_output.lower()
        assert "python-dotenv" in pip_output.lower()

    def test_container_file_structure(self, gerrit_mcp_container: DockerContainer):
        """Test that container has the expected file structure"""
        # Check that main files are present
        result = gerrit_mcp_container.exec("ls -la /app/")
        file_list = result.output.decode('utf-8')
        
        expected_files = ["server.py", "config.py", "pyproject.toml", "requirements.txt"]
        for expected_file in expected_files:
            assert expected_file in file_list, f"Expected file {expected_file} not found in container"

    def test_container_interactive_mode_simulation(self, project_root: Path, test_env_file: str):
        """Test container behavior with stdin input simulation"""
        # Build image for this test
        image_tag = "gerrit-mcp-interactive-test:latest"
        temp_container = DockerContainer("hello-world")
        docker_client = temp_container.get_docker_client()
        
        image, build_logs = docker_client.build(
            path=str(project_root),
            dockerfile="Dockerfile",
            tag=image_tag,
            rm=True
        )
        
        try:
            # Create a separate container instance for this test
            container = DockerContainer(image_tag)
            
            # Set environment variables
            with open(test_env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        container = container.with_env(key, value)
            
            with container:
                # Wait for startup
                try:
                    wait_for_logs(container, "Starting Gerrit Review MCP server", timeout=10)
                except Exception:
                    logs = container.get_logs()
                    pytest.fail(f"Interactive test startup failed. Logs: {logs}")
                
                # Container should be running and responsive
                assert container.get_container_host_ip() is not None
        finally:
            # Clean up the built image
            try:
                docker_client.client.images.remove(image_tag, force=True)
            except Exception:
                pass  # Ignore cleanup errors


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])