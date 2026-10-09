"""Offline verification of Premium emoji UI (no Telegram Bot token required)."""
import ast
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from telegram import InlineKeyboardMarkup, WebAppInfo

from bot_languages import menu_labels
from premium_ui import (
    CUSTOM_EMOJI_IDS,
    disable_premium_icons,
    is_premium_emoji_error,
    premium_html_emoji,
    premium_inline_button,
    reset_premium_icons,
)


class PremiumEmojiTests(unittest.TestCase):
    def setUp(self):
        reset_premium_icons()
        settings = patch.dict(os.environ, {"PREMIUM_EMOJI_ENABLED": "1"})
        settings.start()
        self.addCleanup(settings.stop)
        self.addCleanup(reset_premium_icons)

    def test_ids_are_numeric_strings(self):
        self.assertGreaterEqual(len(CUSTOM_EMOJI_IDS), 10)
        for value in CUSTOM_EMOJI_IDS.values():
            self.assertTrue(value.isdecimal())
            self.assertGreater(len(value), 15)

    def test_button_keeps_callback_and_color(self):
        button = premium_inline_button(
            "💰 BALANS", "balance", callback_data="menu_balance", style="primary"
        )
        self.assertEqual(button.text, "BALANS")
        self.assertEqual(button.icon_custom_emoji_id, CUSTOM_EMOJI_IDS["balance"])
        self.assertEqual(button.callback_data, "menu_balance")
        self.assertEqual(button.style, "primary")

    def test_custom_html_icon(self):
        title = premium_html_emoji("💎", "balance")
        self.assertIn("<tg-emoji emoji-id=", title)
        self.assertIn("💎", title)

    def test_disabled_mode_falls_back_to_original_text(self):
        with patch.dict(os.environ, {"PREMIUM_EMOJI_ENABLED": "0"}):
            button = premium_inline_button(
                "💰 BALANS", "balance", callback_data="menu_balance"
            )
            self.assertEqual(button.text, "💰 BALANS")
            self.assertIsNone(button.icon_custom_emoji_id)
            self.assertEqual(premium_html_emoji("💎", "balance"), "💎")

    def test_telegram_rejection_disables_icons_without_losing_text(self):
        self.assertTrue(is_premium_emoji_error(ValueError("BUTTON_CUSTOM_EMOJI_INVALID")))
        disable_premium_icons()
        button = premium_inline_button(
            "💰 BALANS", "balance", callback_data="menu_balance"
        )
        self.assertEqual(button.text, "💰 BALANS")
        self.assertIsNone(button.icon_custom_emoji_id)
        self.assertFalse(is_premium_emoji_error(ValueError("Too Many Requests")))

    def test_main_keyboard_preserves_actions_and_languages(self):
        root = ast.parse(Path("main.py").read_text(encoding="utf-8"))
        function = next(
            node for node in root.body
            if isinstance(node, ast.FunctionDef) and node.name == "main_keyboard"
        )
        code = compile(ast.Module(body=[function], type_ignores=[]), "main.py", "exec")
        for lang in ("az", "en", "tr"):
            namespace = {
                "get_user_language": lambda uid, _lang=lang: _lang,
                "menu_labels": menu_labels,
                "premium_inline_button": premium_inline_button,
                "WEBAPP_URL": "https://example.com",
                "WebAppInfo": WebAppInfo,
                "InlineKeyboardMarkup": InlineKeyboardMarkup,
                "is_admin": lambda uid: uid == 42,
            }
            exec(code, namespace)
            markup = namespace["main_keyboard"](42)
            ids = {
                button.callback_data: button
                for row in markup.inline_keyboard
                for button in row if button.callback_data
            }
            expected = (
                "menu_ivas_web_panel", "menu_get_number", "menu_active_numbers",
                "menu_search_otp", "menu_get_2fa", "menu_balance", "menu_profile",
                "menu_refer", "menu_leaderboard", "menu_support", "menu_language",
                "menu_admin",
            )
            for action in expected:
                self.assertIn(action, ids)
                self.assertIsNotNone(ids[action].icon_custom_emoji_id)
            self.assertIsNotNone(markup.inline_keyboard[0][0].web_app)
            self.assertEqual(ids["menu_get_number"].style, "success")
            self.assertEqual(ids["menu_admin"].style, "danger")
            with patch.dict(os.environ, {"PREMIUM_EMOJI_ENABLED": "0"}):
                fallback = namespace["main_keyboard"](12)
                fallback_actions = [b for row in fallback.inline_keyboard for b in row]
                self.assertTrue(all(b.icon_custom_emoji_id is None for b in fallback_actions))
                self.assertFalse(any(b.callback_data == "menu_admin" for b in fallback_actions))


if __name__ == "__main__":
    unittest.main()
