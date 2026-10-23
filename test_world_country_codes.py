"""Offline regression tests for the All Countries directory and safe range listings."""
import ast
import unittest
from pathlib import Path

from world_country_codes import WORLD_COUNTRIES, build_all_country_rows, region_flag


class WorldCountryDirectoryTests(unittest.TestCase):
    def test_global_directory_unique_regions(self):
        self.assertGreaterEqual(len(WORLD_COUNTRIES), 240)
        self.assertEqual(len({row[0] for row in WORLD_COUNTRIES}), len(WORLD_COUNTRIES))
        self.assertTrue(all(isinstance(row[2], str) and row[2].isdigit()
                            for row in WORLD_COUNTRIES))
        self.assertIn(("AZ", "Azerbaijan", "994"), [tuple(row) for row in WORLD_COUNTRIES])
        self.assertIn(("XK", "Kosovo", "383"), [tuple(row) for row in WORLD_COUNTRIES])

    def test_all_regions_visible_even_when_api_is_empty(self):
        countries = build_all_country_rows({})
        self.assertEqual(len(countries), len(WORLD_COUNTRIES))
        self.assertTrue(all(not row["ranges"] for row in countries))
        self.assertEqual(region_flag("AZ"), "🇦🇿")

    def test_live_ranges_only_and_longest_calling_code(self):
        country_rows = build_all_country_rows({
            "tg": ["99450211", "1246XXX", "44-7700", "999999", "9945012345678"],
            "wa": ["99450211", "99455XXX"],
        })
        countries = {row["iso"]: row for row in country_rows}
        az = countries["AZ"]
        self.assertEqual(
            [(entry["rid"], entry["service"]) for entry in az["ranges"]],
            [("99450" + "211", "tg"), ("99450" + "211", "wa"), ("99455", "wa")]
        )
        self.assertEqual(len(countries["BB"]["ranges"]), 1)
        self.assertEqual(countries["BB"]["ranges"][0]["rid"], "1246")
        self.assertFalse(any(e["rid"] == "1246" for e in countries["US"]["ranges"]))
        self.assertEqual(countries["GB"]["ranges"][0]["rid"], "447700")
        self.assertFalse(any(e["rid"] == "9945012345678" for e in az["ranges"]))
        self.assertEqual(len(countries), len(WORLD_COUNTRIES))

    def test_shared_calling_codes_not_misrepresented(self):
        rows = build_all_country_rows({"wa": ["1XXX", "7XXX"]})
        canada = next(c for c in rows if c["iso"] == "CA")
        us = next(c for c in rows if c["iso"] == "US")
        russia = next(c for c in rows if c["iso"] == "RU")
        kazakhstan = next(c for c in rows if c["iso"] == "KZ")
        for country in (canada, us, russia, kazakhstan):
            self.assertTrue(country["is_shared"])
            self.assertEqual(len(country["ranges"]), 1)

    def test_all_countries_bot_view_uses_world_directory(self):
        source = Path("main.py").read_text(encoding="utf-8")
        root = ast.parse(source)
        view = next(node for node in root.body if isinstance(node, ast.AsyncFunctionDef)
                    and node.name == "show_all_countries")
        calls = [n.func.id for n in ast.walk(view)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)]
        self.assertIn("build_all_country_rows", calls)


if __name__ == "__main__":
    unittest.main()
