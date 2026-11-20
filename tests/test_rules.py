from dataclasses import replace
from pathlib import Path
import json
import shutil
import tempfile
import unittest

from editcheck.provenance import check_manifest
from editcheck.rules import Clip, Profile, Snapshot, check_timeline, timeline_changes


class TimelineRulesTests(unittest.TestCase):
    def test_reports_move_and_retrack_with_half_open_bounds(self):
        old = Clip('Results', 2, 145, 289)
        moved = replace(old, track=3, start=193, stop=337)
        first = Snapshot('Demo', Profile(1920, 1080, 24), (old,))
        second = replace(first, clips=(moved,))
        [change] = timeline_changes(first, second)
        self.assertEqual(change.before, old)
        self.assertEqual(change.after, moved)
        self.assertEqual(timeline_changes(second, second), ())

    def test_missing_original_and_profile_are_independent_of_proxy(self):
        clip = Clip('Methods', 2, 1, 145, missing_sources=('methods.mp4',), proxy_enabled=True)
        snapshot = Snapshot('Demo', Profile(1280, 720, 30), (clip,))
        issues = check_timeline(snapshot, Profile(1280, 720, 24))
        self.assertEqual([issue.code for issue in issues], ['MISSING_ORIGINAL', 'FRAME_RATE_MISMATCH'])
        self.assertIn('Proxy use is enabled', issues[0].detail)
        self.assertEqual(check_timeline(replace(snapshot, clips=(replace(clip, muted=True),)))[0].level, 'warning')

    def test_fractional_frame_rate_is_not_rounded_to_24(self):
        snapshot = Snapshot('Demo', Profile(1280, 720, 24000 / 1001), (Clip('Results', 2, 145, 289),))
        self.assertFalse(check_timeline(snapshot, Profile(1280, 720, 23.976)))
        self.assertEqual(check_timeline(snapshot, Profile(1280, 720, 24))[0].code, 'FRAME_RATE_MISMATCH')


class ManifestTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        source = Path(__file__).resolve().parents[1] / 'examples' / 'research'
        self.sample = Path(temporary.name) / 'research'
        shutil.copytree(source, self.sample, ignore=shutil.ignore_patterns('__pycache__'))
        self.manifest = self.sample / 'manifest.json'

    def test_clean_then_stale_input(self):
        self.assertEqual(check_manifest(self.manifest), ())
        csv = self.sample / 'measurements.csv'
        csv.write_text(csv.read_text().replace('methods-c,20', 'methods-c,26'), encoding='utf-8')
        [issue] = check_manifest(self.manifest)
        self.assertEqual(issue.code, 'RESEARCH_FILE_CHANGED')
        self.assertIn('Input', issue.detail)
        self.assertIn('measurements.csv', issue.detail)

    def test_manifest_cannot_reference_outside_its_directory(self):
        original = json.loads(self.manifest.read_text(encoding='utf-8'))
        original['figures'][0]['inputs'][0]['path'] = '../outside.csv'
        self.manifest.write_text(json.dumps(original), encoding='utf-8')
        [issue] = check_manifest(self.manifest)
        self.assertEqual(issue.code, 'MANIFEST_INVALID')


if __name__ == '__main__':
    unittest.main()
