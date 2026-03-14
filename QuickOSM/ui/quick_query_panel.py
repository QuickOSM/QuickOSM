"""Panel OSM base class."""
import datetime
import json
import logging
import os

from functools import partial
from os.path import join

from qgis.core import QgsApplication, QgsLayerItem
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidgetItem,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
)

from QuickOSM.core.exceptions import OsmObjectsException, QuickOsmException
from QuickOSM.core.process import process_query, process_quick_query
from QuickOSM.core.query_factory import QueryFactory
from QuickOSM.core.utilities.json_encoder import as_enum
from QuickOSM.core.utilities.query_saved import QueryManagement
from QuickOSM.core.utilities.tools import query_historic, query_preset
from QuickOSM.core.utilities.utilities_qgis import open_plugin_documentation
from QuickOSM.definitions.action import SaveType
from QuickOSM.definitions.gui import Panels
from QuickOSM.definitions.osm import (
    Osm_Layers,
    OsmType,
    QueryLanguage,
    QueryType,
)
from QuickOSM.tools.i18n import tr
from QuickOSM.tools.resources import resources_path
from QuickOSM.ui.base_overpass_panel import BaseOverpassPanel
from QuickOSM.ui.custom_table import TableKeyValue


LOGGER = logging.getLogger('QuickOSM')


class QuickQueryPanel(BaseOverpassPanel, TableKeyValue):

    """Final implementation for the panel."""

    def __init__(self, dialog: QDialog):
        BaseOverpassPanel.__init__(self, dialog)
        TableKeyValue.__init__(self, dialog.table_keys_values_qq, self.dialog.combo_preset_qq)
        self.panel = Panels.QuickQuery
        self.osm_keys = None
        self.preset_data = None
        self.existing_preset = None
        self.action_new = None
        self.action_existing = None

    def setup_panel(self):
        super().setup_panel()
        """Setup the UI for the QuickQuery."""

        # Setup presets and keys auto-completion
        self.setup_preset()

        # Table Keys/Values
        self.setup_table()

        self.dialog.button_map_features.setIcon(QIcon(":images/themes/default/mActionEditHelpContent.svg"))
        self.dialog.button_run_query_qq.setIcon(QIcon(QgsApplication.iconPath("mActionStart.svg")))
        # self.dialog.button_show_query.setIcon(QIcon(resources_path('icons', 'edit.png')))

        # Query type
        self.dialog.combo_query_type_qq.addItem(tr('In'), 'in')
        self.dialog.combo_query_type_qq.addItem(tr('Around'), 'around')
        self.dialog.combo_query_type_qq.addItem(tr('Canvas Extent'), 'canvas')
        self.dialog.combo_query_type_qq.addItem(tr('Layer Extent'), 'layer')
        self.dialog.combo_query_type_qq.addItem(tr('Not Spatial'), 'attributes')

        self.dialog.combo_query_type_qq.setItemIcon(0, QIcon(resources_path('icons', 'in.svg')))
        self.dialog.combo_query_type_qq.setItemIcon(1, QIcon(resources_path('icons', 'around.svg')))
        self.dialog.combo_query_type_qq.setItemIcon(2, QIcon(":images/themes/default/mLayoutItemMap.svg"))
        self.dialog.combo_query_type_qq.setItemIcon(
            3, QIcon(":images/themes/default/algorithms/mAlgorithmRandomPointsWithinExtent.svg"))
        self.dialog.combo_query_type_qq.setItemIcon(4, QgsLayerItem.iconTable())

        self.dialog.combo_query_type_qq.currentIndexChanged.connect(
            self.query_type_updated)

        self.dialog.button_save_query.setMenu(QMenu())

        self.action_new = QAction(SaveType.New.value)
        self.action_new.triggered.connect(self.save_new)
        self.action_existing = QAction(SaveType.Existing.value)
        self.action_existing.triggered.connect(self.save_add_existing)
        self.dialog.button_save_query.menu().addAction(self.action_new)
        self.dialog.button_save_query.menu().addAction(self.action_existing)

        self.dialog.button_save_query.clicked.connect(self.save_query)

        self.dialog.button_show_query.setMenu(QMenu())

        self.dialog.action_oql_qq.triggered.connect(self.query_language_oql)
        self.dialog.action_xml_qq.triggered.connect(self.query_language_xml)
        self.dialog.button_show_query.menu().addAction(self.dialog.action_oql_qq)
        self.dialog.button_show_query.menu().addAction(self.dialog.action_xml_qq)

        query_oql = partial(self.show_query, QueryLanguage.OQL)
        self.dialog.button_show_query.clicked.connect(query_oql)

        self.dialog.button_run_query_qq.clicked.connect(self.run)
        self.dialog.button_map_features.clicked.connect(open_plugin_documentation)
        self.dialog.button_box_qq.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(
            self.dialog.reset_form)

        # setup callbacks for friendly-label-update only
        self.dialog.line_place_qq.textChanged.connect(self.update_friendly)
        self.dialog.spin_place_qq.valueChanged.connect(self.update_friendly)
        self.dialog.combo_extent_layer_qq.layerChanged.connect(self.query_type_updated)

        self.query_type_updated()
        self.init_nominatim_autofill()
        self.update_friendly()

        self.update_history_view()

    def query_type_updated(self):
        """Update the ui when the query type is modified."""
        self._core_query_type_updated(
            self.dialog.combo_query_type_qq,
            self.dialog.stacked_query_type,
            self.dialog.spin_place_qq,
            self.dialog.checkbox_selection_qq)
        self.update_friendly()

    def save_new(self):
        """Verify the save destination."""
        self.existing_preset = False
        self.dialog.button_save_query.setText(tr('Save query in a new preset'))

    def save_add_existing(self):
        """Verify and ask the save destination."""
        self.existing_preset = True
        self.dialog.button_save_query.setText(tr('Save and add query to an existing preset'))

    def query_language_oql(self):
        """Update the wanted language."""
        super().query_language_oql()
        query_oql = partial(self.show_query, QueryLanguage.OQL)
        self.dialog.button_show_query.clicked.connect(query_oql)

    def query_language_xml(self):
        """Update the wanted language."""
        super().query_language_xml()
        query_xml = partial(self.show_query, QueryLanguage.XML)
        self.dialog.button_show_query.clicked.connect(query_xml)

    def gather_values(self) -> dict:
        """Retrieval of the values set by the user."""
        properties = super().gather_values()
        osm_objects = []
        if self.dialog.checkbox_node.isChecked():
            osm_objects.append(OsmType.Node)
        if self.dialog.checkbox_way.isChecked():
            osm_objects.append(OsmType.Way)
        if self.dialog.checkbox_relation.isChecked():
            osm_objects.append(OsmType.Relation)
        properties['osm_objects'] = osm_objects

        if not properties['osm_objects']:
            raise OsmObjectsException

        properties['metadata'] = 'meta' if self.dialog.checkbox_meta.isChecked() else 'body'

        properties = self.gather_couple(properties)

        properties['timeout'] = self.dialog.spin_timeout.value()

        properties['distance'] = self.dialog.spin_place_qq.value()
        if properties['query_type'] != QueryType.AroundArea:
            properties['distance'] = None

        distance_string = None
        if properties['distance']:
            distance_string = str(properties['distance'])
        if isinstance(properties['key'], list):
            expected_name = []
            nb_max = len(properties['key']) if len(properties['key']) <= 2 else 2
            for k in range(nb_max):
                expected_name.append(properties['key'][k])
                expected_name.append(properties['value'][k])
            expected_name.append(properties['place'])
            expected_name.append(distance_string)
        elif not properties['key']:
            key = tr('allKeys')
            expected_name = [key, properties['value'], properties['place'], distance_string]
        else:
            expected_name = [properties['key'], properties['value'], properties['place'], distance_string]
        properties['layer_name'] = '_'.join([f for f in expected_name if f])

        return properties

    def save_query(self):
        """Save a query in a preset."""
        try:
            properties = self.gather_values()

            # Make the query
            query_factory = QueryFactory(
                type_multi_request=properties['type_multi_request'],
                query_type=properties['query_type'],
                key=properties['key'],
                value=properties['value'],
                area=properties['place'],
                around_distance=properties['distance'],
                osm_objects=properties['osm_objects'],
                timeout=properties['timeout'],
                print_mode=properties['metadata']
            )
            query = query_factory.make(QueryLanguage.OQL)
            description = query_factory.friendly_message()
        except QuickOsmException as error:
            self.dialog.display_quickosm_exception(error)
            return
        except Exception as error:
            self.dialog.display_critical_exception(error)
            return

        q_manage = QueryManagement(
            query=query,
            name=properties['layer_name'],
            description=description,
            advanced=False,
            type_multi_request=properties['type_multi_request'],
            keys=properties['key'],
            values=properties['value'],
            area=properties['place'],
            bbox=properties['bbox'],
            output_geometry_types=properties['outputs'],
            output_directory=properties['output_directory'],
            output_format=properties['output_format']
        )
        if self.existing_preset:
            preset_folder = query_preset()
            presets = filter(
                lambda folder: os.path.isdir(join(preset_folder, folder)), os.listdir(preset_folder))
            chosen_preset = QInputDialog.getItem(
                self.dialog, tr('Add in an existing preset'),
                tr('Please select the preset in which the query will be added:'),
                presets, editable=False
            )
            if chosen_preset[1]:
                q_manage.add_query_in_preset(chosen_preset[0])
        else:
            q_manage.add_preset(properties['layer_name'])

        self.dialog.external_panels[Panels.MapPreset].update_personal_preset_view()
        item = self.dialog.menu_widget.item(self.dialog.preset_menu_index)
        self.dialog.menu_widget.setCurrentItem(item)

    def save_history_preset(self, data: dict):
        """Save a query from history to preset."""

        q_manage = QueryManagement(
            query=data['query'],
            name=data['file_name'],
            description=data['description'],
            advanced=data['advanced'],
            type_multi_request=data['type_multi_request'],
            keys=data['keys'],
            values=data['values'],
            area=data['area'],
            bbox=data['bbox'],
            output_geometry_types=data['output_geom_type'],
            white_list_column=data['white_list_column'],
            output_directory=data['output_directory'],
            output_format=data['output_format']
        )
        q_manage.add_preset(data['file_name'])

        self.dialog.external_panels[Panels.MapPreset].update_personal_preset_view()
        item = self.dialog.menu_widget.item(self.dialog.preset_menu_index)
        self.dialog.menu_widget.setCurrentItem(item)

    def update_history_view(self):
        """Update the history view."""
        historic_folder = query_historic()
        files = os.listdir(historic_folder)

        self.dialog.list_historic.clear()

        for file in files[::-1]:
            file_path = join(historic_folder, file)
            with open(file_path, encoding='utf8') as json_file:

                try:
                    data = json.load(json_file, object_hook=as_enum)
                except Exception:
                    # TODO, the fix should be done when writing the JSON file as well
                    # Issue https://github.com/QuickOSM/QuickOSM/issues/493
                    # Issue https://github.com/QuickOSM/QuickOSM/issues/526
                    continue

            name = data['file_name']

            item = QListWidgetItem(self.dialog.list_historic)
            self.dialog.list_historic.addItem(item)

            group = QFrame()
            group.setFrameStyle(QFrame.Shape.StyledPanel)
            group.setStyleSheet('QFrame { margin: 3px; }')
            group.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
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
            button_run = QPushButton()
            button_save = QPushButton()
            button_run.setIcon(QIcon(QgsApplication.iconPath("mActionStart.svg")))
            button_save.setIcon(QIcon(QgsApplication.iconPath("mActionFileSave.svg")))
            button_run.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            button_save.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            button_run.setToolTip(tr('Run the query'))
            button_save.setToolTip(tr('Save this query in a new preset'))
            hbox.addWidget(button_run)
            hbox.addWidget(button_save)
            group.setLayout(hbox)

            # Actions on click
            run = partial(self.run_saved_query, data)
            button_run.clicked.connect(run)
            save = partial(self.save_history_preset, data)
            button_save.clicked.connect(save)

            item.setSizeHint(group.minimumSizeHint())
            self.dialog.list_historic.setItemWidget(item, group)

    def _run_saved_query(self, data: dict):
        """Run a saved query(ies)."""
        for k, query in enumerate(data['query']):
            if data['output_directory'][k]:
                time_str = str(datetime.datetime.now()).replace(' ', '_').replace(':', '-').split('.')[0]
                name = time_str + '_' + data['query_layer_name'][k]
            else:
                name = data['query_layer_name'][k]
            historic_folder = query_historic()
            files = os.listdir(historic_folder)
            files_qml = filter(lambda file_ext: file_ext[-4:] == '.qml', files)
            file_name = join(data['file_name'] + '_' + data['query_name'][k])
            files_qml = self.filter_file_names(file_name, files_qml)
            if list(files_qml):
                LOGGER.debug(f'files: {files_qml}')
                self.join = join(historic_folder, data['file_name'] + '_' + data['query_name'][k] + '_{}.qml')
                file_name = self.join
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

    def _run(self):
        """Process for running the query."""
        self.write_nominatim_file(self.panel)
        properties = self.gather_values()
        num_layers = process_quick_query(
            dialog=self.dialog,
            type_multi_request=properties['type_multi_request'],
            query_type=properties['query_type'],
            key=properties['key'],
            value=properties['value'],
            area=properties['place'],
            distance=properties['distance'],
            bbox=properties['bbox'],
            osm_objects=properties['osm_objects'],
            metadata=properties['metadata'],
            timeout=properties['timeout'],
            output_directory=properties['output_directory'],
            output_format=properties['output_format'],
            prefix_file=properties['prefix_file'],
            layer_name=properties['layer_name'],
            output_geometry_types=properties['outputs'])
        self.update_history_view()
        self.end_query(num_layers)

    def show_query(self, output: QueryLanguage):
        """Show the query in the main window."""
        self.write_nominatim_file(self.panel)
        try:
            properties = self.gather_values()
        except QuickOsmException as error:
            self.dialog.display_quickosm_exception(error)
            return
        except Exception as error:
            self.dialog.display_critical_exception(error)
            return

        # Transfer each output with zip
        check_boxes = zip(
            self.dialog.output_buttons[Panels.QuickQuery],
            self.dialog.output_buttons[Panels.Query])
        for couple in check_boxes:
            couple[1].setChecked(couple[0].isChecked())

        # Transfer the language of the query
        self.query_language_updated()

        # Transfer the output
        self.dialog.output_directory_q.setFilePath(properties['output_directory'])
        index_format = self.dialog.combo_format_q.findData(properties['output_format'])
        self.dialog.combo_format_q.setCurrentIndex(index_format)
        if properties['prefix_file']:
            self.dialog.line_file_prefix_q.setText(properties['prefix_file'])
            self.dialog.line_file_prefix_q.setEnabled(True)

        # Make the query
        query_factory = QueryFactory(
            type_multi_request=properties['type_multi_request'],
            query_type=properties['query_type'],
            key=properties['key'],
            value=properties['value'],
            area=properties['place'],
            around_distance=properties['distance'],
            osm_objects=properties['osm_objects'],
            timeout=properties['timeout'],
            print_mode=properties['metadata']
        )
        try:
            query = query_factory.make(output)
        except QuickOsmException as error:
            self.dialog.display_quickosm_exception(error)
        except Exception as error:
            self.dialog.display_critical_exception(error)
        else:
            self.dialog.text_query.setPlainText(query)
            item = self.dialog.menu_widget.item(self.dialog.query_menu_index)
            self.dialog.menu_widget.setCurrentItem(item)

    def update_friendly(self):
        """Updates the QuickQuery friendly label (label_qq_friendly)."""
        try:
            properties = self.gather_values()
        except QuickOsmException as error:
            self.dialog.display_quickosm_exception(error)
            return
        except Exception as error:
            self.dialog.display_critical_exception(error)
            return

        # Make the query, in order to create the friendly message
        query_factory = QueryFactory(
            type_multi_request=properties['type_multi_request'],
            query_type=properties['query_type'],
            key=properties['key'],
            value=properties['value'],
            area=properties['place'],
            around_distance=properties['distance'],
            osm_objects=properties['osm_objects'],
            timeout=properties['timeout']
        )
        try:
            msg = query_factory.friendly_message()
        except QuickOsmException as error:
            self.dialog.label_qq_friendly.setStyleSheet('QLabel { color : red; }')
            self.dialog.label_qq_friendly.setText(str(error))
        except Exception as error:
            self.dialog.display_critical_exception(error)
            self.dialog.label_qq_friendly.setText('')
        else:
            self.dialog.label_qq_friendly.setStyleSheet('')
            self.dialog.label_qq_friendly.setText(msg)
