"""Restore short-lived allocations during a Render container replacement."""
import ast
import asyncio
import json
import os
import re
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from data_storage import atomic_save

SOURCE = Path(__file__).with_name("main.py").read_text(encoding="utf-8")
TREE = ast.parse(SOURCE)


def isolated(names, globals_):
    selected = [
        node for node in TREE.body
        if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    assert len(selected) == len(names)
    exec(compile(ast.fix_missing_locations(
        ast.Module(body=selected, type_ignores=[])), "main.py", "exec"), globals_)


class ActiveLeaseRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = str(Path(self.temp.name) / "active_leases.json")
        self.active = {}
        self.orders = {}
        self.env = {
            "active_numbers": self.active, "miniapp_orders": self.orders,
            "ACTIVE_LEASES_FILE": self.path, "atomic_save": atomic_save,
            "asyncio": asyncio, "datetime": datetime, "json": json,
            "re": re, "normalize_number": lambda number: re.sub(r"\D", "", number),
            "mask_number": lambda value: value[:4] + "****" + value[-4:],
            "active_number_remaining": lambda info: max(
                0, 180 - int((datetime.now() - info["timestamp"]).total_seconds())),
        }
        isolated({"_persist_active_leases", "_restore_active_leases"}, self.env)

    def test_restore_only_unexpired_allocations_for_same_owner(self):
        now = datetime.now()
        self.active["447700900101"] = {
            "uid": 123, "range": "447700XXX",
            "timestamp": now - timedelta(seconds=65), "lease_id": "a" * 16,
        }
        self.active["447700900102"] = {
            "uid": 456, "range": "447700XXX",
            "timestamp": now - timedelta(seconds=220), "lease_id": "b" * 16,
        }
        self.env["_persist_active_leases"]()
        snapshot = json.loads(Path(self.path).read_text())
        self.assertEqual(list(snapshot), ["447700900101"])
        self.assertNotIn("otp", json.dumps(snapshot).lower())

        self.active.clear()
        count = self.env["_restore_active_leases"]()
        self.assertEqual(count, 1)
        self.assertEqual(self.active["447700900101"]["uid"], 123)
        self.assertEqual(self.orders[123][0]["id"], "a" * 16)
        self.assertEqual(self.orders[123][0]["full_number"], "+447700900101")
        self.assertNotIn(456, self.orders)

    def test_reject_corrupt_lease_and_expired_record(self):
        records = {
            "447700900101": {
                "uid": 123, "range": "447700XXX",
                "timestamp": (datetime.now() - timedelta(hours=2)).isoformat(),
                "lease_id": "a" * 16},
            "447700900102": {
                "uid": 456, "range": "447700XXX",
                "timestamp": datetime.now().isoformat(),
                "lease_id": "invalid"},
        }
        atomic_save(records, self.path)
        self.assertEqual(self.env["_restore_active_leases"](), 0)
        self.assertFalse(self.active)
        self.assertFalse(self.orders)

    def test_invalid_file_fails_closed(self):
        Path(self.path).write_text("{broken")
        with self.assertRaises(RuntimeError):
            self.env["_restore_active_leases"]()


if __name__ == "__main__":
    unittest.main()
