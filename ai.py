from __future__ import annotations
import logging
import httpx
from config import settings

log = logging.getLogger("earnova")

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Ordered list of free models to try — falls back if one is unavailable
FALLBACK_MODELS = [
    "mistralai/mistral-7b-instruct:free",
    "google/gemma-7b-it:free",
    "nousresearch/nous-capybara-7b:free",
    "meta-llama/llama-3-8b-instruct:free",
]

async def ask_ai(user_text: str, lang: str = "bn") -> str:
    if not settings.OPENROUTER_API_KEY:
        return "AI feature is disabled (OPENROUTER_API_KEY not set)."

    if lang == "en":
        system_prompt = "You are a helpful assistant. Always reply in English. Be concise."
    else:
        system_prompt = (
            "You are a helpful assistant. "
            "If the user writes in Bangla, reply in Bangla. "
            "Otherwise reply in English. Be concise."
        )

    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://earnova-bot.replit.app",
        "X-Title": "Earnova Bot",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        for model in FALLBACK_MODELS:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_text},
                ],
                "temperature": 0.4,
            }
            try:
                r = await client.post(OPENROUTER_API_URL, json=payload, headers=headers)
                if r.status_code == 200:
                    data = r.json()
                    return data["choices"][0]["message"]["content"].strip()
                elif r.status_code == 404:
                    log.warning(f"OpenRouter model not found: {model}, trying next...")
                    continue
                else:
                    log.warning(f"OpenRouter error {r.status_code} for model {model}: {r.text[:200]}")
                    continue
            except Exception as e:
                log.warning(f"OpenRouter request failed for model {model}: {e}")
                continue

    return "AI is currently unavailable. Please try again later."
