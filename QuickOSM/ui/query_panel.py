"""Panel OSM base class."""

import html
import logging
import re

from qgis.core import QgsApplication
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QDialog, QDialogButtonBox, QMenu
from qgis.utils import OverrideCursor

from QuickOSM.core.api.connexion_oapi import ConnexionOAPI
from QuickOSM.core.exceptions import (
    MissingParameterException,
    QuickOsmException,
)
from QuickOSM.core.process import process_query
from QuickOSM.core.query_preparation import QueryPreparation
from QuickOSM.core.utilities.tools import get_setting
from QuickOSM.core.utilities.utilities_qgis import (
    open_doc_overpass,
    open_overpass_turbo,
    open_plugin_documentation,
)
from QuickOSM.definitions.gui import Panels
from QuickOSM.definitions.osm import WHITE_LIST, LayerType, QueryLanguage
from QuickOSM.definitions.overpass import OVERPASS_SERVERS
from QuickOSM.tools.i18n import tr
from QuickOSM.tools.resources import resources_path
from QuickOSM.ui.base_overpass_panel import BaseOverpassPanel
from QuickOSM.ui.xml_highlighter import QueryHighlighter



LOGGER = logging.getLogger('QuickOSM')


class QueryPanel(BaseOverpassPanel):

    """Final implementation for the panel."""

    def __init__(self, dialog: QDialog):
        super().__init__(dialog)
        self.panel = Panels.Query

        # Fix #203, the XML Highlighter must be a member of the class
        self.highlighter = None

    def setup_panel(self):
        super().setup_panel()
        self.dialog.combo_query_type_q.addItem(tr('Canvas Extent'), 'canvas')
        self.dialog.combo_query_type_q.addItem(tr('Layer Extent'), 'layer')
        self.dialog.combo_query_type_q.setItemIcon(0, QIcon(":images/themes/default/mLayoutItemMap.svg"))
        self.dialog.combo_query_type_q.setItemIcon(
            1, QIcon(":images/themes/default/algorithms/mAlgorithmRandomPointsWithinExtent.svg"))
        self.dialog.combo_query_type_q.currentIndexChanged.connect(
            self.query_type_updated)
        self.dialog.combo_extent_layer_q.layerChanged.connect(self.query_type_updated)

        self.dialog.button_run_query_q.setIcon(QIcon(QgsApplication.iconPath("mActionStart.svg")))

        self.highlighter = QueryHighlighter(self.dialog.text_query.document())
        self.dialog.text_query.cursorPositionChanged.connect(
            self.highlighter.rehighlight)
        self.dialog.text_query.cursorPositionChanged.connect(
            self.allow_nominatim_or_extent)

        self.dialog.button_overpass_turbo.setIcon(
            QIcon(resources_path('icons', 'turbo.png')))
        self.dialog.button_overpass_turbo.clicked.connect(open_overpass_turbo)

        # Setup menu for documentation
        popup_menu = QMenu()
        map_features_action = QAction(
            'Map Features', self.dialog.button_documentation)
        # noinspection PyUnresolvedReferences
        map_features_action.triggered.connect(open_plugin_documentation)
        popup_menu.addAction(map_features_action)
        overpass_action = QAction('Overpass', self.dialog.button_documentation)
        # noinspection PyUnresolvedReferences
        overpass_action.triggered.connect(open_doc_overpass)
        popup_menu.addAction(overpass_action)
        self.dialog.button_documentation.setMenu(popup_menu)

        self.dialog.button_generate_query.setIcon(QIcon(":images/themes/default/processingAlgorithm.svg"))

        self.dialog.button_generate_query.setMenu(QMenu())

        self.dialog.action_oql_q.triggered.connect(self.query_language_oql)
        self.dialog.action_xml_q.triggered.connect(self.query_language_xml)
        self.dialog.button_generate_query.menu().addAction(self.dialog.action_oql_q)
        self.dialog.button_generate_query.menu().addAction(self.dialog.action_xml_q)

        self.dialog.run_buttons[self.panel].clicked.connect(self.run)
        self.dialog.button_generate_query.clicked.connect(self.query_language_check)
        self.dialog.button_box_q.button(QDialogButtonBox.StandardButton.Reset).clicked.connect(
            self.dialog.reset_form)

        self.allow_nominatim_or_extent()
        self.query_type_updated()

    def gather_values(self) -> dict:
        """Retrieval of the values set by the user."""
        properties = super().gather_values()

        properties['query'] = self.dialog.text_query.toPlainText()

        properties['expected_csv'] = WHITE_LIST
        if self.dialog.checkbox_points_q.isChecked():
            properties['expected_csv'][LayerType.Points.value.lower()] = (
                self.dialog.edit_csv_points.text())
        if self.dialog.checkbox_lines_q.isChecked():
            properties['expected_csv'][LayerType.Lines.value.lower()] = (
                self.dialog.edit_csv_lines.text())
        if self.dialog.checkbox_multilinestrings_q.isChecked():
            properties['expected_csv'][LayerType.Multilinestrings.value.lower()] = (
                self.dialog.edit_csv_multilinestrings.text())
        if self.dialog.checkbox_multipolygons_q.isChecked():
            properties['expected_csv'][LayerType.Multipolygons.value.lower()] = (
                self.dialog.edit_csv_multipolygons.text())

        # TODO check this regex
        # noinspection RegExpRedundantEscape
        if not properties['place'] and \
                re.search(r'\{\{nominatim\}\}', properties['query']) or \
                re.search(r'\{\{nominatimArea:\}\}', properties['query']) \
                or \
                re.search(r'\{\{geocodeArea:\}\}', properties['query']):
            raise MissingParameterException(suffix='nominatim field')

        return properties

    def _run(self):
        self.write_nominatim_file(self.panel)

        try:
            properties = self.gather_values()
        except QuickOsmException as error:
            self.dialog.display_quickosm_exception(error)
            return
        except Exception as error:
            self.dialog.display_critical_exception(error)
            return

        num_layers = process_query(
            dialog=self.dialog,
            query=properties['query'],
            output_dir=properties['output_directory'],
            output_format=properties['output_format'],
            prefix_file=properties['prefix_file'],
            output_geometry_types=properties['outputs'],
            white_list_values=properties['expected_csv'],
            area=properties['place'],
            bbox=properties['bbox'])
        self.end_query(num_layers)

    def generate_query(self, oql_output: bool = True):
        """Generate the query as final."""
        query = self.dialog.text_query.toPlainText()
        area = self.dialog.places_edits[Panels.Query].text()
        self.write_nominatim_file(Panels.Query)

        try:
            properties = self.gather_values()
        except QuickOsmException as error:
            self.dialog.display_quickosm_exception(error)
            return
        except Exception as error:
            self.dialog.display_critical_exception(error)
            return

        server = get_setting('defaultOAPI', OVERPASS_SERVERS[0]) + 'convert'
        query = QueryPreparation(query, properties['bbox'], area, server)
        query_string = query.prepare_query()
        if (oql_output and not query.is_oql_query()) or (not oql_output and query.is_oql_query()):
            query.prepare_query()
            url = query.prepare_url(QueryLanguage.OQL if oql_output else QueryLanguage.XML)
            connexion_overpass_api = ConnexionOAPI(url)
            LOGGER.debug(f'Encoded URL: {url}')
            query_string = connexion_overpass_api.run_convert()
            query_string = html.unescape(query_string)

        self.dialog.text_query.setPlainText(query_string)

    def allow_nominatim_or_extent(self):
        """Disable or enable radio buttons if nominatim or extent.

        Disable buttons if the query is empty.
        """
        query = self.dialog.text_query.toPlainText()

        self.dialog.button_generate_query.setDisabled(query == '')
        self.dialog.button_run_query_q.setDisabled(query == '')

        # TODO check this regexp
        # noinspection RegExpRedundantEscape
        if re.search(r'\{\{nominatim\}\}', query) or \
                re.search(r'\{\{nominatimArea:(.*)\}\}', query) or \
                re.search(r'\{\{geocodeArea:(.*)\}\}', query):
            self.dialog.line_place_q.setEnabled(True)
        else:
            self.dialog.line_place_q.setEnabled(False)
            self.dialog.line_place_q.setText('')

        # TODO check this regexp
        # noinspection RegExpRedundantEscape
        if re.search(r'\{\{(bbox|center)\}\}', query):
            self.dialog.combo_query_type_q.setEnabled(True)
        else:
            self.dialog.combo_query_type_q.setEnabled(False)

    def query_type_updated(self):
        """Update the ui when the query type is modified."""
        self._core_query_type_updated(
            self.dialog.combo_query_type_q,
            self.dialog.combo_extent_layer_q,
            checkbox=self.dialog.checkbox_selection_q)

    def query_language_check(self):
        """Check the wanted language."""

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            if self.dialog.query_language[Panels.Query] == QueryLanguage.OQL:
                self.generate_query(oql_output=True)
            elif self.dialog.query_language[Panels.Query] == QueryLanguage.XML:
                self.generate_query(oql_output=False)
