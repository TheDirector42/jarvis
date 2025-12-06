import os
import time
import webbrowser
import tkinter as tk
from tkinter import ttk
from pathlib import Path

# Mirror the model fallback used in main.py
MODEL_NAME = os.getenv("OLLAMA_MODEL", "llama3:8b")


class JarvisDashboard:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Jarvis HUD")
        self.root.geometry("900x600")
        self.root.configure(bg="#0a0f1a")
        self.accent = "#2dd4ff"
        self.subtle = "#0f172a"

        self._setup_style()
        self._build_layout()
        self._start_ticking()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "Card.TFrame",
            background=self.subtle,
            borderwidth=1,
            relief="solid",
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
            background="#0a0f1a",
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

    def _build_layout(self):
        header = ttk.Label(
            self.root,
            text="Jarvis Systems Overview",
            style="Header.TLabel",
            anchor="w",
        )
        header.pack(fill="x", padx=24, pady=(20, 4))

        tagline = ttk.Label(
            self.root,
            text="Tony Stark–inspired HUD for your local voice assistant.",
            style="Body.TLabel",
            anchor="w",
        )
        tagline.pack(fill="x", padx=24, pady=(0, 16))

        top_frame = tk.Frame(self.root, bg="#0a0f1a")
        top_frame.pack(fill="x", padx=20, pady=4)

        self.status_card = self._card(top_frame)
        self._status_content(self.status_card)

        self.model_card = self._card(top_frame)
        self._model_content(self.model_card)

        self.tools_card = self._card(top_frame)
        self._tools_content(self.tools_card)

        lower_frame = tk.Frame(self.root, bg="#0a0f1a")
        lower_frame.pack(fill="both", expand=True, padx=20, pady=12)

        self.quickstart_card = self._card(lower_frame, fill="both", expand=True)
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
            text="Idle / awaiting wake word",
            style="Card.TLabel",
            font=("Segoe UI Semibold", 12),
        )
        self.status_label.pack(anchor="w", pady=(6, 2))

        self.substatus_label = ttk.Label(
            parent,
            text="Model loaded locally. Microphone listening when main.py runs.",
            style="Card.TLabel",
            font=("Segoe UI", 10),
        )
        self.substatus_label.pack(anchor="w")

        self.pulse = tk.Canvas(parent, width=220, height=8, bg=self.subtle, highlightthickness=0)
        self.pulse.pack(pady=(10, 0), anchor="w")
        self.pulse_rect = self.pulse.create_rectangle(0, 0, 40, 8, fill=self.accent, width=0)
        self.pulse_dir = 1

    def _model_content(self, parent):
        title = ttk.Label(parent, text="Model", style="Card.TLabel")
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
        ]
        for tool in tools:
            ttk.Label(parent, text=f"• {tool}", style="Card.TLabel").pack(anchor="w", pady=(2, 0))

    def _quickstart_content(self, parent):
        title = ttk.Label(parent, text="Quickstart", style="Card.TLabel")
        title.pack(anchor="w")

        steps = [
            "1) Pull the model:  ollama run llama3:8b",
            "2) Start voice assistant:  python main.py",
            "3) Say the wake word:  \"Jarvis\"",
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


def main():
    root = tk.Tk()
    JarvisDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
