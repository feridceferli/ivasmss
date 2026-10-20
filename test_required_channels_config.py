import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from required_channels_config import load_channels, merge_channels, pinned_channels
from data_storage import data_path


class RequiredChannelsTests(unittest.TestCase):
    def setUp(self):
        self.defaults = pinned_channels()

    def test_all_three_links_are_persisted_in_source(self):
        self.assertEqual([row["link"] for row in self.defaults], [
            "https://t.me/betrunaz", "https://t.me/+zNOPEh3GpI83ZDli",
            "https://t.me/+MCTJqBiqQ1piMjIy"])

    def test_missing_private_ids_are_inspectable_without_new_impossible_gate(self):
        self.assertEqual(len(merge_channels([], self.defaults, {})), 1)
        rows = merge_channels([], self.defaults, {}, include_pending=True)
        self.assertEqual(len(rows), 3)
        self.assertFalse(rows[0]["verification_pending"])
        self.assertTrue(rows[1]["verification_pending"])

    def test_existing_private_ids_and_other_requirements_are_preserved(self):
        runtime = [{"link": self.defaults[1]["link"], "chat_id": -1001234567890},
                   {"link": "https://t.me/another", "username": "another"}]
        rows = merge_channels(runtime, self.defaults, {})
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[1]["chat_id"], -1001234567890)
        self.assertEqual(rows[-1], runtime[-1])
        self.assertEqual(len(runtime), 2)

    def test_environment_ids_activate_private_requirements_without_runtime_file(self):
        env = {"REQUIRED_CHANNEL_2_ID": "-1001234567890", "REQUIRED_CHANNEL_3_ID": "-1001234567891"}
        with tempfile.TemporaryDirectory() as folder, patch.dict("os.environ", env, clear=True):
            path = Path(folder) / "required_channels.json"
            for _ in range(2):
                rows = load_channels(path)
                self.assertEqual(len(rows), 3)
                self.assertEqual(rows[1]["chat_id"], -1001234567890)
                self.assertFalse(rows[2]["verification_pending"])

    def test_pinned_channels_survive_empty_runtime_file_and_source_ids_work(self):
        defaults = [dict(row) for row in self.defaults]
        defaults[1]["chat_id"] = -1001234567890
        defaults[2]["chat_id"] = -1001234567891
        self.assertEqual(len(merge_channels([], defaults, {})), 3)
        self.assertEqual(len(merge_channels([], defaults, {})), 3)

    def test_invalid_environment_value_does_not_replace_existing_id(self):
        runtime = [{"link": self.defaults[1]["link"], "chat_id": -1001234567890}]
        rows = merge_channels(runtime, self.defaults, {"REQUIRED_CHANNEL_2_ID": "invalid"})
        self.assertEqual(rows[1]["chat_id"], -1001234567890)

    def test_startup_seeds_and_restores_requirements_without_touching_other_data(self):
        with tempfile.TemporaryDirectory() as folder, patch.dict("os.environ", {"DB_FOLDER": folder}, clear=True):
            path = Path(data_path("required_channels.json"))
            self.assertEqual(json.loads(path.read_text())[0]["username"], "betrunaz")
            path.write_text(json.dumps([{"link": self.defaults[1]["link"], "chat_id": -1001234567890}]))
            data_path("required_channels.json")
            rows = json.loads(path.read_text())
            self.assertEqual(len(rows), 2)
            self.assertEqual(rows[1]["chat_id"], -1001234567890)
            users = Path(folder) / "users.json"
            users.write_text('{"example": {"balance": 1}}')
            data_path("users.json")
            self.assertEqual(users.read_text(), '{"example": {"balance": 1}}')


if __name__ == "__main__":
    unittest.main()
