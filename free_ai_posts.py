"""Optional Groq free-tier captions for safe aggregate Telegram announcements."""
import html
import json
import os
import re

import httpx

from data_storage import atomic_save, data_path

SETTINGS_FILE = data_path("ai_post_settings.json")
STYLES = ("energetic", "professional", "minimal")
DEFAULT_SETTINGS = {"enabled": True, "style": "energetic"}
FALLBACK = {
    "energetic": "✨ Yenilənən xidmət kataloqunu kəşf edin! Dəyişikliklərə nəzər salın.",
    "professional": "📊 Xidmət kataloqu üzrə yenilənmiş məlumatların xülasəsi:",
    "minimal": "🌍 Kataloq yenilənib. Məlumatlara baxın:",
}
GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"


def load_ai_settings():
    result = dict(DEFAULT_SETTINGS)
    try:
        with open(SETTINGS_FILE, encoding="utf-8") as file:
            raw = json.load(file)
        if isinstance(raw, dict):
            if type(raw.get("enabled")) is bool:
                result["enabled"] = raw["enabled"]
            if raw.get("style") in STYLES:
                result["style"] = raw["style"]
    except (OSError, ValueError, TypeError):
        pass
    return result


def save_ai_settings(enabled, style):
    if type(enabled) is not bool or style not in STYLES:
        raise ValueError("invalid_ai_settings")
    result = {"enabled": enabled, "style": style}
    atomic_save(result, SETTINGS_FILE)
    return result


def public_ai_status():
    settings = load_ai_settings()
    key_ready = bool(os.getenv("GROQ_API_KEY", "").strip())
    return {**settings, "provider": "Groq Llama (free tier)",
            "key_configured": key_ready,
            "mode": ("off" if not settings["enabled"] else
                     "ai" if key_ready else "template")}


def safe_intro(value):
    """Reject invented quantities, contacts, secrets and unsupported claims."""
    if not isinstance(value, str):
        return None
    text = " ".join(value.strip().split()).strip("\"'“” «»")
    if not 14 <= len(text) <= 170:
        return None
    if re.search(r"\d|https?://|www\.|@|<|>|\{|\}", text, re.I):
        return None
    if re.search(r"(?i)\b(?:otp|pin|sms|kod|şifrə|parol|zəmanət|pulsuz|free)\b", text):
        return None
    if not any(term in text.casefold() for term in
               ("kataloq", "xidmət", "range", "siyahı", "yenilən", "məlumat")):
        return None
    return text


async def generate_intro(snapshot, settings=None, client=None):
    settings = settings or load_ai_settings()
    if not settings["enabled"]:
        return ""
    style = settings["style"]
    fallback = FALLBACK[style]
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return fallback
    tone = {"energetic": "enerjili və emojili", "professional": "peşəkar",
            "minimal": "çox qısa və minimal"}[style]
    # ONLY numeric aggregate counts, never API range lists, SMS, OTP or users.
    safe_counts = {key: int(snapshot.get(key, 0)) for key in
                   ("services", "countries", "range_entries")}
    payload = {
        "model": GROQ_MODEL, "temperature": 0.65, "max_tokens": 90,
        "messages": [
            {"role": "system", "content": (
                "Azərbaycan dilində Telegram üçün BİR cümləlik cəlbedici giriş yaz. "
                f"Üslub: {tone}. Mövzu: xidmət kataloqunun yenilikləri. "
                "Heç bir rəqəm, qiymət və ya ad uydurma, telefon nömrəsi, "
                "OTP, SMS çatdırılması, nömrə mövcudluğu barədə iddia etmə. "
                "Link, hashtag, HTML və Markdown yazma. 'kataloq', 'xidmət' "
                "və ya 'məlumat' sözünü işlət.")},
            {"role": "user", "content": json.dumps(safe_counts)},
        ],
    }
    try:
        if client is None:
            async with httpx.AsyncClient(timeout=8.0) as session:
                response = await session.post(
                    GROQ_ENDPOINT, json=payload,
                    headers={"Authorization": f"Bearer {api_key}"})
        else:
            response = await client.post(
                GROQ_ENDPOINT, json=payload,
                headers={"Authorization": f"Bearer {api_key}"})
        response.raise_for_status()
        answer = safe_intro(response.json()["choices"][0]["message"]["content"])
        return answer or fallback
    except (httpx.HTTPError, ValueError, TypeError, KeyError, IndexError):
        # Groq free-tier rate limits (429) or outages never block group posts.
        return fallback


async def decorate_feed(snapshot, previous, verified_html):
    """AI may add an intro, but never rewrites the factual provider digest."""
    if not load_ai_settings()["enabled"]:
        return verified_html
    intro = await generate_intro(snapshot)
    return html.escape(intro) + "\n\n" + verified_html
