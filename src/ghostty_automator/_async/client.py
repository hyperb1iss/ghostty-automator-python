"""Async Ghostty client with Playwright-style API."""

from __future__ import annotations

import json
import struct
from pathlib import Path
from typing import TYPE_CHECKING, Any, Self, cast

from ghostty_automator.errors import ConnectionError, IPCError
from ghostty_automator.protocol import (
    MAX_MESSAGE_SIZE,
    PROTOCOL_VERSION,
    Surface,
    extract_surfaces,
    resolve_socket_path,
)

if TYPE_CHECKING:
    from anyio.abc import ByteStream

    from ghostty_automator._async.terminal import Terminal


class Terminals:
    """Collection of terminals with Playwright-style accessors."""

    def __init__(self, ghostty: Ghostty) -> None:
        self._ghostty = ghostty

    async def all(self) -> list[Terminal]:
        """Get all terminals."""
        from ghostty_automator._async.terminal import Terminal

        surfaces = await self._ghostty._list_surfaces()
        return [Terminal(self._ghostty, s) for s in surfaces]

    async def first(self) -> Terminal:
        """Get the first terminal.

        Raises:
            GhosttyError: If no terminals are open.
        """
        from ghostty_automator._async.terminal import Terminal

        surfaces = await self._ghostty._list_surfaces()
        if not surfaces:
            raise IPCError("No terminals found")
        return Terminal(self._ghostty, surfaces[0])

    async def focused(self) -> Terminal | None:
        """Get the focused terminal, or None if none focused."""
        from ghostty_automator._async.terminal import Terminal

        surfaces = await self._ghostty._list_surfaces()
        for s in surfaces:
            if s.focused:
                return Terminal(self._ghostty, s)
        return None

    async def by_title(self, title: str) -> Terminal | None:
        """Find a terminal by title (partial match)."""
        from ghostty_automator._async.terminal import Terminal

        surfaces = await self._ghostty._list_surfaces()
        for s in surfaces:
            if title in s.title:
                return Terminal(self._ghostty, s)
        return None

    async def by_pwd(self, path: str) -> Terminal | None:
        """Find a terminal by working directory (partial match)."""
        from ghostty_automator._async.terminal import Terminal

        surfaces = await self._ghostty._list_surfaces()
        for s in surfaces:
            if path in s.pwd:
                return Terminal(self._ghostty, s)
        return None


class Ghostty:
    """Main Ghostty client - the entry point for terminal automation.

    Example:
        >>> async with Ghostty.connect() as ghostty:
        ...     terminal = await ghostty.terminals.first()
        ...     await terminal.send("echo hello")
        ...     await terminal.wait_for_text("hello")
    """

    def __init__(
        self,
        socket_path: str | Path | None = None,
        app_class: str | None = None,
    ) -> None:
        """Initialize the client.

        Args:
            socket_path: Path to the Ghostty socket. If None, auto-detected.
            app_class: Custom Ghostty app class to connect to.
        """
        self._socket_path = socket_path
        self._app_class = app_class
        self.terminals = Terminals(self)

    @classmethod
    def connect(
        cls,
        socket_path: str | Path | None = None,
        app_class: str | None = None,
    ) -> Ghostty:
        """Create a connected Ghostty client.

        This is the recommended way to create a client:
            >>> async with Ghostty.connect() as ghostty:
            ...     ...
        """
        return cls(socket_path=socket_path, app_class=app_class)

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    # === High-Level API ===

    async def new_window(self, command: list[str] | None = None) -> Terminal:
        """Open a new window and return its terminal.

        Args:
            command: Optional command to run in the new window.

        Returns:
            The Terminal for the new window.
        """
        from ghostty_automator._async.terminal import Terminal

        before = await self._list_surfaces()
        before_ids = {s.id for s in before}

        payload: dict[str, Any] | None = {"arguments": command} if command else None
        await self._send_request("new_window", payload)

        # Poll for new surface
        import anyio

        for _ in range(50):  # 5 second timeout
            await anyio.sleep(0.1)
            after = await self._list_surfaces()
            for s in after:
                if s.id not in before_ids:
                    return Terminal(self, s)

        raise IPCError("New window did not appear")

    async def new_tab(self, command: list[str] | None = None) -> Terminal:
        """Open a new tab and return its terminal.

        Args:
            command: Optional command to run in the new tab.

        Returns:
            The Terminal for the new tab.
        """
        from ghostty_automator._async.terminal import Terminal

        before = await self._list_surfaces()
        before_ids = {s.id for s in before}

        payload: dict[str, Any] | None = {"arguments": command} if command else None
        await self._send_request("new_tab", payload)

        # Poll for new surface
        import anyio

        for _ in range(50):  # 5 second timeout
            await anyio.sleep(0.1)
            after = await self._list_surfaces()
            for s in after:
                if s.id not in before_ids:
                    return Terminal(self, s)

        raise IPCError("New tab did not appear")

    # === Internal Methods ===

    async def _list_surfaces(self) -> list[Surface]:
        """List all surfaces."""
        return extract_surfaces(await self._send_request("list_surfaces"))

    async def _send_request(
        self, action: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Send a request to Ghostty and return the response."""
        import anyio

        socket_path = resolve_socket_path(self._socket_path)
        if not socket_path.exists():
            raise ConnectionError(f"Socket not found: {socket_path}")

        stream: ByteStream = await anyio.connect_unix(str(socket_path))
        try:
            request: dict[str, Any] = {
                "version": PROTOCOL_VERSION,
                "target": self._app_class,
                "action": {action: payload if payload else {}},
            }

            data = json.dumps(request).encode("utf-8")
            if len(data) > MAX_MESSAGE_SIZE:
                raise IPCError("Request too large")

            await stream.send(struct.pack("<I", len(data)) + data)

            length_bytes = await self._recv_exact(stream, 4)
            length = struct.unpack("<I", length_bytes)[0]

            if length > MAX_MESSAGE_SIZE:
                raise IPCError("Response too large")

            response_data = await self._recv_exact(stream, length)
            response = cast(dict[str, Any], json.loads(response_data.decode("utf-8")))

            if not response.get("ok", False):
                raise IPCError(response.get("error", "Unknown error"))

            return response
        finally:
            await stream.aclose()

    async def _recv_exact(self, stream: ByteStream, n: int) -> bytes:
        """Receive exactly n bytes from stream."""
        data = b""
        while len(data) < n:
            chunk = await stream.receive(n - len(data))
            if not chunk:
                raise ConnectionError("Connection closed")
            data += chunk
        return data
