#!/usr/bin/env python3
"""Unit tests for TLS verification configuration handling."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from server import resolve_ssl_verification_setting


class TestSSLVerificationSetting:
    """Verify TLS verification configuration parsing."""

    def test_default_verification_enabled(self):
        """Defaults to strict verification when unset."""
        with patch.dict(os.environ, {}, clear=True):
            assert resolve_ssl_verification_setting() is True

    @pytest.mark.parametrize("env_value", ["true", "TRUE", "1", "yes", "on"])
    def test_truthy_values_enable_verification(self, env_value):
        """Truthy values keep verification enabled."""
        with patch.dict(os.environ, {"GERRIT_SSL_VERIFY": env_value}, clear=True):
            assert resolve_ssl_verification_setting() is True

    @pytest.mark.parametrize("env_value", ["false", "FALSE", "0", "no", "off"])
    def test_falsy_values_disable_verification(self, env_value):
        """Falsy values disable verification."""
        with patch.dict(os.environ, {"GERRIT_SSL_VERIFY": env_value}, clear=True):
            assert resolve_ssl_verification_setting() is False

    def test_ca_bundle_via_env(self, tmp_path):
        """A CA bundle path is accepted via dedicated env variable."""
        bundle_path = tmp_path / "ca.pem"
        bundle_path.write_text("certificate")

        with patch.dict(os.environ, {"GERRIT_CA_BUNDLE": str(bundle_path)}, clear=True):
            assert resolve_ssl_verification_setting() == str(bundle_path)

    def test_ca_bundle_with_whitespace_and_tilde(self, tmp_path):
        """Whitespace and tilde-expansion are handled for CA bundle paths."""
        bundle_path = tmp_path / "ca.pem"
        bundle_path.write_text("certificate")

        env = {
            "HOME": str(tmp_path),
            "GERRIT_CA_BUNDLE": f" ~/{bundle_path.name} ",
        }

        with patch.dict(os.environ, env, clear=True):
            assert resolve_ssl_verification_setting() == str(bundle_path)

    def test_ca_bundle_via_ssl_verify_env(self, tmp_path):
        """A filesystem path supplied in GERRIT_SSL_VERIFY is accepted."""
        bundle_path = tmp_path / "ca.pem"
        bundle_path.write_text("certificate")

        with patch.dict(os.environ, {"GERRIT_SSL_VERIFY": str(bundle_path)}, clear=True):
            assert resolve_ssl_verification_setting() == str(bundle_path)

    def test_invalid_value_raises_error(self):
        """Invalid configuration values raise an informative error."""
        with patch.dict(os.environ, {"GERRIT_SSL_VERIFY": "maybe"}, clear=True):
            with pytest.raises(ValueError):
                resolve_ssl_verification_setting()

    def test_missing_ca_bundle_path_raises_error(self):
        """Missing CA bundle path leads to ValueError."""
        with patch.dict(os.environ, {"GERRIT_CA_BUNDLE": "/non/existent/path.pem"}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                resolve_ssl_verification_setting()
            assert "does not exist" in str(exc_info.value)

    def test_ca_bundle_directory_path_raises_error(self, tmp_path):
        """A CA bundle pointing to a directory is rejected."""
        with patch.dict(os.environ, {"GERRIT_CA_BUNDLE": str(tmp_path)}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                resolve_ssl_verification_setting()
            assert "does not exist" in str(exc_info.value)

    def test_empty_ca_bundle_after_trim_raises_error(self):
        """Whitespace-only CA bundle values are invalid."""
        with patch.dict(os.environ, {"GERRIT_CA_BUNDLE": "   "}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                resolve_ssl_verification_setting()
            assert "empty" in str(exc_info.value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
