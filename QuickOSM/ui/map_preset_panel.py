"""Panel OSM map preset class."""
import datetime
import json
import logging
import os

from functools import partial
from os.path import join

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QSize, Qt
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from QuickOSM.core.exceptions import NoSelectedPreset, QuickOsmException
from QuickOSM.core.process import process_query, process_quick_query
from QuickOSM.core.utilities.json_encoder import as_enum
from QuickOSM.core.utilities.query_saved import QueryManagement
from QuickOSM.core.utilities.tools import query_preset
from QuickOSM.definitions.gui import Panels
from QuickOSM.definitions.osm import Osm_Layers, QueryType
from QuickOSM.tools.i18n import tr
from QuickOSM.tools.resources import resources_path
from QuickOSM.ui.base_overpass_panel import BaseOverpassPanel
from QuickOSM.ui.edit_preset import EditPreset


LOGGER = logging.getLogger('QuickOSM')


class MapPresetPanel(BaseOverpassPanel):
    """Implementation of the map preset panel."""

    advanced_selected = 'orange'
    basic_selected = 'lightblue'

    def __init__(self, dialog: QDialog):
        """Constructor"""
        super().__init__(dialog)
        self.panel = Panels.MapPreset
        self.listAdvanced = []

    def setup_panel(self):
        super().setup_panel()
        """Setup the UI for the QuickQuery."""

        # Query type
        self.dialog.combo_query_type_mp.addItem(tr('In'), 'in')
        self.dialog.combo_query_type_mp.addItem(tr('Around'), 'around')
        self.dialog.combo_query_type_mp.addItem(tr('Canvas Extent'), 'canvas')
        self.dialog.combo_query_type_mp.addItem(tr('Layer Extent'), 'layer')
        self.dialog.combo_query_type_mp.addItem(tr('Not Spatial'), 'attributes')

        self.dialog.combo_query_type_mp.currentIndexChanged.connect(
            self.query_type_updated)
        self.dialog.combo_extent_layer_mp.layerChanged.connect(self.query_type_updated)

        self.setup_default_preset()
        self.dialog.list_default_mp.itemPressed.connect(self.select_default)
        self.dialog.list_personal_preset_mp.itemPressed.connect(self.select_personal)
        self.dialog.button_run_query_mp.clicked.connect(self.prepare_run)
        self.dialog.list_personal_preset_mp.currentRowChanged.connect(self.disable_enable_location)

        self.query_type_updated()
        self.init_nominatim_autofill()

        self.update_personal_preset_view()

    def setup_default_preset(self):
        """Set up the display of presets"""
        preset_folder = resources_path('map_preset')
        folders = os.listdir(preset_folder)

        for folder_name in folders:
            file_path = join(preset_folder, folder_name, folder_name + '.json')
            with open(file_path, encoding='utf8') as json_file:
                data = json.load(json_file, object_hook=as_enum)

            item = QListWidgetItem(self.dialog.list_default_mp)
            item.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
            )
            self.dialog.list_default_mp.addItem(item)

            widget = QFrame()
            widget.setFrameStyle(QFrame.Shape.StyledPanel)
            widget.setStyleSheet('QFrame { margin: 3px; };')
            widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            hbox = QHBoxLayout()
            vbox = QVBoxLayout()
            picture = QLabel()
            icon_path = resources_path('map_preset', folder_name, folder_name + '_icon.png')
            if not os.path.isfile(icon_path):
                icon_path = resources_path('icons', 'QuickOSM.svg')
            icon = QPixmap(icon_path)
            icon.scaled(QSize(150, 250), Qt.AspectRatioMode.KeepAspectRatio)
            picture.setPixmap(icon)
            picture.setStyleSheet('max-height: 150px; max-width: 250px; margin-right: 50px;')
            hbox.addWidget(picture)
            title = QLabel(data['file_name'])
            title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            title.setStyleSheet('font: bold 20px; margin-bottom: 25px;')
            vbox.addWidget(title)
            for label in data['description']:
                if not label:
                    label = tr('No description')
                real_label = QLabel(label)
                real_label.setWordWrap(True)
                vbox.addWidget(real_label)
            hbox.addItem(vbox)
            widget.setLayout(hbox)

            item.setSizeHint(widget.minimumSizeHint())
            self.dialog.list_default_mp.setItemWidget(item, widget)

    def query_type_updated(self):
        """Update the ui when the query type is modified."""
        self._core_query_type_updated(
            self.dialog.combo_query_type_mp,
            self.dialog.stacked_query_type_mp,
            self.dialog.spin_place_mp,
            self.dialog.checkbox_selection_mp)

    def select_default(self):
        """Update the panel knowing a default preset is selected."""
        self.dialog.list_personal_preset_mp.clearSelection()
        self.dialog.combo_query_type_mp.setEnabled(True)
        self.dialog.stacked_query_type_mp.setEnabled(True)

    def select_personal(self):
        """Update the panel knowing a personal preset is selected."""
        self.dialog.list_default_mp.clearSelection()
        row = self.dialog.list_personal_preset_mp.currentRow()
        self.disable_enable_location(row)

    def disable_enable_location(self, row: int):
        """Enable only when it is a basic preset."""
        if self.listAdvanced[row]:
            self.dialog.list_personal_preset_mp.setStyleSheet(
                'QListWidget::item:selected {background: ' + self.advanced_selected + ';}')
            self.dialog.combo_query_type_mp.setEnabled(False)
            self.dialog.stacked_query_type_mp.setEnabled(False)
        else:
            self.dialog.list_personal_preset_mp.setStyleSheet(
                'QListWidget::item:selected {background: ' + self.basic_selected + ';}')
            self.dialog.combo_query_type_mp.setEnabled(True)
            self.dialog.stacked_query_type_mp.setEnabled(True)

    def update_personal_preset_view(self):
        """Update the presets displayed."""
        preset_folder = query_preset()
        files = filter(
            lambda folder: os.path.isdir(join(preset_folder, folder)), os.listdir(preset_folder))

        self.dialog.list_personal_preset_mp.clear()

        for file in files:
            file_path = join(preset_folder, file, file + '.json')
            with open(file_path, encoding='utf8') as json_file:
                data = json.load(json_file, object_hook=as_enum)
            name = data['file_name']

            item = QListWidgetItem(self.dialog.list_personal_preset_mp)
            item.setFlags(
                Qt.ItemFlag.ItemIsSelectable
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsEnabled
            )
            self.dialog.list_personal_preset_mp.addItem(item)

            preset = QFrame()
            preset.setObjectName('FramePreset')
            preset.setFrameStyle(QFrame.Shape.StyledPanel)
            preset.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            hbox = QHBoxLayout()
            vbox = QVBoxLayout()
            label_name = QLabel(name)
            label_name.setStyleSheet('font-weight: bold;')
            label_name.setWordWrap(True)
            vbox.addWidget(label_name)
            for label in data['description']:
                if not label:
                    label = tr('No description')
                real_label = QLabel(label)
                real_label.setWordWrap(True)
                vbox.addWidget(real_label)
            hbox.addItem(vbox)
            button_edit = QPushButton()
            button_remove = QPushButton()
            button_edit.setIcon(QIcon(QgsApplication.iconPath("mActionToggleEditing.svg")))
            button_remove.setIcon(QIcon(QgsApplication.iconPath('symbologyRemove.svg')))
            button_edit.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            button_remove.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            button_edit.setToolTip(tr('Edit the preset'))
            button_remove.setToolTip(tr('Delete the preset'))
            hbox.addWidget(button_edit)
            hbox.addWidget(button_remove)
            if data['advanced']:
                self.listAdvanced.append(True)
                preset.setStyleSheet(
                    '#FramePreset { margin: 3px;'
                    ' border: 3px solid ' + self.advanced_selected + ';'
                    ' border-width: 1px 1px 1px 4px;}')
            else:
                self.listAdvanced.append(False)
                preset.setStyleSheet(
                    '#FramePreset { margin: 3px;'
                    ' border: 3px solid ' + self.basic_selected + ';'
                    ' border-width: 1px 1px 1px 4px;}')
            preset.setLayout(hbox)

            # Actions on click
            remove = partial(self.verification_remove_preset, item, name)
            button_remove.clicked.connect(remove)
            edit = partial(self.edit_preset, data)
            button_edit.clicked.connect(edit)

            item.setSizeHint(preset.minimumSizeHint())
            self.dialog.list_personal_preset_mp.setItemWidget(item, preset)

        self.listAdvanced.append(False)

        if self.dialog.list_personal_preset_mp.count() == 0:
            self.dialog.group_personal_presets.setCollapsed(True)

    def edit_preset(self, data: dict):
        """Open a dialog to edit the preset"""
        edit_dialog = EditPreset(self.dialog, data)
        edit_dialog.show()
        self.update_personal_preset_view()

    def verification_remove_preset(self, item: QListWidgetItem, name: str):
        """Verification of the removal a preset."""
        validate_delete = QMessageBox(
            QMessageBox.Icon.Warning, tr('Confirm preset deletion'),
            tr(f'Are you sure you want to delete the preset \'{name}\'?'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel, self.dialog
        )
        ok = validate_delete.exec()

        if ok == QMessageBox.StandardButton.Yes:
            self.remove_preset(item, name)

    def remove_preset(self, item: QListWidgetItem, name: str):
        """Remove a preset."""
        index = self.dialog.list_personal_preset_mp.row(item)
        self.dialog.list_personal_preset_mp.takeItem(index)

        q_manage = QueryManagement()
        q_manage.remove_preset(name)

    def prepare_run(self):
        """Prepare the data before running the process."""
        selection = self.dialog.list_default_mp.selectedIndexes()
        try:

            if selection:
                preset = self.dialog.list_default_mp.item(selection[0].row())
                preset_widget = self.dialog.list_default_mp.itemWidget(preset)
                preset_label = preset_widget.layout().itemAt(1).itemAt(0).widget().text()
                preset_folder = resources_path('map_preset')
            else:
                selection = self.dialog.list_personal_preset_mp.selectedIndexes()
                if not len(selection):
                    raise NoSelectedPreset

                preset = self.dialog.list_personal_preset_mp.item(selection[0].row())
                preset_widget = self.dialog.list_personal_preset_mp.itemWidget(preset)
                preset_label = preset_widget.layout().itemAt(0).itemAt(0).widget().text()
                preset_folder = query_preset()
            LOGGER.debug(f'Preset chosen: {preset_label}')
            file_path = join(preset_folder, preset_label, preset_label + '.json')
            with open(file_path, encoding='utf8') as json_file:
                data = json.load(json_file, object_hook=as_enum)

            data['folder'] = os.path.dirname(file_path)

            if not data['advanced']:
                properties = self.gather_spatial_values({})
                data['query_type'] = properties['query_type']
                data['distance'] = self.dialog.spin_place_mp.value()
                if data['query_type'] != QueryType.AroundArea:
                    data['distance'] = None
                if data['query_type'] in [QueryType.InArea, QueryType.AroundArea] and properties['place']:
                    for k, _area in enumerate(data['area']):
                        data['area'][k] = properties['place']
                elif data['query_type'] == QueryType.BBox and properties['bbox']:
                    for k, _bbox in enumerate(data['bbox']):
                        data['bbox'][k] = properties['bbox']

            self.run_saved_query(data)

        except QuickOsmException as error:
            self.dialog.display_quickosm_exception(error)

    def _run_saved_query(self, data: dict):
        """Run a saved query(ies)."""
        for k, query in enumerate(data['query']):
            if data['output_directory'][k]:
                time_str = str(datetime.datetime.now()).replace(' ', '_').replace(':', '-').split('.')[0]
                name = time_str + '_' + data['query_layer_name'][k]
            else:
                name = data['query_layer_name'][k]
            files = os.listdir(data['folder'])
            files_qml = filter(lambda file_ext: file_ext[-4:] == '.qml', files)
            file_name = join(data['file_name'] + '_' + data['query_name'][k])
            files_qml = self.filter_file_names(file_name, files_qml)
            if list(files_qml):
                LOGGER.debug(f'files: {files_qml}')
                file_name = join(
                    data['folder'], data['file_name'] + '_' + data['query_name'][k] + '_{}.qml')
                config = {}
                for osm_type in Osm_Layers:
                    config[osm_type] = {
                        'namelayer': name,
                        'style': file_name.format(osm_type)
                    }
            else:
                config = None

            if data['advanced']:
                num_layers = process_query(
                    dialog=self.dialog,
                    query=query,
                    description=data['description'],
                    layer_name=name,
                    white_list_values=data['white_list_column'][k],
                    type_multi_request=data['type_multi_request'][k],
                    key=data['keys'][k],
                    value=data['values'][k],
                    area=data['area'][k],
                    bbox=data['bbox'][k],
                    output_geometry_types=data['output_geom_type'][k],
                    output_format=data['output_format'][k],
                    output_dir=data['output_directory'][k],
                    config_outputs=config
                )
            else:
                if 'query_type' in data:
                    query_type = data['query_type']
                    dist = data['distance']
                else:
                    query_type = QueryType.InArea if data['area'][k] else QueryType.BBox
                    dist = None
                num_layers = process_quick_query(
                    dialog=self.dialog,
                    description=data['description'],
                    type_multi_request=data['type_multi_request'][k],
                    query_type=query_type,
                    key=data['keys'][k],
                    value=data['values'][k],
                    area=data['area'][k],
                    bbox=data['bbox'][k],
                    distance=dist,
                    output_directory=data['output_directory'][k],
                    output_format=data['output_format'][k],
                    layer_name=name,
                    white_list_values=data['white_list_column'][k],
                    output_geometry_types=data['output_geom_type'][k],
                    config_outputs=config
                )
            self.end_query(num_layers)
