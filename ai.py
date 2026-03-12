from __future__ import annotations
import httpx
from config import settings

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "meta-llama/llama-3.1-8b-instruct:free"

async def ask_ai(user_text: str, lang: str = "bn") -> str:
    if not settings.OPENROUTER_API_KEY:
        return "AI feature is disabled (OPENROUTER_API_KEY not set)."

    if lang == "en":
        system_prompt = "You are a helpful assistant. Always reply in English."
    else:
        system_prompt = (
            "You are a helpful assistant. "
            "If the user writes in Bangla, reply in Bangla. "
            "Otherwise reply in English."
        )

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": 0.4,
    }

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://earnova-bot.replit.app",
        "X-Title": "Earnova Bot",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)
            if r.status_code != 200:
                return f"AI error ({r.status_code}). Try again later."
            data = r.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"AI unavailable. Please try again later."
