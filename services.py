"""
services.py

Web-layer orchestration that bridges the browser to the existing core
modules (detector, content parser, actions, history). This replaces the
CustomTkinter GUI wiring from gui/app.py WITHOUT rewriting any of the
core scanning/parsing/action/history logic.

Owns the shared singletons (detector, camera, parser, action handler,
history manager), the live camera streaming + duplicate-suppression loop,
and disk persistence of the scan history.
"""

import base64
import os
import threading
import time
from datetime import datetime

import cv2
import numpy as np

from core.detector import QRDetector, CameraManager
from core.content_parser import ContentParser, QRType
from core.actions import ActionHandler
from core.history import HistoryManager, HistoryEntry

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
HISTORY_FILE = os.path.join(DATA_DIR, "history.json")

# Mirror the desktop app's camera loop tuning (gui/app.py).
CAMERA_POLL_MS = 30
ABSENCE_RESET_FRAMES = 10
MAX_EVENTS = 200


class QRScannerService:
    """Shared service container for the web application."""

    def __init__(self):
        self.detector = QRDetector()
        self.camera = CameraManager()
        self.parser = ContentParser()
        self.action_handler = ActionHandler()
        self.history = HistoryManager()

        self._history_lock = threading.Lock()
        self._camera_lock = threading.Lock()
        self._stream_lock = threading.Lock()
        self._event_lock = threading.Lock()

        self._camera_running = False
        self._stream_active = False
        self._camera_index = 0
        self._last_triggered_data: str | None = None
        self._absence_counter = 0

        # Recent scan payloads (with millisecond timestamps) so the live
        # camera feed can push results to the browser without polling the
        # whole history table.
        self._scan_events: list[dict] = []

        self._load_history()

    # ------------------------------------------------------------------ #
    # History persistence
    # ------------------------------------------------------------------ #

    def _load_history(self) -> None:
        if not os.path.exists(HISTORY_FILE):
            return
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                import json

                raw = json.load(f)
            entries = [HistoryEntry(**e) for e in raw if "timestamp" in e]
            with self._history_lock:
                self.history.load_entries(entries)
        except Exception:
            # Never let a corrupt history file break startup.
            pass

    def _save_history(self) -> None:
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                import json

                json.dump([e.__dict__ for e in self.history.all()], f, indent=2)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # The shared decode -> parse -> action -> history -> display pipeline
    # (equivalent to gui/app.py's _process_decoded_data).
    # ------------------------------------------------------------------ #

    def process_scan(self, raw_data: str) -> dict:
        content = self.parser.parse(raw_data)
        action = self._build_web_action(content)
        with self._history_lock:
            entry = self.history.add(content, action["message"])
            self._save_history()

        payload = self._scan_payload(content, action)
        payload["id"] = entry.id
        payload["timestamp"] = entry.timestamp
        payload["ts"] = time.time()

        with self._event_lock:
            self._scan_events.append(payload)
            if len(self._scan_events) > MAX_EVENTS:
                self._scan_events = self._scan_events[-MAX_EVENTS:]
        return payload

    def _scan_payload(self, content, action: dict) -> dict:
        return {
            "raw": content.raw,
            "type": content.qr_type.value,
            "type_key": content.qr_type.name,
            "display_text": content.display_text,
            "fields": content.fields,
            "body": self._format_body(content),
            "copy_text": self._format_copy_text(content),
            "can_open": action["kind"] != "none",
            "action": action,
        }

    # ------------------------------------------------------------------ #
    # Type-aware display formatting (mirrors gui/widgets.py ResultPanel)
    # ------------------------------------------------------------------ #

    def _format_body(self, content) -> str:
        """Type-specific readable formatting (same as the desktop UI)."""
        f = content.fields
        if content.qr_type == QRType.WIFI:
            return (
                f"Network (SSID): {f.get('ssid')}\n"
                f"Password: {f.get('password')}\n"
                f"Security: {f.get('encryption')}\n"
                f"Hidden: {'Yes' if f.get('hidden') else 'No'}"
            )
        if content.qr_type == QRType.CONTACT:
            lines = [f"Name: {f.get('name', '')}"]
            if f.get("phone"):
                lines.append(f"Phone: {f['phone']}")
            if f.get("email"):
                lines.append(f"Email: {f['email']}")
            if f.get("org"):
                lines.append(f"Organization: {f['org']}")
            return "\n".join(lines)
        if content.qr_type == QRType.CALENDAR_EVENT:
            return (
                f"Event: {f.get('summary', '')}\n"
                f"Start: {f.get('start', '')}\n"
                f"End: {f.get('end', '')}\n"
                f"Location: {f.get('location', '')}\n"
                f"Details: {f.get('description', '')}"
            )
        if content.qr_type == QRType.GEO:
            return f"Latitude: {f.get('lat')}\nLongitude: {f.get('lon')}"
        if content.qr_type == QRType.CRYPTO:
            return (
                f"Currency: {f.get('currency', '').capitalize()}\n"
                f"Address: {f.get('address')}\n"
                f"Amount: {f.get('amount') or 'Not specified'}"
            )
        if content.qr_type == QRType.EMAIL:
            return (
                f"To: {f.get('address')}\n"
                f"Subject: {f.get('subject') or '(none)'}\n"
                f"Body: {f.get('body') or '(none)'}"
            )
        if content.qr_type == QRType.SMS:
            return f"Number: {f.get('number')}\nMessage: {f.get('message') or '(none)'}"
        if content.qr_type == QRType.PHONE:
            return f"Phone Number: {f.get('number')}"
        # URL, TEXT, UNKNOWN fall back to the display/raw content.
        return content.display_text or content.raw

    def _format_copy_text(self, content) -> str:
        """What gets copied to the clipboard for this content type."""
        f = content.fields
        if content.qr_type == QRType.WIFI:
            return f.get("password", "")
        if content.qr_type == QRType.CRYPTO:
            return f.get("address", "")
        if content.qr_type == QRType.GEO:
            return f"{f.get('lat')}, {f.get('lon')}"
        return content.raw

    # ------------------------------------------------------------------ #
    # Web actions (browser equivalents of core/actions.py ActionHandler).
    # The desktop handler used webbrowser.open(); here we hand the browser
    # something it can actually act on (a URL to open or an .ics to save),
    # keeping the same per-type behavior and messages.
    # ------------------------------------------------------------------ #

    def _build_web_action(self, content) -> dict:
        f = content.fields
        t = content.qr_type
        if t == QRType.URL:
            return {"kind": "url", "url": f.get("url", content.raw), "message": "Link ready to open."}
        if t == QRType.EMAIL:
            return {"kind": "url", "url": content.raw, "message": "Email draft ready to open."}
        if t == QRType.GEO:
            url = f"https://www.google.com/maps?q={f.get('lat')},{f.get('lon')}"
            return {"kind": "url", "url": url, "message": "Location ready to open in Maps."}
        if t == QRType.CALENDAR_EVENT:
            ics = self.action_handler.build_ics_content(content)
            return {
                "kind": "ics",
                "filename": f"qr_event_{int(time.time())}.ics",
                "content": ics,
                "message": "Calendar event file ready.",
            }
        if t == QRType.PHONE:
            return {"kind": "none", "message": "Phone number ready to copy."}
        if t == QRType.SMS:
            return {"kind": "none", "message": "SMS details ready to copy."}
        if t == QRType.WIFI:
            return {"kind": "none", "message": "Wi-Fi credentials ready to copy."}
        if t == QRType.CONTACT:
            return {"kind": "none", "message": "Contact details ready to view/copy."}
        if t == QRType.CRYPTO:
            return {"kind": "none", "message": "Crypto address ready to copy."}
        if t == QRType.TEXT:
            return {"kind": "none", "message": "Text ready to copy or save."}
        return {"kind": "none", "message": "Raw data displayed."}

    def open_action(self, raw_data: str) -> dict:
        """Prepare the browser action for a raw QR payload (used by /open)."""
        content = self.parser.parse(raw_data)
        action = self._build_web_action(content)
        return {"success": True, "type": content.qr_type.value, "action": action}

    # ------------------------------------------------------------------ #
    # History accessors
    # ------------------------------------------------------------------ #

    def serialize_entry(self, entry: HistoryEntry) -> dict:
        return {
            "id": entry.id,
            "timestamp": entry.timestamp,
            "qr_type": entry.qr_type,
            "summary": entry.summary,
            "raw_data": entry.raw_data,
            "action_message": entry.action_message,
        }

    def list_history(self, q: str = "", type_filter: str = "", sort: str = "desc", limit: int = 100) -> list[dict]:
        with self._history_lock:
            entries = self.history.all()

        filtered = entries
        if q:
            needle = q.lower()
            filtered = [
                e for e in filtered
                if needle in e.raw_data.lower() or needle in e.summary.lower()
            ]
        if type_filter:
            filtered = [e for e in filtered if e.qr_type == type_filter]

        if sort == "asc":
            filtered.sort(key=lambda e: e.timestamp)
        else:
            filtered.sort(key=lambda e: e.timestamp, reverse=True)

        if limit and limit > 0:
            filtered = filtered[:limit]

        return [self.serialize_entry(e) for e in filtered]

    def clear_history(self) -> int:
        with self._history_lock:
            count = len(self.history.all())
            self.history.clear()
            self._save_history()
        return count

    def delete_history_entry(self, entry_id: str) -> bool:
        with self._history_lock:
            removed = self.history.delete(entry_id)
            if removed:
                self._save_history()
        return removed

    def events_after(self, after_ts: float) -> list[dict]:
        with self._event_lock:
            return [e for e in self._scan_events if e["ts"] > after_ts]

    # ------------------------------------------------------------------ #
    # Camera control (mirrors gui/app.py camera flow)
    # ------------------------------------------------------------------ #

    def list_cameras(self, timeout: float = 6.0) -> list[int]:
        """Probe available camera indices.

        cv2.VideoCapture() can block for a very long time on machines
        with a flaky/busy camera driver, so every index is probed in its
        own daemon thread with several backends (DirectShow then the
        default backend) and we only wait up to `timeout` seconds total.
        Any indices that opened before the budget expires are returned.
        """
        found: list[int] = []
        lock = threading.Lock()

        def _probe_index(idx: int) -> None:
            for backend in (cv2.CAP_DSHOW, None):
                cap = None
                try:
                    cap = cv2.VideoCapture(idx, backend) if backend is not None else cv2.VideoCapture(idx)
                    if cap is not None and cap.isOpened():
                        with lock:
                            if idx not in found:
                                found.append(idx)
                        break
                except Exception:
                    continue
                finally:
                    try:
                        if cap is not None:
                            cap.release()
                    except Exception:
                        pass

        threads = [threading.Thread(target=_probe_index, args=(i,), daemon=True) for i in range(5)]
        for thread in threads:
            thread.start()

        deadline = time.time() + timeout
        for thread in threads:
            remaining = deadline - time.time()
            if remaining <= 0:
                break
            thread.join(timeout=remaining)

        with lock:
            return sorted(found)

    def start_camera(self, index: int | None = None) -> dict:
        with self._camera_lock:
            if self._camera_running:
                return {"success": True, "message": "Camera already running.", "running": True, "index": self._camera_index}

            available = self.list_cameras()
            if not available:
                return {"success": False, "message": "No camera was detected on this system."}

            if index is None or index not in available:
                index = available[0]
            if not self.camera.open(index):
                return {"success": False, "message": "Could not open the camera. It may be in use by another app."}

            self._camera_running = True
            self._camera_index = index
            self._last_triggered_data = None
            self._absence_counter = 0
            return {"success": True, "message": "Camera started.", "running": True, "index": index}

    def stop_camera(self) -> dict:
        with self._camera_lock:
            self._camera_running = False
            self.camera.close()
            return {"success": True, "message": "Camera stopped.", "running": False}

    def switch_camera(self) -> dict:
        with self._camera_lock:
            available = self.list_cameras()
            if len(available) < 2:
                return {"success": False, "message": "Only one camera is available."}

            current = self._camera_index
            start = available.index(current) if current in available else 0
            next_index = available[(start + 1) % len(available)]

            self._camera_running = False
            self.camera.close()
            if not self.camera.open(next_index):
                self._camera_running = True
                return {"success": False, "message": "Could not switch to the next camera."}

            self._camera_running = True
            self._camera_index = next_index
            self._last_triggered_data = None
            self._absence_counter = 0
            return {"success": True, "message": f"Switched to camera {next_index}.", "running": True, "index": next_index}

    def camera_status(self) -> dict:
        return {"running": self._camera_running, "index": self._camera_index}

    # ------------------------------------------------------------------ #
    # Live MJPEG camera stream + on-stream QR detection
    # ------------------------------------------------------------------ #

    def _placeholder_frame(self):
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[:] = (15, 23, 42)
        return frame

    def camera_stream(self):
        """Generator yielding JPEG frames as multipart/x-mixed-replace.

        Runs the same detection loop the desktop app ran on its preview:
        decode every frame, draw a green box around hits, and only re-fire
        the action pipeline when a *different* code appears (the duplicate
        suppression from gui/app.py's ABSENCE_RESET_FRAMES).
        """
        with self._stream_lock:
            if self._stream_active:
                yield self._encode_jpeg(self._placeholder_frame(), "idle")
                return
            self._stream_active = True

        try:
            while self._camera_running and self.camera.is_open():
                ok, frame = self.camera.read_frame()
                if not ok or frame is None:
                    time.sleep(CAMERA_POLL_MS / 1000)
                    continue

                try:
                    codes = self.detector.scan_frame(frame)
                except Exception:
                    codes = []

                if codes:
                    self._absence_counter = 0
                    for code in codes:
                        if code.points:
                            pts = code.points
                            for i in range(len(pts)):
                                cv2.line(frame, pts[i], pts[(i + 1) % len(pts)], (0, 200, 0), 3)

                    newest = codes[0].data
                    if newest != self._last_triggered_data:
                        self._last_triggered_data = newest
                        self.process_scan(newest)
                else:
                    self._absence_counter += 1
                    if self._absence_counter > ABSENCE_RESET_FRAMES:
                        self._last_triggered_data = None

                yield self._encode_jpeg(frame)
        finally:
            with self._stream_lock:
                self._stream_active = False

    @staticmethod
    def _encode_jpeg(frame, reason: str = "frame"):
        ok, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
        if not ok:
            jpg = b""
        return (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" + jpg.tobytes() + b"\r\n"
        )

    # ------------------------------------------------------------------ #
    # Annotated preview for uploaded images (mirrors _show_image_preview)
    # ------------------------------------------------------------------ #

    def annotate_image(self, frame) -> str:
        """Return a base64 data URI of the frame with green boxes drawn."""
        codes = self.detector.scan_frame(frame)
        for code in codes:
            if code.points:
                pts = code.points
                for i in range(len(pts)):
                    cv2.line(frame, pts[i], pts[(i + 1) % len(pts)], (0, 200, 0), 3)
        ok, jpg = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        if not ok:
            return ""
        return "data:image/jpeg;base64," + base64.b64encode(jpg.tobytes()).decode("ascii")


services = QRScannerService()
