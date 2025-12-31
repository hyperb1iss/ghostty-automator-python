"""Tests for expect assertions."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from ghostty_automator._async.expect import TerminalExpect
from ghostty_automator._async.terminal import Terminal
from ghostty_automator.protocol import Screen, Surface


@pytest.fixture
def mock_terminal():
    """Create a mock Terminal."""
    ghostty = MagicMock()
    ghostty._send_request = AsyncMock()
    ghostty._list_surfaces = AsyncMock()

    surface = Surface(
        id="0x123",
        title="zsh",
        pwd="/home/user",
        focused=True,
        rows=24,
        cols=80,
    )

    terminal = Terminal(ghostty, surface)
    return terminal


@pytest.fixture
def expect(mock_terminal):
    """Create a TerminalExpect instance."""
    return TerminalExpect(mock_terminal)


class TestToContain:
    """Tests for expect.to_contain()."""

    @pytest.mark.asyncio
    async def test_passes_when_text_present(self, expect, mock_terminal):
        mock_terminal._ghostty._send_request.return_value = {
            "data": {"content": "hello world", "cursor_x": 0, "cursor_y": 0}
        }

        # Should not raise
        await expect.to_contain("hello", timeout=100)

    @pytest.mark.asyncio
    async def test_fails_when_text_missing(self, expect, mock_terminal):
        mock_terminal._ghostty._send_request.return_value = {
            "data": {"content": "nothing here", "cursor_x": 0, "cursor_y": 0}
        }

        with pytest.raises(AssertionError) as exc_info:
            await expect.to_contain("missing", timeout=100)

        assert "missing" in str(exc_info.value)
        assert "nothing here" in str(exc_info.value)


class TestNotToContain:
    """Tests for expect.not_to_contain()."""

    @pytest.mark.asyncio
    async def test_passes_when_text_absent(self, expect, mock_terminal):
        mock_terminal._ghostty._send_request.return_value = {
            "data": {"content": "hello world", "cursor_x": 0, "cursor_y": 0}
        }

        # Should not raise
        await expect.not_to_contain("error", timeout=100)

    @pytest.mark.asyncio
    async def test_fails_when_text_present(self, expect, mock_terminal):
        mock_terminal._ghostty._send_request.return_value = {
            "data": {"content": "error: something failed", "cursor_x": 0, "cursor_y": 0}
        }

        with pytest.raises(AssertionError) as exc_info:
            await expect.not_to_contain("error", timeout=100)

        assert "NOT to contain" in str(exc_info.value)


class TestToMatch:
    """Tests for expect.to_match()."""

    @pytest.mark.asyncio
    async def test_returns_match_object(self, expect, mock_terminal):
        mock_terminal._ghostty._send_request.return_value = {
            "data": {"content": "user@host:~$ ", "cursor_x": 0, "cursor_y": 0}
        }

        match = await expect.to_match(r"user@(\w+):", timeout=100)

        assert match is not None
        assert match.group(1) == "host"

    @pytest.mark.asyncio
    async def test_fails_when_no_match(self, expect, mock_terminal):
        mock_terminal._ghostty._send_request.return_value = {
            "data": {"content": "nothing", "cursor_x": 0, "cursor_y": 0}
        }

        with pytest.raises(AssertionError):
            await expect.to_match(r"\d+", timeout=100)


class TestToHaveTitle:
    """Tests for expect.to_have_title()."""

    @pytest.mark.asyncio
    async def test_passes_substring_match(self, expect, mock_terminal):
        mock_terminal._ghostty._send_request.return_value = {"data": {}}
        mock_terminal._ghostty._list_surfaces.return_value = [
            Surface(
                id="0x123",
                title="zsh - ~/projects",
                pwd="/home/user/projects",
                focused=True,
                rows=24,
                cols=80,
            )
        ]

        await expect.to_have_title("zsh", timeout=100)

    @pytest.mark.asyncio
    async def test_fails_exact_match_when_different(self, expect, mock_terminal):
        mock_terminal._ghostty._send_request.return_value = {"data": {}}
        mock_terminal._ghostty._list_surfaces.return_value = [
            Surface(
                id="0x123",
                title="zsh - ~/projects",
                pwd="/home/user/projects",
                focused=True,
                rows=24,
                cols=80,
            )
        ]

        with pytest.raises(AssertionError):
            await expect.to_have_title("zsh", exact=True, timeout=100)


class TestPrompt:
    """Tests for expect.prompt()."""

    @pytest.mark.asyncio
    async def test_passes_with_dollar_prompt(self, expect, mock_terminal):
        mock_terminal._ghostty._send_request.return_value = {
            "data": {"content": "user@host:~$ ", "cursor_x": 0, "cursor_y": 0}
        }

        await expect.prompt(timeout=100)

    @pytest.mark.asyncio
    async def test_passes_with_hash_prompt(self, expect, mock_terminal):
        mock_terminal._ghostty._send_request.return_value = {
            "data": {"content": "root@host:~# ", "cursor_x": 0, "cursor_y": 0}
        }

        await expect.prompt(timeout=100)

    @pytest.mark.asyncio
    async def test_fails_when_no_prompt(self, expect, mock_terminal):
        mock_terminal._ghostty._send_request.return_value = {
            "data": {"content": "processing...", "cursor_x": 0, "cursor_y": 0}
        }

        with pytest.raises(AssertionError) as exc_info:
            await expect.prompt(timeout=100)

        assert "prompt" in str(exc_info.value).lower()
