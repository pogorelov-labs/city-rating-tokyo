#!/usr/bin/env python3
"""Kit tests (B-9/G16). Run: python3 -m unittest discover -s kit/tests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from canonical import canon_family, canon_families  # noqa: E402


class TestCanonicalFamilies(unittest.TestCase):
    def test_wikipedia_language_editions_merge(self):
        for raw in ("English Wikipedia", "Thai Wikipedia", "Wikipedia (EN)",
                    "Wikipedia (TH)", "Wikimedia (Wikipedia EN)", "Wikipedia",
                    "wikipedia", "Wikimedia Foundation", "Wikivoyage"):
            self.assertEqual(canon_family(raw), "wikimedia", raw)

    def test_osm_variants_merge(self):
        for raw in ("OpenStreetMap", "OpenStreetMap via Overpass API",
                    "OpenStreetMap / Overpass", "osm-overpass", "openstreetmap"):
            self.assertEqual(canon_family(raw), "openstreetmap", raw)

    def test_portal_casing_variants_merge(self):
        for raw in ("HipFlat", "hipflat", "HipFlat (via search snippet)",
                    "Hipflat / property portals", "HipFlat (property portal)"):
            self.assertEqual(canon_family(raw), "hipflat", raw)
        self.assertEqual(canon_family("FazWaz"), "fazwaz")
        self.assertEqual(canon_family("DDproperty"), "propertyguru-group")

    def test_named_publisher_variants_merge(self):
        self.assertEqual(canon_family("Time Out Bangkok"), "time-out")
        self.assertEqual(canon_family("Thai PBS (public broadcaster)"), "thai-pbs")
        self.assertEqual(canon_family("bkmagazine"), "bk-magazine")
        self.assertEqual(canon_family("Nation Group"), "nation-group")
        self.assertEqual(canon_family("onebangkok_developer"), "onebangkok")
        self.assertEqual(canon_family("condoreviewsthailand.com (independent)"), "condo-reviews")

    def test_generic_buckets_never_merge_with_named(self):
        # news-media must NOT become a named publisher
        self.assertEqual(canon_family("news-media"), "news-media")
        self.assertEqual(canon_family("real_estate_portal"), "real_estate_portal")
        self.assertEqual(canon_family("transit-operator"), "transit-operator")
        self.assertEqual(canon_family("user-generated"), "user-generated")
        self.assertEqual(canon_family("lifestyle_blog"), "lifestyle_blog")
        # and distinct named publishers stay distinct
        self.assertEqual(canon_family("PropertyScout"), "property-scout")
        self.assertNotEqual(canon_family("PropertyScout"), canon_family("PropertySights"))
        self.assertNotEqual(canon_family("Thairath"), canon_family("Nation Group"))

    def test_telegram_channels_never_merge_with_outlets(self):
        # third review (2026-11-08): a channel displaying an outlet's name is a
        # different publisher — masquerading risk (see telegram-channels.json)
        self.assertEqual(canon_family("Bangkok Post (Telegram channel)"),
                         "Bangkok Post (Telegram channel)")
        self.assertEqual(
            canon_family("Telegram channel 'BANGKOK POST' (operator unknown)"),
            "Telegram channel 'BANGKOK POST' (operator unknown)")
        self.assertNotEqual(canon_family("Bangkok Post (Telegram channel)"),
                            canon_family("Bangkok Post"))
        self.assertNotEqual(
            canon_family("Telegram channel 'BANGKOK POST' (operator unknown)"),
            canon_family("Bangkok Post"))

    def test_unknown_passthrough_and_case(self):
        self.assertEqual(canon_family("Khaosod English"), "Khaosod English")
        self.assertEqual(canon_family("  Khaosod English "), "Khaosod English")
        self.assertEqual(canon_family(""), "")
        self.assertIsNone(canon_family(None))

    def test_canon_families_set(self):
        self.assertEqual(canon_families(["English Wikipedia", "Thai Wikipedia"]),
                         {"wikimedia"})
        self.assertEqual(len(canon_families(["English Wikipedia", "OpenStreetMap"])), 2)


if __name__ == "__main__":
    unittest.main()
