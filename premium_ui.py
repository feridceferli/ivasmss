"""Telegram Premium custom emoji icons with safe Unicode fallbacks.

Supports python-telegram-bot >=22.7, including the Bot API
icon_custom_emoji_id field for inline keyboard buttons.
Telegram only permits these icons when the bot owner has Telegram Premium
(or a qualifying Fragment username); gracefully disable on Bot API rejection.
"""
import os
import re

from telegram import InlineKeyboardButton

# Public catalog IDs sourced from Telegram custom emoji UI icon packs.
# Values are strings (not Unicode or sticker file IDs).
CUSTOM_EMOJI_IDS = {
    "mini_app": "5843553939672274145",        # Lightning / speed
    "ivas_panel": "5258093637450866522",      # Robot / tech
    "get_number": "5258260149037965799",      # Card / number services
    "active_numbers": "5875206779196935950",  # Folder / list
    "search_otp": "5260341314095947411",      # Search
    "get_2fa": "5258476306152038031",         # Lock
    "balance": "5807465992363710697",         # Diamond
    "profile": "5258362837411045098",         # Profile
    "refer": "5258513401784573443",           # People
    "leaderboard": "5874948844935974490",     # Star
    "support": "5258503720928288433",         # Help
    "language": "5258420634785947640",        # Settings
    "admin": "5258420634785947640",           # Settings
}

# "1" (default) enables Premium icons with a runtime fallback if Telegram
# rejects them. Set PREMIUM_EMOJI_ENABLED=0 in Render to always show Unicode.
_runtime_disabled = False


def premium_icons_enabled():
    value = os.environ.get("PREMIUM_EMOJI_ENABLED", "1").strip().lower()
    return not _runtime_disabled and value not in {"0", "off", "false", "no"}


def disable_premium_icons():
    global _runtime_disabled
    _runtime_disabled = True


def reset_premium_icons():
    """Used by offline tests only."""
    global _runtime_disabled
    _runtime_disabled = False


def premium_inline_button(label, icon_key, **kwargs):
    """Keep callbacks/styles identical, using an icon before a clean label."""
    emoji_id = CUSTOM_EMOJI_IDS.get(icon_key)
    if emoji_id and premium_icons_enabled():
        # Existing menu labels start with a Unicode emoji and a space.
        # The Telegram premium icon takes its place, avoiding duplication.
        clean_label = label.split(" ", 1)[1] if " " in label else label
        return InlineKeyboardButton(
            text=clean_label,
            icon_custom_emoji_id=emoji_id,
            **kwargs,
        )
    return InlineKeyboardButton(text=label, **kwargs)


def premium_html_emoji(fallback, icon_key):
    """Use only with parse_mode=HTML; otherwise render normal Unicode."""
    emoji_id = CUSTOM_EMOJI_IDS.get(icon_key)
    if premium_icons_enabled() and emoji_id:
        return f'<tg-emoji emoji-id="{emoji_id}">{fallback}</tg-emoji>'
    return fallback


def is_premium_emoji_error(error):
    """A narrow match so unrelated Telegram errors are not swallowed."""
    if error is None:
        return False
    message = str(error).lower()
    markers = (
        "custom_emoji", "custom emoji",
        "button_custom_emoji", "premium emoji",
        "emoji-id", "emoji id",
    )
    return any(marker in message for marker in markers)
