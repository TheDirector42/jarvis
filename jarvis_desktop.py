import os
import time
import json
import webbrowser
import threading
import tkinter as tk
import subprocess
from datetime import datetime
from pathlib import Path
from tkinter import ttk

try:
    import psutil
except ImportError:
    psutil = None

try:
    import speedtest
except ImportError:
    speedtest = None
from langchain_ollama import ChatOllama
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

from tools.time import get_time
from tools.OCR import read_text_from_latest_image
from tools.arp_scan import arp_scan_terminal
from tools.duckduckgo import duckduckgo_search_tool
from tools.matrix import matrix_mode
from tools.screenshot import take_screenshot
from tools.system_insights import system_insights

# Mirror the model fallback used in main.py (must support tools)
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")
LOG_FILE = Path(os.getenv("JARVIS_EVENT_LOG", Path(__file__).parent / "jarvis_events.jsonl"))
TOOLS = [
    get_time,
    arp_scan_terminal,
    read_text_from_latest_image,
    duckduckgo_search_tool,
    matrix_mode,
    take_screenshot,
    system_insights,
]
PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are Jarvis, an intelligent, conversational AI assistant. "
            "You are concise, friendly, and explain reasoning simply. "
            "Use tools when they improve accuracy.",
        ),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)


class JarvisDashboard:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Jarvis HUD")
        self.root.geometry("900x600")
        self.root.configure(bg="#050910")
        self.accent = "#5ef0ff"
        self.accent_dim = "#1b3a4d"
        self.subtle = "#0b1320"
        self.start_time = time.time()
        self.convo_count = 0
        self.last_latency = None
        self.thinking = False
        self.spinner_idx = 0
        self.agent_ready = False
        self.agent_error = None
        self.executor = None
        self.agent_status_text = tk.StringVar(value="Connecting to model...")
        self.agent_detail_text = tk.StringVar(value="")
        self.log_file = LOG_FILE
        self.log_pos = 0
        self.wifi_text = tk.StringVar(value="Wi-Fi: --")
        self.ip_text = tk.StringVar(value="IP: --")
        self.gpu_text = tk.StringVar(value="GPU: --")
        self.batt_text = tk.StringVar(value="Battery: --")
        self.speed_text = tk.StringVar(value="Speed: idle")
        self.speed_running = False

        self._setup_style()
        self._setup_agent()
        self._build_layout()
        self._start_ticking()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Card.TFrame",
            background=self.subtle,
            borderwidth=0,
            relief="flat",
        )
        style.configure(
            "Card.TLabel",
            background=self.subtle,
            foreground="#e2e8f0",
            font=("Segoe UI", 10),
        )
        style.configure(
            "Header.TLabel",
            background="#0a0f1a",
            foreground=self.accent,
            font=("Segoe UI Semibold", 18),
        )
        style.configure(
            "Body.TLabel",
            background="#050910",
            foreground="#cbd5e1",
            font=("Segoe UI", 11),
        )
        style.configure(
            "Accent.TButton",
            background=self.accent,
            foreground="#0b1224",
            font=("Segoe UI Semibold", 10),
            padding=8,
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#67e8f9")],
            foreground=[("active", "#0b1224")],
        )

    def _setup_agent(self):
        try:
            llm = ChatOllama(model=MODEL_NAME, reasoning=False)
            agent = create_tool_calling_agent(llm=llm, tools=TOOLS, prompt=PROMPT)
            self.executor = AgentExecutor(agent=agent, tools=TOOLS, verbose=False)
            self.agent_ready = True
            self.agent_status_text.set(f"Connected to {MODEL_NAME}")
            self.agent_detail_text.set("Ready for chat + tools.")
        except Exception as e:
            self.agent_ready = False
            self.agent_error = str(e)
            self.agent_status_text.set("Model unavailable")
            self.agent_detail_text.set(self.agent_error)

    def _build_layout(self):
        header = ttk.Label(
            self.root,
            text="Jarvis Operations HUD",
            style="Header.TLabel",
            anchor="w",
        )
        header.pack(fill="x", padx=24, pady=(20, 2))

        tagline = ttk.Label(
            self.root,
            text="Live status • Local LLM • Tool execution",
            style="Body.TLabel",
            anchor="w",
        )
        tagline.pack(fill="x", padx=24, pady=(0, 8))

        accent_bar = tk.Canvas(self.root, height=3, bg="#050910", highlightthickness=0)
        accent_bar.pack(fill="x", padx=24, pady=(0, 14))
        accent_bar.create_rectangle(0, 0, 180, 3, fill=self.accent, width=0)

        self.scan_canvas = tk.Canvas(self.root, height=18, bg="#050910", highlightthickness=0)
        self.scan_canvas.pack(fill="x", padx=20, pady=(0, 12))
        self.scan_bars = []
        for i in range(3):
            bar = self.scan_canvas.create_rectangle(-180 + i * 220, 2, -80 + i * 220, 16, fill=self.accent, width=0)
            self.scan_bars.append(bar)

        top_frame = tk.Frame(self.root, bg="#050910")
        top_frame.pack(fill="x", padx=20, pady=4)

        self.status_card = self._card(top_frame)
        self._status_content(self.status_card)

        self.model_card = self._card(top_frame)
        self._model_content(self.model_card)

        self.tools_card = self._card(top_frame)
        self._tools_content(self.tools_card)

        lower_frame = tk.Frame(self.root, bg="#050910")
        lower_frame.pack(fill="both", expand=True, padx=20, pady=12)

        self.chat_card = self._card(lower_frame, fill="both", expand=True)
        self._chat_content(self.chat_card)

        self.quickstart_card = self._card(lower_frame, fill="y", expand=False)
        self._quickstart_content(self.quickstart_card)

    def _card(self, parent, **pack_kwargs):
        frame = ttk.Frame(parent, style="Card.TFrame")
        pack_params = dict(side="left", padx=8, expand=True, fill="both")
        pack_params.update(pack_kwargs)
        frame.pack(**pack_params)
        inner = tk.Frame(frame, bg=self.subtle, padx=14, pady=12)
        inner.pack(fill="both", expand=True)
        return inner

    def _status_content(self, parent):
        title = ttk.Label(parent, text="Status", style="Card.TLabel")
        title.pack(anchor="w")

        self.status_label = ttk.Label(
            parent,
            text="Idle / ready",
            style="Card.TLabel",
            font=("Segoe UI Semibold", 12),
        )
        self.status_label.pack(anchor="w", pady=(6, 2))

        self.substatus_label = ttk.Label(
            parent,
            textvariable=self.agent_status_text,
            style="Card.TLabel",
            font=("Segoe UI", 10),
        )
        self.substatus_label.pack(anchor="w")

        self.detail_label = ttk.Label(
            parent,
            textvariable=self.agent_detail_text,
            style="Card.TLabel",
            font=("Segoe UI", 9),
        )
        self.detail_label.pack(anchor="w", pady=(0, 6))

        self.resp_label = ttk.Label(parent, text="Last latency: --", style="Card.TLabel")
        self.resp_label.pack(anchor="w")

        self.convo_label = ttk.Label(parent, text="Exchanges: 0", style="Card.TLabel")
        self.convo_label.pack(anchor="w")

        self.uptime_label = ttk.Label(parent, text="Uptime: 00:00:00", style="Card.TLabel")
        self.uptime_label.pack(anchor="w")

        self.pulse = tk.Canvas(parent, width=220, height=8, bg=self.subtle, highlightthickness=0)
        self.pulse.pack(pady=(10, 0), anchor="w")
        self.pulse_rect = self.pulse.create_rectangle(0, 0, 40, 8, fill=self.accent, width=0)
        self.pulse_dir = 1

    def _model_content(self, parent):
        title = ttk.Label(parent, text="Model & Vitals", style="Card.TLabel")
        title.pack(anchor="w")

        ttk.Label(parent, text=f"Primary: {MODEL_NAME}", style="Card.TLabel").pack(anchor="w", pady=(6, 0))
        ttk.Label(
            parent,
            text="Provider: Ollama (local inference)",
            style="Card.TLabel",
        ).pack(anchor="w", pady=(2, 0))
        ttk.Label(
            parent,
            text="Behavior: Conversational + tool use",
            style="Card.TLabel",
        ).pack(anchor="w", pady=(2, 0))

        self.model_state_label = ttk.Label(
            parent,
            textvariable=self.agent_status_text,
            style="Card.TLabel",
            font=("Segoe UI Semibold", 10),
        )
        self.model_state_label.pack(anchor="w", pady=(8, 0))

        self.vitals_label = ttk.Label(parent, text="CPU: --  •  RAM: --", style="Card.TLabel")
        self.vitals_label.pack(anchor="w", pady=(4, 0))

        self.gpu_label = ttk.Label(parent, textvariable=self.gpu_text, style="Card.TLabel")
        self.gpu_label.pack(anchor="w", pady=(2, 0))

        self.wifi_label = ttk.Label(parent, textvariable=self.wifi_text, style="Card.TLabel")
        self.wifi_label.pack(anchor="w", pady=(2, 0))

        self.ip_label = ttk.Label(parent, textvariable=self.ip_text, style="Card.TLabel")
        self.ip_label.pack(anchor="w", pady=(2, 0))

        self.batt_label = ttk.Label(parent, textvariable=self.batt_text, style="Card.TLabel")
        self.batt_label.pack(anchor="w", pady=(2, 0))

        self.speed_label = ttk.Label(parent, textvariable=self.speed_text, style="Card.TLabel")
        self.speed_label.pack(anchor="w", pady=(4, 4))

        ttk.Button(
            parent,
            text="Run speed test",
            style="Accent.TButton",
            command=self._run_speedtest,
        ).pack(anchor="w", pady=(0, 8))

        ttk.Button(
            parent,
            text="Open README",
            style="Accent.TButton",
            command=self._open_readme,
        ).pack(anchor="w", pady=(12, 0))

    def _tools_content(self, parent):
        title = ttk.Label(parent, text="Tools", style="Card.TLabel")
        title.pack(anchor="w")

        tools = [
            "🕒 Time lookup",
            "🔍 DuckDuckGo search",
            "🖼 OCR latest screenshot",
            "🖥️ Screenshot capture",
            "📡 ARP network scan",
            "🧮 Matrix mode (demo)",
            "🛠 System insights (CPU/GPU/Wi-Fi/battery/speed)",
        ]
        for tool in tools:
            ttk.Label(parent, text=f"• {tool}", style="Card.TLabel").pack(anchor="w", pady=(2, 0))

    def _chat_content(self, parent):
        title = ttk.Label(parent, text="Conversation Feed", style="Card.TLabel")
        title.pack(anchor="w")

        subtitle = ttk.Label(
            parent,
            text="Live chat between you and Jarvis (voice + HUD).",
            style="Card.TLabel",
        )
        subtitle.pack(anchor="w", pady=(2, 8))

        frame = tk.Frame(parent, bg=self.subtle)
        frame.pack(fill="both", expand=True)

        scrollbar = ttk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")

        self.chat_text = tk.Text(
            frame,
            bg=self.subtle,
            fg="#e2e8f0",
            insertbackground=self.accent,
            wrap="word",
            borderwidth=0,
            highlightthickness=0,
            padx=6,
            pady=6,
        )
        self.chat_text.pack(side="left", fill="both", expand=True)
        self.chat_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.configure(command=self.chat_text.yview)

        self.chat_text.tag_config("meta", foreground="#64748b", font=("Segoe UI", 9))
        self.chat_text.tag_config("user", foreground="#67e8f9", font=("Segoe UI Semibold", 10))
        self.chat_text.tag_config("jarvis", foreground="#dbeafe", font=("Segoe UI", 10))

        input_frame = tk.Frame(parent, bg=self.subtle)
        input_frame.pack(fill="x", pady=(8, 0))

        self.input_var = tk.StringVar()
        self.entry = tk.Entry(
            input_frame,
            textvariable=self.input_var,
            bg="#0b1224",
            fg="#e2e8f0",
            insertbackground=self.accent,
            relief="flat",
            highlightthickness=1,
            highlightbackground="#1e293b",
            highlightcolor=self.accent,
        )
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 8), ipady=6)
        self.entry.bind("<Return>", lambda e: self._on_send())

        self.send_button = ttk.Button(
            input_frame,
            text="Send",
            style="Accent.TButton",
            command=self._on_send,
        )
        self.send_button.pack(side="right")

        self.think_label = ttk.Label(parent, text="", style="Card.TLabel")
        self.think_label.pack(anchor="w", pady=(6, 0))

        self.chat_text.config(state="disabled")
        self._populate_demo_chat()
        self.entry.focus_set()

    def _quickstart_content(self, parent):
        title = ttk.Label(parent, text="Quickstart", style="Card.TLabel")
        title.pack(anchor="w")

        steps = [
            "1) Pull the model:  ollama run qwen2.5:3b",
            "2) Start everything: python start_jarvis.py",
            "3) Say the wake word: \"Jarvis\"",
            "4) Issue a command (e.g., \"What's the time in Sydney?\")",
        ]
        for step in steps:
            ttk.Label(parent, text=step, style="Card.TLabel").pack(anchor="w", pady=(4, 0))

        ttk.Button(
            parent,
            text="Open Ollama models",
            style="Accent.TButton",
            command=lambda: webbrowser.open("https://ollama.com/library"),
        ).pack(anchor="w", pady=(12, 0))

    def _open_readme(self):
        readme_path = Path(__file__).parent / "README.md"
        webbrowser.open(readme_path.as_uri())

    def _start_ticking(self):
        self._tick_status()
        self._tick_pulse()
        self._tick_scan()
        self._tick_vitals()
        self._tick_spinner()
        self._watch_events()

    def _tick_status(self):
        timestamp = time.strftime("%H:%M:%S")
        self.status_label.config(text=f"Idle / ready  •  {timestamp}")
        self.root.after(1000, self._tick_status)

    def _tick_pulse(self):
        current = self.pulse.coords(self.pulse_rect)
        left, _, right, _ = current
        if right >= 220:
            self.pulse_dir = -1
        elif left <= 0:
            self.pulse_dir = 1
        delta = 8 * self.pulse_dir
        self.pulse.move(self.pulse_rect, delta, 0)
        self.root.after(60, self._tick_pulse)

    def _tick_scan(self):
        width = max(self.scan_canvas.winfo_width(), 600)
        for bar in self.scan_bars:
            self.scan_canvas.move(bar, 6, 0)
            left, _, right, _ = self.scan_canvas.coords(bar)
            if left > width:
                self.scan_canvas.move(bar, -width - 120, 0)
        self.root.after(35, self._tick_scan)

    def _tick_vitals(self):
        uptime = int(time.time() - self.start_time)
        self.uptime_label.config(text=f"Uptime: {self._fmt_seconds(uptime)}")
        if self.last_latency is not None:
            self.resp_label.config(text=f"Last latency: {self.last_latency * 1000:.0f} ms")
        else:
            self.resp_label.config(text="Last latency: --")
        self.convo_label.config(text=f"Exchanges: {self.convo_count}")

        if psutil:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            self.vitals_label.config(text=f"CPU: {cpu:.0f}%  •  RAM: {mem:.0f}%")
        else:
            self.vitals_label.config(text="CPU/RAM: install psutil for live stats")

        self.gpu_text.set(self._sample_gpu())
        wifi, ip = self._sample_wifi_ip()
        self.wifi_text.set(wifi)
        self.ip_text.set(ip)
        self.batt_text.set(self._sample_battery())

        self.root.after(1000, self._tick_vitals)

    def _tick_spinner(self):
        if self.thinking:
            frames = ["⠁", "⠂", "⠄", "⡀", "⢀", "⠠", "⠐", "⠈"]
            self.spinner_idx = (self.spinner_idx + 1) % len(frames)
            self.think_label.config(text=f"Jarvis is thinking... {frames[self.spinner_idx]}")
        self.root.after(120, self._tick_spinner)

    def _watch_events(self):
        try:
            if self.log_file.exists():
                with self.log_file.open("r", encoding="utf-8") as f:
                    f.seek(self.log_pos)
                    lines = f.readlines()
                    self.log_pos = f.tell()
            else:
                lines = []
        except Exception:
            lines = []

        for line in lines:
            try:
                event = json.loads(line.strip())
                self._handle_event(event)
            except Exception:
                continue

        self.root.after(800, self._watch_events)

    def _handle_event(self, event: dict):
        kind = event.get("kind")
        text = event.get("text", "")
        msg = event.get("message", "")
        latency_ms = event.get("latency_ms")

        if kind == "user":
            self._append_chat("user", f"You: {text}\n")
            self.chat_text.see("end")
        elif kind == "assistant":
            self._append_chat("jarvis", f"Jarvis: {text}\n\n")
            self.convo_count += 1
            if latency_ms:
                self.last_latency = latency_ms / 1000.0
            self.chat_text.see("end")
        elif kind == "status":
            self.agent_status_text.set(msg)
            self.status_label.config(text=msg)
        elif kind == "error":
            self._append_chat("meta", f"Error: {msg or text}\n")
            self.agent_status_text.set("LLM error")
            if text:
                self.agent_detail_text.set(text)

    def _log_event(self, kind: str, data: dict):
        try:
            LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
            payload = {"kind": kind, "ts": time.time(), "session": "hud"}
            payload.update(data)
            with LOG_FILE.open("a", encoding="utf-8") as f:
                json.dump(payload, f)
                f.write("\n")
        except Exception:
            pass

    def _on_send(self):
        text = self.input_var.get().strip()
        if not text:
            return
        self.input_var.set("")
        self._append_chat("user", f"You: {text}\n")
        self.chat_text.see("end")
        self._log_event("user", {"text": text})

        if not self.executor:
            self._append_chat("meta", f"Jarvis not ready: {self.agent_error or 'no model'}\n")
            return

        self._set_thinking(True)
        threading.Thread(target=self._run_agent, args=(text,), daemon=True).start()

    def _run_agent(self, text: str):
        started = time.time()
        content = ""
        success = False
        try:
            response = self.executor.invoke({"input": text})
            content = response["output"] if isinstance(response, dict) and "output" in response else str(response)
            success = True
        except Exception as e:
            content = f"Error: {e}"
            self.agent_status_text.set("LLM error")
            self.agent_detail_text.set(str(e))
        latency = time.time() - started
        self.root.after(0, lambda: self._finish_response(content, latency, success))

    def _finish_response(self, content: str, latency: float, success: bool):
        if success:
            self.convo_count += 1
            self.last_latency = latency
            self.status_label.config(text="Connected • ready")
            self._log_event("assistant", {"text": content, "latency_ms": latency * 1000.0})
        self._append_chat("jarvis", f"Jarvis: {content}\n\n")
        self.chat_text.see("end")
        self._set_thinking(False)

    def _set_thinking(self, active: bool):
        self.thinking = active
        if active:
            self.think_label.config(text="Jarvis is thinking...")
            self.send_button.state(["disabled"])
        else:
            self.think_label.config(text="")
            self.send_button.state(["!disabled"])

    def _fmt_seconds(self, seconds: int) -> str:
        hrs = seconds // 3600
        mins = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"

    def _sample_gpu(self) -> str:
        cmd = [
            "nvidia-smi",
            "--query-gpu=name,utilization.gpu,temperature.gpu",
            "--format=csv,noheader,nounits",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
            if proc.returncode != 0 or not proc.stdout.strip():
                return "GPU: n/a"
            line = proc.stdout.strip().splitlines()[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 3:
                name, util, temp = parts[0], parts[1], parts[2]
                return f"GPU: {name} {util}% @ {temp}°C"
        except Exception:
            pass
        return "GPU: n/a"

    def _sample_wifi_ip(self) -> tuple[str, str]:
        wifi_text = "Wi-Fi: n/a"
        ip_text = "IP: n/a"
        try:
            proc = subprocess.run(
                ["netsh", "wlan", "show", "interfaces"],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            if proc.returncode == 0 and proc.stdout:
                ssid = signal = ""
                for line in proc.stdout.splitlines():
                    if "SSID" in line and "BSSID" not in line:
                        ssid = line.split(":", 1)[1].strip()
                    if "Signal" in line:
                        signal = line.split(":", 1)[1].strip()
                wifi_text = f"Wi-Fi: {ssid or 'n/a'} ({signal or '--'})"
        except Exception:
            pass

        ip = None
        if psutil:
            try:
                for iface, addrs in psutil.net_if_addrs().items():
                    if "wi-fi" not in iface.lower() and "wlan" not in iface.lower():
                        continue
                    for addr in addrs:
                        if addr.family == 2 and not addr.address.startswith("127."):
                            ip = addr.address
                            break
                if not ip:
                    for addrs in psutil.net_if_addrs().values():
                        for addr in addrs:
                            if addr.family == 2 and not addr.address.startswith("127."):
                                ip = addr.address
                                break
            except Exception:
                ip = None
        if ip:
            ip_text = f"IP: {ip}"
        return wifi_text, ip_text

    def _sample_battery(self) -> str:
        if not psutil or not hasattr(psutil, "sensors_battery"):
            return "Battery: n/a"
        try:
            batt = psutil.sensors_battery()
            if not batt:
                return "Battery: not detected"
            status = "charging" if batt.power_plugged else "discharging"
            return f"Battery: {batt.percent:.0f}% ({status})"
        except Exception:
            return "Battery: n/a"

    def _run_speedtest(self):
        if self.speed_running:
            return
        if not speedtest:
            self.speed_text.set("Speed: install speedtest-cli")
            return
        self.speed_running = True
        self.speed_text.set("Speed: running...")
        threading.Thread(target=self._speedtest_thread, daemon=True).start()

    def _speedtest_thread(self):
        try:
            st = speedtest.Speedtest()
            st.get_best_server()
            down = st.download() / 1_000_000
            up = st.upload() / 1_000_000
            ping = st.results.ping
            text = f"Speed: ↓ {down:.1f} Mbps ↑ {up:.1f} Mbps (ping {ping:.0f} ms)"
        except Exception as e:
            text = f"Speedtest failed: {e}"
        self.root.after(0, lambda: self._set_speed_result(text))

    def _set_speed_result(self, text: str):
        self.speed_text.set(text)
        self.speed_running = False

    def _populate_demo_chat(self):
        self._append_chat("meta", "Waiting for Jarvis events... start the voice assistant to see live chat.\n")
        self.chat_text.see("end")
        self.chat_text.config(state="disabled")

    def _append_chat(self, role: str, content: str):
        state = self.chat_text.cget("state")
        self.chat_text.config(state="normal")
        self.chat_text.insert("end", content, role)
        self.chat_text.config(state=state)


def main():
    root = tk.Tk()
    JarvisDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
