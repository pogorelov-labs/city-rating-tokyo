#!/usr/bin/env python3
"""Corroboration + conflicts passthrough behavior of kit/assemble.py (B-9)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import assemble  # noqa: E402


def raw_bundle(fam_a, fam_b, conflicts=None):
    return {
        "sources": [
            {"index": 0, "canonical_url": "https://a.example/x", "title": "A",
             "publisher": "PubA", "publisher_family": fam_a, "type": "other",
             "body_read": True, "retrieved_at": "2026-11-08T00:00:00Z"},
            {"index": 1, "canonical_url": "https://b.example/y", "title": "B",
             "publisher": "PubB", "publisher_family": fam_b, "type": "news",
             "body_read": True, "retrieved_at": "2026-11-08T00:00:00Z"},
        ],
        "claims": [{
            "claim_id": "testx-c01", "text_en": "A test claim.",
            "kind": "factual_report", "topics": ["test"], "polarity": "neutral",
            "geography": {"scope": "station_area", "place_name": "Test",
                          "relation_to_entity": "inside", "notes": ""},
            "temporal_scope": {"event_date": None, "observed_period": None,
                               "recheck_by": None, "notes": ""},
            "evidence": [{"source_index": 0, "locator": "s1", "paraphrase": "a"},
                         {"source_index": 1, "locator": "s2", "paraphrase": "b"}],
            "limitations": [], "conflicts_with": conflicts or [],
        }],
        "question_answers": [{"id": "Q01", "status": "answered",
                              "claim_ids": ["testx-c01"], "notes": "n"}] +
                             [{"id": f"Q{i:02d}", "status": "not_applicable",
                               "claim_ids": [], "notes": ""}
                              for i in range(2, 13)],
        "editorial": {"preview": {"text_en": "P", "claim_ids": ["testx-c01"]},
                      "guide_lead": {"text_en": "L", "claim_ids": ["testx-c01"]},
                      "strengths": [], "tradeoffs": [], "day_night": [],
                      "within_area_variation": [], "conditional_fit": [],
                      "uncertainties": []},
        "open_issues": [],
    }


ENT = {"kind": "station_area", "name_en": "Test", "name_th": "T",
       "aliases": [], "scope_notes": "", "model_score_default": 7.5,
       "cohort_rank": 1, "cohort_size": 133, "selection_rationale": "r"}
BATCH = {"app_snapshot_id": "test", "popularity_method": "none"}


class TestAssembleCorroboration(unittest.TestCase):
    def test_wiki_language_pair_counts_as_one_family(self):
        counts = {}
        b = assemble.assemble("st.testx", ENT, raw_bundle("English Wikipedia",
                                                          "Thai Wikipedia"), BATCH, counts)
        self.assertEqual(b["claims"][0]["review_status"], "proposed")
        self.assertEqual(counts["canonical_family_merge"], 1)
        # provenance stays raw
        self.assertEqual({s["publisher_family"] for s in b["sources"]},
                         {"English Wikipedia", "Thai Wikipedia"})

    def test_two_canonical_families_corroborate(self):
        b = assemble.assemble("st.testx", ENT,
                              raw_bundle("English Wikipedia", "OpenStreetMap"), BATCH, {})
        self.assertEqual(b["claims"][0]["review_status"], "corroborated")

    def test_conflicts_with_passthrough_filters_unknown(self):
        b = assemble.assemble("st.testx", ENT,
                              raw_bundle("English Wikipedia", "OpenStreetMap",
                                         conflicts=["testx-c01", "testx-c09"]), BATCH, {})
        # assemble only drops ids outside the bundle; self-links survive here and
        # are flagged as errors by validate.py / P1 by audit.py (defense in depth)
        self.assertEqual(b["claims"][0]["conflicts_with"], ["testx-c01"])

    def test_conflicts_with_empty_by_default(self):
        b = assemble.assemble("st.testx", ENT,
                              raw_bundle("English Wikipedia", "OpenStreetMap"), BATCH, {})
        self.assertEqual(b["claims"][0]["conflicts_with"], [])


if __name__ == "__main__":
    unittest.main()
