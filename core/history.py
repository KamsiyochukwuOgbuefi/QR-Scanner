"""
history.py

Keeps a running log of everything scanned during the session and can
export that log to TXT, CSV, or JSON.
"""

import csv
import io
import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from core.content_parser import QRContent


@dataclass
class HistoryEntry:
    id: str
    timestamp: str
    qr_type: str
    summary: str
    raw_data: str
    action_message: str


class HistoryManager:
    """Stores HistoryEntry objects and handles export to disk."""

    # Fields included in TXT/CSV/JSON exports (id is used internally for
    # individual entry management but is not part of the export format).
    EXPORT_FIELDS = ("timestamp", "qr_type", "summary", "raw_data", "action_message")

    def __init__(self):
        self._entries: list[HistoryEntry] = []

    def add(self, content: QRContent, action_message: str) -> HistoryEntry:
        entry = HistoryEntry(
            id=uuid.uuid4().hex[:12],
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            qr_type=content.qr_type.value,
            summary=content.display_text,
            raw_data=content.raw,
            action_message=action_message,
        )
        self._entries.append(entry)
        return entry

    def all(self) -> list[HistoryEntry]:
        return list(self._entries)

    def delete(self, entry_id: str) -> bool:
        """Remove a single entry by id. Returns True if it was found."""
        for i, entry in enumerate(self._entries):
            if entry.id == entry_id:
                del self._entries[i]
                return True
        return False

    def load_entries(self, entries: list[HistoryEntry]) -> None:
        """Replace the in-memory log with the given entries (used on startup)."""
        self._entries = list(entries)

    def remove(self, index: int) -> HistoryEntry | None:
        """Remove the entry at the given list index. Returns None if out of range."""
        if 0 <= index < len(self._entries):
            return self._entries.pop(index)
        return None

    def clear(self) -> None:
        self._entries.clear()

    def is_empty(self) -> bool:
        return len(self._entries) == 0

    # ------------------------------------------------------------------ #
    # Export (string variants so the web layer can stream responses,
    # plus the original file-based methods used by the desktop GUI).
    # ------------------------------------------------------------------ #

    def _export_dicts(self) -> list[dict]:
        return [{f: getattr(e, f) for f in self.EXPORT_FIELDS} for e in self._entries]

    def export_txt_str(self) -> str:
        buffer = io.StringIO()
        for e in self._entries:
            buffer.write(
                f"[{e.timestamp}] {e.qr_type}\n"
                f"  Data: {e.raw_data}\n"
                f"  Action: {e.action_message}\n\n"
            )
        return buffer.getvalue()

    def export_csv_str(self) -> str:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=self.EXPORT_FIELDS)
        writer.writeheader()
        for e in self._entries:
            writer.writerow({f: getattr(e, f) for f in self.EXPORT_FIELDS})
        return buffer.getvalue()

    def export_json_str(self) -> str:
        return json.dumps(self._export_dicts(), indent=2)

    def export_txt(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.export_txt_str())

    def export_csv(self, path: str) -> None:
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write(self.export_csv_str())

    def export_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.export_json_str())
