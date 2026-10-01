"""Keep restored map records bound to the saved result identifiers."""
import json
from pathlib import Path
import tempfile
import unittest
from granule_recordings import result_context, recorded_snapshot


class GranuleRecordings(unittest.TestCase):
    def test_saved_context_and_matching_boundaries(self):
        text = 'searching EMITL2ARFL (EMIT L2A):\n    bounding_box = (-121, 34, -119, 36)\n    temporal = ("2023-01-01", "2023-12-31")\ngranule     when      size  cloud\nscene_001  2023-01-26 22:02  1,500M  10%\n'
        nb = {'cells': [{'outputs': [{'text': [text]}]}, {'source': ['hp.search_map(results=hits)']}]}
        context = result_context(nb, 1)
        self.assertEqual(context['rows'][0]['name'], 'scene_001')
        self.assertEqual(context['kwargs']['bbox'], (-121, 34, -119, 36))
        center = {'center': [35, -120], 'layers': [], 'evidence': 'saved-center-only'}
        record = {'key': context['key'], 'retrieved_at': '2026-10-01', 'granules': [
            {'saved_name': 'scene_001', 'name': 'scene_001', 'bbox': [-120, 34, -119, 35]}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/(context['key']+'.json')
            path.write_text(json.dumps(record))
            snapshot = recorded_snapshot(directory, context, center)
            self.assertEqual(snapshot['layers'][0]['locations'], [[34, -120], [35, -119]])
            record['granules'][0]['saved_name'] = 'different_scene'
            path.write_text(json.dumps(record))
            self.assertEqual(recorded_snapshot(directory, context, center), center)

    def test_source_change_invalidates_record_key(self):
        text = 'searching EMITL2ARFL (EMIT L2A):\ngranule when size cloud\nscene_001  2023-01-26 22:02  1M  -\n'
        nb = {'cells': [{'outputs': [{'text': [text]}]}, {'source': ['hp.search_map(results=hits)']}]}
        original = result_context(nb, 1)['key']
        nb['cells'][1]['source'] = ['hp.search_map(results=hits[:1])']
        self.assertNotEqual(result_context(nb, 1)['key'], original)


if __name__ == '__main__':
    unittest.main()
