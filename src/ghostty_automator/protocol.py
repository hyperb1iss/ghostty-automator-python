"""Low-level IPC protocol types and utilities."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

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

    surfaces: list[Surface] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Tab:
        return cls(surfaces=[Surface.from_dict(s) for s in data.get("surfaces", [])])


@dataclass
class Window:
    """A window containing one or more tabs."""

    tabs: list[Tab] = field(default_factory=list)

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

    def contains(self, pattern: str) -> bool:
        """Check if screen contains the given text."""
        return pattern in self.text


# =============================================================================
# Utilities
# =============================================================================


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
