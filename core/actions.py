"""
actions.py

Given a parsed QRContent object, perform (or prepare) the appropriate
real-world action: open a browser, launch the mail client, open Maps,
build an .ics calendar file, or just hand back text to copy/save.

Kept separate from the GUI so the logic can be tested or reused without
Tkinter running.
"""

import webbrowser
import os
import tempfile
from datetime import datetime

from core.content_parser import QRContent, QRType


class ActionResult:
    """Small container describing what happened when an action ran."""

    def __init__(self, success: bool, message: str, opened_path: str | None = None):
        self.success = success
        self.message = message
        self.opened_path = opened_path


class ActionHandler:
    """Performs the correct action for each QRType."""

    def perform(self, content: QRContent) -> ActionResult:
        """Dispatch to the right handler based on content.qr_type."""
        handler = {
            QRType.URL: self._open_url,
            QRType.EMAIL: self._open_email,
            QRType.PHONE: self._handle_phone,
            QRType.SMS: self._handle_sms,
            QRType.WIFI: self._handle_wifi,
            QRType.GEO: self._open_maps,
            QRType.CALENDAR_EVENT: self._handle_calendar,
            QRType.CONTACT: self._handle_contact,
            QRType.CRYPTO: self._handle_crypto,
            QRType.TEXT: self._handle_text,
            QRType.UNKNOWN: self._handle_unknown,
        }.get(content.qr_type, self._handle_unknown)

        try:
            return handler(content)
        except Exception as exc:
            return ActionResult(False, f"Action failed: {exc}")

    # ------------------------------------------------------------------ #

    def _open_url(self, content: QRContent) -> ActionResult:
        webbrowser.open(content.fields["url"])
        return ActionResult(True, "Opened link in default browser.")

    def _open_email(self, content: QRContent) -> ActionResult:
        webbrowser.open(content.raw)
        return ActionResult(True, "Opened default email client.")

    def _handle_phone(self, content: QRContent) -> ActionResult:
        return ActionResult(True, "Phone number ready to copy.")

    def _handle_sms(self, content: QRContent) -> ActionResult:
        # Desktop OSes generally can't send SMS directly; surface the
        # number/message so the user can act on it (e.g. copy to phone).
        return ActionResult(True, "SMS details ready to copy.")

    def _handle_wifi(self, content: QRContent) -> ActionResult:
        return ActionResult(True, "Wi-Fi credentials ready to copy.")

    def _open_maps(self, content: QRContent) -> ActionResult:
        lat, lon = content.fields["lat"], content.fields["lon"]
        webbrowser.open(f"https://www.google.com/maps?q={lat},{lon}")
        return ActionResult(True, "Opened location in Google Maps.")

    def build_ics_content(self, content: QRContent) -> str:
        """Build a standalone .ics calendar file body from a QRContent."""
        return (
            "BEGIN:VCALENDAR\nVERSION:2.0\nBEGIN:VEVENT\n"
            f"SUMMARY:{content.fields.get('summary', 'Event')}\n"
            f"DTSTART:{content.fields.get('start', '')}\n"
            f"DTEND:{content.fields.get('end', '')}\n"
            f"LOCATION:{content.fields.get('location', '')}\n"
            f"DESCRIPTION:{content.fields.get('description', '')}\n"
            "END:VEVENT\nEND:VCALENDAR\n"
        )

    def _handle_calendar(self, content: QRContent) -> ActionResult:
        # Write a standalone .ics file and open it, which triggers the
        # user's default calendar app to import the event.
        ics_content = self.build_ics_content(content)
        path = os.path.join(tempfile.gettempdir(), f"qr_event_{int(datetime.now().timestamp())}.ics")
        with open(path, "w", encoding="utf-8") as f:
            f.write(ics_content)
        webbrowser.open(f"file://{path}")
        return ActionResult(True, "Calendar event file created and opened.", opened_path=path)

    def _handle_contact(self, content: QRContent) -> ActionResult:
        return ActionResult(True, "Contact details ready to view/copy.")

    def _handle_crypto(self, content: QRContent) -> ActionResult:
        return ActionResult(True, "Crypto address ready to copy.")

    def _handle_text(self, content: QRContent) -> ActionResult:
        return ActionResult(True, "Text ready to copy or save.")

    def _handle_unknown(self, content: QRContent) -> ActionResult:
        return ActionResult(True, "Raw data displayed.")
