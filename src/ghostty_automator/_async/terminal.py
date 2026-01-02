"""Terminal class with Playwright-style automation API."""

from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ghostty_automator.errors import TimeoutError
from ghostty_automator.protocol import DEFAULT_TIMEOUT_MS, Screen, ScreenCells, Surface

if TYPE_CHECKING:
    from ghostty_automator._async.client import Ghostty
    from ghostty_automator._async.expect import TerminalExpect


class Terminal:
    """A terminal surface with Playwright-style automation API.

    Example:
        >>> async with Ghostty.connect() as ghostty:
        ...     terminal = await ghostty.terminals.first()
        ...
        ...     # Send commands
        ...     await terminal.send("cd ~/projects")
        ...     await terminal.send("ls -la")
        ...
        ...     # Wait for output
        ...     await terminal.wait_for_text("package.json")
        ...
        ...     # Assertions
        ...     await terminal.expect.to_contain("src/")
        ...
        ...     # Screenshots
        ...     await terminal.screenshot("debug.png")
    """

    def __init__(self, ghostty: Ghostty, surface: Surface) -> None:
        self._ghostty = ghostty
        self._surface = surface
        self._expect: TerminalExpect | None = None

    @property
    def id(self) -> str:
        """Surface ID."""
        return self._surface.id

    @property
    def title(self) -> str:
        """Window/tab title."""
        return self._surface.title

    @property
    def pwd(self) -> str:
        """Current working directory."""
        return self._surface.pwd

    @property
    def rows(self) -> int:
        """Number of rows."""
        return self._surface.rows

    @property
    def cols(self) -> int:
        """Number of columns."""
        return self._surface.cols

    @property
    def focused(self) -> bool:
        """Whether this terminal is focused."""
        return self._surface.focused

    @property
    def expect(self) -> TerminalExpect:
        """Assertion helpers for this terminal."""
        from ghostty_automator._async.expect import TerminalExpect

        if self._expect is None:
            self._expect = TerminalExpect(self)
        return self._expect

    # === Sending Input ===

    async def send(self, text: str) -> Terminal:
        """Send text to the terminal and press Enter.

        This is the primary way to run commands:
            >>> await terminal.send("ls -la")

        Returns self for chaining.
        """
        await self._ghostty._send_request("send_text", {"surface_id": self.id, "text": text + "\r"})
        return self

    async def type(self, text: str, delay_ms: int = 0) -> Terminal:
        """Type text character by character (no Enter).

        Args:
            text: Text to type.
            delay_ms: Delay between keystrokes in milliseconds.

        Returns self for chaining.
        """
        import anyio

        if delay_ms > 0:
            for char in text:
                await self._ghostty._send_request(
                    "send_text", {"surface_id": self.id, "text": char}
                )
                await anyio.sleep(delay_ms / 1000)
        else:
            await self._ghostty._send_request("send_text", {"surface_id": self.id, "text": text})
        return self

    async def press(self, key: str, mods: str | None = None) -> Terminal:
        """Press a key using native key events.

        Uses W3C key codes for reliable key input. Common keys:
            - "Enter", "Tab", "Escape", "Backspace", "Delete"
            - "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"
            - "Home", "End", "PageUp", "PageDown"
            - "F1" through "F12"
            - "Space"
            - Single letters: "KeyA" through "KeyZ"
            - Digits: "Digit0" through "Digit9"

        For modifier combinations, pass mods parameter:
            >>> await terminal.press("KeyC", mods="ctrl")  # Ctrl+C
            >>> await terminal.press("KeyS", mods="ctrl,shift")  # Ctrl+Shift+S

        Legacy Ctrl+X syntax still works for convenience:
            >>> await terminal.press("Ctrl+C")

        Args:
            key: W3C key code or legacy key name.
            mods: Comma-separated modifiers: "shift", "ctrl", "alt", "super".

        Returns self for chaining.
        """
        # Map friendly names to W3C key codes
        w3c_key_map = {
            # Navigation
            "Enter": "Enter",
            "Tab": "Tab",
            "Escape": "Escape",
            "Backspace": "Backspace",
            "Delete": "Delete",
            "Space": "Space",
            # Arrow keys - accept both formats
            "Up": "ArrowUp",
            "Down": "ArrowDown",
            "Left": "ArrowLeft",
            "Right": "ArrowRight",
            "ArrowUp": "ArrowUp",
            "ArrowDown": "ArrowDown",
            "ArrowLeft": "ArrowLeft",
            "ArrowRight": "ArrowRight",
            # Control keys
            "Home": "Home",
            "End": "End",
            "PageUp": "PageUp",
            "PageDown": "PageDown",
            "Insert": "Insert",
        }

        # Handle legacy Ctrl+<key> syntax
        if key.startswith("Ctrl+"):
            char = key[5:].upper()
            if len(char) == 1 and "A" <= char <= "Z":
                key = f"Key{char}"
                mods = "ctrl" if mods is None else f"ctrl,{mods}"
            else:
                # Fallback to send_text for unknown Ctrl combinations
                code = ord(char) - ord("A") + 1 if len(char) == 1 else 0
                if code > 0:
                    await self._ghostty._send_request(
                        "send_text", {"surface_id": self.id, "text": chr(code)}
                    )
                    return self

        # Map to W3C key code
        w3c_key = w3c_key_map.get(key, key)

        # Send key event (press + release)
        press_payload: dict[str, Any] = {"surface_id": self.id, "key": w3c_key, "action": "press"}
        if mods:
            press_payload["mods"] = mods
        await self._ghostty._send_request("send_key", press_payload)

        release_payload: dict[str, Any] = {"surface_id": self.id, "key": w3c_key, "action": "release"}
        if mods:
            release_payload["mods"] = mods
        await self._ghostty._send_request("send_key", release_payload)

        return self

    async def key_down(self, key: str, mods: str | None = None) -> Terminal:
        """Press a key down (without releasing).

        Useful for holding keys during other operations.

        Args:
            key: W3C key code.
            mods: Modifiers.

        Returns self for chaining.
        """
        payload: dict[str, Any] = {"surface_id": self.id, "key": key, "action": "press"}
        if mods:
            payload["mods"] = mods
        await self._ghostty._send_request("send_key", payload)
        return self

    async def key_up(self, key: str, mods: str | None = None) -> Terminal:
        """Release a key.

        Args:
            key: W3C key code.
            mods: Modifiers.

        Returns self for chaining.
        """
        payload: dict[str, Any] = {"surface_id": self.id, "key": key, "action": "release"}
        if mods:
            payload["mods"] = mods
        await self._ghostty._send_request("send_key", payload)
        return self

    # === Reading Screen ===

    async def screen(self, screen_type: str = "viewport") -> Screen:
        """Get the current screen content.

        Args:
            screen_type: "viewport" for visible content, "screen" for full scrollback.

        Returns:
            Screen object with text content and cursor position.
        """
        response = await self._ghostty._send_request(
            "get_screen", {"surface_id": self.id, "screen": screen_type}
        )
        data = response.get("data", {})
        return Screen(
            text=data.get("content", ""),
            cursor_x=data.get("cursor_x", 0),
            cursor_y=data.get("cursor_y", 0),
        )

    async def text(self) -> str:
        """Get the current screen text (shorthand for screen().text)."""
        return (await self.screen()).text

    async def cells(self, screen_type: str = "viewport") -> ScreenCells:
        """Get structured cell data for the screen.

        Returns detailed cell information including styling (colors, bold, etc.)
        for TUI automation and visual inspection.

        Args:
            screen_type: "viewport" for visible content, "screen" for full scrollback.

        Returns:
            ScreenCells object with cells, cursor position, and dimensions.

        Example:
            >>> cells = await terminal.cells()
            >>> # Find all bold cells
            >>> bold_cells = cells.styled_cells(bold=True)
            >>> # Check specific cell color
            >>> cell = cells.cell_at(0, 0)
            >>> if cell and cell.fg == "rgb(255,0,0)":
            ...     print("Red text at origin")
        """
        import json

        response = await self._ghostty._send_request(
            "get_screen", {"surface_id": self.id, "screen": screen_type, "format": "cells"}
        )
        data = response.get("data", {})
        # The cells format returns JSON in the content field
        cells_json = data.get("content", "{}")
        cells_data = json.loads(cells_json)
        return ScreenCells.from_dict(cells_data)

    # === Waiting ===

    async def wait_for_text(
        self,
        pattern: str,
        *,
        timeout: int = DEFAULT_TIMEOUT_MS,
        regex: bool = False,
    ) -> Terminal:
        """Wait for text to appear on screen.

        Args:
            pattern: Text or regex pattern to wait for.
            timeout: Timeout in milliseconds.
            regex: If True, treat pattern as regex.

        Returns self for chaining.

        Raises:
            TimeoutError: If text doesn't appear within timeout.
        """
        import anyio

        deadline = anyio.current_time() + (timeout / 1000)
        compiled = re.compile(pattern) if regex else None

        while True:
            screen = await self.screen()
            if compiled is not None:
                if compiled.search(screen.text):
                    return self
            elif pattern in screen.text:
                return self

            if anyio.current_time() >= deadline:
                raise TimeoutError(
                    f"Timeout waiting for text: {pattern!r}",
                    timeout_ms=timeout,
                )

            await anyio.sleep(0.1)

    async def wait_for_prompt(
        self,
        prompt_pattern: str = r"[$#>%➤❯λ»›]\s*",
        *,
        timeout: int = DEFAULT_TIMEOUT_MS,
    ) -> Terminal:
        """Wait for a shell prompt to appear.

        Uses plain text (ANSI stripped) for matching to handle fancy prompts.
        Default pattern matches common prompt endings: $ # > % ➤ ❯ λ » ›

        Args:
            prompt_pattern: Regex pattern matching shell prompts.
            timeout: Timeout in milliseconds.

        Returns self for chaining.
        """
        import anyio

        deadline = anyio.current_time() + (timeout / 1000)
        compiled = re.compile(prompt_pattern)

        while True:
            screen = await self.screen()
            # Use plain_text to strip ANSI escape codes from fancy prompts
            # Also strip trailing replacement characters (U+FFFD) that appear
            # in uninitialized terminal space
            text = screen.plain_text.rstrip("\ufffd")
            if compiled.search(text):
                return self

            if anyio.current_time() >= deadline:
                raise TimeoutError(
                    f"Timeout waiting for prompt: {prompt_pattern!r}",
                    timeout_ms=timeout,
                )

            await anyio.sleep(0.1)

    async def wait_for_idle(
        self,
        stable_ms: int = 500,
        *,
        timeout: int = DEFAULT_TIMEOUT_MS,
    ) -> Terminal:
        """Wait for screen content to stabilize.

        Args:
            stable_ms: How long content must be stable to consider idle.
            timeout: Timeout in milliseconds.

        Returns self for chaining.
        """
        import anyio

        deadline = anyio.current_time() + (timeout / 1000)
        stable_duration = stable_ms / 1000

        last_content = ""
        stable_since = anyio.current_time()

        while True:
            screen = await self.screen()
            current_content = screen.text

            now = anyio.current_time()

            if current_content != last_content:
                last_content = current_content
                stable_since = now

            if now - stable_since >= stable_duration:
                return self

            if now >= deadline:
                raise TimeoutError(
                    "Timeout waiting for screen to stabilize",
                    timeout_ms=timeout,
                )

            await anyio.sleep(0.1)

    # === Actions ===

    async def focus(self) -> Terminal:
        """Focus this terminal (bring window to front)."""
        await self._ghostty._send_request("focus_surface", {"surface_id": self.id})
        return self

    async def close(self) -> None:
        """Close this terminal."""
        await self._ghostty._send_request("close_surface", {"surface_id": self.id})

    async def resize(self, rows: int | None = None, cols: int | None = None) -> Terminal:
        """Resize the terminal.

        Args:
            rows: New number of rows.
            cols: New number of columns.

        Returns self for chaining.
        """
        payload: dict[str, Any] = {"surface_id": self.id}
        if rows is not None:
            payload["rows"] = rows
        if cols is not None:
            payload["cols"] = cols
        await self._ghostty._send_request("resize_surface", payload)
        return self

    async def screenshot(self, path: str | Path) -> Path:
        """Take a screenshot of this terminal.

        Args:
            path: Where to save the screenshot.

        Returns:
            Path to the saved screenshot.
        """
        output_path = Path(path).resolve()
        await self._ghostty._send_request(
            "screenshot_surface",
            {"surface_id": self.id, "output_path": str(output_path)},
        )
        return output_path

    # === Mouse ===

    async def click(
        self,
        x: float,
        y: float,
        button: str = "left",
        mods: str | None = None,
    ) -> Terminal:
        """Click at a position in pixels.

        Args:
            x: X position in pixels.
            y: Y position in pixels.
            button: Mouse button ("left", "right", "middle").
            mods: Modifiers ("shift", "ctrl", "alt", "super").

        Returns self for chaining.
        """
        await self._send_mouse(x, y, button, "press", mods)
        await self._send_mouse(x, y, button, "release", mods)
        return self

    async def _send_mouse(
        self,
        x: float,
        y: float,
        button: str | None = None,
        button_action: str | None = None,
        mods: str | None = None,
    ) -> None:
        """Send a mouse event."""
        payload: dict[str, Any] = {"surface_id": self.id, "x": x, "y": y}
        if button is not None:
            payload["button"] = button
        if button_action is not None:
            payload["button_action"] = button_action
        if mods is not None:
            payload["mods"] = mods
        await self._ghostty._send_request("send_mouse", payload)

    async def scroll(
        self,
        delta_y: float = 0.0,
        delta_x: float = 0.0,
        mods: str | None = None,
    ) -> Terminal:
        """Scroll the terminal.

        Args:
            delta_y: Vertical scroll delta (positive = down).
            delta_x: Horizontal scroll delta (positive = right).
            mods: Modifiers ("shift", "ctrl", "alt", "super").

        Returns self for chaining.
        """
        payload: dict[str, Any] = {"surface_id": self.id, "x": delta_x, "y": delta_y}
        if mods is not None:
            payload["mods"] = mods
        await self._ghostty._send_request("send_scroll", payload)
        return self

    async def drag(
        self,
        from_x: float,
        from_y: float,
        to_x: float,
        to_y: float,
        button: str = "left",
        steps: int = 10,
        mods: str | None = None,
    ) -> Terminal:
        """Drag from one position to another.

        Args:
            from_x: Starting X position in pixels.
            from_y: Starting Y position in pixels.
            to_x: Ending X position in pixels.
            to_y: Ending Y position in pixels.
            button: Mouse button to hold during drag.
            steps: Number of intermediate positions for smooth drag.
            mods: Modifiers ("shift", "ctrl", "alt", "super").

        Returns self for chaining.
        """
        import anyio

        # Press at start position
        await self._send_mouse(from_x, from_y, button, "press", mods)
        await anyio.sleep(0.01)

        # Move through intermediate positions
        for i in range(1, steps + 1):
            t = i / steps
            x = from_x + (to_x - from_x) * t
            y = from_y + (to_y - from_y) * t
            await self._send_mouse(x, y, None, None, mods)
            await anyio.sleep(0.01)

        # Release at end position
        await self._send_mouse(to_x, to_y, button, "release", mods)
        return self

    async def double_click(
        self,
        x: float,
        y: float,
        button: str = "left",
        mods: str | None = None,
    ) -> Terminal:
        """Double-click at a position.

        Args:
            x: X position in pixels.
            y: Y position in pixels.
            button: Mouse button.
            mods: Modifiers.

        Returns self for chaining.
        """
        import anyio

        await self.click(x, y, button, mods)
        await anyio.sleep(0.05)
        await self.click(x, y, button, mods)
        return self

    # === Refresh ===

    async def refresh(self) -> Terminal:
        """Refresh terminal metadata from server."""
        surfaces = await self._ghostty._list_surfaces()
        for s in surfaces:
            if s.id == self.id:
                self._surface = s
                break
        return self

    def __repr__(self) -> str:
        return f"Terminal(id={self.id!r}, title={self.title!r}, pwd={self.pwd!r})"
