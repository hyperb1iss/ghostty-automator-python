"""Ghostty Automator - Playwright for Terminals.

A Playwright-style terminal automation library for Ghostty.

Async Example:
    >>> from ghostty_automator import Ghostty
    >>>
    >>> async with Ghostty.connect() as ghostty:
    ...     terminal = await ghostty.terminals.first()
    ...     await terminal.send("ls -la")
    ...     await terminal.wait_for_text("package.json")

Sync Example:
    >>> from ghostty_automator.sync_api import Ghostty
    >>>
    >>> with Ghostty.connect() as ghostty:
    ...     terminal = ghostty.terminals.first()
    ...     terminal.send("ls -la")
    ...     terminal.wait_for_text("package.json")
"""

from __future__ import annotations

from ghostty_automator._async.client import Ghostty
from ghostty_automator._async.terminal import Terminal
from ghostty_automator.errors import (
    ConnectionError,
    GhosttyError,
    IPCError,
    TimeoutError,
)
from ghostty_automator.protocol import Cell, Screen, ScreenCells, Span, Surface, strip_ansi

__all__ = [
    "Cell",
    "ConnectionError",
    "Ghostty",
    "GhosttyError",
    "IPCError",
    "Screen",
    "ScreenCells",
    "Span",
    "Surface",
    "Terminal",
    "TimeoutError",
    "strip_ansi",
]

__version__ = "0.1.0"
