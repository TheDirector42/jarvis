import os
import subprocess
from pathlib import Path
from typing import Optional, Tuple

from langchain.tools import tool

try:
    import psutil
except ImportError:
    psutil = None

try:
    import speedtest
except ImportError:
    speedtest = None


def _run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    return proc.returncode, proc.stdout, proc.stderr


def _cpu_info() -> str:
    if not psutil:
        return "CPU: install psutil"
    load = psutil.cpu_percent(interval=0.2)
    temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
    cpu_temp = None
    for key in ["coretemp", "cpu-thermal", "cpu_thermal"]:
        if key in temps and temps[key]:
            cpu_temp = temps[key][0].current
            break
    if cpu_temp:
        return f"CPU: {load:.0f}% @ {cpu_temp:.0f}°C"
    return f"CPU: {load:.0f}%"


def _gpu_info() -> str:
    cmd = [
        "nvidia-smi",
        "--query-gpu=name,utilization.gpu,temperature.gpu",
        "--format=csv,noheader,nounits",
    ]
    code, out, err = _run(cmd)
    if code != 0:
        return "GPU: n/a"
    line = out.strip().splitlines()[0] if out.strip() else ""
    if not line:
        return "GPU: n/a"
    parts = [p.strip() for p in line.split(",")]
    if len(parts) >= 3:
        name, util, temp = parts[0], parts[1], parts[2]
        return f"GPU: {name} {util}% @ {temp}°C"
    return "GPU: n/a"


def _wifi_info() -> Tuple[str, str]:
    code, out, err = _run(["netsh", "wlan", "show", "interfaces"])
    if code != 0:
        return "Wi-Fi: n/a", "IP: n/a"
    ssid = signal = ""
    for line in out.splitlines():
        if "SSID" in line and "BSSID" not in line:
            ssid = line.split(":", 1)[1].strip()
        if "Signal" in line:
            signal = line.split(":", 1)[1].strip()
    ip = _primary_ip()
    wifi_text = f"Wi-Fi: {ssid or 'n/a'} ({signal or '--'})"
    ip_text = f"IP: {ip or 'n/a'}"
    return wifi_text, ip_text


def _primary_ip() -> Optional[str]:
    if not psutil:
        return None
    for iface, addrs in psutil.net_if_addrs().items():
        if "wi-fi" not in iface.lower() and "wlan" not in iface.lower():
            continue
        for addr in addrs:
            if addr.family == 2 and not addr.address.startswith("127."):
                return addr.address
    # fallback any non-loopback IPv4
    for addrs in psutil.net_if_addrs().values():
        for addr in addrs:
            if addr.family == 2 and not addr.address.startswith("127."):
                return addr.address
    return None


def _battery_info() -> str:
    if not psutil or not hasattr(psutil, "sensors_battery"):
        return "Battery: n/a"
    batt = psutil.sensors_battery()
    if not batt:
        return "Battery: not detected"
    percent = batt.percent
    plugged = batt.power_plugged
    status = "charging" if plugged else "discharging"
    return f"Battery: {percent:.0f}% ({status})"


def _speedtest() -> str:
    if not speedtest:
        return "Speedtest: install speedtest-cli to run (pip install speedtest-cli)"
    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        down = st.download() / 1_000_000
        up = st.upload() / 1_000_000
        ping = st.results.ping
        return f"Speedtest: ↓ {down:.1f} Mbps ↑ {up:.1f} Mbps (ping {ping:.0f} ms)"
    except Exception as e:
        return f"Speedtest failed: {e}"


@tool
def system_insights(run_speedtest: str = "no") -> str:
    """Return system insight: CPU load/temp, GPU load/temp (NVIDIA), Wi-Fi SSID/signal/IP, battery, and optional speedtest (set run_speedtest=yes)."""
    parts = [
        _cpu_info(),
        _gpu_info(),
    ]
    wifi, ip = _wifi_info()
    parts.append(wifi)
    parts.append(ip)
    parts.append(_battery_info())

    if run_speedtest.strip().lower() in {"yes", "y", "true", "1", "run"}:
        parts.append(_speedtest())

    return "\n".join(parts)
