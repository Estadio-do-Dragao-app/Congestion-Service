"""
Tests for MQTT TLS / Authentication configuration (_configure_mqtt_tls).

These tests verify that:
1. Credentials are always applied (username_pw_set called)
2. TLS is enabled when MQTT_CA_CERT env var points to an existing file
3. TLS is silently skipped when MQTT_CA_CERT is empty (backward compat)
4. TLS setup errors are caught and do not raise (graceful degradation)
"""
import ssl
import pytest
from unittest.mock import patch, MagicMock


# ── Helper: import _configure_mqtt_tls with mocked env ──────────────────────

def _get_configure_fn(mqtt_user="svc_test", mqtt_pass="pass_test", ca_cert=""):
    """Re-import mqtt_handler with patched environment variables."""
    import importlib
    import sys
    env = {"MQTT_USER": mqtt_user, "MQTT_PASS": mqtt_pass, "MQTT_CA_CERT": ca_cert}
    with patch.dict("os.environ", env, clear=False):
        # Remove cached module so env vars are re-read at import time
        for mod_name in list(sys.modules.keys()):
            if mod_name in ("mqtt_configs", "mqtt_handler"):
                del sys.modules[mod_name]
        import mqtt_handler as mh
        return mh._configure_mqtt_tls


# ── Tests ────────────────────────────────────────────────────────────────────

class TestConfigureMqttTls:

    def _mock_client(self):
        return MagicMock()

    def test_credentials_always_set(self):
        """username_pw_set must be called regardless of TLS settings."""
        fn = _get_configure_fn(mqtt_user="u", mqtt_pass="p", ca_cert="")
        client = self._mock_client()
        fn(client)
        client.username_pw_set.assert_called_once_with("u", "p")

    def test_no_tls_when_ca_cert_empty(self):
        """tls_set must NOT be called when MQTT_CA_CERT is empty string."""
        fn = _get_configure_fn(ca_cert="")
        client = self._mock_client()
        fn(client)
        client.tls_set.assert_not_called()
        client.tls_insecure_set.assert_not_called()

    def test_tls_enabled_with_ca_cert(self, tmp_path):
        """tls_set IS called when MQTT_CA_CERT points to an existing file."""
        ca_file = tmp_path / "ca.crt"
        ca_file.write_text("FAKE CA CERT")

        fn = _get_configure_fn(ca_cert=str(ca_file))
        client = self._mock_client()
        fn(client)

        client.tls_set.assert_called_once_with(
            ca_certs=str(ca_file),
            tls_version=ssl.PROTOCOL_TLS_CLIENT,
        )
        client.tls_insecure_set.assert_called_once_with(False)

    def test_tls_insecure_set_false(self, tmp_path):
        """tls_insecure_set(False) ensures hostname verification is ON."""
        ca_file = tmp_path / "ca.crt"
        ca_file.write_text("FAKE CA CERT")

        fn = _get_configure_fn(ca_cert=str(ca_file))
        client = self._mock_client()
        fn(client)
        client.tls_insecure_set.assert_called_once_with(False)

    def test_tls_error_does_not_raise(self, tmp_path):
        """If tls_set raises, _configure_mqtt_tls must NOT propagate the exception."""
        ca_file = tmp_path / "ca.crt"
        ca_file.write_text("FAKE CA CERT")

        fn = _get_configure_fn(ca_cert=str(ca_file))
        client = self._mock_client()
        client.tls_set.side_effect = ssl.SSLError("bad cert")

        # Should not raise
        fn(client)

        # Credentials must still have been applied
        client.username_pw_set.assert_called_once()
