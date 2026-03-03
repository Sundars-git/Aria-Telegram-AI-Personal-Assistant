"""
google_auth.py — Google OAuth2 credential management.

Handles loading, refreshing, and (first-time) authorizing Google API
credentials for Gmail and Calendar access.

Setup:
  1. Create a Google Cloud project at https://console.cloud.google.com
  2. Enable Gmail API and Google Calendar API
  3. Create OAuth2 credentials (Desktop App type)
  4. Download the credentials JSON file
  5. Set GOOGLE_CREDENTIALS_PATH in .env (default: credentials.json)
  6. Run `python -m app.google_auth` once to authorize and generate token.json
"""

import logging
import os
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)

# Scopes required for Gmail read + draft and Calendar read + write
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar",
]

# Paths — configurable via environment
_CREDENTIALS_PATH = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
_TOKEN_PATH = os.getenv("GOOGLE_TOKEN_PATH", "token.json")


def get_credentials() -> Optional[Credentials]:
    """
    Load and return valid Google API credentials.

    Priority:
      1. Load existing token.json → refresh if expired
      2. If no token.json → run the OAuth consent flow (interactive, one-time)
      3. Return None if credentials.json is missing

    Returns:
        google.oauth2.credentials.Credentials or None if not configured.
    """
    creds = None

    # Try to load existing token
    if os.path.exists(_TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(_TOKEN_PATH, SCOPES)
        except Exception as exc:
            logger.warning("Could not load token.json: %s", exc)

    # Refresh or re-authorize
    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_token(creds)
            logger.info("Google token refreshed successfully.")
        except Exception as exc:
            logger.error("Token refresh failed: %s", exc)
            creds = None

    if not creds or not creds.valid:
        if not os.path.exists(_CREDENTIALS_PATH):
            logger.warning(
                "Google credentials not found at '%s'. "
                "Gmail and Calendar features are disabled. "
                "See app/google_auth.py docstring for setup instructions.",
                _CREDENTIALS_PATH,
            )
            return None

        try:
            flow = InstalledAppFlow.from_client_secrets_file(
                _CREDENTIALS_PATH, SCOPES
            )
            creds = flow.run_local_server(port=0)
            _save_token(creds)
            logger.info("Google authorization complete — token saved.")
        except Exception as exc:
            logger.error("Google OAuth flow failed: %s", exc)
            return None

    return creds


def _save_token(creds: Credentials) -> None:
    """Persist the credentials to token.json for future use."""
    try:
        with open(_TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
    except Exception as exc:
        logger.error("Could not save token: %s", exc)


def is_configured() -> bool:
    """Check if Google API credentials are available (token or credentials file)."""
    return os.path.exists(_TOKEN_PATH) or os.path.exists(_CREDENTIALS_PATH)


# ── CLI: run this module directly to authorize ────────────────────────────────

if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    print("🔐 Google OAuth2 Authorization")
    print(f"   Credentials file: {_CREDENTIALS_PATH}")
    print(f"   Token file:       {_TOKEN_PATH}")
    print()

    if not os.path.exists(_CREDENTIALS_PATH):
        print(f"❌ '{_CREDENTIALS_PATH}' not found.")
        print("   Download your OAuth2 credentials from Google Cloud Console")
        print("   and place the file in this directory.")
        sys.exit(1)

    creds = get_credentials()
    if creds and creds.valid:
        print("✅ Authorization successful! token.json has been saved.")
        print("   You can now use Gmail and Calendar features in your bot.")
    else:
        print("❌ Authorization failed. Check the logs above for details.")
        sys.exit(1)
