"""Pytest fixtures for ghostty_automator tests."""

from __future__ import annotations

import json
import struct
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.fixture
def mock_socket_path(tmp_path):
    """Create a temporary socket path."""
    return tmp_path / "ghostty.sock"


@pytest.fixture
def mock_surface_data() -> dict[str, Any]:
    """Sample surface data from IPC."""
    return {
        "id": "0x123456",
        "title": "zsh",
        "pwd": "/home/user",
        "focused": True,
        "rows": 24,
        "cols": 80,
    }


@pytest.fixture
def mock_list_surfaces_response(mock_surface_data) -> dict[str, Any]:
    """Sample list_surfaces response."""
    return {
        "ok": True,
        "data": {
            "windows": [
                {
                    "tabs": [
                        {
                            "surfaces": [mock_surface_data]
                        }
                    ]
                }
            ]
        },
    }


@pytest.fixture
def mock_screen_response() -> dict[str, Any]:
    """Sample get_screen response."""
    return {
        "ok": True,
        "data": {
            "content": "user@host:~$ ls\nfile1.txt  file2.txt\nuser@host:~$ ",
            "cursor_x": 13,
            "cursor_y": 2,
        },
    }


class MockStream:
    """Mock async stream for testing IPC."""

    def __init__(self, responses: list[dict[str, Any]]):
        self.responses = responses
        self.response_index = 0
        self.sent_data: list[bytes] = []

    async def send(self, data: bytes) -> None:
        self.sent_data.append(data)

    async def receive(self, n: int) -> bytes:
        if self.response_index >= len(self.responses):
            return b""

        response = self.responses[self.response_index]
        self.response_index += 1

        data = json.dumps(response).encode("utf-8")

        # If requesting length prefix
        if n == 4:
            return struct.pack("<I", len(data))

        return data

    async def aclose(self) -> None:
        pass


@pytest.fixture
def mock_stream_factory():
    """Factory for creating mock streams with responses."""

    def factory(*responses: dict[str, Any]) -> MockStream:
        return MockStream(list(responses))

    return factory
