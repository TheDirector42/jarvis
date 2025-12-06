# 🧠 Jarvis – Local Voice-Controlled AI Assistant

**Jarvis** is a voice-activated, conversational AI assistant powered by a local LLM (Qwen via Ollama). It listens for a wake word, processes spoken commands using a local language model with LangChain, and responds out loud via TTS. It supports tool-calling for dynamic functions like checking the current time.

---

## 🚀 Features

- 🗣 Voice-activated with wake word **"Jarvis"**
- 🧠 Local language model (Qwen via Ollama)
- 🔧 Tool-calling with LangChain
- 🔊 Text-to-speech responses via `pyttsx3`
- 🌍 Example tool: Get the current time in a given city
- 🔐 Optional support for OpenAI API integration
- 🛠 System utilities: mute toggle, open apps, clipboard, file search, recent downloads, and system insights (CPU/GPU/Wi‑Fi/battery/speed)

---


## ▶️ How It Works (`main.py`)

1. **Startup & local LLM Setup**
   - Initializes a local Ollama model (`qwen2.5:3b` by default, configurable via `OLLAMA_MODEL`) via `ChatOllama` (model must support tools)
   - Registers tools (`get_time`) using LangChain

2. **Wake Word Listening**
   - Listens via microphone (e.g., `device_index=0`)
   - If it hears the word **"Jarvis"**, it enters "conversation mode"

3. **Voice Command Handling**
   - Records the user’s spoken command
   - Passes the command to the LLM, which may invoke tools
   - Responds using `pyttsx3` text-to-speech (with optional custom voice)

4. **Timeout**
   - If the user is inactive for more than 30 seconds in conversation mode, it resets to wait for the wake word again.

---

## 🤖 How To Start Jarvis

1. **Install Dependencies**  
   Make sure you have installed all required dependencies listed in `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```
   (Optional) For speed tests in system insights, ensure `speedtest-cli` is installed (already in requirements).

2. **Set Up the Local Model**  
   Ensure you have the `qwen2.5:3b` model (the default, tool-capable) available in Ollama, or set `OLLAMA_MODEL` to a tool-capable model you already have installed. Example pull:
   ```bash
   ollama run qwen2.5:3b
   ```

3. **Run Jarvis**  
   Start the assistant by running:
   ```bash
   python main.py
   ```

4. **One-command launch (HUD + voice)**  
   Start both the desktop HUD and the voice assistant together:
   ```bash
   python start_jarvis.py
   ```
   (The HUD reads live events from `jarvis_events.jsonl`, shared with the voice process.)
---

## 💻 Desktop HUD (Jarvis-style overlay)

Want a quick, Tony Stark–style overview? Launch the desktop HUD:

```bash
python jarvis_desktop.py
```

What it shows:
- Current model (defaults to `qwen2.5:3b`, tool-capable) and live status of the local LLM
- Built-in tools (time lookup, search, OCR, screenshot, ARP scan, matrix demo)
- Live chat feed with Jarvis (local model + tools), with request latency and exchange count
- System vitals (CPU/RAM) and uptime timer
- Quickstart steps and links to Ollama models and the README

