# Ghostty Automator

**Playwright for Terminals** - A Python library for automating Ghostty terminal emulator.

## Installation

```bash
pip install ghostty-automator
```

## Quick Start

### Async API (Recommended)

```python
from ghostty_automator import Ghostty

async with Ghostty.connect() as ghostty:
    # Get the first terminal
    terminal = await ghostty.terminals.first()

    # Send commands
    await terminal.send("ls -la")

    # Wait for output
    await terminal.wait_for_text("package.json")

    # Assertions
    await terminal.expect.to_contain("src/")

    # Screenshots
    await terminal.screenshot("debug.png")
```

### Sync API

```python
from ghostty_automator.sync_api import Ghostty

with Ghostty.connect() as ghostty:
    terminal = ghostty.terminals.first()
    terminal.send("echo hello")
    terminal.wait_for_text("hello")
```

## Features

- **Playwright-style API** - Familiar, ergonomic interface
- **Async-first** - Built on anyio for high performance
- **Strong typing** - Full type hints for IDE support
- **Auto-waiting** - Built-in wait helpers with configurable timeouts
- **Assertions** - Playwright-style `expect` assertions
- **Screenshots** - Capture terminal state as images

## Requirements

- Python 3.11+
- Ghostty terminal with IPC socket enabled

## License

Apache-2.0
