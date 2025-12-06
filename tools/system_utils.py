import os
import subprocess
import ctypes
from pathlib import Path
from typing import List
from langchain.tools import tool


def _run_powershell(command: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


@tool
def toggle_system_mute(_: str = "") -> str:
    """Toggle the system mute state."""
    try:
        VK_VOLUME_MUTE = 0xAD
        KEYEVENTF_EXTENDEDKEY = 0x1
        KEYEVENTF_KEYUP = 0x2
        ctypes.windll.user32.keybd_event(VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY, 0)
        ctypes.windll.user32.keybd_event(
            VK_VOLUME_MUTE, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0
        )
        return "Toggled system mute."
    except Exception as e:
        return f"Error toggling mute: {e}"


@tool
def open_app(app_name: str) -> str:
    """Open a common app by name (e.g., notepad, calculator, chrome, edge, explorer, cmd, powershell)."""
    name = app_name.strip().lower()
    pf = os.environ.get("ProgramFiles", r"C:\Program Files")
    pf86 = os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")
    app_map = {
        "notepad": r"C:\Windows\system32\notepad.exe",
        "calculator": r"C:\Windows\system32\calc.exe",
        "calc": r"C:\Windows\system32\calc.exe",
        "cmd": r"C:\Windows\system32\cmd.exe",
        "powershell": r"C:\Windows\system32\WindowsPowerShell\\v1.0\\powershell.exe",
        "explorer": r"C:\Windows\explorer.exe",
        "chrome": fr"{pf}\Google\Chrome\Application\chrome.exe",
        "edge": fr"{pf86}\Microsoft\Edge\Application\msedge.exe",
    }

    target = app_map.get(name)
    try:
        if target and Path(target).exists():
            subprocess.Popen([target], shell=False)
            return f"Launching {name}."
        # Fallback: let Windows resolve it
        subprocess.Popen(f'start "" "{app_name}"', shell=True)
        return f"Requested launch: {app_name}."
    except Exception as e:
        return f"Error opening {app_name}: {e}"


@tool
def read_clipboard(_: str = "") -> str:
    """Return current clipboard text."""
    try:
        result = _run_powershell("Get-Clipboard")
        if result.returncode != 0:
            return f"Clipboard read failed: {result.stderr.strip()}"
        text = result.stdout.rstrip("\n")
        return text if text else "(clipboard empty)"
    except Exception as e:
        return f"Error reading clipboard: {e}"


@tool
def write_clipboard(text: str) -> str:
    """Set clipboard text to the provided value."""
    try:
        ps = f"Set-Clipboard -Value @'\n{text}\n'@"
        result = _run_powershell(ps)
        if result.returncode != 0:
            return f"Clipboard write failed: {result.stderr.strip()}"
        return "Copied to clipboard."
    except Exception as e:
        return f"Error writing clipboard: {e}"


def _candidate_dirs() -> List[Path]:
    home = Path.home()
    return [
        home / "Downloads",
        home / "Documents",
        home / "Desktop",
    ]


@tool
def find_file(query: str) -> str:
    """Find files whose names contain the query across common user folders."""
    needle = query.strip().lower()
    if not needle:
        return "Provide a file name or part of it."

    matches = []
    for base in _candidate_dirs():
        if not base.exists():
            continue
        for root, _, files in os.walk(base):
            for fname in files:
                if needle in fname.lower():
                    path = Path(root) / fname
                    try:
                        mtime = path.stat().st_mtime
                    except Exception:
                        mtime = 0
                    matches.append((mtime, path))
    if not matches:
        return f"No matches for '{query}'."

    matches.sort(key=lambda x: x[0], reverse=True)
    lines = [f"- {p}" for _, p in matches[:10]]
    return "Found:\n" + "\n".join(lines)


@tool
def list_recent_downloads(_: str = "") -> str:
    """List the most recent files in the Downloads folder."""
    downloads = Path.home() / "Downloads"
    if not downloads.exists():
        return "Downloads folder not found."

    items = []
    for path in downloads.iterdir():
        try:
            mtime = path.stat().st_mtime
        except Exception:
            continue
        items.append((mtime, path))

    if not items:
        return "No items in Downloads."

    items.sort(key=lambda x: x[0], reverse=True)
    lines = []
    for mtime, path in items[:10]:
        lines.append(f"- {path.name}")
    return "Recent Downloads:\n" + "\n".join(lines)
