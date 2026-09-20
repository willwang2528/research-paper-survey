import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class EvolutionTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / 'scripts/evolve.py'
        self.assertTrue(path.exists(), 'Evolution implementation not created yet')
        spec = importlib.util.spec_from_file_location('evolve_test', path)
        self.e = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.e)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        skill = self.repo / 'skills/research-paper-survey'
        skill.mkdir(parents=True)
        (self.repo / 'VERSION').write_text('0.1.0\n')
        (skill / 'VERSION').write_text('0.1.0\n')
        (skill / 'SKILL.md').write_text('---\nname: research-paper-survey\ndescription: example\nmetadata:\n  version: "0.1.0"\n---\n')
        (self.repo / 'CHANGELOG.md').write_text('# Changelog\n')
        (self.repo / 'tests').mkdir()
        (self.repo / 'tests/test_sample.py').write_text('import unittest\nclass T(unittest.TestCase):\n def test_ok(self): self.assertTrue(True)\n')
        self.e.new_iteration(self.repo, 'fix', 'a concrete failing case', 'change the guard')

    def test_release_requires_passing_checks(self):
        with self.assertRaises(ValueError): self.e.release(self.repo, 'fix', '0.1.1', 'Fix')

    def test_changed_sources_invalidate_old_validation(self):
        self.e.check(self.repo, 'fix')
        (self.repo / 'code.py').write_text('print("changed")\n')
        with self.assertRaises(ValueError): self.e.release(self.repo, 'fix', '0.1.1', 'Fix')

    def test_release_updates_versions_and_records_evidence(self):
        self.e.check(self.repo, 'fix')
        data = self.e.release(self.repo, 'fix', '0.1.1', 'Fix')
        self.assertEqual((self.repo / 'VERSION').read_text().strip(), '0.1.1')
        self.assertEqual((self.repo / 'skills/research-paper-survey/VERSION').read_text().strip(), '0.1.1')
        self.assertEqual(data['previous_version'], '0.1.0')
        self.assertIn('0.1.1', (self.repo / 'CHANGELOG.md').read_text())
        with self.assertRaises(ValueError): self.e.release(self.repo, 'fix', '0.1.1', 'Again')

    def test_iteration_id_cannot_escape_repository(self):
        with self.assertRaises(ValueError): self.e.new_iteration(self.repo, '../escape', 'problem', 'proposal')


if __name__ == '__main__': unittest.main()
