# -*- coding: utf-8 -*-
"""Control games on logged-in Android devices with a ChatGPT-powered agent.

This example uses ADB as the bridge between the agent and one or more
connected devices. The game account/session must already be logged in on the
phone/tablet.
"""

from __future__ import annotations

import asyncio
import os
import shlex
import subprocess
from pathlib import Path

from agentscope.agent import ReActAgent, UserAgent
from agentscope.formatter import OpenAIChatFormatter
from agentscope.memory import InMemoryMemory
from agentscope.model import OpenAIChatModel
from agentscope.tool import Toolkit

ADB_TIMEOUT = 20
SCREENSHOT_DIR = Path("./tmp/game_screens")


def _run_adb(args: list[str], device_id: str | None = None) -> str:
    """Run an adb command and return stdout.

    Args:
        args: Raw command arguments after ``adb``.
        device_id: Optional device serial from ``adb devices``.

    Returns:
        The command stdout as string.
    """
    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(args)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=ADB_TIMEOUT,
        check=False,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip() or "unknown adb error"
        return f"Error: {stderr}"
    return result.stdout.strip() or "OK"


def list_connected_devices() -> str:
    """List connected Android devices and their status."""
    return _run_adb(["devices", "-l"])


def launch_game(package_name: str, device_id: str | None = None) -> str:
    """Launch a game app by package name.

    Args:
        package_name: Android package name, e.g. ``com.supercell.clashofclans``.
        device_id: Optional target device serial.
    """
    package_name = package_name.strip()
    if not package_name:
        return "Error: package_name is required."

    return _run_adb(
        [
            "shell",
            "monkey",
            "-p",
            package_name,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ],
        device_id=device_id,
    )


def tap(x: int, y: int, device_id: str | None = None) -> str:
    """Tap one coordinate on a device screen."""
    return _run_adb(["shell", "input", "tap", str(x), str(y)], device_id)


def swipe(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    duration_ms: int = 300,
    device_id: str | None = None,
) -> str:
    """Swipe on device screen coordinates."""
    return _run_adb(
        [
            "shell",
            "input",
            "swipe",
            str(start_x),
            str(start_y),
            str(end_x),
            str(end_y),
            str(max(duration_ms, 0)),
        ],
        device_id,
    )


def send_text(text: str, device_id: str | None = None) -> str:
    """Send text to the currently focused input field on device."""
    if not text:
        return "Error: text cannot be empty."

    encoded = shlex.quote(text).replace(" ", "%s")
    return _run_adb(["shell", "input", "text", encoded], device_id)


def press_keyevent(keycode: int, device_id: str | None = None) -> str:
    """Send Android keyevent to device.

    Example keycodes:
    - 3: HOME
    - 4: BACK
    - 66: ENTER
    """
    return _run_adb(["shell", "input", "keyevent", str(keycode)], device_id)


def capture_screen(device_id: str | None = None) -> str:
    """Capture a screenshot from device and save to local filesystem."""
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
    target = SCREENSHOT_DIR / f"screen_{device_id or 'default'}.png"

    cmd = ["adb"]
    if device_id:
        cmd.extend(["-s", device_id])
    cmd.extend(["exec-out", "screencap", "-p"])

    result = subprocess.run(
        cmd,
        capture_output=True,
        timeout=ADB_TIMEOUT,
        check=False,
    )
    if result.returncode != 0:
        err = (result.stderr or b"").decode("utf-8", errors="ignore").strip()
        return f"Error: {err or 'failed to capture screen'}"

    target.write_bytes(result.stdout)
    return f"Saved screenshot: {target.resolve()}"


async def main() -> None:
    """Run an interactive game-control session with a ChatGPT model."""
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("Please set OPENAI_API_KEY before running.")

    toolkit = Toolkit()
    toolkit.register_tool_function(list_connected_devices)
    toolkit.register_tool_function(launch_game)
    toolkit.register_tool_function(tap)
    toolkit.register_tool_function(swipe)
    toolkit.register_tool_function(send_text)
    toolkit.register_tool_function(press_keyevent)
    toolkit.register_tool_function(capture_screen)

    agent = ReActAgent(
        name="GamePilot",
        sys_prompt=(
            "You control logged-in mobile games through ADB tools. "
            "Always begin by calling list_connected_devices, then ask the user "
            "which device and game to control before taking actions. "
            "Never run more than one direct action per turn without user "
            "confirmation."
        ),
        model=OpenAIChatModel(
            model_name="gpt-4.1",
            api_key=os.environ.get("OPENAI_API_KEY"),
            stream=True,
        ),
        formatter=OpenAIChatFormatter(),
        toolkit=toolkit,
        memory=InMemoryMemory(),
    )

    user = UserAgent("User")
    msg = None

    print("Type 'exit' to stop.")
    while True:
        msg = await user(msg)
        if msg.get_text_content().strip().lower() == "exit":
            break
        msg = await agent(msg)


if __name__ == "__main__":
    asyncio.run(main())
