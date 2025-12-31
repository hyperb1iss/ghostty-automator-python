"""Tests for error types."""

from __future__ import annotations

import pytest

from ghostty_automator.errors import (
    ConnectionError,
    GhosttyError,
    IPCError,
    TimeoutError,
)


class TestGhosttyError:
    """Tests for GhosttyError base class."""

    def test_is_exception(self):
        error = GhosttyError("test")
        assert isinstance(error, Exception)

    def test_message(self):
        error = GhosttyError("test message")
        assert str(error) == "test message"


class TestConnectionError:
    """Tests for ConnectionError."""

    def test_inherits_from_ghostty_error(self):
        error = ConnectionError("socket not found")
        assert isinstance(error, GhosttyError)


class TestIPCError:
    """Tests for IPCError."""

    def test_inherits_from_ghostty_error(self):
        error = IPCError("request failed")
        assert isinstance(error, GhosttyError)


class TestTimeoutError:
    """Tests for TimeoutError."""

    def test_inherits_from_ghostty_error(self):
        error = TimeoutError("timed out", timeout_ms=5000)
        assert isinstance(error, GhosttyError)

    def test_stores_timeout(self):
        error = TimeoutError("timed out", timeout_ms=5000)
        assert error.timeout_ms == 5000
