# ChatGPT Game Device Control (ADB)

This example creates an `AgentScope` ReAct agent that can interact with games on already logged-in Android devices.

## What it can do

- discover connected devices (`adb devices -l`)
- open a game package
- tap/swipe on screen coordinates
- send key events and text
- capture screenshots for visual checks

> Safety: the game account/session should already be logged in on device. The agent only automates inputs and does not bypass authentication.

## Requirements

- Android SDK platform tools (`adb`) in your `PATH`
- one or more Android devices connected with USB debugging enabled
- `OPENAI_API_KEY` exported

## Run

```bash
cd examples/functionality/game_device_control
python main.py
```

Then chat with the agent, for example:

- "List my connected devices."
- "Use device `emulator-5554`, open `com.supercell.clashofclans`."
- "Tap 540 1600."
- "Take a screenshot."

## Notes

- Coordinates depend on each screen resolution.
- For production use, add stronger action guards and allowlists for package names.
