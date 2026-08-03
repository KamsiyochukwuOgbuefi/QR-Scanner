"""QR detection — re-exports the existing core.detector logic for the Flask app."""

from core.detector import QRDetector, DetectedCode, ImageLoadError

__all__ = ["QRDetector", "DetectedCode", "ImageLoadError"]
