import tempfile
import unittest
from pathlib import Path
from integrate_into_ivasmss import patch_bot

class IntegrationTests(unittest.TestCase):
    def test_idempotent_patch(self):
        source = """import os
# ==================== CONFIG SECTION ====================
def is_admin(uid):
    return True

def register_handlers(app):
    app.add_handler('old-handler')
"""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main = root / "main.py"
            main.write_text(source, encoding="utf-8")
            (root / "whatsapp_safe.py").write_text("# placeholder", encoding="utf-8")
            self.assertTrue(patch_bot(root))
            updated = main.read_text(encoding="utf-8")
            self.assertIn("from whatsapp_safe import register_whatsapp_handlers", updated)
            self.assertIn("    register_whatsapp_handlers(app, is_admin)", updated)
            self.assertIn("app.add_handler('old-handler')", updated)
            self.assertFalse(patch_bot(root))
            self.assertEqual(updated, main.read_text(encoding="utf-8"))
            self.assertEqual(source, (root / "main.py.before_whatsapp_safe.bak").read_text(encoding="utf-8"))
            self.assertEqual(1, (root / ".env.example").read_text(encoding="utf-8").count("WA_ACCESS_TOKEN="))

    def test_missing_anchors_are_rejected_without_overwriting_main(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            main = root / "main.py"
            main.write_text("print(1)\n", encoding="utf-8")
            (root / "whatsapp_safe.py").write_text("# placeholder", encoding="utf-8")
            with self.assertRaises(ValueError):
                patch_bot(root)
            self.assertEqual(main.read_text(encoding="utf-8"), "print(1)\n")

if __name__ == "__main__":
    unittest.main()
