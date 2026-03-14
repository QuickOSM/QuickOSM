"""Actions definitions."""
from qgis.core import (
    Qgis,
    QgsAction,
    QgsExpressionContextUtils,
    QgsProject,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QDialog
from qgis.utils import OverrideCursor, iface, plugins

from QuickOSM.core import process
from QuickOSM.core.josm_remote import open_object
from QuickOSM.core.utilities.utilities_qgis import open_webpage
from QuickOSM.definitions.action import Visibility
from QuickOSM.tools.i18n import tr
from QuickOSM.tools.resources import resources_path



ACTIONS_PATH = 'from QuickOSM.core.actions import Actions\n'
ACTIONS_VISIBILITY = [
    Visibility.Canvas.value,
    Visibility.Feature.value,
    Visibility.Field.value
]


def add_actions(layer: QgsVectorLayer, keys: list):
    """Add actions on layer.

    :param layer: The layer.
    :type layer: QgsVectorLayer

    :param keys: The list of keys in the layer.
    :type keys: list
    """
    actions = layer.actions()

    title = tr('OpenStreetMap Browser')
    osm_browser = QgsAction(
        QgsAction.ActionType.OpenUrl,
        title,
        'http://www.openstreetmap.org/browse/[% "osm_type" %]/[% "osm_id" %]',
        '',
        False,
        title,
        ACTIONS_VISIBILITY,
        ''
    )
    actions.addAction(osm_browser)

    title = 'JOSM'
    josm = QgsAction(
        QgsAction.ActionType.GenericPython,
        title,
        ACTIONS_PATH + 'Actions.run("josm","[% "full_id" %]")',
        resources_path('icons', 'josm_icon.svg'),
        False,
        title,
        ACTIONS_VISIBILITY,
        ''
    )
    actions.addAction(josm)

    title = tr('User default editor')
    default_editor = QgsAction(
        QgsAction.ActionType.OpenUrl,
        title,
        'http://www.openstreetmap.org/edit?[% "osm_type" %]=[% "osm_id" %]',
        '',
        False,
        title,
        ACTIONS_VISIBILITY,
        ''
    )
    actions.addAction(default_editor)

    for link in ['mapillary', 'url', 'website', 'wikipedia', 'wikidata', 'ref:UAI']:
        if link in keys:

            # Add an image to the action if available
            image = ''
            if link == 'wikipedia':
                image = resources_path('icons', 'wikipedia.png')
            elif link == 'wikidata':
                image = resources_path('icons', 'wikidata.png')
            elif link in ['url', 'website']:
                image = resources_path('icons', 'external_link.png')
            elif link == 'mapillary':
                image = resources_path('icons', 'mapillary_logo.svg')

            link = link.replace(":", "_")
            generic = QgsAction(
                QgsAction.ActionType.GenericPython,
                link,
                (ACTIONS_PATH
                 + f'Actions.run("{link}","[% "{link}" %]")'),
                image,
                False,
                link,
                ACTIONS_VISIBILITY,
                ''
            )
            actions.addAction(generic)

    if 'network' in keys and 'ref' in keys:
        sketch_line = QgsAction(
            QgsAction.ActionType.GenericPython,
            tr('Sketchline'),
            (
                ACTIONS_PATH +
                'Actions.run_sketch_line("[% "network" %]","[% "ref" %]")'
            ),
            '',
            False,
            '',
            ACTIONS_VISIBILITY,
            ''
        )
        actions.addAction(sketch_line)


def add_relaunch_action(layer: QgsVectorLayer, layer_name: str = ""):
    """ Add the relaunch action """
    actions = layer.actions()

    title = tr('Reload the query in a new file')
    reload = QgsAction(
        QgsAction.ActionType.GenericPython,
        title,
        ACTIONS_PATH + f'Actions.run_reload(layer_name="{layer_name}")',
        '',
        False,
        title,
        [Visibility.Layer.value],
        ''
    )
    actions.addAction(reload)


class Actions:
    """
    Manage actions available on layers
    """

    def __init__(self, dialog: QDialog):
        self.dialog = dialog

    @staticmethod
    def run(field: str, value: str):
        """
        Run an action with only one value as parameter

        :param field:Type of the action
        :type field:str

        :param value:Value of the field for one entity
        :type value:str
        """

        if value == '':
            iface.messageBar().pushMessage(
                tr('Sorry, the field \'{fieldname}\' is empty for this entity.'
                   .format(fieldname=field)),
                level=Qgis.MessageLevel.Warning, duration=7)
        else:

            if field in ['url', 'website', 'wikipedia', 'wikidata']:
                url = None

                if field in ('url', 'website'):
                    url = value

                if field == 'ref_UAI':
                    url = "http://www.education.gouv.fr/pid24302/annuaire-" \
                          "resultat-recherche.html?lycee_name=" + value

                if field == 'wikipedia':
                    url = "http://en.wikipedia.org/wiki/" + value

                if field == 'wikidata':
                    url = "http://www.wikidata.org/wiki/" + value

                open_webpage(url)

            elif field == 'mapillary':
                if 'go2mapillary' in plugins:
                    plugins['go2mapillary'].viewer.open(value)
                else:
                    url = 'https://www.mapillary.com/map/im/' + value
                    open_webpage(url)

            elif field == 'josm':
                if not open_object(value):
                    iface.messageBar().pushMessage(
                        tr('The JOSM remote seems to be disabled.'),
                        level=Qgis.MessageLevel.Critical,
                        duration=7)

            # NOT USED
            elif field == 'rawedit':
                # url = QUrl("http://rawedit.openstreetmap.fr/edit/" + value)
                # web_browser = QWebView(None)
                # web_browser.load(url)
                # web_browser.show()
                pass

    @staticmethod
    def run_sketch_line(network: str, ref: str):
        """
        Run an action with two values for sketchline

        :param network:network of the bus
        :type network:str

        :param ref:ref of the bus
        :type ref:str
        """
        if network == '' or ref == '':
            iface.messageBar().pushMessage(
                tr('Sorry, this field is empty for this entity.'),
                level=Qgis.MessageLevel.Warning,
                duration=7)
        else:
            url = f'http://www.overpass-api.de/api/sketch-line?network={network}&ref={ref}'
            open_webpage(url)

    @staticmethod
    def run_reload(layer_name: str = "", layer: QgsVectorLayer = None, dialog: QDialog = None):
        """ Reload the query """

        if not layer:
            layer = QgsProject.instance().mapLayersByName(layer_name)[0]

        if not layer_name:
            layer_name = QgsExpressionContextUtils.layerScope(layer).variable('layer_name')

        query = QgsExpressionContextUtils.layerScope(layer).variable('quickosm_query')

        with OverrideCursor(Qt.CursorShape.WaitCursor):
            process.reload_query(query, layer_name, dialog)

    def pre_run_reload(self):
        """ Prepare to reload the query."""

        layer = self.dialog.iface.layerTreeView().currentLayer()
        self.run_reload(layer=layer, dialog=self.dialog)
