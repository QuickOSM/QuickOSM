"""Panel OSM Queries based on Overpass base class."""

from qgis.core import (
    Qgis,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsGeometry,
    QgsProject,
    QgsRectangle,
    QgsVectorLayer,
)
from qgis.PyQt.QtWidgets import QCompleter, QDialog

from QuickOSM.core.exceptions import MissingLayerUI, NoSelectedFeatures
from QuickOSM.core.utilities.tools import nominatim_file
from QuickOSM.definitions.gui import Panels
from QuickOSM.definitions.osm import QueryLanguage, QueryType
from QuickOSM.tools.i18n import tr
from QuickOSM.ui.base_processing_panel import BaseProcessingPanel



class BaseOverpassPanel(BaseProcessingPanel):

    """Panel OSM Processing base class.

    This panels will have a run button.

    This is a kind of virtual class.
    """

    def __init__(self, dialog: QDialog):
        super().__init__(dialog)
        self.last_places = []

    def setup_panel(self):
        """Function to set custom UI for some panels."""
        super().setup_panel()
        if self.dialog.advanced_panels[self.panel]:
            self.dialog.advanced_panels[self.panel].setSaveCollapsedState(False)
            self.dialog.advanced_panels[self.panel].setCollapsed(True)

            self.dialog.action_oql[self.panel].setEnabled(False)

    def query_language_xml(self):
        """Update the wanted language."""
        self.dialog.query_language[self.panel] = QueryLanguage.XML
        self.dialog.action_oql[self.panel].setEnabled(True)
        self.dialog.action_xml[self.panel].setEnabled(False)

    def query_language_oql(self):
        """Update the wanted language."""
        self.dialog.query_language[self.panel] = QueryLanguage.OQL
        self.dialog.action_xml[self.panel].setEnabled(True)
        self.dialog.action_oql[self.panel].setEnabled(False)

    def query_language_updated(self):
        """Transfer the wanted language through panels."""
        if self.dialog.query_language[Panels.Query] != \
                self.dialog.query_language[Panels.QuickQuery]:
            self.dialog.query_language[Panels.Query] = self.dialog.query_language[Panels.QuickQuery]
        if self.dialog.query_language[Panels.Query] == QueryLanguage.OQL:
            self.dialog.action_xml[Panels.Query].setEnabled(True)
            self.dialog.action_oql[Panels.Query].setEnabled(False)
        elif self.dialog.query_language[Panels.Query] == QueryLanguage.XML:
            self.dialog.action_oql[Panels.Query].setEnabled(True)
            self.dialog.action_xml[Panels.Query].setEnabled(False)

    def init_nominatim_autofill(self):
        """Open the nominatim file and start setting up the auto-completion."""
        # Useful to avoid duplicate if we add a new completer.
        for line_edit in self.dialog.places_edits.values():
            line_edit.setCompleter(None)

        user_file = nominatim_file()

        with open(user_file, encoding='utf8') as file:
            self.last_places = []
            for line in file:
                self.last_places.append(line.rstrip('\n'))

            nominatim_completer = QCompleter(self.last_places)
            for line_edit in self.dialog.places_edits.values():
                line_edit.setCompleter(nominatim_completer)
                line_edit.completer().setCompletionMode(
                    QCompleter.CompletionMode.PopupCompletion)

    @staticmethod
    def sort_nominatim_places(existing_places: list, place: str) -> list:
        """Helper to sort and limit results of saved nominatim places."""
        if place in existing_places:
            existing_places.pop(existing_places.index(place))
        existing_places.insert(0, place)
        existing_places = list(dict.fromkeys(existing_places))
        return existing_places[:10]

    def write_nominatim_file(self, panel: Panels):
        """Write new nominatim value in the file.

        :param panel: The panel to use to fetch the nominatim value.
        :type panel: Panels
        """
        value = self.dialog.places_edits[panel].text()
        new_list = self.sort_nominatim_places(self.last_places, value)

        user_file = nominatim_file()

        try:
            with open(user_file, 'w', encoding='utf8') as file:
                for item in new_list:
                    if item:
                        file.write(f'{item}\n')
        except UnicodeDecodeError:
            # The file is corrupted ?
            # Remove all old places
            with open(user_file, 'w', encoding='utf8') as file:
                file.write('\n')

        self.init_nominatim_autofill()

    def _core_query_type_updated(self, combo_query_type, widget, spinbox=None, checkbox=None):
        """Enable/disable the extent/layer widget."""
        current = combo_query_type.currentData()

        if combo_query_type.count() == 2:
            # Query tab, widget is the layer selector
            if current == 'layer':
                widget.setVisible(True)
                layer = self.dialog.layers_buttons[self.panel].currentLayer()
                if isinstance(layer, QgsVectorLayer):
                    checkbox.setVisible(True)
                else:
                    checkbox.setVisible(False)
                    checkbox.setChecked(False)
            else:
                widget.setVisible(False)
                checkbox.setVisible(False)
                checkbox.setChecked(False)
        else:
            # Quick query tab, widget is the stacked widget
            if current in ['in', 'around']:
                widget.setCurrentIndex(0)
                spinbox.setVisible(current == 'around')
            elif current in ['layer']:
                widget.setCurrentIndex(1)
                layer = self.dialog.layers_buttons[self.panel].currentLayer()
                if isinstance(layer, QgsVectorLayer):
                    checkbox.setVisible(True)
                else:
                    checkbox.setVisible(False)
                    checkbox.setChecked(False)
            elif current in ['canvas', 'attributes']:
                widget.setCurrentIndex(2)

    # TODO remove
    def _start_process(self):
        """Make some stuff before launching the process."""
        self.dialog.button_show_query.setDisabled(True)
        self.dialog.button_generate_query.setDisabled(True)
        super()._start_process()

    # TODO remove
    def _end_process(self):
        """Make some stuff after the process."""
        self.dialog.button_show_query.setDisabled(False)
        self.dialog.button_generate_query.setDisabled(False)
        super()._end_process()

    def end_query(self, num_layers):
        """Display the message at the end of the query.

        :param num_layers: Number of layers which have been loaded.
        :rtype num_layers: int
        """
        if num_layers:
            text = tr(
                'Successful query, {} layer(s) has been loaded.').format(
                num_layers)
            self.dialog.set_progress_text(text)
            self.dialog.display_message_bar(text, level=Qgis.MessageLevel.Success, duration=5)
        else:
            self.dialog.set_progress_text(tr('No result'))
            self.dialog.display_message_bar(
                tr('Successful query, but no OSM data matched the Overpass query on this Overpass server.'),
                level=Qgis.MessageLevel.Warning, duration=7)

    def gather_values(self) -> dict:
        """Retrieval of the values set by the user."""
        properties = super().gather_values()

        properties = self.gather_spatial_values(properties)

        return properties

    def gather_spatial_values(self, properties: dict) -> dict:
        """Retrieval of the values set by the user."""

        place = self.dialog.places_edits[self.panel].text()
        if place == '':
            place = None
        properties['place'] = place

        query_type = self.dialog.query_type_buttons[self.panel].currentData()

        if query_type in ['in', 'around']:
            place = self.dialog.places_edits[self.panel].text()
            properties['place'] = place
            properties['bbox'] = None

        elif query_type in ['canvas', 'layer']:
            if query_type == 'canvas':
                geom_extent = self.dialog.iface.mapCanvas().extent()
                source_crs = self.dialog.iface.mapCanvas().mapSettings().destinationCrs()
            elif query_type == 'layer':
                # Else if a layer is checked
                layer = self.dialog.layers_buttons[self.panel].currentLayer()
                if not layer:
                    raise MissingLayerUI
                if self.dialog.selection_features[self.panel].isChecked() \
                        and isinstance(layer, QgsVectorLayer):
                    geom_extent = layer.boundingBoxOfSelected()
                    if geom_extent == QgsRectangle(0, 0, 0, 0):
                        raise NoSelectedFeatures
                else:
                    geom_extent = layer.extent()
                source_crs = layer.crs()
            else:
                raise NotImplementedError

            # noinspection PyArgumentList
            geom_extent = QgsGeometry.fromRect(geom_extent)
            epsg_4326 = QgsCoordinateReferenceSystem('EPSG:4326')
            # noinspection PyArgumentList
            crs_transform = QgsCoordinateTransform(
                source_crs, epsg_4326, QgsProject.instance())
            geom_extent.transform(crs_transform)
            properties['bbox'] = geom_extent.boundingBox()
            properties['place'] = None
        else:
            properties['place'] = None
            properties['bbox'] = None

        if query_type == 'in':
            properties['query_type'] = QueryType.InArea
        elif query_type == 'around':
            properties['query_type'] = QueryType.AroundArea
        elif query_type == 'canvas':
            properties['query_type'] = QueryType.BBox
        elif query_type == 'layer':
            properties['query_type'] = QueryType.BBox
        elif query_type == 'attributes':
            properties['query_type'] = QueryType.NotSpatial
        else:
            raise NotImplementedError

        return properties
