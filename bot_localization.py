"""Azerbaijani localization for Telegram messages and keyboard labels."""

import inspect
import json
import re
from functools import wraps
from pathlib import Path

from telegram import (
    Bot,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)


_DATA = json.loads(Path(__file__).with_name("bot_text_az.json").read_text(encoding="utf-8"))
_TEXTS = _DATA["texts"]
_COUNTRY_NAMES = _DATA["country_names"]
_PLACEHOLDER = re.compile(r"\{[^{}]*\}")


def _template_parts(value):
    return _PLACEHOLDER.split(value)


def _template_pattern(value):
    parts = _template_parts(value)
    if len(parts) == 1:
        return None
    pattern = re.escape(parts[0])
    for index, part in enumerate(parts[1:]):
        pattern += rf"(?P<slot{index}>.*?)" + re.escape(part)
    return re.compile(pattern, re.DOTALL)


def _render_template(parts, match):
    rendered = parts[0]
    for index, part in enumerate(parts[1:]):
        rendered += match.group(f"slot{index}") + part
    return rendered


def _restore_input_template(parts, match):
    rendered = parts[0]
    for index, part in enumerate(parts[1:]):
        value = match.group(f"slot{index}")
        rendered += _REVERSE_TEXT.get(value, value) + part
    return rendered


_OUTGOING_TEMPLATES = []
_INCOMING_TEMPLATES = []
for _source, _translation in _TEXTS.items():
    _source_parts = _template_parts(_source)
    _translation_parts = _template_parts(_translation)
    if len(_source_parts) != len(_translation_parts) or len(_source_parts) == 1:
        continue
    _outgoing_pattern = _template_pattern(_source)
    _incoming_pattern = _template_pattern(_translation)
    if _outgoing_pattern:
        _OUTGOING_TEMPLATES.append(
            (_outgoing_pattern, _translation_parts)
        )
    if _incoming_pattern:
        _INCOMING_TEMPLATES.append((_incoming_pattern, _source_parts))

_OUTGOING_TEMPLATES.sort(key=lambda item: len(item[0].pattern), reverse=True)
_INCOMING_TEMPLATES.sort(key=lambda item: len(item[0].pattern), reverse=True)

_PHRASES = {**_COUNTRY_NAMES, **_TEXTS}
_PHRASES = {
    source: translation
    for source, translation in _PHRASES.items()
    if source and source != translation and not _PLACEHOLDER.search(source)
}
_PHRASES = dict(
    sorted(_PHRASES.items(), key=lambda item: len(item[0]), reverse=True)
)
_PHRASE_PATTERN = (
    re.compile("|".join(re.escape(source) for source in _PHRASES))
    if _PHRASES
    else None
)

_REVERSE_TEXT = {}
for _source, _translation in _TEXTS.items():
    _REVERSE_TEXT.setdefault(_translation, _source)
for _source, _translation in _COUNTRY_NAMES.items():
    _REVERSE_TEXT.setdefault(_translation, _source)


def _replace_phrases(value):
    if not _PHRASE_PATTERN:
        return value
    return _PHRASE_PATTERN.sub(lambda match: _PHRASES[match.group(0)], value)


def localize_text(value):
    """Translate a complete message, f-string template, or embedded UI phrase."""
    if not isinstance(value, str) or not value:
        return value

    direct = _TEXTS.get(value)
    if direct is not None:
        return _replace_phrases(direct)

    for pattern, target_parts in _OUTGOING_TEMPLATES:
        value = pattern.sub(
            lambda match, parts=target_parts: _render_template(parts, match),
            value,
        )
    return _replace_phrases(value)


def normalize_button_input(value):
    """Map translated reply-keyboard labels back to the values existing handlers expect."""
    if not isinstance(value, str):
        return value
    direct = _REVERSE_TEXT.get(value)
    if direct is not None:
        return direct
    for pattern, source_parts in _INCOMING_TEMPLATES:
        value = pattern.sub(
            lambda match, parts=source_parts: _restore_input_template(parts, match),
            value,
        )
    return value


def localize_reply_markup(markup):
    """Rebuild Telegram's immutable keyboard buttons with translated visible labels."""
    if isinstance(markup, InlineKeyboardMarkup):
        rows = []
        for row in markup.inline_keyboard:
            translated_row = []
            for button in row:
                data = button.to_dict()
                data["text"] = localize_text(button.text)
                translated_row.append(InlineKeyboardButton(**data))
            rows.append(translated_row)
        return InlineKeyboardMarkup(rows)

    if isinstance(markup, ReplyKeyboardMarkup):
        rows = []
        for row in markup.keyboard:
            translated_row = []
            for button in row:
                if isinstance(button, str):
                    translated_row.append(KeyboardButton(text=localize_text(button)))
                    continue
                data = button.to_dict()
                data["text"] = localize_text(button.text)
                translated_row.append(KeyboardButton(**data))
            rows.append(translated_row)
        options = {
            name: getattr(markup, name)
            for name in (
                "is_persistent",
                "resize_keyboard",
                "one_time_keyboard",
                "input_field_placeholder",
                "selective",
            )
            if getattr(markup, name, None) is not None
        }
        return ReplyKeyboardMarkup(rows, **options)

    return markup


def install_azerbaijani_localization():
    """Translate Telegram output centrally without changing callback data or API fields."""
    methods = {
        "send_message": "text",
        "edit_message_text": "text",
        "answer_callback_query": "text",
        "send_photo": "caption",
        "send_document": "caption",
        "send_video": "caption",
        "send_audio": "caption",
        "send_animation": "caption",
        "send_voice": "caption",
        "edit_message_reply_markup": None,
    }

    for method_name, text_argument in methods.items():
        original = getattr(Bot, method_name, None)
        if original is None or getattr(original, "_az_localized", False):
            continue
        signature = inspect.signature(original)

        @wraps(original)
        async def localized_method(
            self,
            *args,
            _original=original,
            _signature=signature,
            _text_argument=text_argument,
            **kwargs,
        ):
            bound = _signature.bind_partial(self, *args, **kwargs)
            if _text_argument and bound.arguments.get(_text_argument) is not None:
                bound.arguments[_text_argument] = localize_text(
                    bound.arguments[_text_argument]
                )
            if bound.arguments.get("reply_markup") is not None:
                bound.arguments["reply_markup"] = localize_reply_markup(
                    bound.arguments["reply_markup"]
                )
            return await _original(*bound.args, **bound.kwargs)

        localized_method._az_localized = True
        setattr(Bot, method_name, localized_method)
