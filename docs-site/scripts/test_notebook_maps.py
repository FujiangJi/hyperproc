"""Tests for saved-map recovery; no notebook execution or remote requests."""
import unittest
from notebook_maps import WIDGET_STATE, WIDGET_VIEW, map_snapshot


class SavedMaps(unittest.TestCase):
    def test_saved_center_preview(self):
        output = {'text/plain': ['HBox(children=(Map(center=[35.1, -116.2], controls=(…']}
        snapshot = map_snapshot({}, output)
        self.assertEqual(snapshot['center'], [35.1, -116.2])
        self.assertEqual(snapshot['layers'], [])
        self.assertEqual(snapshot['evidence'], 'saved-center-only')

    def test_view_uses_its_own_map_and_saved_polygon(self):
        state = {
            'unrelated': {'model_name': 'LeafletMapModel', 'state': {'center': [0, 0]}},
            'box': {'state': {'children': ['IPY_MODEL_map']}},
            'map': {'model_name': 'LeafletMapModel', 'state': {'center': [35, -116], 'zoom': 10, 'layers': ['IPY_MODEL_polygon']}},
            'polygon': {'model_name': 'LeafletPolygonModel', 'state': {'locations': [[35, -116], [36, -116], [36, -115]], 'name': 'saved footprint'}},
        }
        notebook = {'metadata': {'widgets': {WIDGET_STATE: {'state': state}}}}
        snapshot = map_snapshot(notebook, {WIDGET_VIEW: {'model_id': 'box'}})
        self.assertEqual(snapshot['center'], [35, -116])
        self.assertEqual(snapshot['zoom'], 10)
        self.assertEqual(snapshot['layers'][0]['locations'], state['polygon']['state']['locations'])
        self.assertEqual(snapshot['evidence'], 'saved-widget-state')

    def test_widget_cycle_does_not_hang(self):
        notebook = {'metadata': {'widgets': {WIDGET_STATE: {'state': {
            'box': {'state': {'children': ['IPY_MODEL_box']}}}}}}}
        self.assertIsNone(map_snapshot(notebook, {WIDGET_VIEW: {'model_id': 'box'}}))

    def test_bad_or_executable_center_is_not_evaluated(self):
        for value in ['[100, 0]', '[True, 0]', '[__import__("os"), 0]']:
            self.assertIsNone(map_snapshot({}, {'text/plain': f'Map(center={value})'}))


if __name__ == '__main__':
    unittest.main()
