import pytest
from unittest.mock import patch, MagicMock
import linkedin_auth


def test_refresh_exchanges_refresh_token_for_access_token(monkeypatch):
    monkeypatch.setenv("LINKEDIN_REFRESH_TOKEN", "refresh_abc")
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "client_123")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "secret_xyz")
    monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN", raising=False)

    mock_resp = MagicMock(
        ok=True,
        status_code=200,
        json=lambda: {"access_token": "fresh_token", "expires_in": 5184000},
    )
    with patch("linkedin_auth.requests.post", return_value=mock_resp) as mock_post:
        token = linkedin_auth.get_access_token()

    assert token == "fresh_token"
    url = mock_post.call_args[0][0]
    data = mock_post.call_args[1]["data"]
    assert url == "https://www.linkedin.com/oauth/v2/accessToken"
    assert data["grant_type"] == "refresh_token"
    assert data["refresh_token"] == "refresh_abc"
    assert data["client_id"] == "client_123"
    assert data["client_secret"] == "secret_xyz"


def test_falls_back_to_static_access_token_when_no_refresh(monkeypatch):
    monkeypatch.delenv("LINKEDIN_REFRESH_TOKEN", raising=False)
    monkeypatch.setenv("LINKEDIN_ACCESS_TOKEN", "static_token")

    with patch("linkedin_auth.requests.post") as mock_post:
        token = linkedin_auth.get_access_token()

    assert token == "static_token"
    mock_post.assert_not_called()


def test_refresh_failure_raises_with_body(monkeypatch):
    monkeypatch.setenv("LINKEDIN_REFRESH_TOKEN", "refresh_abc")
    monkeypatch.setenv("LINKEDIN_CLIENT_ID", "client_123")
    monkeypatch.setenv("LINKEDIN_CLIENT_SECRET", "secret_xyz")

    mock_resp = MagicMock(
        ok=False,
        status_code=400,
        text='{"error":"invalid_grant"}',
    )
    with patch("linkedin_auth.requests.post", return_value=mock_resp):
        with pytest.raises(RuntimeError, match="invalid_grant"):
            linkedin_auth.get_access_token()


def test_raises_when_nothing_configured(monkeypatch):
    monkeypatch.delenv("LINKEDIN_REFRESH_TOKEN", raising=False)
    monkeypatch.delenv("LINKEDIN_ACCESS_TOKEN", raising=False)

    with pytest.raises(ValueError, match="LINKEDIN_ACCESS_TOKEN"):
        linkedin_auth.get_access_token()
