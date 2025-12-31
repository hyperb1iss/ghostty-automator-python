<h1 align="center">
  <br>
  🎭 ghostty-automator
  <br>
</h1>

<p align="center">
  <strong>Playwright for Terminals</strong>
</p>

<p align="center">
  <a href="https://github.com/hyperb1iss/ghostty-automator-python/actions/workflows/ci.yml">
    <img src="https://img.shields.io/github/actions/workflow/status/hyperb1iss/ghostty-automator-python/ci.yml?branch=main&style=for-the-badge&logo=github&logoColor=white&label=CI" alt="CI Status">
  </a>
  <a href="https://github.com/hyperb1iss/ghostty-automator-python/blob/main/LICENSE">
    <img src="https://img.shields.io/github/license/hyperb1iss/ghostty-automator-python?style=for-the-badge" alt="License">
  </a>
</p>

<p align="center">
  <a href="https://pypi.org/project/ghostty-automator">
    <img src="https://img.shields.io/pypi/v/ghostty-automator?style=for-the-badge&logo=pypi&logoColor=white" alt="PyPI">
  </a>
  <a href="https://pypi.org/project/ghostty-automator">
    <img src="https://img.shields.io/pypi/pyversions/ghostty-automator?style=for-the-badge&logo=python&logoColor=white" alt="Python Version">
  </a>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-requirements">Requirements</a> •
  <a href="#-installation">Installation</a> •
  <a href="#-usage">Usage</a> •
  <a href="#-api-reference">API Reference</a>
</p>

---

> **⚠️ Important:** This library requires [ghostty-automator](https://github.com/hyperb1iss/ghostty-automator), a fork of Ghostty with IPC automation support. **Stock Ghostty does not include the automation protocol.** Install from the [hyperb1iss/homebrew-tap](https://github.com/hyperb1iss/homebrew-bliss) for easy setup.

## ✨ Features

- **Playwright-style API** — Familiar, ergonomic interface for terminal automation
- **Async-first** — Built on anyio for high performance with sync wrapper available
- **Strong typing** — Full type hints with strict pyright compliance
- **Auto-waiting** — Built-in wait helpers with configurable timeouts
- **Assertions** — Playwright-style `expect` assertions for testing
- **Screenshots** — Capture terminal state as PNG images

## 📋 Requirements

- Python 3.11+
- [ghostty-automator](https://github.com/hyperb1iss/ghostty-automator) (the Ghostty fork with IPC support)

```bash
# Install the Ghostty fork via Homebrew
brew tap hyperb1iss/bliss
brew install ghostty-automator
```

## 📦 Installation

```bash
pip install ghostty-automator
```

Or with uv:

```bash
uv add ghostty-automator
```

## 🚀 Usage

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

If you get a connection error about “insecure permissions”, either fix the socket permissions or connect with:

```python
async with Ghostty.connect(validate_socket=False) as ghostty:
    ...
```

### Sync API

```python
from ghostty_automator.sync_api import Ghostty

with Ghostty.connect() as ghostty:
    terminal = ghostty.terminals.first()
    terminal.send("echo hello")
    terminal.wait_for_text("hello")
```

### Chaining

```python
await terminal.send("npm test")
await terminal.wait_for_text("PASS", timeout=30_000)
await terminal.screenshot("tests-passed.png")
```

## 📖 API Reference

### Ghostty

| Method                              | Description                   |
| ----------------------------------- | ----------------------------- |
| `Ghostty.connect()`                 | Create a connected client     |
| `ghostty.terminals.all()`           | Get all terminals             |
| `ghostty.terminals.first()`         | Get the first terminal        |
| `ghostty.terminals.focused()`       | Get the focused terminal      |
| `ghostty.terminals.by_title(title)` | Find by title (partial match) |
| `ghostty.terminals.by_pwd(path)`    | Find by working directory     |
| `ghostty.new_window(command?)`      | Open a new window             |
| `ghostty.new_tab(command?)`         | Open a new tab                |

### Terminal

| Method                               | Description                            |
| ------------------------------------ | -------------------------------------- |
| `terminal.send(text)`                | Send text + Enter                      |
| `terminal.type(text, delay_ms?)`     | Type character by character            |
| `terminal.press(key)`                | Press a key (Enter, Tab, Ctrl+C, etc.) |
| `terminal.screen()`                  | Get current screen content             |
| `terminal.wait_for_text(pattern)`    | Wait for text to appear                |
| `terminal.wait_for_prompt()`         | Wait for shell prompt                  |
| `terminal.wait_for_idle(stable_ms?)` | Wait for screen to stabilize           |
| `terminal.screenshot(path)`          | Capture as PNG                         |
| `terminal.focus()`                   | Bring window to front                  |
| `terminal.close()`                   | Close the terminal                     |
| `terminal.resize(rows?, cols?)`      | Resize the terminal                    |

### Expect Assertions

| Method                                 | Description              |
| -------------------------------------- | ------------------------ |
| `terminal.expect.to_contain(text)`     | Assert text is present   |
| `terminal.expect.not_to_contain(text)` | Assert text is absent    |
| `terminal.expect.to_match(pattern)`    | Assert regex matches     |
| `terminal.expect.to_have_title(title)` | Assert window title      |
| `terminal.expect.to_have_pwd(path)`    | Assert working directory |
| `terminal.expect.prompt()`             | Assert prompt is visible |

## 🔧 Development

```bash
# Clone and install
git clone https://github.com/hyperb1iss/ghostty-automator-python
cd ghostty-automator-python
uv sync

# Run checks
uv run pytest
uv run pyright src/
uv run ruff check src/
```

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<p align="center">
  Created by <a href="https://hyperbliss.tech">Stefanie Jane</a>
</p>

<p align="center">
  <a href="https://github.com/hyperb1iss">
    <img src="https://img.shields.io/badge/GitHub-hyperb1iss-181717?style=for-the-badge&logo=github" alt="GitHub">
  </a>
  <a href="https://bsky.app/profile/hyperbliss.tech">
    <img src="https://img.shields.io/badge/Bluesky-@hyperbliss.tech-1185fe?style=for-the-badge&logo=bluesky" alt="Bluesky">
  </a>
</p>
