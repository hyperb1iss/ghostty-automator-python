"""Tests for protocol module."""

from __future__ import annotations

import os
from pathlib import Path

from ghostty_automator.protocol import (
    Screen,
    Surface,
    Tab,
    Window,
    extract_surfaces,
    extract_windows,
    resolve_socket_path,
)


class TestSurface:
    """Tests for Surface dataclass."""

    def test_from_dict_complete(self):
        data = {
            "id": "0x123",
            "title": "zsh",
            "pwd": "/home/user",
            "focused": True,
            "rows": 30,
            "cols": 100,
        }
        surface = Surface.from_dict(data)

        assert surface.id == "0x123"
        assert surface.title == "zsh"
        assert surface.pwd == "/home/user"
        assert surface.focused is True
        assert surface.rows == 30
        assert surface.cols == 100

    def test_from_dict_minimal(self):
        data = {"id": "0x456"}
        surface = Surface.from_dict(data)

        assert surface.id == "0x456"
        assert surface.title == ""
        assert surface.pwd == ""
        assert surface.focused is False
        assert surface.rows == 24
        assert surface.cols == 80


class TestTab:
    """Tests for Tab dataclass."""

    def test_from_dict_with_surfaces(self):
        data = {
            "surfaces": [
                {"id": "0x1"},
                {"id": "0x2"},
            ]
        }
        tab = Tab.from_dict(data)

        assert len(tab.surfaces) == 2
        assert tab.surfaces[0].id == "0x1"
        assert tab.surfaces[1].id == "0x2"

    def test_from_dict_empty(self):
        tab = Tab.from_dict({})
        assert tab.surfaces == []


class TestWindow:
    """Tests for Window dataclass."""

    def test_from_dict_with_tabs(self):
        data = {
            "tabs": [
                {"surfaces": [{"id": "0x1"}]},
                {"surfaces": [{"id": "0x2"}]},
            ]
        }
        window = Window.from_dict(data)

        assert len(window.tabs) == 2
        assert len(window.tabs[0].surfaces) == 1


class TestScreen:
    """Tests for Screen dataclass."""

    def test_lines(self):
        screen = Screen(
            text="line1\nline2\nline3",
            cursor_x=0,
            cursor_y=0,
        )
        assert screen.lines == ["line1", "line2", "line3"]

    def test_contains_true(self):
        screen = Screen(text="hello world", cursor_x=0, cursor_y=0)
        assert screen.contains("hello") is True
        assert screen.contains("world") is True

    def test_contains_false(self):
        screen = Screen(text="hello world", cursor_x=0, cursor_y=0)
        assert screen.contains("goodbye") is False


class TestResolveSocketPath:
    """Tests for socket path resolution."""

    def test_explicit_path(self):
        path = resolve_socket_path("/custom/path/ghostty.sock")
        assert path == Path("/custom/path/ghostty.sock")

    def test_xdg_runtime_dir(self, monkeypatch):
        monkeypatch.setenv("XDG_RUNTIME_DIR", "/run/user/1000")
        monkeypatch.delenv("TMPDIR", raising=False)

        path = resolve_socket_path()
        assert path == Path("/run/user/1000/ghostty/ghostty.sock")

    def test_tmpdir_macos(self, monkeypatch):
        monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
        monkeypatch.setenv("TMPDIR", "/var/folders/xx/yy")

        uid = os.getuid()
        path = resolve_socket_path()
        assert path == Path(f"/var/folders/xx/yy/ghostty-{uid}/ghostty.sock")


class TestExtractSurfaces:
    """Tests for extract_surfaces helper."""

    def test_extracts_all_surfaces(self):
        response = {
            "data": {
                "windows": [
                    {
                        "tabs": [
                            {"surfaces": [{"id": "0x1"}, {"id": "0x2"}]},
                            {"surfaces": [{"id": "0x3"}]},
                        ]
                    },
                    {
                        "tabs": [
                            {"surfaces": [{"id": "0x4"}]},
                        ]
                    },
                ]
            }
        }

        surfaces = extract_surfaces(response)
        assert len(surfaces) == 4
        assert [s.id for s in surfaces] == ["0x1", "0x2", "0x3", "0x4"]

    def test_empty_response(self):
        response = {"data": {"windows": []}}
        surfaces = extract_surfaces(response)
        assert surfaces == []


class TestExtractWindows:
    """Tests for extract_windows helper."""

    def test_extracts_windows(self):
        response = {
            "data": {
                "windows": [
                    {"tabs": [{"surfaces": [{"id": "0x1"}]}]},
                    {"tabs": [{"surfaces": [{"id": "0x2"}]}]},
                ]
            }
        }

        windows = extract_windows(response)
        assert len(windows) == 2
