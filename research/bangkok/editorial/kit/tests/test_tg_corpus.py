#!/usr/bin/env python3
"""tg_corpus parser tests (D-6, B-9). No network — fixture HTML only."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))
import tg_corpus  # noqa: E402

FIXTURE = """
<div class="tgme_widget_message ..." data-post="ch_example/41" data-view="...">
  <time datetime="2026-11-08T09:15:00Z+0000"></time>
  <div class="tgme_widget_message_text js-message_text" dir="auto">
    Sathorn pier closed <a href="https://example.com/a">notice</a><br/>until Friday <b>16:00</b>
  </div>
  <div class="tgme_widget_message_footer"><span class="tgme_widget_message_views">1.2K</span></div>
</div>
<div class="tgme_widget_message ..." data-post="ch_example/40" data-view="...">
  <time datetime="2026-11-08T08:00:00Z+0000"></time>
  <div class="tgme_widget_message_photo_wrap"></div>
</div>
"""


class TestTgCorpus(unittest.TestCase):
    def test_parse_feed(self):
        msgs = tg_corpus.parse_feed(FIXTURE)
        self.assertEqual([m["id"] for m in msgs], [41, 40])
        self.assertEqual(msgs[0]["datetime"], "2026-11-08T09:15:00")
        self.assertEqual(msgs[0]["views"], "1.2K")
        self.assertIn("notice (https://example.com/a)", msgs[0]["text"])
        self.assertIn("until Friday", msgs[0]["text"])
        self.assertNotIn("<b>", msgs[0]["text"])
        self.assertEqual(msgs[1]["text"], "[media-only post]")

    def test_clean_text_strips_and_unescapes(self):
        self.assertEqual(tg_corpus.clean_text("a &amp; b<i>x</i>  c"), "a & bx c")

    def test_markup_stripped_inner_text_kept(self):
        # corpus stores untrusted text verbatim (markup stripped, content kept);
        # the G20 sweep is the gate if such text ever reaches bundle copy
        self.assertEqual(tg_corpus.clean_text("<script>alert(1)</script>Sathorn"), "alert(1)Sathorn")


if __name__ == "__main__":
    unittest.main()
