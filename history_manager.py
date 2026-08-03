"""Scan history — re-exports the existing core.history logic."""

from core.history import HistoryManager, HistoryEntry

__all__ = ["HistoryManager", "HistoryEntry"]
