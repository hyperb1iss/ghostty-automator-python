"""Tests for Terminal class."""

from __future__ import annotations

import unittest.mock
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghostty_automator._async.terminal import Terminal
from ghostty_automator.errors import TimeoutError
from ghostty_automator.protocol import Screen, Surface


@pytest.fixture
def mock_ghostty():
    """Create a mock Ghostty client."""
    ghostty = MagicMock()
    ghostty._send_request = AsyncMock()
    ghostty._list_surfaces = AsyncMock()
    return ghostty


@pytest.fixture
def mock_surface():
    """Create a mock surface."""
    return Surface(
        id="0x123456",
        title="zsh",
        pwd="/home/user",
        focused=True,
        rows=24,
        cols=80,
    )


@pytest.fixture
def terminal(mock_ghostty, mock_surface):
    """Create a Terminal instance."""
    return Terminal(mock_ghostty, mock_surface)


class TestTerminalProperties:
    """Tests for Terminal properties."""

    def test_id(self, terminal):
        assert terminal.id == "0x123456"

    def test_title(self, terminal):
        assert terminal.title == "zsh"

    def test_pwd(self, terminal):
        assert terminal.pwd == "/home/user"

    def test_rows(self, terminal):
        assert terminal.rows == 24

    def test_cols(self, terminal):
        assert terminal.cols == 80

    def test_focused(self, terminal):
        assert terminal.focused is True

    def test_repr(self, terminal):
        repr_str = repr(terminal)
        assert "Terminal" in repr_str
        assert "0x123456" in repr_str


class TestTerminalSend:
    """Tests for Terminal.send()."""

    @pytest.mark.asyncio
    async def test_send_adds_carriage_return(self, terminal, mock_ghostty):
        await terminal.send("ls -la")

        mock_ghostty._send_request.assert_called_once_with(
            "send_text",
            {"surface_id": "0x123456", "text": "ls -la\r"},
        )

    @pytest.mark.asyncio
    async def test_send_returns_self(self, terminal):
        result = await terminal.send("echo hello")
        assert result is terminal


class TestTerminalType:
    """Tests for Terminal.type()."""

    @pytest.mark.asyncio
    async def test_type_no_delay(self, terminal, mock_ghostty):
        await terminal.type("hello")

        mock_ghostty._send_request.assert_called_once_with(
            "send_text",
            {"surface_id": "0x123456", "text": "hello"},
        )

    @pytest.mark.asyncio
    async def test_type_with_delay(self, terminal, mock_ghostty):
        with patch("anyio.sleep", new_callable=AsyncMock) as mock_sleep:
            await terminal.type("ab", delay_ms=100)

            assert mock_ghostty._send_request.call_count == 2
            mock_sleep.assert_called()


class TestTerminalPress:
    """Tests for Terminal.press()."""

    @pytest.mark.asyncio
    async def test_press_enter(self, terminal, mock_ghostty):
        await terminal.press("Enter")

        # press() sends both press and release events
        assert mock_ghostty._send_request.call_count == 2
        calls = mock_ghostty._send_request.call_args_list
        assert calls[0] == unittest.mock.call(
            "send_key", {"surface_id": "0x123456", "key": "Enter", "action": "press"}
        )
        assert calls[1] == unittest.mock.call(
            "send_key", {"surface_id": "0x123456", "key": "Enter", "action": "release"}
        )

    @pytest.mark.asyncio
    async def test_press_tab(self, terminal, mock_ghostty):
        await terminal.press("Tab")

        # press() sends both press and release events
        assert mock_ghostty._send_request.call_count == 2
        calls = mock_ghostty._send_request.call_args_list
        assert calls[0] == unittest.mock.call(
            "send_key", {"surface_id": "0x123456", "key": "Tab", "action": "press"}
        )
        assert calls[1] == unittest.mock.call(
            "send_key", {"surface_id": "0x123456", "key": "Tab", "action": "release"}
        )

    @pytest.mark.asyncio
    async def test_press_ctrl_c(self, terminal, mock_ghostty):
        await terminal.press("Ctrl+C")

        # Ctrl+C uses send_key with mods
        assert mock_ghostty._send_request.call_count == 2
        calls = mock_ghostty._send_request.call_args_list
        assert calls[0] == unittest.mock.call(
            "send_key",
            {"surface_id": "0x123456", "key": "KeyC", "action": "press", "mods": "ctrl"},
        )
        assert calls[1] == unittest.mock.call(
            "send_key",
            {"surface_id": "0x123456", "key": "KeyC", "action": "release", "mods": "ctrl"},
        )

    @pytest.mark.asyncio
    async def test_press_arrow_up(self, terminal, mock_ghostty):
        await terminal.press("Up")

        assert mock_ghostty._send_request.call_count == 2
        calls = mock_ghostty._send_request.call_args_list
        assert calls[0] == unittest.mock.call(
            "send_key", {"surface_id": "0x123456", "key": "ArrowUp", "action": "press"}
        )
        assert calls[1] == unittest.mock.call(
            "send_key", {"surface_id": "0x123456", "key": "ArrowUp", "action": "release"}
        )

    @pytest.mark.asyncio
    async def test_press_dynamic_ctrl(self, terminal, mock_ghostty):
        # Ctrl+A uses send_key with mods
        await terminal.press("Ctrl+A")

        assert mock_ghostty._send_request.call_count == 2
        calls = mock_ghostty._send_request.call_args_list
        assert calls[0] == unittest.mock.call(
            "send_key",
            {"surface_id": "0x123456", "key": "KeyA", "action": "press", "mods": "ctrl"},
        )
        assert calls[1] == unittest.mock.call(
            "send_key",
            {"surface_id": "0x123456", "key": "KeyA", "action": "release", "mods": "ctrl"},
        )


class TestTerminalScreen:
    """Tests for Terminal.screen()."""

    @pytest.mark.asyncio
    async def test_screen_returns_content(self, terminal, mock_ghostty):
        mock_ghostty._send_request.return_value = {
            "data": {
                "content": "hello world",
                "cursor_x": 5,
                "cursor_y": 10,
            }
        }

        screen = await terminal.screen()

        assert isinstance(screen, Screen)
        assert screen.text == "hello world"
        assert screen.cursor_x == 5
        assert screen.cursor_y == 10


class TestTerminalWaitForText:
    """Tests for Terminal.wait_for_text()."""

    @pytest.mark.asyncio
    async def test_wait_for_text_found_immediately(self, terminal, mock_ghostty):
        mock_ghostty._send_request.return_value = {
            "data": {"content": "hello world", "cursor_x": 0, "cursor_y": 0}
        }

        result = await terminal.wait_for_text("hello", timeout=1000)
        assert result is terminal

    @pytest.mark.asyncio
    async def test_wait_for_text_timeout(self, terminal, mock_ghostty):
        mock_ghostty._send_request.return_value = {
            "data": {"content": "nothing here", "cursor_x": 0, "cursor_y": 0}
        }

        with pytest.raises(TimeoutError) as exc_info:
            await terminal.wait_for_text("missing", timeout=100)

        assert exc_info.value.timeout_ms == 100

    @pytest.mark.asyncio
    async def test_wait_for_text_regex(self, terminal, mock_ghostty):
        mock_ghostty._send_request.return_value = {
            "data": {"content": "user@host:~$ ", "cursor_x": 0, "cursor_y": 0}
        }

        result = await terminal.wait_for_text(r"\$\s*$", timeout=1000, regex=True)
        assert result is terminal


class TestTerminalActions:
    """Tests for Terminal action methods."""

    @pytest.mark.asyncio
    async def test_focus(self, terminal, mock_ghostty):
        await terminal.focus()

        mock_ghostty._send_request.assert_called_once_with(
            "focus_surface", {"surface_id": "0x123456"}
        )

    @pytest.mark.asyncio
    async def test_close(self, terminal, mock_ghostty):
        await terminal.close()

        mock_ghostty._send_request.assert_called_once_with(
            "close_surface", {"surface_id": "0x123456"}
        )

    @pytest.mark.asyncio
    async def test_resize(self, terminal, mock_ghostty):
        await terminal.resize(rows=30, cols=100)

        mock_ghostty._send_request.assert_called_once_with(
            "resize_surface",
            {"surface_id": "0x123456", "rows": 30, "cols": 100},
        )

    @pytest.mark.asyncio
    async def test_screenshot(self, terminal, mock_ghostty, tmp_path):
        output_path = tmp_path / "screenshot.png"
        result = await terminal.screenshot(output_path)

        assert result == output_path.resolve()
        mock_ghostty._send_request.assert_called_once()
