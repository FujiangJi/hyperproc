"""Regression tests: renamed parameters/exports must fail documentation checks."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import audit_guides


class GuideAuditTests(unittest.TestCase):
    def check_guide(self, example):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            docs = repo/'docs-site'
            (docs/'docs').mkdir(parents=True)
            (repo/'hyperproc').mkdir()
            (repo/'pyproject.toml').write_text('[project.optional-dependencies]\nsearch = ["requests"]\n')
            (repo/'hyperproc/__init__.py').write_text('from hyperproc.operations import correct as apply\n')
            (repo/'hyperproc/operations.py').write_text('def correct(ds, *, mode="default"):\n    pass\n')
            (docs/'docs/index.md').write_text(example)
            with patch.multiple(audit_guides, ROOT=docs, REPO=repo):
                return audit_guides.audit()

    def test_current_alias_and_keyword_pass(self):
        errors, counts = self.check_guide('```python\nimport hyperproc as hp\nhp.apply(ds, mode="local")\n```')
        self.assertEqual(errors, [])
        self.assertEqual(counts['source_bound_calls'], 1)

    def test_removed_keyword_fails(self):
        errors, _ = self.check_guide('```python\nhp.apply(ds, old_mode="local")\n```')
        self.assertTrue(any('old_mode' in error for error in errors))

    def test_missing_required_input_fails(self):
        errors, _ = self.check_guide('```python\nhp.apply()\n```')
        self.assertTrue(any('ds' in error for error in errors))

    def test_removed_export_fails(self):
        errors, _ = self.check_guide('```python\nhp.removed(ds)\n```')
        self.assertTrue(any('callable not found' in error for error in errors))

    def test_unknown_extra_fails(self):
        errors, _ = self.check_guide("```bash\npip install 'hyperproc[missing]'\n```")
        self.assertTrue(any('unknown install extra' in error for error in errors))


if __name__ == '__main__':
    unittest.main()
