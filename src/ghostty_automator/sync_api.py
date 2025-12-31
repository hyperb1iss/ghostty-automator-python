"""Synchronous API for Ghostty Automator.

Import from here for sync usage:
    >>> from ghostty_automator.sync_api import Ghostty
    >>>
    >>> with Ghostty.connect() as ghostty:
    ...     terminal = ghostty.terminals.first()
    ...     terminal.send("echo hello")
"""

from ghostty_automator._sync.api import Ghostty, Terminal, TerminalExpect, Terminals

__all__ = ["Ghostty", "Terminal", "TerminalExpect", "Terminals"]
