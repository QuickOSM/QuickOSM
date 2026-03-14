"""Configuration panel."""

import logging

from os.path import isfile

from qgis.core import Qgis, QgsProject
from qgis.PyQt.QtWidgets import QDialog

from QuickOSM.core.exceptions import (
    FileDoesntExistException,
    QuickOsmException,
)
from QuickOSM.core.parser.osm_parser import OsmParser
from QuickOSM.core.process import open_file
from QuickOSM.definitions.gui import Panels
from QuickOSM.definitions.osm import MultiType
from QuickOSM.tools.i18n import tr
from QuickOSM.tools.resources import resources_path
from QuickOSM.ui.base_processing_panel import BaseProcessingPanel
from QuickOSM.ui.custom_table import TableKeyValue


LOGGER = logging.getLogger('QuickOSM')


class OsmFilePanel(BaseProcessingPanel, TableKeyValue):

    """Final implementation for the panel."""

    def __init__(self, dialog: QDialog):
        """Constructor"""
        BaseProcessingPanel.__init__(self, dialog)
        TableKeyValue.__init__(self, dialog.table_keys_values_f, self.dialog.combo_preset_f)
        super().__init__(dialog)
        self.panel = Panels.File

    def setup_panel(self):
        """Setup the panel"""
        super().setup_panel()
        self.dialog.radio_osm_conf.setChecked(False)
        self.dialog.osm_conf.setEnabled(False)
        # TODO self.edit_file_prefix_f.setDisabled(True)

        self.dialog.radio_selection_keys.setChecked(False)

        # Setup key auto completion
        self.setup_preset()

        # Table Keys/Values
        self.setup_table()

        self.dialog.osm_file.setDialogTitle(tr('Select an OSM/PBF file'))
        self.dialog.osm_file.setFilter('OSM file (*.osm *.pbf)')

        default_osm_conf = resources_path('ogr', 'to_be_modified_osmconf.ini')
        if not isfile(default_osm_conf):
            default_osm_conf = ''
        self.dialog.osm_conf.setDialogTitle(tr('Select OSM conf file'))
        self.dialog.osm_conf.setFilter('OSM conf (*.ini)')
        self.dialog.osm_conf.lineEdit().setPlaceholderText(default_osm_conf)

        self.dialog.osm_file.lineEdit().textChanged.connect(self.disable_enable_buttons)
        self.dialog.osm_conf.lineEdit().textChanged.connect(self.disable_enable_buttons)
        self.dialog.radio_osm_conf.toggled.connect(self.disable_enable_buttons)
        self.dialog.radio_selection_keys.toggled.connect(self.disable_enable_buttons)
        self.dialog.output_directory_f.lineEdit().textChanged.connect(self.disable_enable_format_prefix)
        self.dialog.button_run_file.clicked.connect(self.run)

        self.disable_enable_buttons()

    def disable_enable_buttons(self):
        """Display enable only the suitable parameters."""
        osm_file = not self.dialog.osm_file.lineEdit().isNull()
        self.dialog.button_run_file.setEnabled(osm_file)

        if self.dialog.radio_osm_conf.isChecked():
            self.dialog.osm_conf.setEnabled(True)
            self.dialog.table_keys_values_f.setEnabled(False)
            self.dialog.combo_preset_f.setEnabled(False)
            self.dialog.output_directory_f.setEnabled(False)
            self.dialog.combo_format_f.setEnabled(False)
            self.dialog.line_file_prefix_file.setEnabled(False)
            run_possible = \
                not self.dialog.osm_conf.lineEdit().isNull() or \
                bool(self.dialog.osm_conf.lineEdit().placeholderText())
            self.dialog.button_run_file.setEnabled(osm_file and run_possible)
        elif self.dialog.radio_selection_keys.isChecked():
            self.dialog.table_keys_values_f.setEnabled(True)
            self.dialog.combo_preset_f.setEnabled(True)
            self.dialog.output_directory_f.setEnabled(True)
            self.disable_enable_format_prefix()
            self.dialog.osm_conf.setEnabled(False)
        else:
            self.dialog.table_keys_values_f.setEnabled(False)
            self.dialog.combo_preset_f.setEnabled(False)
            self.dialog.output_directory_f.setEnabled(True)
            self.disable_enable_format_prefix()
            self.dialog.osm_conf.setEnabled(False)

    def gather_values(self) -> dict:
        """Retrieval of the values set by the user."""
        properties = super().gather_values()

        properties['osm_file'] = self.dialog.osm_file.filePath()
        conf = self.dialog.osm_conf.filePath()
        if conf:
            properties['osm_conf'] = conf
        else:
            properties['osm_conf'] = (
                self.dialog.osm_conf.lineEdit().placeholderText())

        properties['subset'] = self.dialog.radio_selection_keys.isChecked()
        if properties['subset']:
            properties = self.gather_couple(properties)
        properties['load_only'] = self.dialog.radio_osm_conf.isChecked()

        if not isfile(properties['osm_file']):
            raise FileDoesntExistException(suffix="*.osm or *.pbf")

        if properties['load_only']:
            if not isfile(properties['osm_conf']):
                raise FileDoesntExistException(suffix="*.ini")

        return properties

    @staticmethod
    def generate_sql(properties: dict) -> str:
        """Generate the subset query."""
        key = properties['key']
        val = properties['value']
        if len(val) == 0:
            val = ['']

        multi_keys = len(key) > 1

        if key:

            keys = []
            for k, v in zip(key, val):
                if v:
                    keys.append(f'\"{k}\"=\'{v}\'')
                else:
                    keys.append(f'\"{k}\"')

            if multi_keys:
                type_multi = properties['type_multi_request']
                key_lbl = ''
                index = 0
                for k, type_multi_k in enumerate(type_multi):
                    if index == k:
                        if type_multi_k == MultiType.AND:
                            i = 1
                            key_and = keys[k] + ' AND ' + keys[k + i]

                            while (k + i) < len(type_multi) and type_multi[k + i] == MultiType.AND:
                                i += 1
                                key_and += ' AND ' + keys[k + i]

                            key_lbl += f'({key_and})'
                            index = k + i
                        elif type_multi_k == MultiType.OR:
                            if k == 0:
                                key_lbl += keys[k]
                            key_lbl += ' OR '
                            i = 1
                            while (k + i) < len(type_multi) and type_multi[k + i] == MultiType.OR:
                                key_lbl += keys[k + i] + ' or '
                                i += 1
                            index = k + i
                            if k + i == len(type_multi):
                                key_lbl += keys[k + i]
            else:
                key_lbl = keys[0]

            return key_lbl

    def _run(self):
        """Run the process"""
        try:
            properties = self.gather_values()
        except QuickOsmException as error:
            self.dialog.display_quickosm_exception(error)
            return
        except Exception as error:
            self.dialog.display_critical_exception(error)
            return

        if properties['load_only']:
            # Legacy, waiting to remove the OsmParser for QGIS >= 3.6
            # Change in osm_file_dialog.py L131 too
            output_geom_legacy = [layer.value.lower() for layer in properties['outputs']]
            osm_parser = OsmParser(
                properties['osm_file'],
                load_only=True,
                osm_conf=properties['osm_conf'],
                layers=output_geom_legacy)
            layers = osm_parser.processing_parse()
            for item in layers.values():
                # noinspection PyArgumentList
                QgsProject.instance().addMapLayer(item)
        elif properties['subset']:
            sql_query = self.generate_sql(properties)
            open_file(
                dialog=self.dialog,
                osm_file=properties['osm_file'],
                key=properties['key'],
                output_geom_types=properties['outputs'],
                output_dir=properties['output_directory'],
                output_format=properties['output_format'],
                prefix_file=properties['prefix_file'],
                subset=True,
                subset_query=sql_query
            )
            self.dialog.display_message_bar(
                tr('Successful query'),
                level=Qgis.MessageLevel.Success,
                duration=5)
        else:
            open_file(
                dialog=self.dialog,
                osm_file=properties['osm_file'],
                output_geom_types=properties['outputs'],
                output_dir=properties['output_directory'],
                output_format=properties['output_format'],
                prefix_file=properties['prefix_file'])
            self.dialog.display_message_bar(
                tr('Successful query'),
                level=Qgis.MessageLevel.Success,
                duration=5)
