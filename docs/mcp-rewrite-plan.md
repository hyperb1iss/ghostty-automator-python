# Ghostty MCP Server Rewrite Plan

## Overview

Rewrite the MCP server to use `ghostty-automator-python` as the backend, eliminating duplicate client code and exposing the library's full capabilities.

**Location:** `/Users/bliss/dev/ghostty-automator-python/src/ghostty_mcp/`

## Architecture

```
ghostty-automator-python/
├── src/
│   ├── ghostty_automator/     # Library (existing)
│   │   ├── _async/
│   │   ├── _sync/
│   │   └── protocol.py
│   └── ghostty_mcp/           # MCP Server (new)
│       ├── __init__.py
│       └── server.py
├── pyproject.toml             # Add [project.scripts] entry
└── ...
```

## Tool Design

### Guiding Principles

1. **Minimal tool count** - Fewer tools = less LLM confusion
2. **Supertool pattern** - One tool with `action` parameter for related operations
3. **Full coverage** - Every library feature accessible
4. **Sensible defaults** - Common operations should be simple

### Tool Inventory (3 Tools)

| Tool | Purpose |
|------|---------|
| `list_terminals` | List all open terminal surfaces |
| `terminal` | All actions on a single terminal |
| `new_terminal` | Create new window or tab |

### `list_terminals` Tool

```python
@mcp.tool()
async def list_terminals() -> str:
    """List all open Ghostty terminal surfaces.

    Returns JSON array with id, title, pwd, rows, cols, focused for each terminal.
    Use terminal IDs with the `terminal` tool to interact with specific terminals.
    """
```

### `terminal` Tool (Supertool)

Single tool with `action` parameter. All actions require `terminal_id` except where noted.

#### Actions Reference

| Action | Description | Key Parameters |
|--------|-------------|----------------|
| **Input** |||
| `send` | Send command + Enter | `text` |
| `type` | Type text (no Enter) | `text`, `delay_ms?` |
| `key` | Press key combo | `key`, `mods?` |
| **Mouse** |||
| `click` | Click at position | `x`, `y`, `button?`, `mods?` |
| `double_click` | Double-click | `x`, `y`, `button?` |
| `drag` | Drag from→to | `from_x`, `from_y`, `to_x`, `to_y`, `steps?` |
| `scroll` | Scroll terminal | `delta_y`, `delta_x?`, `mods?` |
| **Screen** |||
| `read` | Get screen text | `screen_type?` → `{text, plain_text, cursor_x, cursor_y}` |
| `cells` | Get styled cell data | `screen_type?` → `{cells, cursor_x, cursor_y, rows, cols}` |
| `screenshot` | Capture as PNG | `output_path` → `{path}` |
| **Waiting** |||
| `wait_text` | Wait for text/regex | `pattern`, `regex?`, `timeout_ms?` |
| `wait_prompt` | Wait for shell prompt | `prompt_pattern?`, `timeout_ms?` |
| `wait_idle` | Wait for stability | `stable_ms?`, `timeout_ms?` |
| **Assertions** |||
| `expect` | Assert text present | `text`, `timeout_ms?` |
| `expect_not` | Assert text absent | `text`, `timeout_ms?` |
| **Management** |||
| `focus` | Bring to front | - |
| `close` | Close terminal | - |
| `resize` | Change dimensions | `rows?`, `cols?` |

### `new_terminal` Tool

```python
@mcp.tool()
async def new_terminal(
    type: Literal["window", "tab"] = "window",
    command: list[str] | None = None,
) -> str:
    """Create a new Ghostty window or tab.

    Args:
        type: "window" for new window, "tab" for new tab in current window
        command: Optional command to run in the new terminal

    Returns:
        JSON with terminal_id of the new terminal
    """
```

### Total: 3 tools (with 18 actions in terminal supertool)

## Tool Specifications

### 1. `list_terminals`

```python
@mcp.tool()
async def list_terminals() -> str:
    """List all open Ghostty terminal surfaces.

    Returns JSON array of terminals with id, title, pwd, rows, cols, focused.
    Use the terminal IDs with other tools to interact with specific terminals.
    """
```

### 2. `get_terminal`

```python
@mcp.tool()
async def get_terminal(
    id: str | None = None,
    title: str | None = None,
    pwd: str | None = None,
    focused: bool = False,
) -> str:
    """Get a specific terminal by ID, title substring, pwd substring, or focused state.

    Provide exactly one of: id, title, pwd, or focused=True.
    Returns terminal info or error if not found.
    """
```

### 3. `send_command`

```python
@mcp.tool()
async def send_command(terminal_id: str, command: str) -> str:
    """Send a command to a terminal (appends Enter).

    Use this for running shell commands. The command is sent followed by
    a carriage return to execute it.

    Args:
        terminal_id: Target terminal surface ID
        command: The command to execute
    """
```

### 4. `type_text`

```python
@mcp.tool()
async def type_text(
    terminal_id: str,
    text: str,
    delay_ms: int = 0,
) -> str:
    """Type text into a terminal without pressing Enter.

    Use this for typing into prompts, search boxes, or when you don't
    want to execute a command yet.

    Args:
        terminal_id: Target terminal surface ID
        text: Text to type
        delay_ms: Delay between keystrokes in milliseconds (0 = instant)
    """
```

### 5. `press_key`

```python
@mcp.tool()
async def press_key(
    terminal_id: str,
    key: str,
    mods: str | None = None,
) -> str:
    """Press a key or key combination.

    Supports W3C key codes: Enter, Tab, Escape, Backspace, Delete, Space,
    ArrowUp/Down/Left/Right (or Up/Down/Left/Right), F1-F12, Home, End,
    PageUp, PageDown, Insert, KeyA-KeyZ, Digit0-Digit9.

    Args:
        terminal_id: Target terminal surface ID
        key: Key to press (e.g., "Enter", "Tab", "Escape", "KeyC")
             Also supports "Ctrl+C" syntax for convenience
        mods: Comma-separated modifiers: "ctrl", "shift", "alt", "super"

    Examples:
        press_key(id, "Enter")           # Press Enter
        press_key(id, "KeyC", "ctrl")    # Ctrl+C
        press_key(id, "Ctrl+C")          # Same as above
        press_key(id, "Tab")             # Tab completion
        press_key(id, "Escape")          # Exit mode in vim/etc
    """
```

### 6. `click`

```python
@mcp.tool()
async def click(
    terminal_id: str,
    x: float,
    y: float,
    button: str = "left",
    mods: str | None = None,
) -> str:
    """Click at a pixel position in the terminal.

    Args:
        terminal_id: Target terminal surface ID
        x: X pixel position
        y: Y pixel position
        button: "left", "right", or "middle"
        mods: Comma-separated modifiers: "ctrl", "shift", "alt", "super"
    """
```

### 7. `double_click`

```python
@mcp.tool()
async def double_click(
    terminal_id: str,
    x: float,
    y: float,
    button: str = "left",
) -> str:
    """Double-click at a pixel position (e.g., to select a word).

    Args:
        terminal_id: Target terminal surface ID
        x: X pixel position
        y: Y pixel position
        button: "left", "right", or "middle"
    """
```

### 8. `drag`

```python
@mcp.tool()
async def drag(
    terminal_id: str,
    from_x: float,
    from_y: float,
    to_x: float,
    to_y: float,
    button: str = "left",
    steps: int = 10,
) -> str:
    """Drag from one position to another (e.g., to select text).

    Args:
        terminal_id: Target terminal surface ID
        from_x, from_y: Starting pixel position
        to_x, to_y: Ending pixel position
        button: Mouse button to hold during drag
        steps: Number of intermediate positions for smooth motion
    """
```

### 9. `scroll`

```python
@mcp.tool()
async def scroll(
    terminal_id: str,
    delta_y: float = 0.0,
    delta_x: float = 0.0,
    mods: str | None = None,
) -> str:
    """Scroll the terminal.

    Args:
        terminal_id: Target terminal surface ID
        delta_y: Vertical scroll (positive = down, negative = up)
        delta_x: Horizontal scroll (positive = right, negative = left)
        mods: Comma-separated modifiers
    """
```

### 10. `read_screen`

```python
@mcp.tool()
async def read_screen(
    terminal_id: str,
    screen_type: str = "viewport",
) -> str:
    """Read the terminal screen content.

    Args:
        terminal_id: Target terminal surface ID
        screen_type: "viewport" for visible content, "screen" for full scrollback

    Returns:
        JSON with text, plain_text (ANSI stripped), cursor_x, cursor_y
    """
```

### 11. `read_cells`

```python
@mcp.tool()
async def read_cells(
    terminal_id: str,
    screen_type: str = "viewport",
) -> str:
    """Read terminal screen with styled cell data.

    Returns detailed cell information including character, position,
    colors (fg, bg), and style flags (bold, italic, underline, etc.).
    Useful for TUI automation and visual inspection.

    Args:
        terminal_id: Target terminal surface ID
        screen_type: "viewport" for visible content, "screen" for full scrollback

    Returns:
        JSON with cells array, cursor position, and dimensions
    """
```

### 12. `screenshot`

```python
@mcp.tool()
async def screenshot(
    terminal_id: str,
    output_path: str,
) -> str:
    """Capture terminal as PNG image.

    Args:
        terminal_id: Target terminal surface ID
        output_path: Path to save the PNG file

    Returns:
        JSON with resolved absolute path to saved file
    """
```

### 13. `wait_for_text`

```python
@mcp.tool()
async def wait_for_text(
    terminal_id: str,
    pattern: str,
    regex: bool = False,
    timeout_ms: int = 30000,
) -> str:
    """Wait for text or regex pattern to appear on screen.

    Polls the screen every 100ms until the pattern is found or timeout.
    Essential for waiting for command output before proceeding.

    Args:
        terminal_id: Target terminal surface ID
        pattern: Text or regex pattern to wait for
        regex: If True, treat pattern as regular expression
        timeout_ms: Maximum wait time in milliseconds

    Returns:
        JSON with ok=true on success, or error on timeout
    """
```

### 14. `wait_for_prompt`

```python
@mcp.tool()
async def wait_for_prompt(
    terminal_id: str,
    prompt_pattern: str = r"[$#>%➤❯λ»›]\s*",
    timeout_ms: int = 30000,
) -> str:
    """Wait for shell prompt to appear.

    Useful after running commands to ensure the shell is ready
    for the next command.

    Args:
        terminal_id: Target terminal surface ID
        prompt_pattern: Regex pattern for prompt (default matches common prompts)
        timeout_ms: Maximum wait time in milliseconds
    """
```

### 15. `wait_for_idle`

```python
@mcp.tool()
async def wait_for_idle(
    terminal_id: str,
    stable_ms: int = 500,
    timeout_ms: int = 30000,
) -> str:
    """Wait for screen content to stabilize.

    Waits until screen content remains unchanged for stable_ms milliseconds.
    Useful for waiting for animations or streaming output to complete.

    Args:
        terminal_id: Target terminal surface ID
        stable_ms: How long content must be stable to consider idle
        timeout_ms: Maximum total wait time
    """
```

### 16. `expect_text`

```python
@mcp.tool()
async def expect_text(
    terminal_id: str,
    text: str,
    timeout_ms: int = 30000,
) -> str:
    """Assert that text is present on screen.

    Waits up to timeout for text to appear, then asserts.
    Returns success or raises assertion error with screen content.

    Args:
        terminal_id: Target terminal surface ID
        text: Text that must be present
        timeout_ms: Maximum wait time
    """
```

### 17. `expect_no_text`

```python
@mcp.tool()
async def expect_no_text(
    terminal_id: str,
    text: str,
    timeout_ms: int = 1000,
) -> str:
    """Assert that text is NOT present on screen.

    Checks periodically for the duration of timeout to ensure
    text never appears.

    Args:
        terminal_id: Target terminal surface ID
        text: Text that must NOT be present
        timeout_ms: How long to check for absence
    """
```

### 18-19. Window Management

```python
@mcp.tool()
async def new_window(command: list[str] | None = None) -> str:
    """Open a new Ghostty window.

    Args:
        command: Optional command to run in the new window

    Returns:
        JSON with terminal_id of the new window
    """

@mcp.tool()
async def new_tab(command: list[str] | None = None) -> str:
    """Open a new tab in the current Ghostty window.

    Args:
        command: Optional command to run in the new tab

    Returns:
        JSON with terminal_id of the new tab
    """

@mcp.tool()
async def focus_terminal(terminal_id: str) -> str:
    """Bring a terminal window to the front."""

@mcp.tool()
async def close_terminal(terminal_id: str) -> str:
    """Close a terminal."""

@mcp.tool()
async def resize_terminal(
    terminal_id: str,
    rows: int | None = None,
    cols: int | None = None,
) -> str:
    """Resize a terminal.

    Args:
        terminal_id: Target terminal surface ID
        rows: New row count (None to keep current)
        cols: New column count (None to keep current)
    """
```

## Implementation Plan

### Phase 1: Setup
1. Create `src/ghostty_mcp/` directory structure
2. Add MCP dependencies to pyproject.toml (`fastmcp>=2.14`)
3. Add entry point: `ghostty-mcp = "ghostty_mcp.server:main"`

### Phase 2: Core Server
1. Create `server.py` with FastMCP setup
2. Implement connection management (shared `Ghostty` client)
3. Add server instructions/documentation

### Phase 3: Implement Tools (in order of importance)
1. Discovery: `list_terminals`, `get_terminal`
2. Input: `send_command`, `type_text`, `press_key`
3. Reading: `read_screen`, `read_cells`, `screenshot`
4. Waiting: `wait_for_text`, `wait_for_prompt`, `wait_for_idle`
5. Mouse: `click`, `double_click`, `drag`, `scroll`
6. Assertions: `expect_text`, `expect_no_text`
7. Window: `new_window`, `new_tab`, `focus_terminal`, `close_terminal`, `resize_terminal`

### Phase 4: Testing & Polish
1. Manual testing with Claude Code
2. Update SKILL.md documentation
3. Remove old ghostty-mcp from Ghostty repo (or deprecate)

## Migration Notes

### Breaking Changes
- Tool names changed (e.g., `terminal(action="read")` → `read_screen()`)
- Response format standardized
- Old MCP server location deprecated

### Compatibility
- Keep FastMCP for consistency
- Same socket path resolution
- Same timeout defaults

## Open Questions

1. Should we keep a monolithic `terminal()` tool for backwards compat?
2. Should `get_terminal` auto-select first terminal if only one exists?
3. Should we add a `run_and_wait()` convenience tool?
4. Resource support? (e.g., expose terminal list as MCP resource)
