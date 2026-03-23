"""
Django management command to set up Google Calendar OAuth authentication.

Generates and saves OAuth2 credentials for Google Calendar integration.
Uses device flow for headless/server environments.
"""

import json
import logging
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Set up Google Calendar OAuth authentication and save credentials token."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            help="Google Calendar email (optional, for reference only)",
        )

    def handle(self, *args, **options):
        client_id = getattr(settings, "GOOGLE_CALENDAR_CLIENT_ID", "")
        client_secret = getattr(settings, "GOOGLE_CALENDAR_CLIENT_SECRET", "")

        if not client_id or not client_secret:
            self.stdout.write(
                self.style.ERROR(
                    "❌ Google Calendar credentials not configured in .env file.\n"
                    "Please add GOOGLE_CALENDAR_CLIENT_ID and GOOGLE_CALENDAR_CLIENT_SECRET."
                )
            )
            return

        try:
            from google_auth_oauthlib.flow import InstalledAppFlow
            from google.auth.transport.requests import Request

            # OAuth2 scopes required for calendar operations
            SCOPES = ["https://www.googleapis.com/auth/calendar"]

            # Get the base directory
            if hasattr(settings, "BASE_DIR"):
                base_dir = settings.BASE_DIR
            else:
                base_dir = Path(__file__).resolve().parent.parent.parent.parent

            token_path = Path(base_dir) / "calendar_token.json"

            # Client config with multiple redirect URIs to handle different scenarios
            client_config = {
                "installed": {
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": [
                        "http://localhost:8080/",
                        "http://localhost:8000/",
                        "urn:ietf:wg:oauth:2.0:oob",  # Out-of-band for manual code entry
                    ],
                }
            }

            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)

            # Use run_local_server with open_browser=False for better control
            self.stdout.write(
                self.style.SUCCESS(
                    f"\n{'='*60}\n"
                    f"🔐 Google Calendar OAuth Setup\n"
                    f"{'='*60}\n\n"
                    f"Starting authorization flow...\n"
                )
            )

            creds = flow.run_local_server(port=8080, open_browser=True)

            # Save the token
            token_data = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": creds.scopes,
            }
            token_path.write_text(json.dumps(token_data))

            self.stdout.write(
                self.style.SUCCESS(
                    f"\n✅ Google Calendar authenticated successfully!\n"
                    f"   Token saved to: {token_path}\n\n"
                    f"🎉 Delivery events will now be created automatically\n"
                    f"   when orders are placed in Google Calendar.\n"
                )
            )

        except ImportError as e:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Missing required package: {e}\n"
                    f"Install with: pip install google-auth-oauthlib google-auth-httplib2"
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(
                    f"❌ Error during setup: {e}\n"
                    f"Please check your credentials and try again."
                )
            )
