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
    underline: int = 0  # 0=none, 1=single, 2=double, 3=curly, 4=dotted, 5=dashed
    strikethrough: bool = False
    inverse: bool = False


@dataclass
class Span:
    """A span of consecutive characters with the same style."""

    text: str
    x: int
    y: int
    fg: str | None = None
    bg: str | None = None
    bold: bool = False
    italic: bool = False
    faint: bool = False
    underline: int = 0
    strikethrough: bool = False
    inverse: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any], y: int) -> Span:
        """Parse span from JSON data."""
        # Parse fg color - can be palette index or [r,g,b] array
        fg = data.get("fg")
        if fg is not None:
            fg = _format_color(fg)

        # Parse bg color
        bg = data.get("bg")
        if bg is not None:
            bg = _format_color(bg)

        return cls(
            text=data.get("t", ""),
            x=data.get("x", 0),
            y=y,
            fg=fg,
            bg=bg,
            bold=bool(data.get("b", 0)),
            italic=bool(data.get("i", 0)),
            faint=bool(data.get("f", 0)),
            underline=data.get("u", 0),
            strikethrough=bool(data.get("s", 0)),
            inverse=bool(data.get("inv", 0)),
        )

    def to_cells(self) -> list[Cell]:
        """Expand span into individual cells."""
        cells: list[Cell] = []
        for i, char in enumerate(self.text):
            cells.append(
                Cell(
                    char=char,
                    x=self.x + i,
                    y=self.y,
                    fg=self.fg,
                    bg=self.bg,
                    bold=self.bold,
                    italic=self.italic,
                    faint=self.faint,
                    underline=self.underline,
                    strikethrough=self.strikethrough,
                    inverse=self.inverse,
                )
            )
        return cells


def _format_color(color: int | list[int]) -> str:
    """Format color as string from palette index or RGB array."""
    if isinstance(color, int):
        return f"palette({color})"
    # color must be a list at this point
    if len(color) == 3:
        return f"rgb({color[0]},{color[1]},{color[2]})"
    return str(color)


@dataclass
class ScreenCells:
    """Screen content with structured cell data for TUI inspection.

    The internal representation uses spans for efficiency, but cells can be
    accessed via the cells property for backward compatibility.
    """

    spans: list[Span]
    cursor_x: int
    cursor_y: int
    rows: int
    cols: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScreenCells:
        """Parse from span-based JSON format.

        Format: {
            "rows": [{"spans": [{"x": 0, "t": "text", ...}], "wrap": bool}],
            "cursor": {"x": 0, "y": 0},
            "size": {"rows": 24, "cols": 80}
        }
        """
        spans: list[Span] = []
        for y, row_data in enumerate(data.get("rows", [])):
            for span_data in row_data.get("spans", []):
                spans.append(Span.from_dict(span_data, y))

        # Extract cursor position from nested object
        cursor = data.get("cursor", {})
        cursor_x = cursor.get("x", 0)
        cursor_y = cursor.get("y", 0)

        # Extract dimensions from size object
        size = data.get("size", {})
        rows = size.get("rows", 24)
        cols = size.get("cols", 80)

        return cls(
            spans=spans,
            cursor_x=cursor_x,
            cursor_y=cursor_y,
            rows=rows,
            cols=cols,
        )

    @property
    def cells(self) -> list[Cell]:
        """Expand all spans into individual cells (backward compat)."""
        result: list[Cell] = []
        for span in self.spans:
            result.extend(span.to_cells())
        return result

    def spans_at_row(self, y: int) -> list[Span]:
        """Get all spans in a row."""
        return [s for s in self.spans if s.y == y]

    def cell_at(self, x: int, y: int) -> Cell | None:
        """Get cell at position, or None if not found."""
        for span in self.spans:
            if span.y != y:
                continue
            if span.x <= x < span.x + len(span.text):
                # Found the span containing this x position
                char_idx = x - span.x
                return Cell(
                    char=span.text[char_idx],
                    x=x,
                    y=y,
                    fg=span.fg,
                    bg=span.bg,
                    bold=span.bold,
                    italic=span.italic,
                    faint=span.faint,
                    underline=span.underline,
                    strikethrough=span.strikethrough,
                    inverse=span.inverse,
                )
        return None

    def row(self, y: int) -> list[Cell]:
        """Get all cells in a row."""
        cells: list[Cell] = []
        for span in self.spans:
            if span.y == y:
                cells.extend(span.to_cells())
        return sorted(cells, key=lambda c: c.x)

    def text_at_row(self, y: int) -> str:
        """Get text content of a row (efficient span-based)."""
        row_spans = sorted(self.spans_at_row(y), key=lambda s: s.x)
        return "".join(s.text for s in row_spans)

    def styled_spans(self, **filters: Any) -> list[Span]:
        """Find spans matching style filters.

        Example:
            >>> cells.styled_spans(bold=True)  # All bold spans
            >>> cells.styled_spans(fg="rgb(255,0,0)")  # Red foreground
        """
        result: list[Span] = []
        for span in self.spans:
            match = True
            for attr, value in filters.items():
                if getattr(span, attr, None) != value:
                    match = False
                    break
            if match:
                result.append(span)
        return result

    def styled_cells(self, **filters: Any) -> list[Cell]:
        """Find cells matching style filters.

        Example:
            >>> cells.styled_cells(bold=True)  # All bold cells
            >>> cells.styled_cells(fg="rgb(255,0,0)")  # Red foreground
        """
        result: list[Cell] = []
        for span in self.styled_spans(**filters):
            result.extend(span.to_cells())
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
