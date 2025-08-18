"""
Configuration module for Gerrit MCP server authentication.

This module handles environment variable configuration for authentication methods
and provides factory functions for creating appropriate authentication handlers.

Supports both HTTP Digest authentication (original/default) and HTTP Basic 
authentication (optional) to maintain backward compatibility while providing
flexibility for different Gerrit server configurations.
"""

import os
import sys
import logging
import re
from typing import Union
from urllib.parse import urlparse

import requests
from requests.auth import HTTPBasicAuth, HTTPDigestAuth

# Version check for requests library
try:
    # Use modern importlib.metadata instead of deprecated pkg_resources
    try:
        from importlib.metadata import version
    except ImportError:
        # Fallback for Python < 3.8
        from importlib_metadata import version
    
    requests_version = version("requests")
    major, minor, patch = map(int, requests_version.split('.')[:3])
    if major < 2 or (major == 2 and minor < 31):
        raise ImportError(
            f"requests library version {requests_version} is too old. "
            "Please upgrade to requests>=2.31.0 for latest security patches:\n"
            "  pip install --upgrade 'requests>=2.31.0'"
        )
except (ImportError, Exception) as e:
    if "requests" in str(e):
        print(f"Warning: Could not verify requests version: {e}", file=sys.stderr)

# Valid authentication methods
VALID_AUTH_METHODS = ['digest', 'basic']
DEFAULT_AUTH_METHOD = 'digest'  # Maintain backward compatibility with original codebase

# Export list
__all__ = ['get_auth_method', 'get_password', 'create_auth_handler', 'VALID_AUTH_METHODS', 'DEFAULT_AUTH_METHOD']


def get_auth_method() -> str:
    """
    Get the authentication method from environment variables.
    
    Reads the GERRIT_AUTH_METHOD environment variable and validates it.
    Defaults to 'digest' to preserve the original HTTP Digest authentication
    behavior. HTTP Basic authentication is available as an optional case.
    
    Returns:
        str: The authentication method ('digest' or 'basic')
        
    Raises:
        ValueError: If the authentication method is invalid
        
    Environment Variables:
        GERRIT_AUTH_METHOD: Authentication method to use. Valid values are:
            - 'digest' (default): Use HTTP Digest authentication (original method, uses GERRIT_HTTP_PASSWORD)
            - 'basic': Use HTTP Basic authentication (optional case, uses GERRIT_PASSWORD for LDAP)
            
    Examples:
        >>> # Default behavior - HTTP Digest (preserves original)
        >>> os.environ.pop('GERRIT_AUTH_METHOD', None)
        >>> get_auth_method()
        'digest'
        
        >>> # Explicit HTTP Digest (original method)
        >>> os.environ['GERRIT_AUTH_METHOD'] = 'digest'
        >>> get_auth_method()
        'digest'
        
        >>> # HTTP Basic authentication (optional case)
        >>> os.environ['GERRIT_AUTH_METHOD'] = 'basic'
        >>> get_auth_method()
        'basic'
        
        >>> # Case insensitive
        >>> os.environ['GERRIT_AUTH_METHOD'] = 'BASIC'
        >>> get_auth_method()
        'basic'
    """
    auth_method = os.environ.get('GERRIT_AUTH_METHOD', DEFAULT_AUTH_METHOD)
    auth_method_lower = auth_method.lower()
    
    if auth_method_lower not in VALID_AUTH_METHODS:
        raise ValueError(
            f"Invalid authentication method: '{auth_method}'. "
            f"Must be one of {VALID_AUTH_METHODS}. "
            f"Default is '{DEFAULT_AUTH_METHOD}' (preserves original HTTP Digest behavior)."
        )
    
    return auth_method_lower


def get_password() -> str:
    """
    Get the appropriate password based on the authentication method.
    
    Returns the correct password environment variable based on the selected
    authentication method:
    - HTTP Digest (default): Uses GERRIT_HTTP_PASSWORD (original behavior)
    - HTTP Basic (optional): Uses GERRIT_PASSWORD (LDAP password)
    
    Returns:
        str: The password for the selected authentication method
        
    Raises:
        ValueError: If the required password environment variable is not set
        
    Environment Variables:
        GERRIT_HTTP_PASSWORD: Used for HTTP Digest authentication (original)
        GERRIT_PASSWORD: Used for HTTP Basic authentication (LDAP)
        
    Examples:
        >>> # Default - HTTP Digest uses GERRIT_HTTP_PASSWORD
        >>> os.environ['GERRIT_HTTP_PASSWORD'] = 'http-password'
        >>> os.environ.pop('GERRIT_AUTH_METHOD', None)
        >>> get_password()
        'http-password'
        
        >>> # HTTP Basic uses GERRIT_PASSWORD
        >>> os.environ['GERRIT_AUTH_METHOD'] = 'basic'
        >>> os.environ['GERRIT_PASSWORD'] = 'ldap-password'
        >>> get_password()
        'ldap-password'
    """
    auth_method = get_auth_method()
    
    if auth_method == 'basic':
        password = os.environ.get('GERRIT_PASSWORD')
        if not password:
            raise ValueError(
                "GERRIT_PASSWORD environment variable is required for HTTP Basic authentication (LDAP). "
                "Please set GERRIT_PASSWORD to your LDAP password."
            )
        return password
    else:  # Default to digest (original behavior)
        password = os.environ.get('GERRIT_HTTP_PASSWORD')
        if not password:
            raise ValueError(
                "GERRIT_HTTP_PASSWORD environment variable is required for HTTP Digest authentication. "
                "Please set GERRIT_HTTP_PASSWORD to your HTTP password from Gerrit Settings > HTTP Credentials."
            )
        return password


def create_auth_handler(username: str, password: str) -> Union[HTTPBasicAuth, HTTPDigestAuth]:
    """
    Create an authentication handler based on the configured method.
    
    This factory function creates the appropriate authentication handler
    based on the GERRIT_AUTH_METHOD environment variable. Preserves the
    original HTTP Digest authentication as the default behavior, with
    HTTP Basic authentication available as an optional case.
    
    Args:
        username: The username for authentication
        password: The password for authentication (should come from get_password())
        
    Returns:
        Union[HTTPBasicAuth, HTTPDigestAuth]: The appropriate authentication handler
        
    Raises:
        ValueError: If the authentication method is invalid
        
    Examples:
        >>> # Default behavior - HTTP Digest (preserves original)
        >>> os.environ.pop('GERRIT_AUTH_METHOD', None)
        >>> auth = create_auth_handler('user', 'http-pass')
        >>> isinstance(auth, HTTPDigestAuth)
        True
        
        >>> # HTTP Basic authentication (optional case)
        >>> os.environ['GERRIT_AUTH_METHOD'] = 'basic'
        >>> auth = create_auth_handler('user', 'ldap-pass')
        >>> isinstance(auth, HTTPBasicAuth)
        True
        
        >>> # HTTP Digest authentication (explicit, same as default)
        >>> os.environ['GERRIT_AUTH_METHOD'] = 'digest'
        >>> auth = create_auth_handler('user', 'http-pass')
        >>> isinstance(auth, HTTPDigestAuth)
        True
    """
    auth_method = get_auth_method()
    
    if auth_method == 'basic':
        # Optional case: HTTP Basic with LDAP password
        return HTTPBasicAuth(username, password)
    else:  # Default: HTTP Digest (preserves original behavior)
        return HTTPDigestAuth(username, password)