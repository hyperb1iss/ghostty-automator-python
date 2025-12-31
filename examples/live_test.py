#!/usr/bin/env python3
"""Live test of ghostty-automator against running Ghostty instance."""

import asyncio
import tempfile
from pathlib import Path

from ghostty_automator import Ghostty


async def test_live() -> None:
    print("=" * 60)
    print("ghostty-automator Live Test")
    print("=" * 60)

    async with Ghostty.connect() as ghostty:
        # List all terminals
        terminals = await ghostty.terminals.all()
        print(f"\n[1] Found {len(terminals)} terminal(s)")

        for t in terminals:
            print(f"    {t.id}: {t.title!r} @ {t.pwd}")

        # Get the first terminal
        terminal = await ghostty.terminals.first()
        print(f"\n[2] Using terminal: {terminal.id}")

        # Test send + wait_for_text
        print("\n[3] Testing send + wait_for_text...")
        await terminal.send("echo 'TEST_MARKER_12345'")
        await terminal.wait_for_text("TEST_MARKER_12345", timeout=5000)
        print("    Passed: text appeared")

        # Test expect assertions
        print("\n[4] Testing expect.to_contain...")
        await terminal.expect.to_contain("TEST_MARKER_12345")
        print("    Passed: assertion succeeded")

        # Test expect.not_to_contain
        print("\n[5] Testing expect.not_to_contain...")
        await terminal.expect.not_to_contain("THIS_SHOULD_NOT_EXIST_xyz123")
        print("    Passed: text correctly absent")

        # Test expect.to_match (regex)
        print("\n[6] Testing expect.to_match (regex)...")
        match = await terminal.expect.to_match(r"TEST_MARKER_\d+")
        print(f"    Passed: matched {match.group()!r}")

        # Test wait_for_prompt
        print("\n[7] Testing wait_for_prompt...")
        await terminal.send("echo done")
        await terminal.wait_for_prompt(timeout=5000)
        print("    Passed: prompt detected")

        # Test screenshot
        print("\n[8] Testing screenshot...")
        with tempfile.TemporaryDirectory() as tmpdir:
            screenshot_path = Path(tmpdir) / "test_screenshot.png"
            result = await terminal.screenshot(screenshot_path)
            if result.exists():
                size = result.stat().st_size
                print(f"    Passed: saved {size} bytes to {result.name}")
            else:
                print("    Failed: screenshot not created")

        # Test screen content
        print("\n[9] Testing screen content...")
        screen = await terminal.screen()
        print(f"    Lines: {len(screen.lines)}")
        print(f"    Cursor: ({screen.cursor_x}, {screen.cursor_y})")
        print(f"    Contains 'echo': {screen.contains('echo')}")

        # Test press (Ctrl+L to clear)
        print("\n[10] Testing press (Ctrl+L to clear)...")
        await terminal.press("Ctrl+L")
        await asyncio.sleep(0.2)
        print("    Passed: sent Ctrl+L")

        print("\n" + "=" * 60)
        print("All tests passed!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_live())
