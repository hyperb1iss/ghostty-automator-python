"""Playwright-style expect assertions for terminals."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ghostty_automator.errors import TimeoutError
from ghostty_automator.protocol import DEFAULT_TIMEOUT_MS, Screen

if TYPE_CHECKING:
    from ghostty_automator._async.terminal import Terminal


_MAX_ASSERTION_LINES = 80
_MAX_ASSERTION_CHARS = 8_000


def _truncate_screen(screen: Screen) -> str:
    text = screen.plain_text
    lines = text.splitlines()

    if len(lines) > _MAX_ASSERTION_LINES:
        omitted = len(lines) - _MAX_ASSERTION_LINES
        lines = [f"… ({omitted} lines truncated) …", *lines[-_MAX_ASSERTION_LINES:]]
        text = "\n".join(lines)

    if len(text) > _MAX_ASSERTION_CHARS:
        text = "… (truncated) …\n" + text[-_MAX_ASSERTION_CHARS:]

    return text


class TerminalExpect:
    """Playwright-style expect assertions for a terminal.

    Example:
        >>> await terminal.expect.to_contain("hello")
        >>> await terminal.expect.to_match(r"user@.*\\$")
        >>> await terminal.expect.not_to_contain("error")
    """

    def __init__(self, terminal: Terminal) -> None:
        self._terminal = terminal

    async def to_contain(
        self,
        text: str,
        *,
        timeout: int = DEFAULT_TIMEOUT_MS,
    ) -> None:
        """Assert that terminal contains the given text.

        Args:
            text: Text to look for.
            timeout: How long to wait for the text to appear.

        Raises:
            AssertionError: If text is not found within timeout.
        """
        try:
            await self._terminal.wait_for_text(text, timeout=timeout)
        except TimeoutError as e:
            screen = await self._terminal.screen()
            raise AssertionError(
                f"Expected terminal to contain {text!r}\n\n"
                f"Actual content:\n{_truncate_screen(screen)}"
            ) from e

    async def not_to_contain(
        self,
        text: str,
        *,
        timeout: int = 1000,
    ) -> None:
        """Assert that terminal does NOT contain the given text.

        Args:
            text: Text that should not be present.
            timeout: How long to check for absence.

        Raises:
            AssertionError: If text is found.
        """
        import anyio

        deadline = anyio.current_time() + (timeout / 1000)

        while anyio.current_time() < deadline:
            screen = await self._terminal.screen()
            if text in screen.text:
                raise AssertionError(
                    f"Expected terminal NOT to contain {text!r}\n\n"
                    f"Actual content:\n{_truncate_screen(screen)}"
                )
            await anyio.sleep(0.1)

    async def to_match(
        self,
        pattern: str,
        *,
        timeout: int = DEFAULT_TIMEOUT_MS,
    ) -> re.Match[str]:
        """Assert that terminal matches the given regex pattern.

        Args:
            pattern: Regex pattern to match.
            timeout: How long to wait for a match.

        Returns:
            The regex match object.

        Raises:
            AssertionError: If pattern doesn't match within timeout.
        """
        try:
            await self._terminal.wait_for_text(pattern, timeout=timeout, regex=True)
            screen = await self._terminal.screen()
            match = re.search(pattern, screen.text)
            if match:
                return match
            raise AssertionError(f"Pattern {pattern!r} not found after wait")
        except TimeoutError as e:
            screen = await self._terminal.screen()
            raise AssertionError(
                f"Expected terminal to match pattern {pattern!r}\n\n"
                f"Actual content:\n{_truncate_screen(screen)}"
            ) from e

    async def to_have_title(
        self,
        title: str,
        *,
        exact: bool = False,
        timeout: int = DEFAULT_TIMEOUT_MS,
    ) -> None:
        """Assert that terminal has the given title.

        Args:
            title: Expected title.
            exact: If True, require exact match. Otherwise substring match.
            timeout: How long to wait.

        Raises:
            AssertionError: If title doesn't match.
        """
        import anyio

        deadline = anyio.current_time() + (timeout / 1000)

        while anyio.current_time() < deadline:
            await self._terminal.refresh()
            actual = self._terminal.title

            if exact:
                if actual == title:
                    return
            elif title in actual:
                return

            await anyio.sleep(0.1)

        raise AssertionError(
            f"Expected terminal title {'to be' if exact else 'to contain'} {title!r}\n"
            f"Actual title: {self._terminal.title!r}"
        )

    async def to_have_pwd(
        self,
        path: str,
        *,
        exact: bool = False,
        timeout: int = DEFAULT_TIMEOUT_MS,
    ) -> None:
        """Assert that terminal has the given working directory.

        Args:
            path: Expected path.
            exact: If True, require exact match. Otherwise substring match.
            timeout: How long to wait.

        Raises:
            AssertionError: If pwd doesn't match.
        """
        import anyio

        deadline = anyio.current_time() + (timeout / 1000)

        while anyio.current_time() < deadline:
            await self._terminal.refresh()
            actual = self._terminal.pwd

            if exact:
                if actual == path:
                    return
            elif path in actual:
                return

            await anyio.sleep(0.1)

        raise AssertionError(
            f"Expected terminal pwd {'to be' if exact else 'to contain'} {path!r}\n"
            f"Actual pwd: {self._terminal.pwd!r}"
        )

    async def to_be_focused(self, *, timeout: int = DEFAULT_TIMEOUT_MS) -> None:
        """Assert that this terminal is focused.

        Raises:
            AssertionError: If terminal is not focused.
        """
        import anyio

        deadline = anyio.current_time() + (timeout / 1000)

        while anyio.current_time() < deadline:
            await self._terminal.refresh()
            if self._terminal.focused:
                return
            await anyio.sleep(0.1)

        raise AssertionError("Expected terminal to be focused")

    async def prompt(self, *, timeout: int = DEFAULT_TIMEOUT_MS) -> None:
        """Assert that a shell prompt is visible.

        This is a shorthand for checking common prompt patterns.
        """
        try:
            await self._terminal.wait_for_prompt(timeout=timeout)
        except TimeoutError as e:
            screen = await self._terminal.screen()
            raise AssertionError(
                f"Expected shell prompt to be visible\n\n"
                f"Actual content:\n{_truncate_screen(screen)}"
            ) from e
