"""Dialog that edit a preset"""
import logging
import os

from qgis.core import QgsApplication, QgsCoordinateReferenceSystem
from qgis.gui import QgsExtentWidget, QgsFileWidget
from qgis.PyQt.QtCore import QPoint, Qt, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QInputDialog,
    QListWidgetItem,
    QMenu,
    QMessageBox,
)

from QuickOSM.core.utilities.query_saved import QueryManagement
from QuickOSM.core.utilities.tools import query_preset
from QuickOSM.definitions.format import Format
from QuickOSM.definitions.gui import Panels
from QuickOSM.definitions.osm import LayerType
from QuickOSM.tools.i18n import tr
from QuickOSM.tools.resources import load_ui, resources_path
from QuickOSM.ui.custom_table import TableKeyValue


FORM_CLASS = load_ui('edit_preset.ui')
LOGGER = logging.getLogger('QuickOSM')


class EditPreset(QDialog, FORM_CLASS, TableKeyValue):
    """Dialog that edit a preset"""

    def __init__(self, parent=None, data_preset: dict = None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.dialog = parent
        self.panel = Panels.MapPreset
        self.folder = query_preset()
        TableKeyValue.__init__(self, self.table_keys_values_eb, self.combo_preset_eb)
        self.setup_preset()
        self.setup_table()

        self.previous_name = data_preset['file_name']
        self.current_query = 0
        self.nb_queries = len(data_preset['query'])

        for k in range(self.nb_queries):
            self.list_queries.addItem(data_preset['query_name'][k])

        self.button_add.setIcon(QIcon(QgsApplication.iconPath('symbologyAdd.svg')))
        self.button_add.setText('')
        self.button_add.setToolTip(tr('Add a new query to the map preset'))
        self.button_add.clicked.connect(self.add_query)

        self.button_remove.setIcon(QIcon(QgsApplication.iconPath('symbologyRemove.svg')))
        self.button_remove.setText('')
        self.button_remove.setToolTip(tr('Remove the selected query from the map preset'))
        self.button_remove.clicked.connect(self.remove_selection)

        self.list_queries.currentRowChanged.connect(self.change_query)
        self.list_queries.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.list_queries.customContextMenuRequested.connect(self.item_context)

        self.label_help_qml.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.bbox = QgsExtentWidget()
        self.bbox.setMapCanvas(parent.iface.mapCanvas())
        self.bbox_layout.addWidget(self.bbox)
        self.crs = QgsCoordinateReferenceSystem('EPSG:4326')

        self.combo_output_format.addItem(
            Format.GeoPackage.value.label, Format.GeoPackage)
        self.combo_output_format.addItem(
            Format.GeoJSON.value.label, Format.GeoJSON)
        self.combo_output_format.addItem(
            Format.Shapefile.value.label, Format.Shapefile)
        self.combo_output_format.addItem(
            Format.Kml.value.label, Format.Kml)

        self.output_directory.lineEdit().setPlaceholderText(
            tr('Save to temporary file'))
        self.output_directory.setStorageMode(
            QgsFileWidget.StorageMode.GetDirectory)

        self.data = data_preset.copy()
        if self.data:
            self.preset_name.setText(self.data['file_name'])
            self.description.setPlainText('\\n'.join(self.data['description']))

            if self.data['advanced']:
                self.radio_advanced.setChecked(True)
                self.change_type_preset()
            self.data_filling_form()

        self.disable_enable_format()

        self.update_qml_format()
        self.preset_name.textChanged.connect(self.update_qml_format)

        self.radio_advanced.toggled.connect(self.change_type_preset)
        self.change_type_preset()
        self.output_directory.lineEdit().textChanged.connect(self.disable_enable_format)

        # Icons
        # Tab 0 is set in the radio button function
        self.tab_widget.setTabIcon(1, QIcon(":images/themes/default/mIconModelOutput.svg"))
        self.tab_widget.setTabIcon(2, QIcon(":images/themes/default/propertyicons/symbology.svg"))

        # Buttonbox
        self.button_box.button(QDialogButtonBox.StandardButton.Cancel).clicked.connect(self.close)
        self.button_box.button(QDialogButtonBox.StandardButton.Ok).clicked.connect(self.validate)
        self.button_box.button(QDialogButtonBox.StandardButton.Help).clicked.connect(self.open_help)

    def item_context(self, pos: QPoint):
        """Set context submenu to delete item in the list."""
        item = self.list_queries.mapToGlobal(pos)
        submenu = QMenu()
        rename_action = submenu.addAction(tr('Rename'))
        delete_action = submenu.addAction(tr('Delete'))
        right_click_item = submenu.exec(item)
        if right_click_item and right_click_item == delete_action:
            index = self.list_queries.indexAt(pos).row()
            self.verification_delete_query(index)
        if right_click_item and right_click_item == rename_action:
            query = self.list_queries.itemAt(pos)
            self.rename_query(query)

    def disable_enable_format(self):
        """Enable only if the directory is set."""
        boolean = not self.output_directory.lineEdit().isNull()
        self.combo_output_format.setEnabled(boolean)

    def update_qml_format(self):
        """Update the explanation of the qml file name format."""
        file_name = self.preset_name.text()
        query_name = self.list_queries.item(self.current_query).text()

        folder = os.path.join(self.folder, file_name)
        help_string = '<html>'
        help_string += tr(
            "You can associate predefined styles with layers. You need to add QML file(s) in this folder :"
        )
        help_string += '<br><b>'
        help_string += f"<a href=\"{folder}\">{folder}</a>"
        help_string += '</b><br><br>'
        help_string += tr("The name of QML files must follow this convention")
        help_string += " : "
        help_string += "<b>&#123;"
        help_string += tr("name of the preset")
        help_string += "&#125;</b>_<b>&#123;"
        help_string += tr("name of the query")
        help_string += "&#125;</b>_<b>&#123;"
        help_string += tr("geometry")
        help_string += "&#125;</b>.qml"
        help_string += '<br><br>'
        help_string += tr("These parameters are separated by '_' and the geometry must be one these values :")
        help_string += ' '
        help_string += ', '.join(['"' + j.value.lower() + '"' for j in LayerType])
        help_string += '.<br>'
        help_string += '<br>'
        help_string += tr(f'For the current preset "{file_name}"')
        help_string += '<br>'
        help_string += tr(f'and the current query "{query_name}"')
        help_string += '<br>'
        help_string += tr('this is the list of filenames you can use')
        help_string += " :"
        help_string += '<ul>'
        for layer_type in LayerType:
            help_string += '<li><b>'
            help_string += file_name + '_' + query_name + '_' + layer_type.value.lower()
            help_string += '.qml</b></li>'
        help_string += '<ul>'
        help_string += '<html>'
        self.label_help_qml.setText(help_string)

    def data_filling_form(self, num_query: int = 0):
        """Writing the form with data from preset"""

        self.layer_name.setText(self.data['query_layer_name'][num_query])
        self.query.setPlainText(self.data['query'][num_query])
        keys = self.data['keys'][num_query]
        values = self.data['values'][num_query]
        type_multi_request = self.data['type_multi_request'][num_query]
        self.fill_table(keys, values, type_multi_request)

        self.area.setText(self.data['area'][num_query])
        if self.data['bbox'][num_query]:
            self.bbox.setOutputExtentFromUser(self.data['bbox'][num_query], self.crs)
        else:
            self.bbox.clear()

        if LayerType.Points in self.data['output_geom_type'][num_query]:
            self.checkbox_points.setChecked(True)
        else:
            self.checkbox_points.setChecked(False)
        if LayerType.Lines in self.data['output_geom_type'][num_query]:
            self.checkbox_lines.setChecked(True)
        else:
            self.checkbox_lines.setChecked(False)
        if LayerType.Multilinestrings in self.data['output_geom_type'][num_query]:
            self.checkbox_multilinestrings.setChecked(True)
        else:
            self.checkbox_multilinestrings.setChecked(False)
        if LayerType.Multipolygons in self.data['output_geom_type'][num_query]:
            self.checkbox_multipolygons.setChecked(True)
        else:
            self.checkbox_multipolygons.setChecked(False)

        if self.data['white_list_column'][num_query]['points']:
            self.white_points.setText(self.data['white_list_column'][num_query]['points'])
        else:
            self.white_points.setText('')
        if self.data['white_list_column'][num_query]['lines']:
            self.white_lines.setText(self.data['white_list_column'][num_query]['lines'])
        else:
            self.white_lines.setText('')
        if self.data['white_list_column'][num_query]['multilinestrings']:
            self.white_multilinestrings.setText(self.data['white_list_column'][num_query]['multilinestrings'])
        else:
            self.white_multilinestrings.setText('')
        if self.data['white_list_column'][num_query]['multipolygons']:
            self.white_multipolygons.setText(self.data['white_list_column'][num_query]['multipolygons'])
        else:
            self.white_multipolygons.setText('')

        index = self.combo_output_format.findData(self.data['output_format'][num_query])
        self.combo_output_format.setCurrentIndex(index)

        self.output_directory.setFilePath(self.data['output_directory'][num_query])
        self.update_qml_format()

    def change_type_preset(self):
        """Update the form according the preset type."""
        if self.radio_advanced.isChecked():
            self.tab_widget.setTabIcon(0, QIcon(resources_path('icons', 'edit.png')))
            self.stacked_parameters_preset.setCurrentWidget(self.advanced_parameters)
        else:
            self.tab_widget.setTabIcon(0, QIcon(resources_path('icons', 'quick.png')))
            self.stacked_parameters_preset.setCurrentWidget(self.basic_parameters)

    def change_query(self):
        """Display the selected query in the view."""
        self.gather_parameters(self.current_query)
        self.current_query = self.list_queries.currentRow()
        self.data_filling_form(self.current_query)

    def add_query(self, default_name: str = ''):
        """Add a query in the preset"""
        if not default_name:
            text, ok = QInputDialog().getText(self, "New query", "Name of the query")
            if not ok:
                return
        else:
            # We are in tests
            text = default_name

        if not text:
            text = tr('Query') + str(self.nb_queries + 1)

        q_manage = QueryManagement()
        self.data = q_manage.add_empty_query_in_preset(self.data)

        new_query = QListWidgetItem(text)
        self.list_queries.addItem(new_query)
        self.nb_queries += 1

        self.list_queries.setCurrentItem(new_query)

    def remove_selection(self):
        """Remove the selected row from the table."""
        selection = self.list_queries.selectedIndexes()
        if len(selection) <= 0:
            return

        row = selection[0].row()
        self.verification_delete_query(row)

    def verification_delete_query(self, row: int):
        """Delete a query in the preset"""
        name = self.list_queries.item(row).text()
        validate_delete = QMessageBox(
            QMessageBox.Icon.Warning, tr('Confirm query deletion'),
            tr(f'Are you sure you want to delete the query \'{name}\'?'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, self
        )
        ok = validate_delete.exec()

        if ok == QMessageBox.StandardButton.Yes:
            self.delete_query(row)

    def delete_query(self, row: int):
        """Delete a query in the preset"""
        self.nb_queries -= 1

        self.list_queries.takeItem(row)

        q_manage = QueryManagement()
        self.data = q_manage.remove_query_in_preset(self.data, row)

        for k in range(row, self.nb_queries):
            self.list_queries.item(k).setText(tr('Query') + str(k + 1))

        self.current_query = self.list_queries.currentRow()

    def rename_query(self, query: QListWidgetItem):
        """Rename a query in the preset"""
        input_dialog = QInputDialog(self)
        new_name = input_dialog.getText(
            self, tr("Rename the query"),
            tr("New name:"), text=query.text())
        if new_name[1] and new_name[0]:
            query.setText(new_name[0].replace(' ', '_'))
            self.update_qml_format()

    def show_extent_canvas(self):
        """Show the extent in the canvas"""
        if self.data['bbox'][self.current_query]:
            self.canvas.setMapTool(self.show_extent_tool)
            self.show_extent_tool.show_extent(self.data['bbox'][self.current_query])

            self.setVisible(False)
            self.dialog.setVisible(False)

    def end_show_extent(self):
        """End the show of the extent."""
        self.canvas.unsetMapTool(self.show_extent_tool)

        self.setVisible(True)
        self.dialog.setVisible(True)

    def gather_general_parameters(self):
        """Save the general parameters."""
        self.data['file_name'] = self.preset_name.text().replace(' ', '_')
        description = self.description.toPlainText().split('\\n')
        self.data['description'] = description
        self.data['advanced'] = self.radio_advanced.isChecked()
        list_name_queries = [
            self.list_queries.item(k).text().replace(' ', '_') for k in range(self.list_queries.count())
        ]
        self.data['query_name'] = list_name_queries

    def gather_parameters(self, num_query: int = 0):
        """Save the parameters."""
        self.data['query_layer_name'][num_query] = self.layer_name.text()
        self.data['query'][num_query] = self.query.toPlainText()
        properties = self.gather_couple({})
        self.data['keys'][num_query] = properties['key']
        self.data['values'][num_query] = properties['value']
        self.data['type_multi_request'][num_query] = properties['type_multi_request']
        self.data['area'][num_query] = self.area.text()
        if not self.bbox.outputExtent().isNull():
            self.bbox.setOutputCrs(self.crs)
            self.data['bbox'][num_query] = self.bbox.outputExtent()
        else:
            self.data['bbox'][num_query] = ''

        output_geom = []
        if self.checkbox_points.isChecked():
            output_geom.append(LayerType.Points)
        if self.checkbox_lines.isChecked():
            output_geom.append(LayerType.Lines)
        if self.checkbox_multilinestrings.isChecked():
            output_geom.append(LayerType.Multilinestrings)
        if self.checkbox_multipolygons.isChecked():
            output_geom.append(LayerType.Multipolygons)
        self.data['output_geom_type'][num_query] = output_geom

        if self.white_points.text():
            white_list = {'points': self.white_points.text()}
        else:
            white_list = {'points': None}
        if self.white_lines.text():
            white_list['lines'] = self.white_lines.text()
        else:
            white_list['lines'] = None
        if self.white_multilinestrings.text():
            white_list['multilinestrings'] = self.white_multilinestrings.text()
        else:
            white_list['multilinestrings'] = None
        if self.white_multipolygons.text():
            white_list['multipolygons'] = self.white_multipolygons.text()
        else:
            white_list['multipolygons'] = None
        self.data['white_list_column'][num_query] = white_list

        self.data['output_format'][num_query] = self.combo_output_format.currentData()
        self.data['output_directory'][num_query] = self.output_directory.filePath()

    def validate(self):
        """Update the preset"""
        self.gather_parameters(self.current_query)
        self.gather_general_parameters()

        q_manage = QueryManagement()
        if self.previous_name != self.data['file_name']:
            q_manage.rename_preset(self.previous_name, self.data['file_name'], self.data)
        else:
            q_manage.update_preset(self.data)

        self.dialog.external_panels[Panels.MapPreset].update_personal_preset_view()
        self.close()

    @staticmethod
    def open_help():
        """Open the help web page"""
        QDesktopServices.openUrl(QUrl("https://quickosm.github.io/QuickOSM/user-guide/map-preset/"))
