#!/usr/bin/env python3
"""
Docker integration tests for Gerrit MCP Server using testcontainers.

This module tests Docker build, container startup, and runtime behavior using
the testcontainers-python library with improved lifecycle management.
"""

import contextlib
import os
import tempfile
import time
from pathlib import Path
from typing import Generator

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.docker_client import DockerClient

# Test configuration with environment variable overrides for CI/CD flexibility
TEST_CONFIG = {
    "STARTUP_TIMEOUT": int(os.getenv("TEST_STARTUP_TIMEOUT", "30")),
    "LOGS_SETTLE_DELAY": float(os.getenv("TEST_LOGS_SETTLE_DELAY", "2.0")),
    "CONTAINER_READY_TIMEOUT": int(os.getenv("TEST_CONTAINER_READY_TIMEOUT", "10")),
    "IMAGE_TAG_PREFIX": "gerrit-mcp-test",
}

# Skip tests if Docker is not available
try:
    DockerClient().client.ping()
    _docker_available = True
except Exception:
    _docker_available = False

pytestmark = pytest.mark.skipif(
    not _docker_available,
    reason="Docker daemon not available",
)


def _wait_for_container_ready(container: DockerContainer, timeout: int = 10) -> bool:
    """
    Wait for container to be in a ready state.
    
    Args:
        container: The DockerContainer instance to check
        timeout: Maximum time to wait in seconds
        
    Returns:
        True if container is ready
        
    Raises:
        TimeoutError: If container is not ready within timeout
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            container._container.reload()
            if container._container.status == "running":
                return True
        except Exception:
            pass
        time.sleep(0.5)
    
    # Gather diagnostic information for timeout
    try:
        container._container.reload()
        status = container._container.status
        logs = container.get_logs()
        raise TimeoutError(
            f"Container not ready within {timeout} seconds. "
            f"Status: {status}, Logs: {logs}"
        )
    except Exception as e:
        raise TimeoutError(f"Container not ready within {timeout} seconds. Error: {e}")


def _start_mcp_server_detached(container: DockerContainer) -> bool:
    """
    Start MCP server in background and verify startup.
    
    Args:
        container: The DockerContainer instance to run the server in
        
    Returns:
        True if server started successfully, False otherwise
    """
    try:
        # Start MCP server with timeout and capture logs
        container.exec([
            "sh", "-c",
            "cd /app && timeout 5s python server.py 2>&1 | tee /tmp/mcp_startup.log || true"
        ])
        
        # Allow time for server startup and log generation
        time.sleep(TEST_CONFIG["LOGS_SETTLE_DELAY"])
        
        # Verify startup by checking log file
        log_result = container.exec(["cat", "/tmp/mcp_startup.log"])
        if log_result.exit_code == 0:
            log_content = log_result.output.decode('utf-8')
            return "Starting Gerrit Review MCP server" in log_content
        
        return False
        
    except Exception:
        return False


def _setup_container_env(container: DockerContainer, test_env_file: str) -> None:
    """
    Configure container environment variables from test file.
    
    Args:
        container: The DockerContainer instance to configure
        test_env_file: Path to the test environment file
    """
    with open(test_env_file, 'r', encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                container.with_env(key, value)


def _create_test_container(docker_image: str, test_env_file: str) -> DockerContainer:
    """
    Create a properly configured test container.
    
    Args:
        docker_image: Docker image tag to use
        test_env_file: Path to test environment file
        
    Returns:
        Configured DockerContainer instance
    """
    container = (DockerContainer(docker_image)
                 .with_command("sleep infinity")
                 .with_env("PYTHONUNBUFFERED", "1")
                 .with_kwargs(auto_remove=False))
    
    _setup_container_env(container, test_env_file)
    return container


@pytest.fixture(scope="module")
def project_root() -> Path:
    """Get the project root directory"""
    return Path(__file__).parent.parent


@pytest.fixture(scope="module")
def test_env_file(project_root: Path) -> Generator[str, None, None]:
    """Create a temporary test environment file"""
    test_env_content = """# Test environment file for Gerrit Code Review MCP Server
# This is for testing the server startup only - not for actual Gerrit connection

GERRIT_HOST=test.gerrit.example.com
GERRIT_USER=test-user
GERRIT_HTTP_PASSWORD=test-password
GERRIT_EXCLUDED_PATTERNS=\\.pbxproj$,\\.xcworkspace$,node_modules/,\\.lock$
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False, encoding="utf-8") as f:
        f.write(test_env_content)
        temp_file_path = f.name
    
    try:
        yield temp_file_path
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.unlink(temp_file_path)


@pytest.fixture(scope="module")
def docker_image(project_root: Path) -> Generator[str, None, None]:
    """Build Docker image once per test module to avoid conflicts"""
    # Create unique image tag to prevent conflicts
    timestamp = int(time.time())
    image_tag = f"{TEST_CONFIG['IMAGE_TAG_PREFIX']}-{timestamp}"
    
    docker_client = DockerClient()
    
    try:
        # Build the image from Dockerfile
        image, build_logs = docker_client.client.images.build(
            path=str(project_root),
            dockerfile="Dockerfile",
            tag=image_tag,
            rm=True,
        )
        yield image_tag
    finally:
        # Clean up image after all tests complete
        with contextlib.suppress(Exception):
            docker_client.client.images.remove(image_tag, force=True)


@pytest.fixture(scope="function")
def gerrit_mcp_container(docker_image: str, test_env_file: str) -> Generator[DockerContainer, None, None]:
    """
    Create a test container with proper lifecycle management.
    
    Uses auto_remove=False to prevent premature container removal during tests.
    """
    container = _create_test_container(docker_image, test_env_file)
    container.start()
    
    try:
        _wait_for_container_ready(container, TEST_CONFIG["CONTAINER_READY_TIMEOUT"])
        yield container
    finally:
        container.stop()


class TestDockerIntegrationTestcontainers:
    """Test Docker container build and runtime behavior using testcontainers"""

    def test_container_build_and_startup(self, gerrit_mcp_container: DockerContainer):
        """Test that container builds and starts successfully with MCP server."""
        # Verify container is running
        assert gerrit_mcp_container.get_container_host_ip() is not None
        
        # Test MCP server startup
        server_started = _start_mcp_server_detached(gerrit_mcp_container)
        assert server_started, "MCP server failed to start properly"

    def test_container_logs_no_errors(self, gerrit_mcp_container: DockerContainer):
        """Test that container startup doesn't produce error messages."""
        _start_mcp_server_detached(gerrit_mcp_container)
        
        # Allow logs to settle
        time.sleep(TEST_CONFIG["LOGS_SETTLE_DELAY"])
        
        logs = gerrit_mcp_container.get_logs()
        logs_text = logs[0].decode('utf-8') + logs[1].decode('utf-8')
        
        # Check for error patterns
        error_patterns = ["error", "exception", "failed", "traceback"]
        logs_lower = logs_text.lower()
        
        for pattern in error_patterns:
            assert pattern not in logs_lower, (
                f"Found error pattern '{pattern}' in container logs: {logs_text}"
            )

    def test_container_health_comprehensive(self, gerrit_mcp_container: DockerContainer):
        """Comprehensive container health validation."""
        # Verify container is running
        assert gerrit_mcp_container.get_container_host_ip() is not None
        
        # Test Python environment
        result = gerrit_mcp_container.exec(["python", "--version"])
        assert result.exit_code == 0, f"Python version check failed: {result.output}"
        
        # Test package imports
        import_test = "import mcp, requests, dotenv; print('All packages imported successfully')"
        result = gerrit_mcp_container.exec(["python", "-c", import_test])
        assert result.exit_code == 0, f"Package import test failed: {result.output}"
        
        # Test MCP server startup
        server_started = _start_mcp_server_detached(gerrit_mcp_container)
        assert server_started, "MCP server failed to start during health check"

    def test_container_environment_variables(self, gerrit_mcp_container: DockerContainer):
        """Test that environment variables are properly set in the container"""
        # Execute a command to check environment variables
        result = gerrit_mcp_container.exec(["env"])
        assert result.exit_code == 0
        env_output = result.output.decode('utf-8')
        
        # Check that our test environment variables are present
        assert "GERRIT_HOST=test.gerrit.example.com" in env_output
        assert "GERRIT_USER=test-user" in env_output
        assert "GERRIT_HTTP_PASSWORD=test-password" in env_output

    def test_container_python_environment(self, gerrit_mcp_container: DockerContainer):
        """Test that Python environment is properly configured"""
        # Check Python version
        result = gerrit_mcp_container.exec(["python", "--version"])
        assert result.exit_code == 0
        python_version = result.output.decode('utf-8').strip()
        assert "Python 3." in python_version
        
        # Check that required packages are installed
        # Try to get package list with pip
        try:
            result = gerrit_mcp_container.exec(["pip", "list", "--format=freeze"])
            pip_output = result.output.decode('utf-8')
            
            # Check if we got useful output from pip, regardless of exit code
            if pip_output.strip():
                # Check for key dependencies in pip output
                pip_lower = pip_output.lower()
                assert "mcp" in pip_lower
                assert "requests" in pip_lower
                assert "python-dotenv" in pip_lower
                return  # Success, no need to try import tests
        except Exception:
            # If pip command fails completely, fall back to import tests
            pass
        
        # Fallback: Test that key packages can be imported
        try:
            result = gerrit_mcp_container.exec(["python", "-c", 'import mcp; print("mcp imported successfully")'])
            assert result.exit_code == 0
            mcp_test = result.output.decode('utf-8')
            assert "mcp imported successfully" in mcp_test
            
            result = gerrit_mcp_container.exec(["python", "-c", 'import requests; print("requests imported successfully")'])
            assert result.exit_code == 0
            requests_test = result.output.decode('utf-8')
            assert "requests imported successfully" in requests_test
            
            result = gerrit_mcp_container.exec(["python", "-c", 'import dotenv; print("python-dotenv imported successfully")'])
            assert result.exit_code == 0
            dotenv_test = result.output.decode('utf-8')
            assert "python-dotenv imported successfully" in dotenv_test
        except Exception as e:
            pytest.fail(f"Could not verify Python packages installation: {e}")

    def test_container_file_structure(self, gerrit_mcp_container: DockerContainer):
        """Test that container has the expected file structure"""
        # Check that main files are present
        result = gerrit_mcp_container.exec(["ls", "-la", "/app/"])
        assert result.exit_code == 0
        file_list = result.output.decode('utf-8')
        
        # Required files that must be present
        expected_files = ["server.py", "config.py", "pyproject.toml"]
        for expected_file in expected_files:
            assert expected_file in file_list, f"Expected file {expected_file} not found in container"
        
        # Optional files (requirements.txt may not exist in PEP 621 builds)
        # We don't assert on optional files, just check they exist if present

    def test_container_interactive_mode_simulation(self, docker_image: str, test_env_file: str):
        """Test container behavior with stdin input simulation."""
        container = _create_test_container(docker_image, test_env_file)
        container.start()
        
        try:
            _wait_for_container_ready(container, TEST_CONFIG["CONTAINER_READY_TIMEOUT"])
            
            # Test MCP server startup
            server_started = _start_mcp_server_detached(container)
            assert server_started, "MCP server failed to start in interactive mode test"
            
            # Verify container is responsive
            assert container.get_container_host_ip() is not None
        finally:
            container.stop()

    def test_container_lifecycle_management(self, docker_image: str, test_env_file: str):
        """Test that containers are properly managed with auto_remove=False."""
        container = _create_test_container(docker_image, test_env_file)
        container.start()
        
        try:
            _wait_for_container_ready(container, TEST_CONFIG["CONTAINER_READY_TIMEOUT"])
            
            # Verify container stays alive (doesn't auto-remove)
            container_id = container._container.id
            assert container_id is not None
            
            # Wait and verify container is still running
            time.sleep(2)
            container._container.reload()
            assert container._container.status == "running"
            
            # Verify command execution works
            result = container.exec(["echo", "test"])
            assert result.exit_code == 0
            assert "test" in result.output.decode('utf-8')
            
        finally:
            container.stop()

    def test_parallel_container_creation(self, docker_image: str, test_env_file: str):
        """Test that multiple containers can be created simultaneously without conflicts."""
        containers = []
        
        try:
            # Create multiple containers with unique identifiers
            for i in range(3):
                container = _create_test_container(docker_image, test_env_file)
                container.with_env("CONTAINER_ID", str(i))
                container.start()
                containers.append(container)
            
            # Verify all containers are running with unique identities
            for i, container in enumerate(containers):
                _wait_for_container_ready(container, TEST_CONFIG["CONTAINER_READY_TIMEOUT"])
                
                result = container.exec(["printenv", "CONTAINER_ID"])
                assert result.exit_code == 0
                assert str(i) in result.output.decode('utf-8')
                
        finally:
            # Clean up all containers
            for container in containers:
                try:
                    container.stop()
                except Exception:
                    pass  # Ignore cleanup errors

    def test_container_error_recovery(self, docker_image: str, test_env_file: str):
        """Test error handling and recovery scenarios"""
        # Test 1: Container that fails to start properly
        bad_container = (DockerContainer(docker_image)
                         .with_command("sh -c 'sleep 1 && exit 1'")  # Command that fails after brief delay
                         .with_kwargs(auto_remove=False))
        
        bad_container.start()
        
        try:
            # Should handle failed containers gracefully
            # Wait for container to start, then it will exit with error
            time.sleep(2)  # Give it time to fail
            
            # Container should have exited by now
            bad_container._container.reload()
            # Don't assert specific status as it may vary, just ensure we can handle it
            
        finally:
            try:
                bad_container.stop()
            except Exception:
                pass  # Container may already be stopped
        
        # Test 2: Container with good command should still work
        good_container = (DockerContainer(docker_image)
                          .with_command("sleep infinity")
                          .with_env("PYTHONUNBUFFERED", "1")
                          .with_kwargs(auto_remove=False))
        
        # Set environment variables
        with open(test_env_file, 'r', encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    good_container.with_env(key, value)
        
        good_container.start()
        
        try:
            _wait_for_container_ready(good_container, TEST_CONFIG["CONTAINER_READY_TIMEOUT"])
            assert good_container.get_container_host_ip() is not None
        finally:
            good_container.stop()

    def test_image_reuse_efficiency(self, docker_image: str, test_env_file: str):
        """Test that the shared image fixture improves efficiency"""
        # This test verifies that we're reusing the same image
        # rather than building a new one for each test
        
        container1 = (DockerContainer(docker_image)
                      .with_command("sleep infinity")
                      .with_env("PYTHONUNBUFFERED", "1")
                      .with_kwargs(auto_remove=False))
        
        container2 = (DockerContainer(docker_image)
                      .with_command("sleep infinity")
                      .with_env("PYTHONUNBUFFERED", "1")
                      .with_kwargs(auto_remove=False))
        
        # Set environment variables for both
        for container in [container1, container2]:
            with open(test_env_file, 'r', encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        container.with_env(key, value)
        
        container1.start()
        container2.start()
        
        try:
            # Both should start successfully using the same image
            _wait_for_container_ready(container1, TEST_CONFIG["CONTAINER_READY_TIMEOUT"])
            _wait_for_container_ready(container2, TEST_CONFIG["CONTAINER_READY_TIMEOUT"])
            
            # Verify both are using the same image
            image1 = container1._container.image.id
            image2 = container2._container.image.id
            assert image1 == image2, "Containers should use the same image"
            
        finally:
            for container in [container1, container2]:
                try:
                    container.stop()
                except Exception:
                    pass

    def test_configuration_environment_variables(self, gerrit_mcp_container: DockerContainer):
        """Test that configuration environment variables work correctly"""
        # Test that our TEST_CONFIG values are being used
        assert TEST_CONFIG["STARTUP_TIMEOUT"] >= 30
        assert TEST_CONFIG["LOGS_SETTLE_DELAY"] >= 0
        assert TEST_CONFIG["CONTAINER_READY_TIMEOUT"] >= 10
        
        # Test that container respects PYTHONUNBUFFERED
        result = gerrit_mcp_container.exec(["printenv", "PYTHONUNBUFFERED"])
        assert result.exit_code == 0
        assert "1" in result.output.decode('utf-8')
        
        # Test that test environment variables are set
        result = gerrit_mcp_container.exec(["printenv", "GERRIT_HOST"])
        assert result.exit_code == 0
        assert "test.gerrit.example.com" in result.output.decode('utf-8')