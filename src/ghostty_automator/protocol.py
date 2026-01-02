"""Low-level IPC protocol types and utilities."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ANSI escape sequence pattern (SGR, CSI, OSC, etc.)
#
# Supports OSC terminated by BEL (\\x07) or String Terminator (ESC \\).
ANSI_PATTERN = re.compile(r"\x1b(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~]|\][^\x07\x1b]*(?:\x07|\x1b\\))")


def _surface_list() -> list[Surface]:
    return []


def _tab_list() -> list[Tab]:
    return []


# =============================================================================
# Constants
# =============================================================================

PROTOCOL_VERSION = 1
MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB
DEFAULT_TIMEOUT_MS = 30_000

# =============================================================================
# Data Types
# =============================================================================


@dataclass
class Surface:
    """A terminal surface (a single terminal view)."""

    id: str
    title: str
    pwd: str
    focused: bool
    rows: int
    cols: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Surface:
        return cls(
            id=data["id"],
            title=data.get("title", ""),
            pwd=data.get("pwd", ""),
            focused=data.get("focused", False),
            rows=data.get("rows", 24),
            cols=data.get("cols", 80),
        )


@dataclass
class Tab:
    """A tab containing one or more surfaces."""

    surfaces: list[Surface] = field(default_factory=_surface_list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Tab:
        return cls(surfaces=[Surface.from_dict(s) for s in data.get("surfaces", [])])


@dataclass
class Window:
    """A window containing one or more tabs."""

    tabs: list[Tab] = field(default_factory=_tab_list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Window:
        return cls(tabs=[Tab.from_dict(t) for t in data.get("tabs", [])])


@dataclass
class Screen:
    """Screen content from a terminal surface."""

    text: str
    cursor_x: int
    cursor_y: int

    @property
    def lines(self) -> list[str]:
        """Get screen content as list of lines."""
        return self.text.splitlines()

    @property
    def plain_text(self) -> str:
        """Get text with ANSI escape codes stripped."""
        return strip_ansi(self.text)

    def contains(self, pattern: str) -> bool:
        """Check if screen contains the given text."""
        return pattern in self.text


@dataclass
class Cell:
    """A terminal cell with character and styling information."""

    char: str
    x: int
    y: int
    fg: str | None = None  # "rgb(r,g,b)" or "palette(n)" or None
    bg: str | None = None
    underline_color: str | None = None
    bold: bool = False
    italic: bool = False
    faint: bool = False
    underline: bool = False
    strikethrough: bool = False
    inverse: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Cell:
        return cls(
            char=data.get("char", " "),
            x=data.get("x", 0),
            y=data.get("y", 0),
            fg=data.get("fg"),
            bg=data.get("bg"),
            underline_color=data.get("underline_color"),
            bold=data.get("bold", False),
            italic=data.get("italic", False),
            faint=data.get("faint", False),
            underline=data.get("underline", False),
            strikethrough=data.get("strikethrough", False),
            inverse=data.get("inverse", False),
        )


@dataclass
class ScreenCells:
    """Screen content with structured cell data for TUI inspection."""

    cells: list[Cell]
    cursor_x: int
    cursor_y: int
    rows: int
    cols: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScreenCells:
        # Flatten rows array into cells list, adding y coordinate
        cells: list[Cell] = []
        for y, row_data in enumerate(data.get("rows", [])):
            for cell_data in row_data.get("cells", []):
                cell_data["y"] = y
                cells.append(Cell.from_dict(cell_data))

        # Extract cursor position from nested object
        cursor = data.get("cursor", {})
        cursor_x = cursor.get("x", 0)
        cursor_y = cursor.get("y", 0)

        # Extract dimensions from size object
        size = data.get("size", {})
        rows = size.get("rows", 24)
        cols = size.get("cols", 80)

        return cls(
            cells=cells,
            cursor_x=cursor_x,
            cursor_y=cursor_y,
            rows=rows,
            cols=cols,
        )

    def cell_at(self, x: int, y: int) -> Cell | None:
        """Get cell at position, or None if not found."""
        for cell in self.cells:
            if cell.x == x and cell.y == y:
                return cell
        return None

    def row(self, y: int) -> list[Cell]:
        """Get all cells in a row."""
        return [c for c in self.cells if c.y == y]

    def text_at_row(self, y: int) -> str:
        """Get text content of a row."""
        row_cells = sorted(self.row(y), key=lambda c: c.x)
        return "".join(c.char for c in row_cells)

    def styled_cells(self, **filters: Any) -> list[Cell]:
        """Find cells matching style filters.

        Example:
            >>> cells.styled_cells(bold=True)  # All bold cells
            >>> cells.styled_cells(fg="rgb(255,0,0)")  # Red foreground
        """
        result: list[Cell] = []
        for cell in self.cells:
            match = True
            for attr, value in filters.items():
                if getattr(cell, attr, None) != value:
                    match = False
                    break
            if match:
                result.append(cell)
        return result


# =============================================================================
# Utilities
# =============================================================================


def strip_ansi(text: str) -> str:
    """Strip ANSI escape sequences from text."""
    return ANSI_PATTERN.sub("", text)


def resolve_socket_path(socket_path: str | Path | None = None) -> Path:
    """Resolve the Ghostty socket path."""
    if socket_path:
        return Path(socket_path)

    uid = os.getuid()
    socket_name = "ghostty.sock"

    # Try XDG_RUNTIME_DIR first (Linux)
    if xdg_runtime := os.environ.get("XDG_RUNTIME_DIR"):
        return Path(xdg_runtime) / "ghostty" / socket_name

    # Try TMPDIR (macOS)
    if tmpdir := os.environ.get("TMPDIR"):
        return Path(tmpdir) / f"ghostty-{uid}" / socket_name

    # Fallback
    return Path(f"/tmp/ghostty-{uid}/{socket_name}")


def extract_surfaces(response: dict[str, Any]) -> list[Surface]:
    """Extract surfaces from a list_surfaces response."""
    surfaces: list[Surface] = []
    for window_data in response.get("data", {}).get("windows", []):
        window = Window.from_dict(window_data)
        for tab in window.tabs:
            surfaces.extend(tab.surfaces)
    return surfaces


def extract_windows(response: dict[str, Any]) -> list[Window]:
    """Extract windows from a list_surfaces response."""
    return [Window.from_dict(w) for w in response.get("data", {}).get("windows", [])]
