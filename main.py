import os
import logging
import time
import json
import uuid
from pathlib import Path
import pyttsx3
from dotenv import load_dotenv
import speech_recognition as sr
from langchain_ollama import ChatOllama, OllamaLLM

# from langchain_openai import ChatOpenAI # if you want to use openai
from langchain_core.messages import HumanMessage
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate

# importing tools
from tools.time import get_time
from tools.OCR import read_text_from_latest_image
from tools.arp_scan import arp_scan_terminal
from tools.duckduckgo import duckduckgo_search_tool
from tools.matrix import matrix_mode
from tools.screenshot import take_screenshot
from tools.system_utils import (
    toggle_system_mute,
    open_app,
    read_clipboard,
    write_clipboard,
    find_file,
    list_recent_downloads,
)
from tools.system_insights import system_insights

load_dotenv()

MIC_INDEX = None
TRIGGER_WORD = "jarvis"
CONVERSATION_TIMEOUT = 30  # seconds of inactivity before exiting conversation mode
MODEL_NAME = os.getenv("OLLAMA_MODEL", "qwen2.5:3b")  # must support tools
LOG_FILE = Path(os.getenv("JARVIS_EVENT_LOG", Path(__file__).parent / "jarvis_events.jsonl"))
SESSION_ID = str(uuid.uuid4())

logging.basicConfig(level=logging.DEBUG)  # logging

# api_key = os.getenv("OPENAI_API_KEY") removed because it's not needed for ollama
# org_id = os.getenv("OPENAI_ORG_ID") removed because it's not needed for ollama

recognizer = sr.Recognizer()
mic = sr.Microphone(device_index=MIC_INDEX)


def log_event(kind: str, data: dict):
    try:
        LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
        payload = {"kind": kind, "ts": time.time(), "session": SESSION_ID}
        payload.update(data)
        with LOG_FILE.open("a", encoding="utf-8") as f:
            json.dump(payload, f)
            f.write("\n")
    except Exception as e:
        logging.debug(f"Failed to log event: {e}")

# Initialize LLM
try:
    llm = ChatOllama(model=MODEL_NAME, reasoning=False)
    log_event("status", {"message": f"Model {MODEL_NAME} loaded"})
except Exception as e:
    logging.critical(
        "Failed to load Ollama model '%s'. Install it with `ollama run %s` "
        "or set OLLAMA_MODEL to a model you already have. Error: %s",
        MODEL_NAME,
        MODEL_NAME,
        e,
    )
    log_event("error", {"message": "Failed to load model", "detail": str(e)})
    raise

# llm = ChatOpenAI(model="gpt-4o-mini", api_key=api_key, organization=org_id) for openai

# Tool list
tools = [get_time, arp_scan_terminal, read_text_from_latest_image, duckduckgo_search_tool, matrix_mode, take_screenshot]
tools += [toggle_system_mute, open_app, read_clipboard, write_clipboard, find_file, list_recent_downloads]
tools += [system_insights]

# Tool-calling prompt
prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are Jarvis, an intelligent, conversational AI assistant. Your goal is to be helpful, friendly, and informative. You can respond in natural, human-like language and use tools when needed to answer questions more accurately. Always explain your reasoning simply when appropriate, and keep your responses conversational and concise.",
        ),
        ("human", "{input}"),
        ("placeholder", "{agent_scratchpad}"),
    ]
)

# Agent + executor
agent = create_tool_calling_agent(llm=llm, tools=tools, prompt=prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)


# TTS setup
def speak_text(text: str):
    try:
        engine = pyttsx3.init()
        for voice in engine.getProperty("voices"):
            if "jamie" in voice.name.lower():
                engine.setProperty("voice", voice.id)
                break
        engine.setProperty("rate", 180)
        engine.setProperty("volume", 1.0)
        engine.say(text)
        engine.runAndWait()
        time.sleep(0.3)
    except Exception as e:
        logging.error(f"❌ TTS failed: {e}")


# Main interaction loop
def write():
    conversation_mode = False
    last_interaction_time = None
    log_event("status", {"message": "Jarvis listening for wake word"})

    try:
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            while True:
                try:
                    if not conversation_mode:
                        logging.info("🎤 Listening for wake word...")
                        audio = recognizer.listen(source, timeout=10)
                        transcript = recognizer.recognize_google(audio)
                        logging.info(f"🗣 Heard: {transcript}")

                        if TRIGGER_WORD.lower() in transcript.lower():
                            logging.info(f"🗣 Triggered by: {transcript}")
                            speak_text("Yes sir?")
                            conversation_mode = True
                            last_interaction_time = time.time()
                            log_event("status", {"message": "Wake word detected"})
                        else:
                            logging.debug("Wake word not detected, continuing...")
                    else:
                        logging.info("🎤 Listening for next command...")
                        audio = recognizer.listen(source, timeout=10)
                        command = recognizer.recognize_google(audio)
                        logging.info(f"📥 Command: {command}")
                        log_event("user", {"text": command})

                        logging.info("🤖 Sending command to agent...")
                        started = time.time()
                        try:
                            response = executor.invoke({"input": command})
                            content = response["output"]
                            logging.info(f"✅ Agent responded: {content}")
                            latency_ms = (time.time() - started) * 1000.0
                            log_event("assistant", {"text": content, "latency_ms": latency_ms})

                            print("Jarvis:", content)
                            speak_text(content)
                            last_interaction_time = time.time()
                        except Exception as e:
                            logging.error(f"❌ Agent failed: {e}")
                            log_event("error", {"message": "Agent failure", "detail": str(e)})
                            speak_text("I had a problem handling that.")

                        if time.time() - last_interaction_time > CONVERSATION_TIMEOUT:
                            logging.info("⌛ Timeout: Returning to wake word mode.")
                            conversation_mode = False

                except sr.WaitTimeoutError:
                    logging.warning("⚠️ Timeout waiting for audio.")
                    if (
                        conversation_mode
                        and time.time() - last_interaction_time > CONVERSATION_TIMEOUT
                    ):
                        logging.info(
                            "⌛ No input in conversation mode. Returning to wake word mode."
                        )
                        conversation_mode = False
                except sr.UnknownValueError:
                    logging.warning("⚠️ Could not understand audio.")
                except Exception as e:
                    logging.error(f"❌ Error during recognition or tool call: {e}")
                    time.sleep(1)

    except Exception as e:
        logging.critical(f"❌ Critical error in main loop: {e}")


if __name__ == "__main__":
    write()
