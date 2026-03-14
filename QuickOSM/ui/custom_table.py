"""Set up and manage a custum table widget."""
import logging
import os

from functools import partial

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QComboBox,
    QCompleter,
    QHeaderView,
    QListWidgetItem,
    QPushButton,
    QWidget,
)

from QuickOSM.core.parser.preset_parser import PresetsParser
from QuickOSM.core.utilities.completer_free import (
    DiacriticFreeCompleter,
    DiactricFreeStringListModel,
)
from QuickOSM.definitions.gui import Panels
from QuickOSM.definitions.osm import MultiType
from QuickOSM.tools.i18n import tr
from QuickOSM.tools.resources import resources_path


LOGGER = logging.getLogger('QuickOSM')


class TableKeyValue:
    """Handle the keys/values parameters."""

    def __init__(self, table_widget: QWidget, preset_widget: QWidget):
        """Constructor"""
        self.table = table_widget
        self.preset = preset_widget
        self.preset_data = None
        self.preset_items = []
        self.couple = None
        self.keys = None

        self.all_keys_placeholder = tr('Query on all keys')
        self.all_values_placeholder = tr('Query on all values')

    def set_couple(self, couple: dict):
        """Set the couple parameter"""
        self.couple = couple
        self.keys = list(self.couple.keys())
        self.keys.append('')
        self.keys.sort()
        while self.keys[1] == '':
            self.keys.pop(1)

    def setup_preset(self):
        """Set up the preset"""
        parser = PresetsParser()
        self.preset_data = parser.parser()
        keys_preset = list(self.preset_data.elements.keys())
        keys_preset.append('')
        keys_preset.sort()
        keys_preset_completer = DiacriticFreeCompleter()
        completer_model = DiactricFreeStringListModel()
        keys_preset_completer.setModel(completer_model)
        keys_preset_completer.setCompletionRole(completer_model.diactricFreeRole())
        completer_model.setStringList(keys_preset)
        self.preset.addItems(keys_preset)
        self.preset.addItem(keys_preset.pop(0))
        if not os.getenv('CI') and self.panel and self.panel == Panels.QuickQuery:
            for k, key in enumerate(keys_preset):
                icon_path = self.preset_data.elements[key].icon
                widget_item = QListWidgetItem(key)
                if icon_path:
                    icon_path = resources_path('icons', "josm", icon_path)
                    if os.path.exists(icon_path):
                        icon = QPixmap(icon_path)
                        widget_item.setData(
                            Qt.ItemDataRole.DecorationRole,
                            icon.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio)
                        )
                        self.preset.setItemData(
                            k + 1, icon.scaled(20, 20, Qt.AspectRatioMode.KeepAspectRatio),
                            Qt.ItemDataRole.DecorationRole
                        )
                self.preset_items.append(widget_item)
        self.preset.setCompleter(keys_preset_completer)
        self.preset.completer().setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion)
        self.preset.completer().setFilterMode(
            Qt.MatchFlag.MatchContains
        )
        self.preset.completer().setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )

        self.preset.activated.connect(self.choice_preset)
        self.preset.lineEdit().setPlaceholderText(
            tr('Not mandatory. Ex: bakery'))

        osm_keys = parser.osm_keys_values()
        self.set_couple(osm_keys)

    def setup_table(self):
        """Set up the table"""

        # Table Keys/Values
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setMinimumSectionSize(25)
        index_type = header.logicalIndexAt(0)
        header.resizeSection(index_type, 50)

        add_row, remove_row = self.prepare_button()

        self.table.setCellWidget(0, 3, add_row)
        self.table.setCellWidget(0, 4, remove_row)

        key_field = self.prepare_key_field()
        value_field = self.prepare_value_field()

        self.table.setCellWidget(0, 1, key_field)
        self.table.setCellWidget(0, 2, value_field)

    def prepare_button(self) -> (QPushButton, QPushButton, QPushButton):
        """Set up the buttons for a row in the table widget."""
        add_row = QPushButton()
        add_row.setIcon(QIcon(QgsApplication.iconPath('symbologyAdd.svg')))
        add_row.setText('')
        add_row.setToolTip(tr('Add a line below.'))
        remove_row = QPushButton()
        remove_row.setIcon(QIcon(QgsApplication.iconPath('symbologyRemove.svg')))
        remove_row.setText('')
        remove_row.setToolTip(tr('Remove the line.'))

        add_row.clicked.connect(self.add_row_to_table)
        remove_row.clicked.connect(self.remove_selection)

        return add_row, remove_row

    def prepare_type_multi_request(self) -> QComboBox:
        """Set up the choice of multi request type for a row in the table widget."""
        type_operation = QComboBox()
        type_operation.setToolTip(
            tr('Set the type of multi-request. '
                '"And" verify both conditions. "Or" verify either of the conditions.'))
        type_operation.addItem(MultiType.AND.value, MultiType.AND)
        type_operation.addItem(MultiType.OR.value, MultiType.OR)

        type_operation.currentIndexChanged.connect(self.update_friendly)

        return type_operation

    def prepare_key_field(self) -> QComboBox:
        """Set up the key field for a row in the table widget."""
        key_field = QComboBox()
        key_field.setEditable(True)
        key_field.setToolTip(tr('An OSM key to fetch. If empty, all keys will be fetched.'))
        key_field.installEventFilter(self.dialog)

        keys_completer = QCompleter(self.keys)
        key_field.addItems(self.keys)
        key_field.setCompleter(keys_completer)
        key_field.completer().setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion)
        key_field.completer().setCaseSensitivity(
            Qt.CaseSensitivity.CaseInsensitive
        )

        key_field.lineEdit().setPlaceholderText(
            self.all_keys_placeholder)

        row = partial(self.key_edited, None)
        key_field.editTextChanged.connect(row)

        return key_field

    def prepare_value_field(self) -> QComboBox:
        """Set up the value field for a row in the table widget."""
        value_field = QComboBox()
        value_field.setEditable(True)
        value_field.setToolTip(tr('An OSM value to fetch. If empty, all values will be fetched.'))
        value_field.installEventFilter(self.dialog)

        value_field.lineEdit().setPlaceholderText(
            self.all_values_placeholder)

        value_field.editTextChanged.connect(self.update_friendly)

        return value_field

    def add_row_to_table(self, row: int = None):
        """Add a row in the table widget."""
        # noinspection PyCallingNonCallable
        table = self.table
        nb_row = table.rowCount()
        table.setRowCount(nb_row + 1)

        if not row:
            selection = table.selectedIndexes()
            if selection:
                row = selection[0].row()
            else:
                row = 0
        index_value = table.cellWidget(row, 2).currentIndex()

        type_operation = self.prepare_type_multi_request()

        self.table.setCellWidget(nb_row, 0, type_operation)

        key_field = self.prepare_key_field()
        value_field = self.prepare_value_field()

        table.setCellWidget(nb_row, 1, key_field)
        table.setCellWidget(nb_row, 2, value_field)

        add_row, remove_row = self.prepare_button()

        table.setCellWidget(nb_row, 3, add_row)
        table.setCellWidget(nb_row, 4, remove_row)

        if nb_row - 1 != row:
            for line in range(1, nb_row - row):
                key = table.cellWidget(nb_row - line, 1).currentText()
                value = table.cellWidget(nb_row - line, 2).currentText()

                index = table.cellWidget(nb_row - line + 1, 1).findText(key)
                table.cellWidget(nb_row - line + 1, 1).setCurrentIndex(index)
                self.key_edited(int(nb_row - line + 1))
                index = table.cellWidget(nb_row - line + 1, 2).findText(value)
                table.cellWidget(nb_row - line + 1, 2).setCurrentIndex(index)

                and_or = table.cellWidget(nb_row - line, 0).currentIndex()
                table.cellWidget(nb_row - line + 1, 0).setCurrentIndex(and_or)

                table.cellWidget(nb_row - line, 0).setCurrentIndex(0)
                table.cellWidget(nb_row - line, 1).setCurrentIndex(0)
                self.key_edited(int(nb_row - line))

            table.cellWidget(row, 2).setCurrentIndex(index_value)

        self.update_friendly()

    def remove_selection(self):
        """Remove the selected row from the table."""
        selection = self.table.selectedIndexes()
        if len(selection) <= 0:
            row = 0
        else:
            row = selection[0].row()

        if self.table.rowCount() > 1:
            if row == 0:
                self.table.setCellWidget(1, 0, None)
            self.table.clearSelection()
            self.table.removeRow(row)
            self.update_friendly()
        elif self.table.rowCount() == 1:
            self.table.cellWidget(0, 1).setCurrentIndex(0)

    def choice_preset(self, choice: str = None):
        """Fill the table with the keys/values from the preset."""
        if not isinstance(choice, str):
            choice = self.preset.currentText()
        element_chosen = self.preset_data.elements.get(choice)

        if not element_chosen:
            # Issue #387
            # The user wrote a string without having a proper list in the dropdown.
            LOGGER.info(f"User input '{choice}' is not recognised as a valid preset.")
            return

        keys, values = [], []
        for item in element_chosen.heirs:
            item_chosen = self.preset_data.items[item]
            item_keys = list(item_chosen.keys())
            for key in item_keys:
                value = item_chosen[key]
                if key in keys:
                    found = False
                    index_key = [k for k, key_item in enumerate(keys) if key_item == key]
                    for index in index_key:
                        if values[index] == value:
                            found = True
                            continue
                    if not found:
                        if isinstance(value, list):
                            for val in value:
                                keys.append(key)
                                values.append(val)
                        elif isinstance(value, str):
                            keys.append(key)
                            values.append(value)
                elif isinstance(value, list):
                    for val in value:
                        keys.append(key)
                        values.append(val)
                elif isinstance(value, str):
                    keys.append(key)
                    values.append(value)

        selection = self.table.selectedIndexes()
        if selection:
            row = selection[0].row()
        else:
            row = 0
        type_multi_request = [MultiType.OR for _k in keys]

        self.fill_table(keys, values, type_multi_request, row)

    def fill_table(self, keys: list, values: list, type_multi_request: list, row: int = 0):
        """Fill the table with custom parameters."""
        self.table.setRowCount(1)
        self.table.cellWidget(0, 1).setCurrentIndex(0)
        self.table.cellWidget(0, 2).lineEdit().setText('')

        for num in range(len(keys) - 1):
            if self.table.cellWidget(row + num, 0):
                if type_multi_request[num - 1] == MultiType.AND:
                    self.table.cellWidget(row + num, 0).setCurrentIndex(0)
                elif type_multi_request[num - 1] == MultiType.OR:
                    self.table.cellWidget(row + num, 0).setCurrentIndex(1)
            index = self.table.cellWidget(row + num, 1).findText(keys[num])
            self.table.cellWidget(row + num, 1).setCurrentIndex(index)
            self.key_edited(row + num)
            if values[num]:
                index = self.table.cellWidget(row + num, 2).findText(values[num])
                self.table.cellWidget(row + num, 2).setCurrentIndex(index)
            self.add_row_to_table(row + num)
        if len(keys) > 0:
            num = len(keys) - 1
            if self.table.cellWidget(row + num, 0) and num != 0:
                if type_multi_request[num - 1] == MultiType.AND:
                    self.table.cellWidget(row + num, 0).setCurrentIndex(0)
                elif type_multi_request[num - 1] == MultiType.OR:
                    self.table.cellWidget(row + num, 0).setCurrentIndex(1)
            index = self.table.cellWidget(row + num, 1).findText(keys[-1])
            self.table.cellWidget(row + num, 1).setCurrentIndex(index)
            self.key_edited(row + num)
            if values[-1]:
                index = self.table.cellWidget(row + num, 2).findText(values[-1])
                self.table.cellWidget(row + num, 2).setCurrentIndex(index)

            index = self.table.cellWidget(row, 2).findText(values[0])
            self.table.cellWidget(row, 2).setCurrentIndex(index)

    def key_edited(self, row: int = None):
        """Add values to the combobox according to the key."""
        if row is None:
            selection = self.table.selectedIndexes()
            if selection:
                row = selection[0].row()
            else:
                row = 0
        key_field = self.table.cellWidget(row, 1)
        value_field = self.table.cellWidget(row, 2)

        value_field.clear()
        value_field.setCompleter(None)

        try:
            current_values = self.couple[key_field.currentText()]
        except KeyError:
            self.update_friendly()
            return
        except AttributeError:
            self.update_friendly()
            return

        if len(current_values) == 0:
            current_values.insert(0, '')

        if len(current_values) > 1 and current_values[0] != '':
            current_values.insert(0, '')
            current_values.sort()

        values_completer = QCompleter(current_values)
        value_field.setCompleter(values_completer)
        value_field.addItems(current_values)
        self.update_friendly()

    def gather_couple(self, properties: dict) -> dict:
        """Gather the keys and values parameters"""
        rows = self.table.rowCount()
        key_added = False
        properties['key'] = []
        properties['value'] = []
        properties['type_multi_request'] = []
        for row in range(rows):
            keys = self.table.cellWidget(row, 1)
            if keys:
                values = self.table.cellWidget(row, 2)
                type_request = self.table.cellWidget(row, 0)
                properties['key'].append(keys.currentText())
                properties['value'].append(values.currentText())
                if type_request:
                    properties['type_multi_request'].append(type_request.currentData())
                key_added = True
        if not key_added:
            properties['key'] = None
            properties['value'] = None
            properties['type_multi_request'] = None

        return properties

    def update_friendly(self):
        """Updates the QuickQuery friendly label (label_qq_friendly)."""
        pass
