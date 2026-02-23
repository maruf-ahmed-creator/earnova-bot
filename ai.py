from __future__ import annotations
import httpx
from config import settings

async def ask_ai(user_text: str, lang: str = "bn") -> str:
    if not settings.OPENAI_API_KEY:
        return "AI feature is disabled (missing OPENAI_API_KEY)."

    sys = "You are a helpful assistant. Reply in Bangla if the user writes Bangla, otherwise reply in English."
    if lang == "en":
        sys = "You are a helpful assistant. Reply in English."

    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": sys},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.4,
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post("https://api.openai.com/v1/chat/completions", json=payload, headers=headers)
        if r.status_code != 200:
            return f"AI error ({r.status_code}). Try again later."
        data = r.json()
        return data["choices"][0]["message"]["content"].strip()
