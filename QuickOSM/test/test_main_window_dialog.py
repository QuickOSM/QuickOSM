"""Tests for the main window."""

from qgis.testing import unittest

from QuickOSM.definitions.gui import Panels
from QuickOSM.ui.dialog import Dialog


class TestUiMainWindow(unittest.TestCase):
    """Tests for the main window."""

    def test_show_query_empty(self):
        """Test we can show a query by switching tab with all params."""
        dialog = Dialog()
        index = dialog.combo_query_type_qq.findData('canvas')
        dialog.combo_query_type_qq.setCurrentIndex(index)
        dialog.button_show_query.click()
        expected_index = dialog.stacked_panels_widget.indexOf(dialog.query_page)
        self.assertEqual(dialog.stacked_panels_widget.currentIndex(), expected_index)
        self.assertNotEqual(dialog.text_query.toPlainText(), '')

    def test_show_query_key_value_in(self):
        """Test we can show a query by switching tab with key value in params."""
        dialog = Dialog()
        index = dialog.table_keys_values_qq.cellWidget(0, 1).findData('amenity')
        dialog.table_keys_values_qq.cellWidget(0, 1).setCurrentIndex(index)
        index = dialog.table_keys_values_qq.cellWidget(0, 2).findData('bench')
        dialog.table_keys_values_qq.cellWidget(0, 2).setCurrentIndex(index)
        dialog.places_edits[Panels.QuickQuery].setText('foo')
        dialog.button_show_query.click()
        expected_index = dialog.stacked_panels_widget.indexOf(dialog.query_page)
        self.assertEqual(dialog.stacked_panels_widget.currentIndex(), expected_index)
        self.assertNotEqual(dialog.text_query.toPlainText(), '')

    def test_show_query_oql(self):
        """Test we can show a query in OQL by switching tab."""
        dialog = Dialog()
        index = dialog.table_keys_values_qq.cellWidget(0, 1).findData('amenity')
        dialog.table_keys_values_qq.cellWidget(0, 1).setCurrentIndex(index)
        index = dialog.table_keys_values_qq.cellWidget(0, 2).findData('bench')
        dialog.table_keys_values_qq.cellWidget(0, 2).setCurrentIndex(index)
        dialog.places_edits[Panels.QuickQuery].setText('foo')
        dialog.action_oql_qq.trigger()
        dialog.button_show_query.click()
        expected_index = dialog.stacked_panels_widget.indexOf(dialog.query_page)
        self.assertEqual(dialog.stacked_panels_widget.currentIndex(), expected_index)
        self.assertNotEqual(dialog.text_query.toPlainText(), '')
        self.assertEqual(dialog.text_query.toPlainText()[-1], ';')

    def test_show_query_xml(self):
        """Test we can show a query in XML by switching tab."""
        dialog = Dialog()
        index = dialog.table_keys_values_qq.cellWidget(0, 1).findData('amenity')
        dialog.table_keys_values_qq.cellWidget(0, 1).setCurrentIndex(index)
        index = dialog.table_keys_values_qq.cellWidget(0, 2).findData('bench')
        dialog.table_keys_values_qq.cellWidget(0, 2).setCurrentIndex(index)
        dialog.places_edits[Panels.QuickQuery].setText('foo')
        dialog.action_xml_qq.trigger()
        dialog.button_show_query.click()
        expected_index = dialog.stacked_panels_widget.indexOf(dialog.query_page)
        self.assertEqual(dialog.stacked_panels_widget.currentIndex(), expected_index)
        self.assertNotEqual(dialog.text_query.toPlainText(), '')
        self.assertEqual(dialog.text_query.toPlainText()[-2], '>')

    def test_preset(self):
        """Test we can obtain a couple key/value with preset."""
        dialog = Dialog()
        index = dialog.combo_preset_qq.findText('Shops/Food/Bakery')
        dialog.combo_preset_qq.setCurrentIndex(index)
        dialog.external_panels[Panels.QuickQuery].choice_preset()
        index_01 = dialog.table_keys_values_qq.cellWidget(0, 1).findText('shop')
        index_02 = dialog.table_keys_values_qq.cellWidget(0, 2).findText('bakery')
        self.assertEqual(
            dialog.table_keys_values_qq.cellWidget(0, 1).currentIndex(),
            index_01
        )
        self.assertEqual(
            dialog.table_keys_values_qq.cellWidget(0, 2).currentIndex(),
            index_02
        )

    def test_add_row_below(self):
        """Test we can add a row below in the table."""
        dialog = Dialog()
        index_01 = dialog.table_keys_values_qq.cellWidget(0, 1).findText('amenity')
        dialog.table_keys_values_qq.cellWidget(0, 1).setCurrentIndex(index_01)
        index_02 = dialog.table_keys_values_qq.cellWidget(0, 2).findText('bench')
        dialog.table_keys_values_qq.cellWidget(0, 2).setCurrentIndex(index_02)
        dialog .table_keys_values_qq.cellWidget(0, 3).click()
        index_11 = dialog.table_keys_values_qq.cellWidget(1, 1).findText('amenity')
        dialog.table_keys_values_qq.cellWidget(1, 1).setCurrentIndex(index_11)
        dialog.external_panels[Panels.QuickQuery].key_edited(1)
        index_12 = dialog.table_keys_values_qq.cellWidget(1, 2).findText('bar')
        dialog.table_keys_values_qq.cellWidget(1, 2).setCurrentIndex(index_12)
        dialog.table_keys_values_qq.cellWidget(0, 3).click()
        self.assertEqual(dialog.table_keys_values_qq.rowCount(), 3)
        self.assertEqual(
            dialog.table_keys_values_qq.cellWidget(2, 1).currentIndex(),
            index_11
        )
        self.assertEqual(
            dialog.table_keys_values_qq.cellWidget(2, 2).currentIndex(),
            index_12
        )
        self.assertEqual(
            dialog.table_keys_values_qq.cellWidget(1, 1).currentIndex(),
            0
        )
        self.assertEqual(
            dialog.table_keys_values_qq.cellWidget(0, 1).currentIndex(),
            index_01
        )

    def test_remove_row(self):
        """Test we can remove a row in the table."""
        dialog = Dialog()
        index = dialog.table_keys_values_qq.cellWidget(0, 1).findText('amenity')
        dialog.table_keys_values_qq.cellWidget(0, 1).setCurrentIndex(index)
        index = dialog.table_keys_values_qq.cellWidget(0, 2).findText('bench')
        dialog.table_keys_values_qq.cellWidget(0, 2).setCurrentIndex(index)
        dialog .table_keys_values_qq.cellWidget(0, 3).click()
        index_11 = dialog.table_keys_values_qq.cellWidget(1, 1).findText('amenity')
        dialog.table_keys_values_qq.cellWidget(1, 1).setCurrentIndex(index_11)
        dialog.external_panels[Panels.QuickQuery].key_edited(1)
        index_12 = dialog.table_keys_values_qq.cellWidget(1, 2).findText('bar')
        dialog.table_keys_values_qq.cellWidget(1, 2).setCurrentIndex(index_12)
        index = dialog.table_keys_values_qq.cellWidget(0, 2).findText('bench')
        dialog.table_keys_values_qq.cellWidget(0, 2).setCurrentIndex(index)
        dialog.table_keys_values_qq.cellWidget(0, 4).click()
        self.assertEqual(dialog.table_keys_values_qq.rowCount(), 1)
        self.assertEqual(
            dialog.table_keys_values_qq.cellWidget(0, 1).currentIndex(),
            index_11
        )
        self.assertEqual(
            dialog.table_keys_values_qq.cellWidget(0, 2).currentIndex(),
            index_12
        )
