"""Checks for calendar integrity and safe standalone SVG generation."""
import copy
import importlib.util
import io
from datetime import date, timedelta
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET
from PIL import Image

spec = importlib.util.spec_from_file_location("refresh_profile", Path(__file__).with_name("refresh-profile.py"))
profile = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile)
NS = {"s": "http://www.w3.org/2000/svg"}

def calendar_fixture(length=365, count=1):
    weeks = []
    start = date(2025, 10, 8)
    for offset in range(length):
        day = start + timedelta(days=offset)
        weekday = (day.weekday() + 1) % 7
        if not weeks or weekday == 0:
            weeks.append({"contributionDays": []})
        weeks[-1]["contributionDays"].append({
            "date": day.isoformat(), "weekday": weekday,
            "contributionCount": count,
            "contributionLevel": "FIRST_QUARTILE" if count else "NONE",
        })
    return {"weeks": weeks, "totalContributions": length * count}

class ProfileTests(unittest.TestCase):
    def test_full_year_and_leap_year_render_one_cell_per_real_day(self):
        for length in (365, 366):
            with self.subTest(length=length):
                calendar = calendar_fixture(length, count=3)
                svg = ET.fromstring(profile.render_calendar(calendar))
                cells = svg.findall("s:rect", NS)
                self.assertEqual(len(cells), length)
                self.assertEqual(len({c.find("s:title", NS).text.split(":")[0] for c in cells}), length)
                self.assertEqual(cells[0].get("y"), "72")
                total = svg.find("s:text[@class='total']", NS).text
                self.assertIn(f"{length * 3:,}".replace(",", "."), total)
                self.assertIn("contribuições", total)

    def test_empty_activity_is_a_valid_calendar(self):
        svg = ET.fromstring(profile.render_calendar(calendar_fixture(count=0)))
        cells = svg.findall("s:rect", NS)
        self.assertTrue(all(c.get("class") == "cell" for c in cells))
        self.assertTrue(all(c.get("fill") == profile.COLORS[0] for c in cells))

    def test_bad_api_data_is_rejected(self):
        valid = calendar_fixture()
        for field, value in (("contributionCount", -1), ("contributionCount", True),
                             ("contributionLevel", "unknown"), ("weekday", 9),
                             ("date", "2020-01-01")):
            with self.subTest(field=field, value=value):
                invalid = copy.deepcopy(valid)
                invalid["weeks"][0]["contributionDays"][0][field] = value
                with self.assertRaises(ValueError):
                    profile.render_calendar(invalid)
        invalid = copy.deepcopy(valid)
        invalid["totalContributions"] += 1
        with self.assertRaises(ValueError):
            profile.render_calendar(invalid)
        with self.assertRaises(ValueError):
            profile.render_calendar(calendar_fixture(length=30))

    def test_portrait_fits_card_and_escapes_ascii(self):
        raw = io.BytesIO()
        Image.new("RGB", (400, 400), (200, 170, 130)).save(raw, format="PNG")
        portrait, rows = profile.render_portrait(raw.getvalue())
        svg = ET.fromstring(portrait)
        self.assertEqual(len(rows), 58)
        self.assertTrue(all(len(row) == 90 for row in rows))
        self.assertEqual(svg.get("viewBox"), "0 0 340 430")
        self.assertFalse(svg.findall(".//s:script", NS))
        self.assertFalse(svg.findall(".//s:image", NS))
        self.assertEqual(ET.fromstring(profile.text(1, 1, "<>&")).text, "<>&")

if __name__ == "__main__":
    unittest.main()
