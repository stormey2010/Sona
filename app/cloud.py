"""Groq speech APIs, Cerebras chat, and Tavily web tools for Sona."""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import requests

from .stt import SonaError, recording_path, setting


def groq_transcribe(path: Path) -> str:
    try:
        from groq import Groq
        with path.open("rb") as audio:
            result = Groq(api_key=setting("GROQ_API_KEY")).audio.transcriptions.create(
                file=audio, model=setting("GROQ_STT_MODEL", "whisper-large-v3-turbo"),
                language=setting("STT_LANGUAGE", "en"), temperature=0,
                response_format="verbose_json",
            )
        return result.text.strip() or "(No speech detected.)"
    except Exception as exc:
        raise SonaError(f"Groq STT failed: {exc}") from exc


def speak(text: str) -> Path:
    if not text.strip():
        raise SonaError("There is no text to speak.")
    try:
        from groq import Groq
        target = recording_path().with_name(recording_path().stem + "-speech.wav")
        response = Groq(api_key=setting("GROQ_API_KEY")).audio.speech.create(
            model=setting("GROQ_TTS_MODEL", "canopylabs/orpheus-v1-english"),
            voice=setting("GROQ_TTS_VOICE", "autumn"), input=text[:200], response_format="wav",
        )
        response.write_to_file(str(target))
        device = os.getenv("TTS_AUDIO_DEVICE") or "default"
        subprocess.run(["aplay", "--device", device, str(target)], check=True)
        return target
    except Exception as exc:
        raise SonaError(f"Groq TTS failed: {exc}") from exc


def tavily(name: str, arguments: dict) -> dict:
    key = setting("TAVILY_API_KEY")
    endpoint = {"web_search": "search", "web_extract": "extract", "web_crawl": "crawl"}[name]
    response = requests.post(f"https://api.tavily.com/{endpoint}", headers={"Authorization": f"Bearer {key}"}, json=arguments, timeout=45)
    response.raise_for_status()
    return response.json()


TOOLS = [
    {"type": "function", "function": {"name": "web_search", "description": "Search the web.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "web_extract", "description": "Extract text from web URLs.", "parameters": {"type": "object", "properties": {"urls": {"type": "array", "items": {"type": "string"}}}, "required": ["urls"]}}},
    {"type": "function", "function": {"name": "web_crawl", "description": "Crawl a web page.", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
]


def ask(prompt: str) -> str:
    messages = [{"role": "system", "content": setting("CEREBRAS_SYSTEM_PROMPT", "You are Sona, a concise helpful voice assistant.")}, {"role": "user", "content": prompt}]
    headers = {"Authorization": f"Bearer {setting('CEREBRAS_API_KEY')}", "Content-Type": "application/json"}
    for _ in range(4):
        payload = {"model": setting("CEREBRAS_MODEL", "gpt-oss-120b"), "messages": messages, "tools": TOOLS, "max_tokens": 2048, "temperature": 1, "top_p": 1, "reasoning_effort": "low"}
        response = requests.post("https://api.cerebras.ai/v1/chat/completions", headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        message = response.json()["choices"][0]["message"]
        calls = message.get("tool_calls") or []
        messages.append(message)
        if not calls:
            return message.get("content") or "I do not have a response."
        for call in calls:
            name = call["function"]["name"]
            arguments = json.loads(call["function"]["arguments"])
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(tavily(name, arguments))})
    raise SonaError("The assistant reached its web-tool limit.")
