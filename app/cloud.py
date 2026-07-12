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


def home_assistant(name: str, arguments: dict) -> object:
    base = setting("HOMEASSISTANT_URL").rstrip("/")
    headers = {"Authorization": f"Bearer {setting('HOMEASSISTANT_TOKEN')}", "Content-Type": "application/json"}
    if name == "ha_get_state":
        response = requests.get(f"{base}/api/states/{arguments['entity_id']}", headers=headers, timeout=30)
    elif name == "ha_search_entities":
        response = requests.get(f"{base}/api/states", headers=headers, timeout=30)
        response.raise_for_status()
        query = arguments["query"].lower()
        return [x for x in response.json() if query in x.get("entity_id", "").lower() or query in str(x.get("attributes", {}).get("friendly_name", "")).lower()][:25]
    else:
        domain, service = arguments["service"].split(".", 1)
        response = requests.post(f"{base}/api/services/{domain}/{service}", headers=headers, json=arguments.get("data", {}), timeout=30)
    response.raise_for_status()
    return response.json()


TOOLS = [
    {"type": "function", "function": {"name": "web_search", "description": "Search the web.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "web_extract", "description": "Extract text from web URLs.", "parameters": {"type": "object", "properties": {"urls": {"type": "array", "items": {"type": "string"}}}, "required": ["urls"]}}},
    {"type": "function", "function": {"name": "web_crawl", "description": "Crawl a web page.", "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}}},
    {"type": "function", "function": {"name": "ha_search_entities", "description": "Search Home Assistant entities by name or entity ID.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "ha_get_state", "description": "Get a Home Assistant entity state.", "parameters": {"type": "object", "properties": {"entity_id": {"type": "string"}}, "required": ["entity_id"]}}},
    {"type": "function", "function": {"name": "ha_call_service", "description": "Call a Home Assistant service such as light.turn_on. Include entity_id in data.", "parameters": {"type": "object", "properties": {"service": {"type": "string"}, "data": {"type": "object"}}, "required": ["service", "data"]}}},
]


def ask(prompt: str, history: list[dict[str, str]]) -> tuple[str, dict[str, int]]:
    clean_history = [{"role": item["role"], "content": item["content"]} for item in history]
    messages = [{"role": "system", "content": setting("CEREBRAS_SYSTEM_PROMPT", "You are Sona, a concise helpful voice assistant.")}, *clean_history, {"role": "user", "content": prompt}]
    headers = {"Authorization": f"Bearer {setting('CEREBRAS_API_KEY')}", "Content-Type": "application/json"}
    totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    for _ in range(4):
        payload = {"model": setting("CEREBRAS_MODEL", "gpt-oss-120b"), "messages": messages, "tools": TOOLS, "max_tokens": 2048, "temperature": 1, "top_p": 1, "reasoning_effort": "low"}
        response = requests.post("https://api.cerebras.ai/v1/chat/completions", headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        data = response.json()
        usage = data.get("usage") or {}
        for key in totals:
            totals[key] += int(usage.get(key, 0) or 0)
        message = data["choices"][0]["message"]
        calls = message.get("tool_calls") or []
        messages.append(message)
        if not calls:
            return message.get("content") or "I do not have a response.", totals
        for call in calls:
            name = call["function"]["name"]
            arguments = json.loads(call["function"]["arguments"])
            result = home_assistant(name, arguments) if name.startswith("ha_") else tavily(name, arguments)
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": json.dumps(result)})
    raise SonaError("The assistant reached its web-tool limit.")
