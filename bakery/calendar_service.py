"""
Google Calendar integration for Tastyz Bakery.

Creates delivery events on a Google Calendar when orders are placed,
so staff can track upcoming deliveries.
Uses OAuth2 with the GOOGLE_CALENDAR_CLIENT_ID and CLIENT_SECRET from .env.
"""

import logging
from datetime import datetime, timedelta

from django.conf import settings

logger = logging.getLogger(__name__)


def _get_calendar_service():
    """
    Build an authenticated Google Calendar API service using service-to-service
    or stored credentials.  Returns None if not configured.
    """
    client_id = getattr(settings, "GOOGLE_CALENDAR_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_CALENDAR_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        logger.debug("Google Calendar not configured — skipping")
        return None

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        # Look for saved token in project root
        import json
        from pathlib import Path

        token_path = Path(settings.BASE_DIR) / "calendar_token.json"
        if not token_path.exists():
            logger.info(
                "Google Calendar token file not found at %s. "
                "Run 'python manage.py setup_google_calendar' to authenticate.",
                token_path,
            )
            return None

        token_data = json.loads(token_path.read_text())
        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
        )

        service = build("calendar", "v3", credentials=creds)
        return service
    except Exception as exc:
        logger.warning("Failed to build Google Calendar service: %s", exc)
        return None


def create_delivery_event(order) -> dict | None:
    """
    Create a Google Calendar event for an order delivery.

    Args:
        order: bakery.models.Order instance

    Returns:
        dict with event details if created, None if calendar unavailable.
    """
    service = _get_calendar_service()
    if service is None:
        logger.debug("Calendar service unavailable — delivery event not created")
        return None

    try:
        # Schedule delivery 2 hours from now (or use delivery_date if set)
        delivery_time = getattr(order, "delivery_date", None)
        if not delivery_time:
            delivery_time = datetime.now() + timedelta(hours=2)

        end_time = delivery_time + timedelta(hours=1)

        event = {
            "summary": f"🎂 Delivery: {order.product_name_snapshot}",
            "description": (
                f"Customer: {order.customer_name}\n"
                f"Phone: {order.customer_phone}\n"
                f"Product: {order.product_name_snapshot}\n"
                f"Quantity: {order.quantity}\n"
                f"Special Instructions: {order.special_instructions or 'None'}\n"
                f"Order ID: {order.pk}"
            ),
            "start": {
                "dateTime": delivery_time.isoformat(),
                "timeZone": "Africa/Kampala",
            },
            "end": {
                "dateTime": end_time.isoformat(),
                "timeZone": "Africa/Kampala",
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 30},
                ],
            },
        }

        created_event = service.events().insert(calendarId="primary", body=event).execute()
        logger.info("Calendar event created: %s", created_event.get("id"))
        return {
            "event_id": created_event.get("id"),
            "html_link": created_event.get("htmlLink"),
            "summary": created_event.get("summary"),
        }
    except Exception as exc:
        logger.error("Failed to create calendar event: %s", exc)
        return None


def get_upcoming_deliveries(max_results: int = 10) -> list[dict]:
    """
    Fetch upcoming delivery events from Google Calendar.

    Returns:
        List of event dicts with summary, start time, description.
    """
    service = _get_calendar_service()
    if service is None:
        return []

    try:
        now = datetime.utcnow().isoformat() + "Z"
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
                q="Delivery:",
            )
            .execute()
        )
        events = events_result.get("items", [])
        return [
            {
                "event_id": e.get("id"),
                "summary": e.get("summary", ""),
                "start": e.get("start", {}).get("dateTime", ""),
                "description": e.get("description", ""),
                "html_link": e.get("htmlLink", ""),
            }
            for e in events
        ]
    except Exception as exc:
        logger.error("Failed to fetch calendar events: %s", exc)
        return []


def is_calendar_configured() -> bool:
    """Check if Google Calendar credentials are available."""
    client_id = getattr(settings, "GOOGLE_CALENDAR_CLIENT_ID", "")
    client_secret = getattr(settings, "GOOGLE_CALENDAR_CLIENT_SECRET", "")
    return bool(client_id and client_secret)
