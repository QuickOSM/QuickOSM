"""Tests for the preset and the history of queries."""
import json
import os

from qgis.core import QgsCoordinateReferenceSystem, QgsRectangle
from qgis.PyQt.QtWidgets import QDialogButtonBox
from qgis.testing import unittest

from QuickOSM.core.utilities.json_encoder import as_enum
from QuickOSM.core.utilities.query_saved import QueryManagement
from QuickOSM.core.utilities.tools import query_preset
from QuickOSM.definitions.format import Format
from QuickOSM.definitions.gui import Panels
from QuickOSM.ui.dialog import Dialog
from QuickOSM.ui.edit_preset import EditPreset


class TestBookmarkQuery(unittest.TestCase):
    """Tests for the preset and the history of queries."""

    def setUp(self):
        """Set up the tests"""
        self.maxDiff = None
        self.preset_folder = query_preset()

        self.dialog = Dialog()

        index = self.dialog.table_keys_values_qq.cellWidget(0, 1).findText('amenity')
        self.dialog.table_keys_values_qq.cellWidget(0, 1).setCurrentIndex(index)
        index = self.dialog.table_keys_values_qq.cellWidget(0, 2).findText('bench')
        self.dialog.table_keys_values_qq.cellWidget(0, 2).setCurrentIndex(index)
        self.dialog.places_edits[Panels.QuickQuery].setText('foo')
        self.dialog.button_save_query.click()

        self.preset = self.dialog.list_personal_preset_mp.item(0)
        layout_label = self.dialog.list_personal_preset_mp.itemWidget(self.preset).layout()
        self.name_preset = layout_label.itemAt(0).itemAt(0).widget().text()

    def set_up_preset_data_text(self) -> dict:
        """Load the data save in the json file linked to the preset."""
        preset_file = os.path.join(
            self.preset_folder, self.name_preset, self.name_preset + '.json')
        with open(preset_file, encoding='utf8') as json_file:
            data_preset = json.load(json_file)

        return data_preset

    def set_up_preset_data(self) -> dict:
        """Load the data save in the json file linked to the preset."""
        preset_folder = query_preset()
        preset_file = os.path.join(
            preset_folder, self.name_preset, self.name_preset + '.json')
        with open(preset_file, encoding='utf8') as json_file:
            data_preset = json.load(json_file, object_hook=as_enum)

        return data_preset

    def tearDown(self):
        """End of the tests"""
        self.dialog.external_panels[Panels.MapPreset].remove_preset(self.preset, self.name_preset)

    def test_save_in_preset(self):
        """Test if the file is save in preset."""
        nb_preset = self.dialog.list_personal_preset_mp.count()
        self.assertEqual(nb_preset, 1)
        self.assertEqual(self.name_preset, 'amenity_bench_foo')

    def test_preset_format(self):
        """Test if the file in preset is as expected."""
        data_preset = self.set_up_preset_data_text()

        expected_json = {
            "query":
                [
                    "[out:xml] [timeout:25];\n {{geocodeArea:foo}} -> .area_0;\n(\n"
                    "    node[\"amenity\"=\"bench\"](area.area_0);\n    "
                    "way[\"amenity\"=\"bench\"](area.area_0);\n    "
                    "relation[\"amenity\"=\"bench\"](area.area_0);\n);\n"
                    "(._;>;);\nout body;"
                ],
            "description":
                ["All OSM objects with the key 'amenity'='bench' in foo are going to be downloaded."],
            "advanced": False,
            "file_name": "amenity_bench_foo",
            "query_layer_name": ["amenity_bench_foo"],
            "query_name": ["Query1"],
            "type_multi_request": [[]],
            "keys": [["amenity"]],
            "values": [["bench"]],
            "area": ["foo"],
            "bbox": [""],
            "output_geom_type":
                [
                    [
                        {"__enum__": "LayerType.Points"},
                        {"__enum__": "LayerType.Lines"},
                        {"__enum__": "LayerType.Multilinestrings"},
                        {"__enum__": "LayerType.Multipolygons"}
                    ]
                ],
            "white_list_column":
                [{"multilinestrings": None, "points": None, "lines": None, "multipolygons": None}],
            "output_directory": [""],
            "output_format": [{"__enum__": "Format.GeoPackage"}]
        }

        self.assertDictEqual(expected_json, data_preset)

    def test_view_bookmark(self):
        """Test if we can display a preset."""
        data_preset = self.set_up_preset_data()

        edit_dialog = EditPreset(self.dialog, data_preset)

        self.assertEqual(data_preset['file_name'], edit_dialog.preset_name.text())
        self.assertEqual(
            data_preset['description'], edit_dialog.description.toPlainText().split('\\n')
        )
        self.assertEqual(data_preset['query_layer_name'][0], edit_dialog.layer_name.text())
        self.assertEqual(data_preset['query'][0], edit_dialog.query.toPlainText())
        self.assertEqual(data_preset['area'][0], edit_dialog.area.text())
        self.assertTrue(edit_dialog.bbox.outputExtent().isNull())
        self.assertTrue(edit_dialog.bbox.outputExtent().isNull())
        self.assertTrue(edit_dialog.checkbox_points.isChecked())
        self.assertTrue(edit_dialog.checkbox_lines.isChecked())
        self.assertTrue(edit_dialog.checkbox_multilinestrings.isChecked())
        self.assertTrue(edit_dialog.checkbox_multipolygons.isChecked())
        self.assertFalse(edit_dialog.white_points.text())
        self.assertFalse(edit_dialog.white_lines.text())
        self.assertFalse(edit_dialog.white_multilinestrings.text())
        self.assertFalse(edit_dialog.white_multipolygons.text())
        self.assertEqual(edit_dialog.combo_output_format.currentData(), Format.GeoPackage)
        self.assertEqual(
            data_preset['output_directory'][0], edit_dialog.output_directory.filePath()
        )

        nb_queries = edit_dialog.list_queries.count()
        self.assertEqual(nb_queries, 1)

        edit_dialog.preset_name.setText('Test a new name')
        edit_dialog.button_box.button(QDialogButtonBox.StandardButton.Cancel).click()

        self.dialog.external_panels[Panels.MapPreset].update_personal_preset_view()

        self.preset = self.dialog.list_personal_preset_mp.item(0)
        layout_label = self.dialog.list_personal_preset_mp.itemWidget(self.preset).layout()
        self.name_preset = layout_label.itemAt(0).itemAt(0).widget().text()
        self.assertNotEqual(self.name_preset, 'Test_a_new_name')

    def test_edit_rename_bookmark(self):
        """Test if we can edit and rename a preset."""
        data_preset = self.set_up_preset_data()

        edit_dialog = EditPreset(self.dialog, data_preset)
        edit_dialog.preset_name.setText('Test a new name')
        edit_dialog.button_box.button(QDialogButtonBox.StandardButton.Ok).click()

        self.dialog.external_panels[Panels.MapPreset].update_personal_preset_view()

        self.preset = self.dialog.list_personal_preset_mp.item(0)
        layout_label = self.dialog.list_personal_preset_mp.itemWidget(self.preset).layout()
        self.name_preset = layout_label.itemAt(0).itemAt(0).widget().text()
        self.assertEqual(self.name_preset, 'Test_a_new_name')

    def test_edited_bookmark_file(self):
        """Test if we can edit a preset and check the edited json file."""
        data_preset = self.set_up_preset_data()

        edit_dialog = EditPreset(self.dialog, data_preset)

        edit_dialog.description.setPlainText('Be or not to be...\\nShakespear')
        edit_dialog.layer_name.setText('Misery')
        edit_dialog.query.setPlainText('I would like two pencils please.')
        edit_dialog.checkbox_points.setChecked(True)
        edit_dialog.checkbox_lines.setChecked(True)
        edit_dialog.checkbox_multilinestrings.setChecked(False)
        edit_dialog.checkbox_multipolygons.setChecked(False)
        edit_dialog.white_points.setText('name')
        index = edit_dialog.combo_output_format.findData(Format.Kml)
        edit_dialog.combo_output_format.setCurrentIndex(index)

        edit_dialog.button_box.button(QDialogButtonBox.StandardButton.Ok).click()
        self.preset = self.dialog.list_personal_preset_mp.item(0)

        new_data = self.set_up_preset_data_text()

        expected_json = {
            "query":
                [
                    "I would like two pencils please."
                ],
            "description":
                ["Be or not to be...", "Shakespear"],
            "advanced": False,
            "file_name": "amenity_bench_foo",
            "query_layer_name": ["Misery"],
            "query_name": ["Query1"],
            "type_multi_request": [[]],
            "keys": [["amenity"]],
            "values": [["bench"]],
            "area": ["foo"],
            "bbox": [''],
            "output_geom_type":
                [
                    [
                        {"__enum__": "LayerType.Points"},
                        {"__enum__": "LayerType.Lines"}
                    ]
                ],
            "white_list_column":
                [{"multilinestrings": None, "points": 'name', "lines": None, "multipolygons": None}],
            "output_directory": [""],
            "output_format": [{"__enum__": "Format.Kml"}]
        }

        self.assertDictEqual(expected_json, new_data)

    def test_advanced_view(self):
        """Test if the view match the preset type."""
        data_preset = self.set_up_preset_data()

        edit_dialog = EditPreset(self.dialog, data_preset)

        current = edit_dialog.stacked_parameters_preset.currentWidget()
        self.assertEqual(current, edit_dialog.basic_parameters)

        edit_dialog.radio_advanced.setChecked(True)

        current = edit_dialog.stacked_parameters_preset.currentWidget()
        self.assertEqual(current, edit_dialog.advanced_parameters)

    def test_bookmark_several_query(self):
        """Test if we can manage (add and remove) several queries in a preset."""
        data_preset = self.set_up_preset_data()

        edit_dialog = EditPreset(self.dialog, data_preset)

        self.assertEqual(edit_dialog.current_query, 0)
        edit_dialog.add_query('Query2')

        nb_queries = edit_dialog.list_queries.count()
        self.assertEqual(nb_queries, 2)
        self.assertEqual(edit_dialog.current_query, 1)
        self.assertEqual(edit_dialog.layer_name.text(), '')

        edit_dialog.layer_name.setText('Query2')
        index = edit_dialog.table_keys_values_eb.cellWidget(0, 1).findText('type')
        edit_dialog.table_keys_values_eb.cellWidget(0, 1).setCurrentIndex(index)
        edit_dialog.table_keys_values_eb.cellWidget(0, 3).click()
        index = edit_dialog.table_keys_values_eb.cellWidget(1, 1).findText('route')
        edit_dialog.table_keys_values_eb.cellWidget(1, 1).setCurrentIndex(index)
        edit_dialog.key_edited(1)
        index = edit_dialog.table_keys_values_eb.cellWidget(1, 2).findText('bicycle')
        edit_dialog.table_keys_values_eb.cellWidget(1, 2).setCurrentIndex(index)
        index = edit_dialog.table_keys_values_eb.cellWidget(0, 2).findText('route')
        edit_dialog.table_keys_values_eb.cellWidget(0, 2).setCurrentIndex(index)

        edit_dialog.button_box.button(QDialogButtonBox.StandardButton.Ok).click()
        self.preset = self.dialog.list_personal_preset_mp.item(0)

        new_data = self.set_up_preset_data_text()

        expected_json = {
            "query":
                [
                    "[out:xml] [timeout:25];\n {{geocodeArea:foo}} -> .area_0;\n(\n"
                    "    node[\"amenity\"=\"bench\"](area.area_0);\n    "
                    "way[\"amenity\"=\"bench\"](area.area_0);\n    "
                    "relation[\"amenity\"=\"bench\"](area.area_0);\n);\n"
                    "(._;>;);\nout body;",
                    ""
                ],
            "description":
                ["All OSM objects with the key 'amenity'='bench' in foo are going to be downloaded."],
            "advanced": False,
            "file_name": "amenity_bench_foo",
            "query_layer_name": ["amenity_bench_foo", "Query2"],
            "query_name": ["Query1", "Query2"],
            "type_multi_request": [[], [{"__enum__": "MultiType.AND"}]],
            "keys": [["amenity"], ["type", "route"]],
            "values": [["bench"], ["route", "bicycle"]],
            "area": ["foo", ""],
            "bbox": ['', ''],
            "output_geom_type":
                [
                    [
                        {"__enum__": "LayerType.Points"},
                        {"__enum__": "LayerType.Lines"},
                        {"__enum__": "LayerType.Multilinestrings"},
                        {"__enum__": "LayerType.Multipolygons"}
                    ], [
                        {"__enum__": "LayerType.Points"},
                        {"__enum__": "LayerType.Lines"},
                        {"__enum__": "LayerType.Multilinestrings"},
                        {"__enum__": "LayerType.Multipolygons"}
                    ]
                ],
            "white_list_column":
                [
                    {"multilinestrings": None, "points": None, "lines": None, "multipolygons": None},
                    {"multilinestrings": None, "points": None, "lines": None, "multipolygons": None}
                ],
            "output_directory": ["", ""],
            "output_format": [{"__enum__": "Format.GeoPackage"}, None]
        }

        self.assertDictEqual(expected_json, new_data)

        edit_dialog.list_queries.setCurrentRow(0)
        self.assertEqual(edit_dialog.current_query, 0)
        self.assertEqual(edit_dialog.layer_name.text(), 'amenity_bench_foo')

        edit_dialog.delete_query(0)

        nb_queries = edit_dialog.list_queries.count()
        self.assertEqual(nb_queries, 1)
        self.assertEqual(edit_dialog.layer_name.text(), 'Query2')

        crs = QgsCoordinateReferenceSystem('EPSG:4326')
        x_min = 2.71828
        x_max = 3.1415926
        y_min = 0.0
        y_max = 1.6180339
        rect = QgsRectangle(x_min, y_min, x_max, y_max)
        edit_dialog.bbox.setOutputExtentFromUser(rect, crs)

        self.assertEqual(
            edit_dialog.stacked_parameters_preset.currentWidget(), edit_dialog.basic_parameters)
        edit_dialog.radio_advanced.setChecked(True)
        self.assertEqual(
            edit_dialog.stacked_parameters_preset.currentWidget(), edit_dialog.advanced_parameters)

        edit_dialog.button_box.button(QDialogButtonBox.StandardButton.Ok).click()
        self.preset = self.dialog.list_personal_preset_mp.item(0)

        new_data = self.set_up_preset_data_text()

        expected_json = {
            "query":
                [
                    ""
                ],
            "description":
                ["All OSM objects with the key 'amenity'='bench' in foo are going to be downloaded."],
            "advanced": True,
            "file_name": "amenity_bench_foo",
            "query_layer_name": ["Query2"],
            "query_name": ["Query1"],
            "type_multi_request": [[{"__enum__": "MultiType.AND"}]],
            "keys": [["type", "route"]],
            "values": [["route", "bicycle"]],
            "area": [""],
            "bbox": [{'__extent__': '2.71828 0.0 3.1415926 1.6180339'}],
            "output_geom_type":
                [
                    [
                        {"__enum__": "LayerType.Points"},
                        {"__enum__": "LayerType.Lines"},
                        {"__enum__": "LayerType.Multilinestrings"},
                        {"__enum__": "LayerType.Multipolygons"}
                    ]
                ],
            "white_list_column":
                [{"multilinestrings": None, "points": None, "lines": None, "multipolygons": None}],
            "output_directory": [""],
            "output_format": [None]
        }

        self.assertDictEqual(expected_json, new_data)

    def test_add_in_preset(self):
        """Test if we can add a query in a preset from the Quick Query panel."""
        data_preset = self.set_up_preset_data()

        edit_dialog = EditPreset(self.dialog, data_preset)

        nb_queries = edit_dialog.list_queries.count()
        self.assertEqual(nb_queries, 1)

        nb_preset = self.dialog.list_personal_preset_mp.count()
        self.assertEqual(nb_preset, 1)

        q_manage = QueryManagement(
            query='',
            name='aeroway_control_tower_foo',
            description='',
            advanced=False,
            keys='aeroway',
            values='control_tower',
            area='foo'
        )
        q_manage.add_query_in_preset('amenity_bench_foo')

        self.preset = self.dialog.list_personal_preset_mp.item(0)
        layout_label = self.dialog.list_personal_preset_mp.itemWidget(self.preset).layout()
        self.name_preset = layout_label.itemAt(0).itemAt(0).widget().text()

        data_preset = self.set_up_preset_data()

        edit_dialog = EditPreset(self.dialog, data_preset)

        nb_queries = edit_dialog.list_queries.count()
        self.assertEqual(nb_queries, 2)

        nb_preset = self.dialog.list_personal_preset_mp.count()
        self.assertEqual(nb_preset, 1)
