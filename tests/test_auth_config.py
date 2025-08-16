#!/usr/bin/env python3
"""
Unit tests for authentication configuration functionality.

Tests the core authentication method switching between HTTP Digest (default)
and HTTP Basic (optional) authentication methods.
"""

import os
import pytest
from unittest.mock import patch
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

# Import the modules we're testing
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import (
    get_auth_method,
    get_password,
    create_auth_handler,
    VALID_AUTH_METHODS,
    DEFAULT_AUTH_METHOD
)


class TestAuthMethodConfiguration:
    """Test authentication method configuration and validation."""
    
    def test_default_auth_method(self):
        """Test that default authentication method is 'digest'."""
        with patch.dict(os.environ, {}, clear=True):
            assert get_auth_method() == 'digest'
            assert get_auth_method() == DEFAULT_AUTH_METHOD
    
    @pytest.mark.parametrize("auth_method,expected", [
        ('digest', 'digest'),
        ('basic', 'basic'),
        ('DIGEST', 'digest'),
        ('BASIC', 'basic'),
        ('Basic', 'basic'),
        ('Digest', 'digest'),
    ])
    def test_valid_auth_methods(self, auth_method, expected):
        """Test valid authentication methods (case insensitive)."""
        with patch.dict(os.environ, {'GERRIT_AUTH_METHOD': auth_method}):
            assert get_auth_method() == expected
    
    @pytest.mark.parametrize("invalid_method", [
        'invalid',
        'oauth',
        'token',
        '',
        'digest,basic',
        'none'
    ])
    def test_invalid_auth_methods(self, invalid_method):
        """Test that invalid authentication methods raise ValueError."""
        with patch.dict(os.environ, {'GERRIT_AUTH_METHOD': invalid_method}):
            with pytest.raises(ValueError) as exc_info:
                get_auth_method()
            assert f"Invalid authentication method: '{invalid_method}'" in str(exc_info.value)
            assert f"Must be one of {VALID_AUTH_METHODS}" in str(exc_info.value)


class TestPasswordConfiguration:
    """Test password configuration based on authentication method."""
    
    def test_digest_password_configuration(self):
        """Test password configuration for HTTP Digest authentication."""
        with patch.dict(os.environ, {
            'GERRIT_AUTH_METHOD': 'digest',
            'GERRIT_HTTP_PASSWORD': 'http-password-123'
        }, clear=True):
            assert get_password() == 'http-password-123'
    
    def test_basic_password_configuration(self):
        """Test password configuration for HTTP Basic authentication."""
        with patch.dict(os.environ, {
            'GERRIT_AUTH_METHOD': 'basic',
            'GERRIT_PASSWORD': 'ldap-password-456'
        }, clear=True):
            assert get_password() == 'ldap-password-456'
    
    def test_missing_digest_password(self):
        """Test error when GERRIT_HTTP_PASSWORD is missing for digest auth."""
        with patch.dict(os.environ, {'GERRIT_AUTH_METHOD': 'digest'}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                get_password()
            assert "GERRIT_HTTP_PASSWORD environment variable is required" in str(exc_info.value)
            assert "HTTP Digest authentication" in str(exc_info.value)
    
    def test_missing_basic_password(self):
        """Test error when GERRIT_PASSWORD is missing for basic auth."""
        with patch.dict(os.environ, {'GERRIT_AUTH_METHOD': 'basic'}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                get_password()
            assert "GERRIT_PASSWORD environment variable is required" in str(exc_info.value)
            assert "HTTP Basic authentication (LDAP)" in str(exc_info.value)


class TestAuthenticationFactory:
    """Test the authentication factory functionality."""
    
    def test_digest_auth_creation_default(self):
        """Test HTTP Digest authentication handler creation (default)."""
        with patch.dict(os.environ, {}, clear=True):
            auth = create_auth_handler('testuser', 'testpass')
            assert isinstance(auth, HTTPDigestAuth)
            assert auth.username == 'testuser'
            assert auth.password == 'testpass'
    
    def test_digest_auth_creation_explicit(self):
        """Test HTTP Digest authentication handler creation (explicit)."""
        with patch.dict(os.environ, {'GERRIT_AUTH_METHOD': 'digest'}):
            auth = create_auth_handler('testuser', 'testpass')
            assert isinstance(auth, HTTPDigestAuth)
            assert auth.username == 'testuser'
            assert auth.password == 'testpass'
    
    def test_basic_auth_creation(self):
        """Test HTTP Basic authentication handler creation."""
        with patch.dict(os.environ, {'GERRIT_AUTH_METHOD': 'basic'}):
            auth = create_auth_handler('testuser', 'testpass')
            assert isinstance(auth, HTTPBasicAuth)
            assert auth.username == 'testuser'
            assert auth.password == 'testpass'


class TestIntegrationScenarios:
    """Test complete integration scenarios."""
    
    def test_complete_digest_flow(self):
        """Test complete flow for HTTP Digest authentication."""
        with patch.dict(os.environ, {
            'GERRIT_AUTH_METHOD': 'digest',
            'GERRIT_HTTP_PASSWORD': 'http-password-123'
        }, clear=True):
            # Get configuration
            auth_method = get_auth_method()
            password = get_password()
            
            # Create auth handler
            auth = create_auth_handler('testuser', password)
            
            # Verify results
            assert auth_method == 'digest'
            assert password == 'http-password-123'
            assert isinstance(auth, HTTPDigestAuth)
            assert auth.username == 'testuser'
            assert auth.password == 'http-password-123'
    
    def test_complete_basic_flow(self):
        """Test complete flow for HTTP Basic authentication."""
        with patch.dict(os.environ, {
            'GERRIT_AUTH_METHOD': 'basic',
            'GERRIT_PASSWORD': 'ldap-password-456'
        }, clear=True):
            # Get configuration
            auth_method = get_auth_method()
            password = get_password()
            
            # Create auth handler
            auth = create_auth_handler('testuser', password)
            
            # Verify results
            assert auth_method == 'basic'
            assert password == 'ldap-password-456'
            assert isinstance(auth, HTTPBasicAuth)
            assert auth.username == 'testuser'
            assert auth.password == 'ldap-password-456'
    
    def test_backward_compatibility_default(self):
        """Test backward compatibility with no configuration (default behavior)."""
        with patch.dict(os.environ, {
            'GERRIT_HTTP_PASSWORD': 'original-password'
        }, clear=True):
            # Should default to digest authentication
            auth_method = get_auth_method()
            password = get_password()
            auth = create_auth_handler('testuser', password)
            
            assert auth_method == 'digest'
            assert password == 'original-password'
            assert isinstance(auth, HTTPDigestAuth)


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])