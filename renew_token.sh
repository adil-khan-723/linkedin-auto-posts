#!/usr/bin/env bash
#
# One-command LinkedIn token renewal.
#
# Run this every ~2 months (or when a scheduled run fails with
# EXPIRED_ACCESS_TOKEN). It opens a browser for you to approve, mints a fresh
# access token, and pushes it straight to the GitHub Actions secret
# LINKEDIN_ACCESS_TOKEN. No copy-paste.
#
# First-time setup: put your app credentials in a local .env file (gitignored):
#     LINKEDIN_CLIENT_ID=xxxx
#     LINKEDIN_CLIENT_SECRET=xxxx
# Requirements: python3, gh (authenticated), and the app's Auth tab must list
# redirect URL http://localhost:8000/callback
#
# Usage:  ./renew_token.sh
set -euo pipefail

cd "$(dirname "$0")"

REPO="adil-khan-723/linkedin-auto-posts"

# Load credentials from .env if present
if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

if [[ -z "${LINKEDIN_CLIENT_ID:-}" || -z "${LINKEDIN_CLIENT_SECRET:-}" ]]; then
  echo "ERROR: LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET not set."
  echo "Put them in a .env file next to this script, or export them, then rerun."
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh (GitHub CLI) not found. Install it and run 'gh auth login'."
  exit 1
fi

# Isolated venv so we don't fight Homebrew's externally-managed python
if [[ ! -d .venv ]]; then
  echo "Creating virtualenv..."
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q requests python-dotenv

echo "Launching OAuth flow — approve in the browser when it opens..."
python get_refresh_token.py --set-secret --repo "$REPO"

echo
echo "Token renewed and pushed to $REPO."
echo "Verify with a manual run:"
echo "  gh workflow run \"LinkedIn Post Pipeline\" --repo $REPO"
