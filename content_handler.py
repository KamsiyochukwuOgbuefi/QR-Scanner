"""Content parsing & actions — re-exports the existing core logic."""

from core.content_parser import ContentParser, QRContent, QRType
from core.actions import ActionHandler, ActionResult

__all__ = ["ContentParser", "QRContent", "QRType", "ActionHandler", "ActionResult"]
