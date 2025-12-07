import os
import requests
from langchain.tools import tool


def _env_ip() -> str:
    return os.getenv("BAMBU_IP", "").strip()


def _env_code() -> str:
    return os.getenv("BAMBU_ACCESS_CODE", "").strip()


def _fetch_status(ip: str, code: str):
    url = f"http://{ip}/server/state"
    headers = {"Authorization": f"Basic {code}"} if code else {}
    resp = requests.get(url, headers=headers, timeout=5)
    resp.raise_for_status()
    return resp.json()


@tool
def bambu_printer_status(printer_ip: str = "", access_code: str = "") -> str:
    """Check Bambu Lab printer (e.g., P1S) status: job, state, progress, and remaining time. Provide IP and access code (or set env BAMBU_IP and BAMBU_ACCESS_CODE)."""
    ip = printer_ip.strip() or _env_ip()
    code = access_code.strip() or _env_code()
    if not ip:
        return "Set printer_ip or env BAMBU_IP."
    try:
        data = _fetch_status(ip, code)
    except Exception as e:
        return f"Failed to reach printer at {ip}: {e}"

    job = data.get("print", {}).get("file", "unknown")
    state = data.get("print", {}).get("state", "unknown")
    progress = data.get("print", {}).get("progress", 0)
    remain = data.get("print", {}).get("remaining_time", 0)
    temps = data.get("temperature", {})
    bed = temps.get("bed", {}).get("current")
    nozzle = temps.get("nozzle", {}).get("current")

    parts = [
        f"Job: {job}",
        f"State: {state}",
        f"Progress: {progress}%",
        f"Time remaining: {remain} min",
    ]
    if bed is not None:
        parts.append(f"Bed: {bed}°C")
    if nozzle is not None:
        parts.append(f"Nozzle: {nozzle}°C")
    return " | ".join(parts)
