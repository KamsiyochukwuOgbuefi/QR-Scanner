"""
detector.py

Handles the actual "finding QR codes in pixels" part:
- Scanning a single image file (possibly containing multiple QR codes).
- Managing a webcam and scanning live frames.

Uses pyzbar for decoding (handles multiple codes per image robustly) and
OpenCV for image I/O, camera access, and drawing bounding boxes.
"""

from dataclasses import dataclass

import cv2
import numpy as np

try:
    from pyzbar.pyzbar import decode as zbar_decode
    ZBAR_AVAILABLE = True
except Exception:
    # pyzbar needs the zbar shared library (libzbar0 on Linux). It is
    # bundled with the Windows/macOS wheels, but on a minimal Linux
    # runtime (e.g. Render's native Python) it may be missing. In that
    # case we fall back to OpenCV's built-in QR detector below.
    zbar_decode = None
    ZBAR_AVAILABLE = False


@dataclass
class DetectedCode:
    """One QR code found in an image/frame."""
    data: str
    points: list  # list of (x, y) tuples forming the bounding polygon


class ImageLoadError(Exception):
    """Raised when an image file can't be loaded or decoded."""


class QRDetector:
    """Detects and decodes QR codes from static images or camera frames."""

    SUPPORTED_EXTENSIONS = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp", ".tiff")

    def scan_image_file(self, image_path: str) -> list[DetectedCode]:
        """Load an image from disk and return all QR codes found in it."""
        image = cv2.imread(image_path)
        if image is None:
            raise ImageLoadError(f"Could not load image: {image_path}")
        return self.scan_frame(image)

    def scan_frame(self, frame: np.ndarray) -> list[DetectedCode]:
        """Scan a single OpenCV BGR frame (image array) for QR codes."""
        results = []
        if ZBAR_AVAILABLE:
            try:
                decoded_objects = zbar_decode(frame)
            except Exception:
                decoded_objects = []

            for obj in decoded_objects:
                if obj.type != "QRCODE":
                    continue
                try:
                    data = obj.data.decode("utf-8")
                except UnicodeDecodeError:
                    data = obj.data.decode("utf-8", errors="replace")
                points = [(p.x, p.y) for p in obj.polygon] if obj.polygon else []
                results.append(DetectedCode(data=data, points=points))

            if results:
                return results

        # Fallback: OpenCV's built-in QR detector. Used when zbar is not
        # available (no libzbar0), and also as a second pass when zbar
        # found nothing (they complement each other on tricky images).
        try:
            detector = cv2.QRCodeDetector()
            retval, decoded_info, points, _ = detector.detectAndDecodeMulti(frame)
            if retval and decoded_info:
                for i, text in enumerate(decoded_info):
                    if not text:
                        continue
                    if isinstance(text, bytes):
                        text = text.decode("utf-8", errors="replace")
                    pts = []
                    if points is not None and len(points) > i:
                        pts = [(float(x), float(y)) for x, y in points[i]]
                    results.append(DetectedCode(data=text, points=pts))
        except Exception:
            pass

        return results


class CameraManager:
    """Wraps OpenCV VideoCapture for a simple open/read/close camera workflow."""

    def __init__(self):
        self._cap: cv2.VideoCapture | None = None
        self._index: int | None = None

    @staticmethod
    def list_available_cameras(max_check: int = 5) -> list[int]:
        """Probe the first few camera indices and return the ones that open."""
        available = []
        for i in range(max_check):
            cap = cv2.VideoCapture(i)
            if cap is not None and cap.isOpened():
                available.append(i)
                cap.release()
        return available

    def open(self, index: int = 0) -> bool:
        """Open the camera at the given index. Returns True on success."""
        self.close()
        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            cap.release()
            return False
        self._cap = cap
        self._index = index
        return True

    def is_open(self) -> bool:
        return self._cap is not None and self._cap.isOpened()

    def read_frame(self):
        """Read a single frame. Returns (success, frame)."""
        if not self.is_open():
            return False, None
        return self._cap.read()

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
        self._cap = None
        self._index = None
