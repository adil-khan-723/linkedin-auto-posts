#!/usr/bin/env python3
"""
ONE-TIME local helper to obtain a LinkedIn refresh token.

Run this once on your machine to bootstrap the auto-refresh flow. After that the
pipeline renews its own access token every run and you never touch tokens again
until the refresh token itself expires (~365 days).

Prerequisites (LinkedIn Developer Portal — https://developer.linkedin.com):
  1. Your app must have the "Sign In with LinkedIn using OpenID Connect" and
     "Share on LinkedIn" products enabled.
  2. Programmatic refresh tokens must be enabled for the app (they are, for apps
     with the Community Management API / standard OAuth). If the token response
     below has no "refresh_token", your app is not eligible and you must keep
     rotating LINKEDIN_ACCESS_TOKEN manually.
  3. Add this exact redirect URL in the app's Auth tab:
         http://localhost:8000/callback

Usage:
    export LINKEDIN_CLIENT_ID=xxxx
    export LINKEDIN_CLIENT_SECRET=xxxx
    python get_refresh_token.py

It opens a browser, you approve, and it prints the refresh + access tokens.
"""
import argparse
import os
import subprocess
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlencode, urlparse, parse_qs

DEFAULT_REPO = "adil-khan-723/linkedin-auto-posts"

import requests

REDIRECT_URI = "http://localhost:8000/callback"
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
# w_member_social = post; openid/profile = read member id
SCOPES = "openid profile w_member_social"

_auth_code = {}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        if "code" in qs:
            _auth_code["code"] = qs["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Authorized. You can close this tab and return to the terminal.")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"No code in callback: " + self.path.encode())

    def log_message(self, *args):
        pass


def _gh_set_secret(name, value, repo):
    result = subprocess.run(
        ["gh", "secret", "set", name, "--repo", repo],
        input=value,
        text=True,
    )
    if result.returncode == 0:
        print(f"  set secret {name} on {repo}")
    else:
        print(f"  FAILED to set secret {name} (gh exit {result.returncode})")


def handle_tokens(data, repo, set_secret):
    """Print tokens; optionally push them to GitHub secrets via gh."""
    access = data.get("access_token")
    refresh = data.get("refresh_token")

    print("\n=== SUCCESS ===")
    print("access_token (short-lived, ~60d):\n ", access)
    if refresh:
        print("\nrefresh_token (~365d) — LINKEDIN_REFRESH_TOKEN secret:\n ", refresh)
    else:
        print(
            "\nNOTE: no refresh_token returned — app is not enrolled for "
            "programmatic refresh. The access_token above is what the pipeline "
            "uses (LINKEDIN_ACCESS_TOKEN); rerun this to renew before it expires."
        )

    if not set_secret:
        if refresh:
            print(
                "\nSet the secrets:\n"
                f"  gh secret set LINKEDIN_REFRESH_TOKEN --repo {repo}\n"
                f"  gh secret set LINKEDIN_CLIENT_SECRET --repo {repo}"
            )
        else:
            print(f"\nSet the secret:\n  gh secret set LINKEDIN_ACCESS_TOKEN --repo {repo}")
        return

    print(f"\nSetting GitHub secrets on {repo} ...")
    if refresh:
        _gh_set_secret("LINKEDIN_REFRESH_TOKEN", refresh, repo)
        client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
        if client_secret:
            _gh_set_secret("LINKEDIN_CLIENT_SECRET", client_secret, repo)
    else:
        _gh_set_secret("LINKEDIN_ACCESS_TOKEN", access, repo)
    print("Done. Trigger a run to verify: "
          f'gh workflow run "LinkedIn Post Pipeline" --repo {repo}')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--set-secret", action="store_true",
                        help="push the token(s) to GitHub secrets via gh")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    args = parser.parse_args()

    client_id = os.getenv("LINKEDIN_CLIENT_ID")
    client_secret = os.getenv("LINKEDIN_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("ERROR: set LINKEDIN_CLIENT_ID and LINKEDIN_CLIENT_SECRET env vars first.")
        sys.exit(1)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
    }
    url = f"{AUTH_URL}?{urlencode(params)}"
    print("Opening browser to authorize...\nIf it doesn't open, visit:\n", url, "\n")
    webbrowser.open(url)

    server = HTTPServer(("localhost", 8000), _Handler)
    while "code" not in _auth_code:
        server.handle_request()
    code = _auth_code["code"]

    resp = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    if not resp.ok:
        print(f"Token exchange failed {resp.status_code}: {resp.text}")
        sys.exit(1)

    data = resp.json()
    handle_tokens(data, repo=args.repo, set_secret=args.set_secret)


if __name__ == "__main__":
    main()
