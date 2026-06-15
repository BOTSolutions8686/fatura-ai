# Fatura AI — Agent Dashboard

A lightweight local web dashboard (Python stdlib only) that watches up to 4
agent log files and displays their last 80 lines in a live 2×2 grid.

## Run it

```bash
./tools/dashboard/start.sh
```

Or manually:

```bash
python3 tools/dashboard/server.py
open http://localhost:7070
```

## How agents write to the dashboard

Start each agent in its own terminal, piping output through `tee`:

```bash
# Terminal 1 — Aider
aider … 2>&1 | tee /tmp/fatura-agent-1.log

# Terminal 2 — Claude Code CLI
claude … 2>&1 | tee /tmp/fatura-agent-2.log

# Terminal 3 — OpenCode
opencode … 2>&1 | tee /tmp/fatura-agent-3.log

# Terminal 4 — orchestrator / bench
bench start 2>&1 | tee /tmp/fatura-agent-4.log
```

The dashboard checks for `/tmp/fatura-agent-{1..4}.log` every 2 seconds and
shows any that exist. Panels appear automatically; no restart needed.

## Panel labels (auto-detected from content)

| Keyword in output | Label       | Border colour |
|-------------------|-------------|---------------|
| `aider`           | Aider        | Blue          |
| `claude` / `❯`   | Claude Code  | Purple        |
| `opencode`        | OpenCode     | Green         |
| *(anything else)* | Orchestrator | Orange        |

## Requirements

- macOS or Linux  
- Python 3.6+  
- No pip installs — stdlib only
