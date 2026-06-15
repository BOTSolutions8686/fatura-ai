# Fatura AI — Agent Dashboard

A lightweight local web dashboard that shows up to 4 Terminal.app windows in real-time.
No external dependencies — Python stdlib only.

## Run it

```bash
./tools/dashboard/start.sh
```

Or manually:

```bash
python3 tools/dashboard/server.py
open http://localhost:7070
```

## What it shows

- 2×2 grid of your Terminal.app windows (last 80 lines each)
- Auto-detected labels: **Aider** · **Claude Code** · **OpenCode** · **Orchestrator**
- Colored left border per agent type
- Auto-scrolls to bottom; polls every 2 seconds
- Status bar: last update time + window count

## Requirements

- macOS (uses AppleScript to read Terminal.app)
- Terminal.app must be running with your agent sessions open
- Python 3.6+
