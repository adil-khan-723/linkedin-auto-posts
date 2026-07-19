"""
Resolve a valid LinkedIn access token.

Preferred path: exchange a long-lived refresh token (~365 days) for a fresh
access token on every run, so the pipeline never breaks on the ~60-day access
token expiry.

Fallback: use a static LINKEDIN_ACCESS_TOKEN (legacy behaviour) if no refresh
token is configured.

One-time setup: run get_refresh_token.py locally to obtain the initial
LINKEDIN_REFRESH_TOKEN, then store it (plus client id/secret) as repo secrets.
"""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"


def _refresh(refresh_token, client_id, client_secret):
    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if not resp.ok:
        raise RuntimeError(
            f"LinkedIn token refresh {resp.status_code}: {resp.text}"
        )
    return resp.json()["access_token"]


def get_access_token():
    """Return a usable access token, refreshing if possible."""
    refresh_token = os.getenv("LINKEDIN_REFRESH_TOKEN")
    if refresh_token:
        client_id = os.getenv("LINKEDIN_CLIENT_ID")
        client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        if not client_id or not client_secret:
            raise ValueError(
                "LINKEDIN_REFRESH_TOKEN is set but LINKEDIN_CLIENT_ID / "
                "LINKEDIN_CLIENT_SECRET are missing"
            )
        return _refresh(refresh_token, client_id, client_secret)

    token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    if not token:
        raise ValueError(
            "No credentials: set LINKEDIN_REFRESH_TOKEN (preferred) or "
            "LINKEDIN_ACCESS_TOKEN"
        )
    return token
