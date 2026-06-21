#!/usr/bin/env python3
"""
setup_auth.py - One-Time YouTube OAuth Setup
Run this ONCE on your LOCAL computer (not on GitHub).

Before running:
  1. Go to console.cloud.google.com
  2. Create or select a project
  3. Enable "YouTube Data API v3"
  4. APIs and Services > Credentials > Create OAuth 2.0 Client ID
  5. Application type: Desktop app
  6. Download the JSON -> save as "client_secrets.json" here
  7. Run: python setup_auth.py
  8. Copy the printed JSON to GitHub Secret YOUTUBE_TOKEN_JSON
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def main():
    print("=" * 55)
    print("  YouTube OAuth Setup")
    print("=" * 55)
    print("\nOpening browser — sign in with your YouTube channel...\n")

    flow = InstalledAppFlow.from_client_secrets_file(
        "client_secrets.json", scopes=SCOPES
    )
    creds = flow.run_local_server(port=8080, open_browser=True)

    token = {
        "token":         creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri":     creds.token_uri,
        "client_id":     creds.client_id,
        "client_secret": creds.client_secret,
        "scopes":        list(creds.scopes),
    }

    with open("token.json", "w") as f:
        json.dump(token, f, indent=2)

    print("\n" + "=" * 55)
    print("Copy this ENTIRE string to GitHub Secret 'YOUTUBE_TOKEN_JSON':")
    print("=" * 55)
    print(json.dumps(token))
    print("=" * 55)
    print("\nWARNING: Never commit token.json or client_secrets.json to Git!")
    print("Both are already listed in .gitignore.\n")


if __name__ == "__main__":
    main()
