#!/usr/bin/env python3
"""
Fatura AI Agent Dashboard — http://localhost:7070
Reads Terminal.app windows via AppleScript and serves them to the browser.
"""
import json
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

PORT = 7070
HTML_FILE = Path(__file__).parent / "index.html"

APPLESCRIPT_WINDOW = """
tell application "Terminal"
    try
        set theContent to contents of tab 1 of window {win_index}
        set lineCount to count of paragraphs of theContent
        set startLine to lineCount - 79
        if startLine < 1 then set startLine to 1
        set lastLines to paragraphs startLine thru lineCount of theContent
        set lineText to ""
        repeat with ln in lastLines
            set lineText to lineText & ln & linefeed
        end repeat
        return lineText
    on error errMsg
        return "(error: " & errMsg & ")"
    end try
end tell
"""

APPLESCRIPT_COUNT = """
tell application "Terminal"
    return count of windows
end tell
"""


def get_window_count():
    try:
        result = subprocess.run(
            ["osascript", "-e", APPLESCRIPT_COUNT],
            capture_output=True, text=True, timeout=5
        )
        return int(result.stdout.strip())
    except Exception:
        return 0


def get_window_content(win_index):
    script = APPLESCRIPT_WINDOW.replace("{win_index}", str(win_index))
    try:
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True, text=True, timeout=8
        )
        return result.stdout if result.stdout else "(no content)"
    except subprocess.TimeoutExpired:
        return "(timeout reading window)"
    except Exception as e:
        return f"(error: {e})"


def detect_label(content):
    c = content.lower()
    if "aider" in c:
        return "Aider"
    if "opencode" in c or "open code" in c:
        return "OpenCode"
    if "claude" in c or "❯" in content:
        return "Claude Code"
    return "Orchestrator"


def read_terminals():
    count = min(get_window_count(), 9)
    windows = []
    for i in range(1, count + 1):
        content = get_window_content(i)
        windows.append({
            "window": i,
            "label": detect_label(content),
            "content": content,
        })
    return windows


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # suppress access logs

    def do_GET(self):
        if self.path == "/":
            self._serve_html()
        elif self.path == "/api/terminals":
            self._serve_terminals()
        else:
            self.send_error(404)

    def _serve_html(self):
        html = HTML_FILE.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.end_headers()
        self.wfile.write(html)

    def _serve_terminals(self):
        data = read_terminals()
        body = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    server = HTTPServer(("localhost", PORT), DashboardHandler)
    print(f"Fatura AI Agent Dashboard running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
