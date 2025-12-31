#!/usr/bin/env python3
"""Fancy TUI testing with mouse automation.

Tests mouse interactions including clicks, scrolling, and dragging.
"""

import asyncio
import tempfile
from pathlib import Path

from ghostty_automator import Ghostty


async def test_mouse_basics() -> None:
    """Test basic mouse operations."""
    print("\n=== Mouse Basics Test ===")

    async with Ghostty.connect() as ghostty:
        terminal = await ghostty.terminals.first()

        print(f"[1] Terminal: {terminal.id} ({terminal.cols}x{terminal.rows})")

        # Test click
        print("[2] Testing click...")
        await terminal.click(100, 100)
        print("    Click sent!")

        # Test double-click
        print("[3] Testing double-click...")
        await terminal.double_click(150, 100)
        print("    Double-click sent!")

        # Test drag
        print("[4] Testing drag...")
        await terminal.drag(50, 100, 200, 100)
        print("    Drag complete!")

        print("    All mouse basics passed!")


async def test_vim_mouse() -> None:
    """Test mouse interactions with vim."""
    print("\n=== Vim Mouse Test ===")

    async with Ghostty.connect() as ghostty:
        terminal = await ghostty.terminals.first()

        # Create a temp file with content
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            for i in range(1, 21):
                f.write(f"Line {i}: This is test content for mouse automation\n")
            temp_file = f.name

        try:
            # Open vim with mouse support
            print("[1] Opening vim with mouse support...")
            await terminal.send(f"vim -c 'set mouse=a' {temp_file}")
            await asyncio.sleep(0.5)

            # Wait for vim to load
            await terminal.wait_for_text("Line 1", timeout=5000)
            print("    vim is running!")

            # Click on line 5 (rough estimate based on cell height)
            print("[2] Clicking on line 5...")
            cell_height = 16  # approximate
            await terminal.click(50, cell_height * 5)
            await asyncio.sleep(0.2)

            # Test drag to select text (visual mode)
            print("[3] Testing drag selection...")
            await terminal.drag(50, cell_height * 3, 200, cell_height * 3)
            await asyncio.sleep(0.3)

            # Take screenshot
            print("[4] Taking screenshot...")
            with tempfile.TemporaryDirectory() as tmpdir:
                screenshot = Path(tmpdir) / "vim_test.png"
                await terminal.screenshot(screenshot)
                print(f"    Screenshot: {screenshot.stat().st_size} bytes")

            # Quit vim
            print("[5] Quitting vim...")
            await terminal.press("Escape")
            await terminal.type(":q!")
            await terminal.press("Enter")
            await asyncio.sleep(0.3)

            await terminal.wait_for_prompt(timeout=3000)
            print("    vim test complete!")

        finally:
            Path(temp_file).unlink(missing_ok=True)


async def test_less_pager() -> None:
    """Test less pager with keyboard navigation."""
    print("\n=== Less Pager Test ===")

    async with Ghostty.connect() as ghostty:
        terminal = await ghostty.terminals.first()

        # Generate some content and pipe to less
        print("[1] Opening less with generated content...")
        await terminal.send("seq 1 100 | less")
        await asyncio.sleep(0.5)

        await terminal.wait_for_text("1", timeout=3000)
        print("    less is running!")

        # Navigate with keyboard
        print("[2] Navigating with keyboard (space to page down)...")
        await terminal.type(" ")  # Space to page down
        await asyncio.sleep(0.3)
        print("    Paged down!")

        # Take screenshot
        print("[3] Taking screenshot...")
        with tempfile.TemporaryDirectory() as tmpdir:
            screenshot = Path(tmpdir) / "less_test.png"
            await terminal.screenshot(screenshot)
            print(f"    Screenshot: {screenshot.stat().st_size} bytes")

        # Quit less
        print("[4] Quitting less...")
        await terminal.type("q")
        await asyncio.sleep(0.5)

        await terminal.wait_for_prompt(timeout=5000)
        print("    less test complete!")


async def test_htop_mouse() -> None:
    """Test mouse with htop (if installed)."""
    print("\n=== htop Mouse Test ===")

    async with Ghostty.connect() as ghostty:
        terminal = await ghostty.terminals.first()

        # Check if htop exists
        await terminal.send("command -v htop")
        await terminal.wait_for_prompt(timeout=2000)
        screen = await terminal.screen()

        if "htop" not in screen.plain_text:
            print("    htop not installed, skipping...")
            return

        print("[1] Launching htop...")
        await terminal.send("htop")
        await asyncio.sleep(1)

        await terminal.wait_for_text("CPU", timeout=5000)
        print("    htop is running!")

        # Click on a process row
        print("[2] Clicking on process list...")
        await terminal.click(200, 150)
        await asyncio.sleep(0.3)

        # Take screenshot
        print("[3] Taking screenshot...")
        with tempfile.TemporaryDirectory() as tmpdir:
            screenshot = Path(tmpdir) / "htop_test.png"
            await terminal.screenshot(screenshot)
            print(f"    Screenshot: {screenshot.stat().st_size} bytes")

        # Quit htop
        print("[4] Quitting htop...")
        await terminal.press("q")
        await asyncio.sleep(0.3)

        await terminal.wait_for_prompt(timeout=3000)
        print("    htop test complete!")


async def main() -> None:
    """Run all TUI tests."""
    print("=" * 60)
    print("Ghostty TUI Automation Tests")
    print("=" * 60)

    try:
        await test_mouse_basics()
        await test_vim_mouse()
        await test_less_pager()
        await test_htop_mouse()
    except Exception as e:
        print(f"\nTest failed: {e}")
        raise

    print("\n" + "=" * 60)
    print("All TUI tests completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
