"""Exception types for Ghostty Automator."""

from __future__ import annotations


class GhosttyError(Exception):
    """Base exception for Ghostty automation errors."""


class ConnectionError(GhosttyError):
    """Failed to connect to Ghostty."""


class IPCError(GhosttyError):
    """IPC request failed."""


class TimeoutError(GhosttyError):
    """Operation timed out."""

    def __init__(self, message: str, timeout_ms: int) -> None:
        super().__init__(message)
        self.timeout_ms = timeout_ms
