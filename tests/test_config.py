from __future__ import annotations

import warnings

import pytest

from avatcado import Avatcado, AvatcadoError


class TestConfigResolution:
    def test_accepts_string_api_key(self) -> None:
        client = Avatcado("avat_live_mykey")
        assert client.vat is not None
        assert client.rates is not None
        client.close()

    def test_accepts_kwarg_api_key(self) -> None:
        client = Avatcado(api_key="avat_live_mykey")
        assert client.vat is not None
        client.close()

    def test_falls_back_to_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AVATCADO_API_KEY", "avat_live_envkey")
        client = Avatcado()
        assert client.vat is not None
        client.close()

    def test_raises_when_no_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AVATCADO_API_KEY", raising=False)
        with pytest.raises(AvatcadoError, match="No API key provided"):
            Avatcado()

    def test_raises_when_empty_key(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("AVATCADO_API_KEY", raising=False)
        with pytest.raises(AvatcadoError):
            Avatcado("")

    def test_custom_base_url(self) -> None:
        client = Avatcado("avat_live_key", base_url="https://custom.api.avatcado.com")
        assert client._config.base_url == "https://custom.api.avatcado.com"
        client.close()

    def test_custom_timeout(self) -> None:
        client = Avatcado("avat_live_key", timeout=5.0)
        assert client._config.timeout == 5.0
        client.close()

    def test_default_base_url(self) -> None:
        client = Avatcado("avat_live_key")
        assert client._config.base_url == "https://api.avatcado.com"
        client.close()

    def test_default_timeout(self) -> None:
        client = Avatcado("avat_live_key")
        assert client._config.timeout == 30.0
        client.close()

    def test_warns_on_invalid_key_prefix(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            client = Avatcado("invalid_prefix_key")
            assert len(w) == 1
            assert "avat_live_" in str(w[0].message)
            client.close()

    def test_no_warning_for_live_key(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            client = Avatcado("avat_live_key")
            assert len(w) == 0
            client.close()

    def test_no_warning_for_test_key(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            client = Avatcado("avat_test_key")
            assert len(w) == 0
            client.close()

    def test_env_var_used_when_arg_is_none(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AVATCADO_API_KEY", "avat_live_from_env")
        client = Avatcado()
        assert client._config.api_key == "avat_live_from_env"
        client.close()

    def test_explicit_key_overrides_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("AVATCADO_API_KEY", "avat_live_from_env")
        client = Avatcado("avat_live_explicit")
        assert client._config.api_key == "avat_live_explicit"
        client.close()
