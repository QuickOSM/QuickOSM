"""Tests for the overpass panel file."""
from typing import Tuple

from qgis.core import (
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsProject,
    QgsVectorLayer,
    edit,
)
from qgis.testing import unittest

from QuickOSM.core.exceptions import NoSelectedFeatures
from QuickOSM.definitions.gui import Panels
from QuickOSM.definitions.osm import QueryType
from QuickOSM.ui.dialog import Dialog


class TestQuickOSMWidget(unittest.TestCase):
    """Tests for the overpass panel file."""

    def test_sort_nominatim_places(self):
        """Test if reorder last nominatim places works."""
        dialog = Dialog()

        existing_places = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
        new_list = dialog.external_panels[Panels.QuickQuery].sort_nominatim_places(
            existing_places, '3')
        expected = ['3', '1', '2', '4', '5', '6', '7', '8', '9', '10']
        self.assertListEqual(expected, new_list)

        existing_places = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
        new_list = dialog.external_panels[Panels.QuickQuery].sort_nominatim_places(
            existing_places, '11')
        expected = ['11', '1', '2', '3', '4', '5', '6', '7', '8', '9']
        self.assertListEqual(expected, new_list)

        existing_places = ['1', '2', '3', '4', '5']
        new_list = dialog.external_panels[Panels.QuickQuery].sort_nominatim_places(
            existing_places, '3')
        expected = ['3', '1', '2', '4', '5']
        self.assertListEqual(expected, new_list)

        existing_places = ['1', '2', '3', '4', '5']
        new_list = dialog.external_panels[Panels.QuickQuery].sort_nominatim_places(
            existing_places, '6')
        expected = ['6', '1', '2', '3', '4', '5']
        self.assertListEqual(expected, new_list)

        existing_places = ['1', '2', '3', '4', '5']
        new_list = dialog.external_panels[Panels.QuickQuery].sort_nominatim_places(
            existing_places, '1')
        expected = ['1', '2', '3', '4', '5']
        self.assertListEqual(expected, new_list)

        existing_places = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
        new_list = dialog.external_panels[Panels.QuickQuery].sort_nominatim_places(
            existing_places, '1')
        expected = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10']
        self.assertListEqual(expected, new_list)

    @staticmethod
    def selected_features_set_up() -> Tuple[Dialog, QgsVectorLayer]:
        """Set the tests about the selected features."""
        dialog = Dialog()
        project: QgsProject = QgsProject.instance()
        project.clear()

        # Creating a new layer
        layer = QgsVectorLayer('Point?crs=epsg:4326&field=id:integer&index=yes', 'layer', 'memory')
        with edit(layer):
            feature1 = QgsFeature()
            feature1.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(10, 10)))
            feature1.setAttributes([1])
            feature2 = QgsFeature()
            feature2.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(5, 15)))
            feature2.setAttributes([2])
            feature3 = QgsFeature()
            feature3.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(25, 40)))
            feature3.setAttributes([3])
            layer.addFeatures([feature1, feature2, feature3])
        project.addMapLayer(layer)

        index = dialog.combo_query_type_qq.findData('layer')
        dialog.combo_query_type_qq.setCurrentIndex(index)
        dialog.selection_features[Panels.QuickQuery].setChecked(True)

        return dialog, layer

    def test_no_selected_features(self):
        """ Test the exception about the selected features option """
        dialog, layer = self.selected_features_set_up()

        with self.assertRaises(NoSelectedFeatures):
            dialog.external_panels[Panels.QuickQuery].gather_values()

    def test_selected_features(self):
        """ Test the selected features option """
        dialog, layer = self.selected_features_set_up()
        layer.select(1)
        layer.select(2)
        properties_select = dialog.external_panels[Panels.QuickQuery].gather_values()
        self.assertEqual(properties_select['query_type'], QueryType.BBox)

        dialog.selection_features[Panels.QuickQuery].setChecked(False)
        properties_all = dialog.external_panels[Panels.QuickQuery].gather_values()
        self.assertNotEqual(properties_select['bbox'], properties_all['bbox'])


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestQuickOSMWidget)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
