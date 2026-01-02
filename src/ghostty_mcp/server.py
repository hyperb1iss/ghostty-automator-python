"""Ghostty MCP Server - Terminal automation via Model Context Protocol.

This server provides programmatic control over Ghostty terminal windows
using the ghostty-automator library.

Tools:
    - list_terminals: Discover all open terminal surfaces
    - terminal: Interact with a specific terminal (18 actions)
    - new_terminal: Create new window or tab
"""

from __future__ import annotations

import json
from enum import Enum
from typing import Any

from fastmcp import FastMCP

from ghostty_automator import Ghostty, Screen, ScreenCells, Terminal
from ghostty_automator.errors import GhosttyError, TimeoutError

# =============================================================================
# Server Setup
# =============================================================================

mcp = FastMCP(
    "ghostty",
    instructions="""Ghostty Terminal Automation Server

This server provides control over Ghostty terminal windows.

Workflow:
1. Use `list_terminals` to discover available terminal surfaces
2. Use `terminal` with a terminal_id and action to interact
3. Use `new_terminal` to create new windows/tabs

Each terminal has a unique ID like "0x153872000". Use these IDs to target
specific terminals.

Common patterns:
- Run a command: terminal(id, action="send", text="ls -la")
- Read screen: terminal(id, action="read")
- Wait for output: terminal(id, action="wait_text", pattern="$")
- Press key: terminal(id, action="key", key="Enter")
- Click: terminal(id, action="click", x=100, y=50)
""",
)


# =============================================================================
# Types
# =============================================================================


class TerminalAction(str, Enum):
    """Actions available for the terminal tool."""

    # Input
    SEND = "send"
    TYPE = "type"
    KEY = "key"

    # Mouse
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    DRAG = "drag"
    SCROLL = "scroll"

    # Screen
    READ = "read"
    CELLS = "cells"
    SCREENSHOT = "screenshot"

    # Waiting
    WAIT_TEXT = "wait_text"
    WAIT_PROMPT = "wait_prompt"
    WAIT_IDLE = "wait_idle"

    # Assertions
    EXPECT = "expect"
    EXPECT_NOT = "expect_not"

    # Management
    FOCUS = "focus"
    CLOSE = "close"
    RESIZE = "resize"


# =============================================================================
# Helpers
# =============================================================================


def _json(data: Any) -> str:
    """Convert data to JSON string."""
    return json.dumps(data, default=str)


def _screen_to_dict(screen: Screen) -> dict[str, Any]:
    """Convert Screen to dict for JSON serialization."""
    return {
        "text": screen.text,
        "plain_text": screen.plain_text,
        "cursor_x": screen.cursor_x,
        "cursor_y": screen.cursor_y,
    }


def _cells_to_dict(cells: ScreenCells) -> dict[str, Any]:
    """Convert ScreenCells to dict for JSON serialization."""
    return {
        "cells": [
            {
                "char": c.char,
                "x": c.x,
                "y": c.y,
                "fg": c.fg,
                "bg": c.bg,
                "bold": c.bold,
                "italic": c.italic,
                "underline": c.underline,
                "strikethrough": c.strikethrough,
                "inverse": c.inverse,
            }
            for c in cells.cells
        ],
        "cursor_x": cells.cursor_x,
        "cursor_y": cells.cursor_y,
        "rows": cells.rows,
        "cols": cells.cols,
    }


async def _get_terminal(terminal_id: str) -> Terminal:
    """Get a terminal by ID."""
    async with Ghostty.connect() as ghostty:
        terminals = await ghostty.terminals.all()
        for t in terminals:
            if t.id == terminal_id:
                return t
        msg = f"Terminal not found: {terminal_id}"
        raise GhosttyError(msg)


# =============================================================================
# Tools
# =============================================================================


@mcp.tool()
async def list_terminals() -> str:
    """List all open Ghostty terminal surfaces.

    Returns JSON array of terminals with:
    - id: Unique surface ID (use with terminal tool)
    - title: Window/tab title
    - pwd: Current working directory
    - rows/cols: Terminal dimensions
    - focused: Whether terminal has focus

    Example response:
    [{"id": "0x123", "title": "zsh", "pwd": "/home/user", "rows": 24, "cols": 80, "focused": true}]
    """
    try:
        async with Ghostty.connect() as ghostty:
            terminals = await ghostty.terminals.all()
            return _json(
                [
                    {
                        "id": t.id,
                        "title": t.title,
                        "pwd": t.pwd,
                        "rows": t.rows,
                        "cols": t.cols,
                        "focused": t.focused,
                    }
                    for t in terminals
                ]
            )
    except GhosttyError as e:
        return _json({"error": str(e)})


@mcp.tool()
async def terminal(
    terminal_id: str,
    action: TerminalAction,
    # Input params
    text: str | None = None,
    delay_ms: int = 0,
    key: str | None = None,
    mods: str | None = None,
    # Mouse params
    x: float | None = None,
    y: float | None = None,
    button: str = "left",
    from_x: float | None = None,
    from_y: float | None = None,
    to_x: float | None = None,
    to_y: float | None = None,
    steps: int = 10,
    delta_x: float = 0.0,
    delta_y: float = 0.0,
    # Screen params
    screen_type: str = "viewport",
    output_path: str | None = None,
    # Wait params
    pattern: str | None = None,
    regex: bool = False,
    timeout_ms: int = 30000,
    prompt_pattern: str | None = None,
    stable_ms: int = 500,
    # Resize params
    rows: int | None = None,
    cols: int | None = None,
) -> str:
    """Interact with a terminal surface.

    Args:
        terminal_id: Target terminal ID (from list_terminals)
        action: Action to perform (see below)

    Actions:

    INPUT:
        send: Send text + Enter (run command)
            - text: Command to send
        type: Type text without Enter
            - text: Text to type
            - delay_ms: Delay between keystrokes (ms)
        key: Press key combination
            - key: Key name (Enter, Tab, Escape, ArrowUp, KeyC, F1, etc.)
            - mods: Modifiers (ctrl, shift, alt, super) comma-separated

    MOUSE:
        click: Click at position
            - x, y: Pixel coordinates
            - button: left/right/middle
            - mods: Optional modifiers
        double_click: Double-click at position
            - x, y: Pixel coordinates
            - button: left/right/middle
        drag: Drag from one position to another
            - from_x, from_y: Start position
            - to_x, to_y: End position
            - steps: Intermediate positions (default 10)
        scroll: Scroll the terminal
            - delta_y: Vertical scroll (positive=down)
            - delta_x: Horizontal scroll (positive=right)
            - mods: Optional modifiers

    SCREEN:
        read: Get screen content
            - screen_type: viewport (visible) or screen (scrollback)
            Returns: {text, plain_text, cursor_x, cursor_y}
        cells: Get styled cell data
            - screen_type: viewport or screen
            Returns: {cells: [...], cursor_x, cursor_y, rows, cols}
        screenshot: Capture as PNG
            - output_path: Where to save the image
            Returns: {path: absolute_path}

    WAITING:
        wait_text: Wait for text/regex to appear
            - pattern: Text or regex to wait for
            - regex: If true, treat pattern as regex
            - timeout_ms: Max wait time (default 30000)
        wait_prompt: Wait for shell prompt
            - prompt_pattern: Custom prompt regex (optional)
            - timeout_ms: Max wait time
        wait_idle: Wait for screen to stabilize
            - stable_ms: How long content must be stable (default 500)
            - timeout_ms: Max wait time

    ASSERTIONS:
        expect: Assert text is present
            - text: Text that must be on screen
            - timeout_ms: Max wait time
        expect_not: Assert text is NOT present
            - text: Text that must NOT be on screen
            - timeout_ms: How long to check

    MANAGEMENT:
        focus: Bring terminal window to front
        close: Close the terminal
        resize: Change terminal dimensions
            - rows: New row count (optional)
            - cols: New column count (optional)
    """
    try:
        t = await _get_terminal(terminal_id)

        match action:
            # Input actions
            case TerminalAction.SEND:
                if not text:
                    return _json({"error": "text is required for send action"})
                await t.send(text)
                return _json({"ok": True, "sent": text})

            case TerminalAction.TYPE:
                if not text:
                    return _json({"error": "text is required for type action"})
                await t.type(text, delay_ms=delay_ms)
                return _json({"ok": True, "typed": text, "delay_ms": delay_ms})

            case TerminalAction.KEY:
                if not key:
                    return _json({"error": "key is required for key action"})
                await t.press(key, mods=mods)
                return _json({"ok": True, "key": key, "mods": mods})

            # Mouse actions
            case TerminalAction.CLICK:
                if x is None or y is None:
                    return _json({"error": "x and y are required for click action"})
                await t.click(x, y, button=button, mods=mods)
                return _json({"ok": True, "x": x, "y": y, "button": button})

            case TerminalAction.DOUBLE_CLICK:
                if x is None or y is None:
                    return _json({"error": "x and y are required for double_click action"})
                await t.double_click(x, y, button=button)
                return _json({"ok": True, "x": x, "y": y, "button": button})

            case TerminalAction.DRAG:
                if None in (from_x, from_y, to_x, to_y):
                    return _json(
                        {"error": "from_x, from_y, to_x, to_y are required for drag action"}
                    )
                # Type narrowing for pyright
                assert from_x is not None
                assert from_y is not None
                assert to_x is not None
                assert to_y is not None
                await t.drag(from_x, from_y, to_x, to_y, steps=steps)
                return _json(
                    {"ok": True, "from": [from_x, from_y], "to": [to_x, to_y], "steps": steps}
                )

            case TerminalAction.SCROLL:
                await t.scroll(delta_y=delta_y, delta_x=delta_x, mods=mods)
                return _json({"ok": True, "delta_x": delta_x, "delta_y": delta_y})

            # Screen actions
            case TerminalAction.READ:
                screen = await t.screen(screen_type=screen_type)
                return _json(_screen_to_dict(screen))

            case TerminalAction.CELLS:
                cells = await t.cells(screen_type=screen_type)
                return _json(_cells_to_dict(cells))

            case TerminalAction.SCREENSHOT:
                if not output_path:
                    return _json({"error": "output_path is required for screenshot action"})
                path = await t.screenshot(output_path)
                return _json({"ok": True, "path": str(path)})

            # Wait actions
            case TerminalAction.WAIT_TEXT:
                if not pattern:
                    return _json({"error": "pattern is required for wait_text action"})
                await t.wait_for_text(pattern, regex=regex, timeout=timeout_ms)
                return _json({"ok": True, "pattern": pattern, "found": True})

            case TerminalAction.WAIT_PROMPT:
                if prompt_pattern:
                    await t.wait_for_prompt(prompt_pattern=prompt_pattern, timeout=timeout_ms)
                else:
                    await t.wait_for_prompt(timeout=timeout_ms)
                return _json({"ok": True, "prompt_found": True})

            case TerminalAction.WAIT_IDLE:
                await t.wait_for_idle(stable_ms=stable_ms, timeout=timeout_ms)
                return _json({"ok": True, "stable": True, "stable_ms": stable_ms})

            # Assertion actions
            case TerminalAction.EXPECT:
                if not text:
                    return _json({"error": "text is required for expect action"})
                await t.expect.to_contain(text, timeout=timeout_ms)
                return _json({"ok": True, "text": text, "found": True})

            case TerminalAction.EXPECT_NOT:
                if not text:
                    return _json({"error": "text is required for expect_not action"})
                await t.expect.not_to_contain(text, timeout=timeout_ms)
                return _json({"ok": True, "text": text, "absent": True})

            # Management actions
            case TerminalAction.FOCUS:
                await t.focus()
                return _json({"ok": True, "focused": True})

            case TerminalAction.CLOSE:
                await t.close()
                return _json({"ok": True, "closed": True})

            case TerminalAction.RESIZE:
                await t.resize(rows=rows, cols=cols)
                return _json({"ok": True, "rows": rows, "cols": cols})

    except TimeoutError as e:
        return _json({"error": f"Timeout: {e}", "timeout_ms": e.timeout_ms})
    except GhosttyError as e:
        return _json({"error": str(e)})
    except AssertionError as e:
        return _json({"error": f"Assertion failed: {e}"})

    return _json({"error": f"Unknown action: {action}"})


@mcp.tool()
async def new_terminal(
    type: str = "window",
    command: list[str] | None = None,
) -> str:
    """Create a new Ghostty window or tab.

    Args:
        type: "window" for new window, "tab" for new tab
        command: Optional command to run in the new terminal

    Returns:
        JSON with terminal_id of the new terminal

    Example:
        new_terminal(type="tab", command=["python", "-i"])
    """
    try:
        async with Ghostty.connect() as ghostty:
            if type == "tab":
                t = await ghostty.new_tab(command=command)
            else:
                t = await ghostty.new_window(command=command)

            return _json(
                {
                    "ok": True,
                    "terminal_id": t.id,
                    "title": t.title,
                    "pwd": t.pwd,
                }
            )
    except GhosttyError as e:
        return _json({"error": str(e)})


# =============================================================================
# Entry Point
# =============================================================================


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
