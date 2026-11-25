"""Optional LLM hook. If OPENAI_API_KEY (or ASA_LLM_BASE_URL + ASA_LLM_API_KEY for any
OpenAI-compatible endpoint) is set, agents can ask a model to polish text.
Without a key every agent falls back to deterministic templates, so the demo
always runs offline."""
from __future__ import annotations

import json
import os
import urllib.request


def available() -> bool:
    return bool(os.environ.get("ASA_LLM_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def complete(prompt: str, fallback: str) -> str:
    if not available():
        return fallback
    base = os.environ.get("ASA_LLM_BASE_URL", "https://api.openai.com/v1")
    key = os.environ.get("ASA_LLM_API_KEY") or os.environ["OPENAI_API_KEY"]
    model = os.environ.get("ASA_LLM_MODEL", "gpt-4o-mini")
    body = json.dumps({"model": model, "messages": [
        {"role": "system", "content": "You write short, friendly, accurate text for a school AI club. Never use long dashes."},
        {"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(base + "/chat/completions", data=body,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)["choices"][0]["message"]["content"].strip()
    except Exception:
        return fallback
