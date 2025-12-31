"""Tests for Ghostty client."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ghostty_automator._async.client import Ghostty, Terminals
from ghostty_automator.errors import ConnectionError, IPCError
from ghostty_automator.protocol import Surface


class TestGhosttyConnect:
    """Tests for Ghostty.connect()."""

    def test_connect_returns_ghostty(self):
        ghostty = Ghostty.connect()
        assert isinstance(ghostty, Ghostty)

    def test_connect_with_socket_path(self):
        ghostty = Ghostty.connect(socket_path="/custom/path.sock")
        assert ghostty._socket_path == "/custom/path.sock"

    def test_connect_with_app_class(self):
        ghostty = Ghostty.connect(app_class="com.custom.ghostty")
        assert ghostty._app_class == "com.custom.ghostty"


class TestGhosttyContextManager:
    """Tests for Ghostty context manager."""

    @pytest.mark.asyncio
    async def test_async_context_manager(self):
        async with Ghostty.connect() as ghostty:
            assert isinstance(ghostty, Ghostty)


class TestTerminals:
    """Tests for Terminals collection."""

    @pytest.fixture
    def mock_ghostty(self):
        ghostty = MagicMock(spec=Ghostty)
        ghostty._send_request = AsyncMock()
        ghostty._list_surfaces = AsyncMock()
        return ghostty

    @pytest.fixture
    def terminals(self, mock_ghostty):
        return Terminals(mock_ghostty)

    @pytest.mark.asyncio
    async def test_all_returns_list(self, terminals, mock_ghostty):
        mock_ghostty._list_surfaces.return_value = [
            Surface("0x1", "term1", "/home", False, 24, 80),
            Surface("0x2", "term2", "/tmp", True, 24, 80),
        ]

        result = await terminals.all()

        assert len(result) == 2
        assert result[0].id == "0x1"
        assert result[1].id == "0x2"

    @pytest.mark.asyncio
    async def test_first_returns_first(self, terminals, mock_ghostty):
        mock_ghostty._list_surfaces.return_value = [
            Surface("0x1", "term1", "/home", False, 24, 80),
            Surface("0x2", "term2", "/tmp", True, 24, 80),
        ]

        result = await terminals.first()
        assert result.id == "0x1"

    @pytest.mark.asyncio
    async def test_first_raises_when_empty(self, terminals, mock_ghostty):
        mock_ghostty._list_surfaces.return_value = []

        with pytest.raises(IPCError, match="No terminals found"):
            await terminals.first()

    @pytest.mark.asyncio
    async def test_focused_returns_focused(self, terminals, mock_ghostty):
        mock_ghostty._list_surfaces.return_value = [
            Surface("0x1", "term1", "/home", False, 24, 80),
            Surface("0x2", "term2", "/tmp", True, 24, 80),
        ]

        result = await terminals.focused()

        assert result is not None
        assert result.id == "0x2"

    @pytest.mark.asyncio
    async def test_focused_returns_none_when_none_focused(self, terminals, mock_ghostty):
        mock_ghostty._list_surfaces.return_value = [
            Surface("0x1", "term1", "/home", False, 24, 80),
        ]

        result = await terminals.focused()
        assert result is None

    @pytest.mark.asyncio
    async def test_by_title_finds_match(self, terminals, mock_ghostty):
        mock_ghostty._list_surfaces.return_value = [
            Surface("0x1", "vim - file.py", "/home", False, 24, 80),
            Surface("0x2", "zsh", "/tmp", True, 24, 80),
        ]

        result = await terminals.by_title("vim")

        assert result is not None
        assert result.id == "0x1"

    @pytest.mark.asyncio
    async def test_by_title_returns_none_when_no_match(self, terminals, mock_ghostty):
        mock_ghostty._list_surfaces.return_value = [
            Surface("0x1", "zsh", "/home", False, 24, 80),
        ]

        result = await terminals.by_title("nvim")
        assert result is None

    @pytest.mark.asyncio
    async def test_by_pwd_finds_match(self, terminals, mock_ghostty):
        mock_ghostty._list_surfaces.return_value = [
            Surface("0x1", "zsh", "/home/user/projects", False, 24, 80),
            Surface("0x2", "zsh", "/tmp", True, 24, 80),
        ]

        result = await terminals.by_pwd("projects")

        assert result is not None
        assert result.id == "0x1"


class TestGhosttyNewWindow:
    """Tests for Ghostty.new_window()."""

    @pytest.mark.asyncio
    async def test_new_window_returns_terminal(self):
        ghostty = Ghostty.connect()
        ghostty._send_request = AsyncMock()
        ghostty._list_surfaces = AsyncMock()

        # First call: existing surfaces
        # Second call: with new surface
        ghostty._list_surfaces.side_effect = [
            [Surface("0x1", "existing", "/home", False, 24, 80)],
            [
                Surface("0x1", "existing", "/home", False, 24, 80),
                Surface("0x2", "new", "/home", True, 24, 80),
            ],
        ]

        with patch("anyio.sleep", new_callable=AsyncMock):
            terminal = await ghostty.new_window()

        assert terminal.id == "0x2"

    @pytest.mark.asyncio
    async def test_new_window_with_command(self):
        ghostty = Ghostty.connect()
        ghostty._send_request = AsyncMock()
        ghostty._list_surfaces = AsyncMock()

        ghostty._list_surfaces.side_effect = [
            [],
            [Surface("0x1", "htop", "/home", True, 24, 80)],
        ]

        with patch("anyio.sleep", new_callable=AsyncMock):
            await ghostty.new_window(command=["htop"])

        ghostty._send_request.assert_called_with("new_window", {"arguments": ["htop"]})
