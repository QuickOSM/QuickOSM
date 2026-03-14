"""Test the osm file loader panel."""

import unittest

from qgis.core import QgsProject

from QuickOSM.definitions.osm import MultiType
from QuickOSM.tools.resources import plugin_test_data_path
from QuickOSM.ui.dialog import Dialog
from QuickOSM.ui.osm_file_panel import OsmFilePanel



class TestFileLoader(unittest.TestCase):
    """Test the osm file loader panel."""

    def setUp(self):
        self.file = plugin_test_data_path('osm_parser', 'map.osm')

    def test_generate_filter(self):
        """Test if we can obtain a valid filter expression"""

        # 1 couple key/value
        properties = {
            'key': ['foo'],
            'value': ['bar'],
            'type_multi_request': []
        }

        expression = OsmFilePanel.generate_sql(properties)
        expected_exp = '\"foo\"=\'bar\''
        self.assertEqual(expected_exp, expression)

        # 2 couples key/value, AND
        properties = {
            'key': ['foo', 'foofoo'],
            'value': ['bar', 'barbar'],
            'type_multi_request': [MultiType.AND]
        }

        expression = OsmFilePanel.generate_sql(properties)
        expected_exp = '(\"foo\"=\'bar\' AND \"foofoo\"=\'barbar\')'
        self.assertEqual(expected_exp, expression)

        # 2 couples key/value, OR
        properties = {
            'key': ['foo', 'foofoo'],
            'value': ['bar', 'barbar'],
            'type_multi_request': [MultiType.OR]
        }

        expression = OsmFilePanel.generate_sql(properties)
        expected_exp = '\"foo\"=\'bar\' OR \"foofoo\"=\'barbar\''
        self.assertEqual(expected_exp, expression)

    def test_load_only(self):
        """Test if we can only load a file."""

        dialog = Dialog()
        dialog.osm_file.setFilePath(self.file)
        dialog.radio_osm_conf.setChecked(True)
        dialog.button_run_file.click()
        project = QgsProject().instance()
        nb_layers = len(project.mapLayers())
        self.assertEqual(nb_layers, 4)

        project.clear()


if __name__ == '__main__':
    unittest.main()
