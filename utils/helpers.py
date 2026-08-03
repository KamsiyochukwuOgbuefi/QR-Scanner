"""Miscellaneous helper functions shared across modules."""

import os


def is_supported_image(path: str, extensions: tuple) -> bool:
    """Check whether a file path has one of the supported image extensions."""
    return os.path.splitext(path)[1].lower() in extensions


def truncate(text: str, length: int = 60) -> str:
    """Shorten text for display, adding an ellipsis if it was cut off."""
    if len(text) <= length:
        return text
    return text[: length - 3] + "..."
