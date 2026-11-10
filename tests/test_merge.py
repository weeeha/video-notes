"""Run: python3 -m unittest discover tests"""
import importlib.util, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("vn", ROOT / "skills/video-notes/video-notes.py")
vn = importlib.util.module_from_spec(spec); spec.loader.exec_module(vn)


class MergeTest(unittest.TestCase):
    def setUp(self):
        self.segs = vn.parse_srt(Path(__file__).with_name("demo.srt"))

    def test_steady_talk_keeps_one_row_per_screen(self):
        # demo: three notes about three screen regions, starting at 0 s, 6 s and 14 s
        rows = vn.merge(self.segs)
        self.assertEqual([round(r[0]) for r in rows], [0, 6, 14])

    def test_rows_never_exceed_cap(self):
        for r in vn.merge(self.segs, max_len=8.0):
            self.assertLessEqual(r[1] - r[0], 8.0)

    def test_stutter_still_collapses(self):
        rows = vn.merge([[0, 1, "make it bigger"], [1.5, 2.5, "Make it bigger"]])
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
