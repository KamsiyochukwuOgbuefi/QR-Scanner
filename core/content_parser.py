"""
content_parser.py

Takes the raw string decoded from a QR code and figures out what KIND of
content it is (URL, email, phone number, Wi-Fi credentials, etc.), then
breaks it down into a structured, easy-to-use object.

This is the "brain" that makes the scanner universal instead of URL-only.
"""

from dataclasses import dataclass, field
from enum import Enum
from urllib.parse import urlparse, parse_qs
import re


class QRType(Enum):
    """All content types the scanner knows how to recognize."""
    URL = "URL"
    EMAIL = "Email"
    PHONE = "Phone Number"
    SMS = "SMS"
    WIFI = "Wi-Fi Credentials"
    GEO = "Geographic Location"
    CALENDAR_EVENT = "Calendar Event"
    CONTACT = "Contact Card"
    CRYPTO = "Cryptocurrency Address"
    TEXT = "Plain Text"
    UNKNOWN = "Unknown"


@dataclass
class QRContent:
    """
    Structured representation of decoded QR data.

    raw:          the exact string that came out of the decoder
    qr_type:      one of QRType
    fields:       dict of parsed-out fields specific to the type
                  (e.g. {"ssid": ..., "password": ...} for Wi-Fi)
    display_text: a short human-readable summary, ready to show in the UI
    """
    raw: str
    qr_type: QRType
    fields: dict = field(default_factory=dict)
    display_text: str = ""


class ContentParser:
    """Classifies and parses raw QR code strings into QRContent objects."""

    # Recognized cryptocurrency URI schemes
    CRYPTO_SCHEMES = {"bitcoin", "ethereum", "litecoin", "dogecoin", "bitcoincash", "monero"}

    def parse(self, raw_data: str) -> QRContent:
        """Main entry point: inspect raw_data and return a QRContent object."""
        if raw_data is None:
            raw_data = ""

        text = raw_data.strip()

        # Order matters: check the more specific/structured formats first,
        # then fall back to generic URL detection, then plain text.
        parsers = [
            self._try_wifi,
            self._try_vevent,
            self._try_vcard,
            self._try_mecard,
            self._try_mailto,
            self._try_tel,
            self._try_sms,
            self._try_geo,
            self._try_crypto,
            self._try_url,
        ]

        for parser_fn in parsers:
            result = parser_fn(text)
            if result is not None:
                return result

        # Nothing matched a known structured format
        if text:
            return QRContent(
                raw=raw_data,
                qr_type=QRType.TEXT,
                fields={"text": text},
                display_text=text if len(text) <= 120 else text[:117] + "...",
            )

        return QRContent(raw=raw_data, qr_type=QRType.UNKNOWN, display_text="(empty)")

    # ------------------------------------------------------------------ #
    # Individual format parsers. Each returns a QRContent on success,
    # or None if the text doesn't match that format.
    # ------------------------------------------------------------------ #

    def _try_wifi(self, text: str) -> QRContent | None:
        """WIFI:T:WPA;S:MyNetwork;P:MyPassword;H:true;;"""
        if not text.upper().startswith("WIFI:"):
            return None

        fields = {"encryption": "", "ssid": "", "password": "", "hidden": False}
        body = text[5:]
        # Split on unescaped semicolons
        parts = re.split(r"(?<!\\);", body)
        for part in parts:
            if ":" not in part:
                continue
            key, _, value = part.partition(":")
            value = value.replace("\\;", ";").replace("\\:", ":").replace("\\,", ",")
            key = key.strip().upper()
            if key == "T":
                fields["encryption"] = value or "None"
            elif key == "S":
                fields["ssid"] = value
            elif key == "P":
                fields["password"] = value
            elif key == "H":
                fields["hidden"] = value.lower() == "true"

        if not fields["ssid"]:
            return None

        summary = f"SSID: {fields['ssid']} | Security: {fields['encryption'] or 'None'}"
        return QRContent(raw=text, qr_type=QRType.WIFI, fields=fields, display_text=summary)

    def _try_vevent(self, text: str) -> QRContent | None:
        """iCalendar-style event: BEGIN:VEVENT ... END:VEVENT"""
        if "BEGIN:VEVENT" not in text.upper():
            return None

        fields = {"summary": "", "location": "", "start": "", "end": "", "description": ""}
        for line in text.splitlines():
            line = line.strip()
            if line.upper().startswith("SUMMARY:"):
                fields["summary"] = line.split(":", 1)[1]
            elif line.upper().startswith("LOCATION:"):
                fields["location"] = line.split(":", 1)[1]
            elif line.upper().startswith("DTSTART"):
                fields["start"] = line.split(":", 1)[-1]
            elif line.upper().startswith("DTEND"):
                fields["end"] = line.split(":", 1)[-1]
            elif line.upper().startswith("DESCRIPTION:"):
                fields["description"] = line.split(":", 1)[1]

        summary = fields["summary"] or "Untitled Event"
        display = f"{summary}"
        if fields["start"]:
            display += f" ({fields['start']})"
        return QRContent(raw=text, qr_type=QRType.CALENDAR_EVENT, fields=fields, display_text=display)

    def _try_vcard(self, text: str) -> QRContent | None:
        """vCard contact: BEGIN:VCARD ... END:VCARD"""
        if "BEGIN:VCARD" not in text.upper():
            return None

        fields = {"name": "", "phone": "", "email": "", "org": "", "title": ""}
        for line in text.splitlines():
            line = line.strip()
            upper = line.upper()
            if upper.startswith("FN:"):
                fields["name"] = line.split(":", 1)[1]
            elif upper.startswith("TEL"):
                fields["phone"] = line.split(":", 1)[-1]
            elif upper.startswith("EMAIL"):
                fields["email"] = line.split(":", 1)[-1]
            elif upper.startswith("ORG:"):
                fields["org"] = line.split(":", 1)[1]
            elif upper.startswith("TITLE:"):
                fields["title"] = line.split(":", 1)[1]

        display = fields["name"] or fields["email"] or "Contact Card"
        return QRContent(raw=text, qr_type=QRType.CONTACT, fields=fields, display_text=display)

    def _try_mecard(self, text: str) -> QRContent | None:
        """MECARD contact: MECARD:N:Doe,John;TEL:123;EMAIL:a@b.com;;"""
        if not text.upper().startswith("MECARD:"):
            return None

        fields = {"name": "", "phone": "", "email": "", "address": ""}
        body = text[7:]
        parts = re.split(r"(?<!\\);", body)
        for part in parts:
            if ":" not in part:
                continue
            key, _, value = part.partition(":")
            key = key.strip().upper()
            value = value.replace("\\;", ";").replace("\\:", ":").replace("\\,", ",")
            if key == "N":
                fields["name"] = value.replace(",", " ").strip()
            elif key == "TEL":
                fields["phone"] = value
            elif key == "EMAIL":
                fields["email"] = value
            elif key == "ADR":
                fields["address"] = value

        display = fields["name"] or fields["phone"] or "Contact Card"
        return QRContent(raw=text, qr_type=QRType.CONTACT, fields=fields, display_text=display)

    def _try_mailto(self, text: str) -> QRContent | None:
        """mailto:someone@example.com?subject=Hi&body=Hello"""
        if not text.lower().startswith("mailto:"):
            return None

        parsed = urlparse(text)
        query = parse_qs(parsed.query)
        fields = {
            "address": parsed.path,
            "subject": query.get("subject", [""])[0],
            "body": query.get("body", [""])[0],
        }
        return QRContent(raw=text, qr_type=QRType.EMAIL, fields=fields, display_text=fields["address"])

    def _try_tel(self, text: str) -> QRContent | None:
        """tel:+1234567890"""
        if not text.lower().startswith("tel:"):
            return None
        number = text[4:]
        return QRContent(raw=text, qr_type=QRType.PHONE, fields={"number": number}, display_text=number)

    def _try_sms(self, text: str) -> QRContent | None:
        """sms:+1234567890 or smsto:+1234567890:message"""
        lower = text.lower()
        if not (lower.startswith("sms:") or lower.startswith("smsto:")):
            return None

        body_text = text.split(":", 1)[1]
        number, _, message = body_text.partition(":")
        fields = {"number": number, "message": message}
        return QRContent(raw=text, qr_type=QRType.SMS, fields=fields, display_text=number)

    def _try_geo(self, text: str) -> QRContent | None:
        """geo:37.7749,-122.4194 or geo:37.7749,-122.4194,100"""
        if not text.lower().startswith("geo:"):
            return None

        body_text = text[4:].split("?")[0]
        coords = body_text.split(",")
        if len(coords) < 2:
            return None

        fields = {"lat": coords[0].strip(), "lon": coords[1].strip()}
        display = f"{fields['lat']}, {fields['lon']}"
        return QRContent(raw=text, qr_type=QRType.GEO, fields=fields, display_text=display)

    def _try_crypto(self, text: str) -> QRContent | None:
        """bitcoin:1A2b3C...?amount=0.01"""
        parsed = urlparse(text)
        scheme = parsed.scheme.lower()
        if scheme not in self.CRYPTO_SCHEMES:
            return None

        query = parse_qs(parsed.query)
        fields = {
            "currency": scheme,
            "address": parsed.path,
            "amount": query.get("amount", [""])[0],
        }
        display = f"{scheme.capitalize()}: {fields['address']}"
        return QRContent(raw=text, qr_type=QRType.CRYPTO, fields=fields, display_text=display)

    def _try_url(self, text: str) -> QRContent | None:
        """Generic http(s)/ftp URL, including social media links."""
        parsed = urlparse(text)
        if parsed.scheme.lower() in ("http", "https", "ftp") and parsed.netloc:
            return QRContent(raw=text, qr_type=QRType.URL, fields={"url": text}, display_text=text)
        return None
