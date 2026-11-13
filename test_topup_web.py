"""Focused validation tests for the Mini App receipt flow."""
import base64
import unittest

from topup_ledger import TopupError
from topup_web import parse_amount_cents, decode_receipt


class ReceiptValidationTests(unittest.TestCase):
    def test_amounts_in_integer_cents(self):
        self.assertEqual(parse_amount_cents("1"), 100)
        self.assertEqual(parse_amount_cents("2.50"), 250)
        self.assertEqual(parse_amount_cents("10000"), 1_000_000)

    def test_reject_invalid_amounts(self):
        for amount in ("0", "0.99", "10000.01", "-1", "1.234", "NaN", "1e4", 5):
            with self.subTest(amount=amount), self.assertRaises(TopupError):
                parse_amount_cents(amount)

    def test_png_receipt(self):
        raw = b"\x89PNG\r\n\x1a\n" + b"x" * 40
        data, filename = decode_receipt("data:image/png;base64," + base64.b64encode(raw).decode())
        self.assertEqual(data, raw)
        self.assertEqual(filename, "receipt.png")

    def test_reject_bad_receipt(self):
        for value in ("", "data:text/plain;base64,YWJj", "data:image/png;base64,abc!",
                      "data:image/jpeg;base64," + base64.b64encode(b"x" * 50).decode()):
            with self.subTest(value=value[:35]), self.assertRaises(TopupError):
                decode_receipt(value)


if __name__ == "__main__":
    unittest.main()
