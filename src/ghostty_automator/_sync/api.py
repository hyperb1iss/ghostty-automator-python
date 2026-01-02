"""Synchronous API wrapper for Ghostty Automator.

This module provides synchronous versions of all async APIs by running
the event loop internally, similar to Playwright's sync_api.

Example:
    >>> from ghostty_automator.sync_api import Ghostty
    >>>
    >>> with Ghostty.connect() as ghostty:
    ...     terminal = ghostty.terminals.first()
    ...     terminal.send("echo hello")
    ...     terminal.wait_for_text("hello")
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Self, TypeVar

from ghostty_automator._async import client as async_client, terminal as async_terminal
from ghostty_automator._async.expect import TerminalExpect as AsyncTerminalExpect
from ghostty_automator.protocol import DEFAULT_TIMEOUT_MS, Screen, ScreenCells

T = TypeVar("T")


def _run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Run an async coroutine synchronously."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None:
        # We're inside an async context - use a new thread
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()  # type: ignore[return-value]

    return asyncio.run(coro)


class TerminalExpect:
    """Synchronous expect assertions for a terminal."""

    def __init__(self, async_expect: AsyncTerminalExpect) -> None:
        self._async_expect = async_expect

    def to_contain(self, text: str, *, timeout: int = DEFAULT_TIMEOUT_MS) -> None:
        """Assert that terminal contains the given text."""
        _run_sync(self._async_expect.to_contain(text, timeout=timeout))

    def not_to_contain(self, text: str, *, timeout: int = 1000) -> None:
        """Assert that terminal does NOT contain the given text."""
        _run_sync(self._async_expect.not_to_contain(text, timeout=timeout))

    def to_match(self, pattern: str, *, timeout: int = DEFAULT_TIMEOUT_MS) -> re.Match[str]:
        """Assert that terminal matches the given regex pattern."""
        return _run_sync(self._async_expect.to_match(pattern, timeout=timeout))

    def to_have_title(
        self,
        title: str,
        *,
        exact: bool = False,
        timeout: int = DEFAULT_TIMEOUT_MS,
    ) -> None:
        """Assert that terminal has the given title."""
        _run_sync(self._async_expect.to_have_title(title, exact=exact, timeout=timeout))

    def to_have_pwd(
        self,
        path: str,
        *,
        exact: bool = False,
        timeout: int = DEFAULT_TIMEOUT_MS,
    ) -> None:
        """Assert that terminal has the given working directory."""
        _run_sync(self._async_expect.to_have_pwd(path, exact=exact, timeout=timeout))

    def to_be_focused(self, *, timeout: int = DEFAULT_TIMEOUT_MS) -> None:
        """Assert that this terminal is focused."""
        _run_sync(self._async_expect.to_be_focused(timeout=timeout))

    def prompt(self, *, timeout: int = DEFAULT_TIMEOUT_MS) -> None:
        """Assert that a shell prompt is visible."""
        _run_sync(self._async_expect.prompt(timeout=timeout))


class Terminal:
    """Synchronous terminal wrapper."""

    def __init__(self, async_terminal_obj: async_terminal.Terminal) -> None:
        self._async_terminal = async_terminal_obj
        self._expect: TerminalExpect | None = None

    @property
    def id(self) -> str:
        """Surface ID."""
        return self._async_terminal.id

    @property
    def title(self) -> str:
        """Window/tab title."""
        return self._async_terminal.title

    @property
    def pwd(self) -> str:
        """Current working directory."""
        return self._async_terminal.pwd

    @property
    def rows(self) -> int:
        """Number of rows."""
        return self._async_terminal.rows

    @property
    def cols(self) -> int:
        """Number of columns."""
        return self._async_terminal.cols

    @property
    def focused(self) -> bool:
        """Whether this terminal is focused."""
        return self._async_terminal.focused

    @property
    def expect(self) -> TerminalExpect:
        """Assertion helpers for this terminal."""
        if self._expect is None:
            self._expect = TerminalExpect(self._async_terminal.expect)
        return self._expect

    # === Sending Input ===

    def send(self, text: str) -> Terminal:
        """Send text to the terminal and press Enter."""
        _run_sync(self._async_terminal.send(text))
        return self

    def type(self, text: str, delay_ms: int = 0) -> Terminal:
        """Type text character by character (no Enter)."""
        _run_sync(self._async_terminal.type(text, delay_ms=delay_ms))
        return self

    def press(self, key: str, mods: str | None = None) -> Terminal:
        """Press a key using native key events.

        Uses W3C key codes. See async Terminal.press() for full documentation.
        """
        _run_sync(self._async_terminal.press(key, mods=mods))
        return self

    def key_down(self, key: str, mods: str | None = None) -> Terminal:
        """Press a key down (without releasing)."""
        _run_sync(self._async_terminal.key_down(key, mods=mods))
        return self

    def key_up(self, key: str, mods: str | None = None) -> Terminal:
        """Release a key."""
        _run_sync(self._async_terminal.key_up(key, mods=mods))
        return self

    # === Reading Screen ===

    def screen(self, screen_type: str = "viewport") -> Screen:
        """Get the current screen content."""
        return _run_sync(self._async_terminal.screen(screen_type=screen_type))

    def text(self) -> str:
        """Get the current screen text."""
        return _run_sync(self._async_terminal.text())

    def cells(self, screen_type: str = "viewport") -> ScreenCells:
        """Get structured cell data for the screen.

        See async Terminal.cells() for full documentation.
        """
        return _run_sync(self._async_terminal.cells(screen_type=screen_type))

    # === Waiting ===

    def wait_for_text(
        self,
        pattern: str,
        *,
        timeout: int = DEFAULT_TIMEOUT_MS,
        regex: bool = False,
    ) -> Terminal:
        """Wait for text to appear on screen."""
        _run_sync(self._async_terminal.wait_for_text(pattern, timeout=timeout, regex=regex))
        return self

    def wait_for_prompt(
        self,
        prompt_pattern: str = r"[$#>%]\s*$",
        *,
        timeout: int = DEFAULT_TIMEOUT_MS,
    ) -> Terminal:
        """Wait for a shell prompt to appear."""
        _run_sync(self._async_terminal.wait_for_prompt(prompt_pattern, timeout=timeout))
        return self

    def wait_for_idle(
        self,
        stable_ms: int = 500,
        *,
        timeout: int = DEFAULT_TIMEOUT_MS,
    ) -> Terminal:
        """Wait for screen content to stabilize."""
        _run_sync(self._async_terminal.wait_for_idle(stable_ms, timeout=timeout))
        return self

    # === Actions ===

    def focus(self) -> Terminal:
        """Focus this terminal (bring window to front)."""
        _run_sync(self._async_terminal.focus())
        return self

    def close(self) -> None:
        """Close this terminal."""
        _run_sync(self._async_terminal.close())

    def resize(self, rows: int | None = None, cols: int | None = None) -> Terminal:
        """Resize the terminal."""
        _run_sync(self._async_terminal.resize(rows=rows, cols=cols))
        return self

    def screenshot(self, path: str | Path) -> Path:
        """Take a screenshot of this terminal."""
        return _run_sync(self._async_terminal.screenshot(path))

    # === Mouse ===

    def click(
        self,
        x: float,
        y: float,
        button: str = "left",
        mods: str | None = None,
    ) -> Terminal:
        """Click at a position in pixels."""
        _run_sync(self._async_terminal.click(x, y, button=button, mods=mods))
        return self

    # === Refresh ===

    def refresh(self) -> Terminal:
        """Refresh terminal metadata from server."""
        _run_sync(self._async_terminal.refresh())
        return self

    def __repr__(self) -> str:
        return repr(self._async_terminal)


class Terminals:
    """Synchronous collection of terminals."""

    def __init__(self, async_terminals: async_client.Terminals) -> None:
        self._async_terminals = async_terminals

    def all(self) -> list[Terminal]:
        """Get all terminals."""
        async_terms: list[async_terminal.Terminal] = _run_sync(self._async_terminals.all())
        return [Terminal(t) for t in async_terms]

    def first(self) -> Terminal:
        """Get the first terminal."""
        result: async_terminal.Terminal = _run_sync(self._async_terminals.first())
        return Terminal(result)

    def focused(self) -> Terminal | None:
        """Get the focused terminal, or None if none focused."""
        result: async_terminal.Terminal | None = _run_sync(self._async_terminals.focused())
        return Terminal(result) if result else None

    def by_title(self, title: str) -> Terminal | None:
        """Find a terminal by title (partial match)."""
        result: async_terminal.Terminal | None = _run_sync(self._async_terminals.by_title(title))
        return Terminal(result) if result else None

    def by_pwd(self, path: str) -> Terminal | None:
        """Find a terminal by working directory (partial match)."""
        result: async_terminal.Terminal | None = _run_sync(self._async_terminals.by_pwd(path))
        return Terminal(result) if result else None


class Ghostty:
    """Synchronous Ghostty client.

    Example:
        >>> with Ghostty.connect() as ghostty:
        ...     terminal = ghostty.terminals.first()
        ...     terminal.send("echo hello")
        ...     terminal.wait_for_text("hello")
    """

    def __init__(self, async_ghostty: async_client.Ghostty) -> None:
        self._async_ghostty = async_ghostty
        self.terminals = Terminals(async_ghostty.terminals)

    @classmethod
    def connect(
        cls,
        socket_path: str | Path | None = None,
        app_class: str | None = None,
        *,
        request_timeout_ms: int = DEFAULT_TIMEOUT_MS,
        validate_socket: bool = True,
    ) -> Ghostty:
        """Create a connected Ghostty client."""
        async_ghostty = async_client.Ghostty.connect(
            socket_path=socket_path,
            app_class=app_class,
            request_timeout_ms=request_timeout_ms,
            validate_socket=validate_socket,
        )
        return cls(async_ghostty)

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        pass

    def new_window(self, command: list[str] | None = None) -> Terminal:
        """Open a new window and return its terminal."""
        async_term: async_terminal.Terminal = _run_sync(
            self._async_ghostty.new_window(command=command)
        )
        return Terminal(async_term)

    def new_tab(self, command: list[str] | None = None) -> Terminal:
        """Open a new tab and return its terminal."""
        async_term: async_terminal.Terminal = _run_sync(
            self._async_ghostty.new_tab(command=command)
        )
        return Terminal(async_term)
