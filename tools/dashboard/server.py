#!/usr/bin/env python3
"""
Fatura AI Agent Dashboard — http://localhost:7070

Reads /tmp/fatura-agent-{1..4}.log (last 80 lines each).
Start agents with:  <command> 2>&1 | tee /tmp/fatura-agent-1.log
"""
import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PORT = 7070
HTML_FILE = Path(__file__).parent / "index.html"
LOG_DIR = Path("/tmp")
LOG_PREFIX = "fatura-agent-"
MAX_WINDOWS = 4
TAIL_LINES = 80

AGENT_LABELS = {
    "1": "Agent 1",
    "2": "Agent 2",
    "3": "Agent 3",
    "4": "Agent 4",
}

# --- AppleScript fallback (macOS only) ---

APPLESCRIPT_COUNT = """
tell application "Terminal"
    return count of windows
end tell
"""

APPLESCRIPT_WINDOW = """
tell application "Terminal"
    try
        set w to window {idx}
        set theContent to history of w
        if theContent is "" then
            set theContent to "(empty)"
        end if
        set lineList to paragraphs of theContent
        set lineCount to count of lineList
        set startLine to lineCount - 79
        if startLine < 1 then set startLine to 1
        set resultText to ""
        repeat with i from startLine to lineCount
            set resultText to resultText & item i of lineList & linefeed
        end repeat
        return resultText
    on error e
        return "(unavailable: " & e & ")"
    end try
end tell
"""


def _run_script(script, timeout=6):
    try:
        r = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=timeout
        )
        return r.stdout.strip()
    except Exception:
        return ""


def detect_label(content: str) -> str:
    c = content.lower()
    if "aider" in c:
        return "Aider"
    if "opencode" in c or "open-code" in c:
        return "OpenCode"
    if "claude" in c or "❯" in content:
        return "Claude Code"
    return "Orchestrator"


# --- Log file source (primary) ---

def tail_file(path: Path, n: int = TAIL_LINES) -> str:
    """Return the last n lines of a file, or empty string if unreadable."""
    try:
        size = os.path.getsize(path)
        if size == 0:
            return ""
        with open(path, "rb") as f:
            # Read up to 4 KB per line * n lines from the end
            chunk = min(size, n * 200)
            f.seek(-chunk, 2)
            raw = f.read().decode("utf-8", errors="replace")
        lines = raw.splitlines()
        return "\n".join(lines[-n:])
    except Exception:
        return ""


def read_log_files() -> list:
    results = []
    for i in range(1, MAX_WINDOWS + 1):
        path = LOG_DIR / f"{LOG_PREFIX}{i}.log"
        if path.exists():
            content = tail_file(path) or "(log file is empty)"
            results.append({
                "window": i,
                "source": "log",
                "label": detect_label(content),
                "content": content,
                "path": str(path),
            })
    return results


# --- AppleScript source (fallback when no log files) ---

def read_applescript() -> list:
    raw_count = _run_script(APPLESCRIPT_COUNT)
    try:
        count = min(int(raw_count), MAX_WINDOWS)
    except ValueError:
        return []

    results = []
    for i in range(1, count + 1):
        script = APPLESCRIPT_WINDOW.replace("{idx}", str(i))
        content = _run_script(script)
        if content and not content.startswith("(unavailable"):
            results.append({
                "window": i,
                "source": "applescript",
                "label": detect_label(content),
                "content": content,
                "path": None,
            })
    return results


def read_terminals() -> list:
    logs = read_log_files()
    if logs:
        return logs
    # Fall back to AppleScript if no log files found
    return read_applescript()


# --- HTTP server ---

class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress noisy access logs

    def do_GET(self):
        if self.path == "/":
            self._serve_file(HTML_FILE, "text/html; charset=utf-8")
        elif self.path == "/api/terminals":
            self._serve_json(read_terminals())
        else:
            self.send_error(404)

    def _serve_file(self, path: Path, mime: str):
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _serve_json(self, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("localhost", PORT), DashboardHandler)
    print(f"Fatura AI Agent Dashboard → http://localhost:{PORT}")
    print(f"Watching: {LOG_DIR}/{LOG_PREFIX}{{1..{MAX_WINDOWS}}}.log")
    print("Press Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
