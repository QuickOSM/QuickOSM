"""Decorate the layer as a QuickOSM output."""

from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm
from qgis.core import (
    QgsCategorizedSymbolRenderer,
    QgsLayerMetadata,
    QgsProcessingAlgorithm,
    QgsProcessingLayerPostProcessorInterface,
    QgsProcessingOutputVectorLayer,
    QgsProcessingParameterVectorLayer,
    QgsRendererCategory,
    QgsSymbol,
    QgsWkbTypes,
)
from qgis.PyQt.QtGui import QColor

from QuickOSM.core import actions
from QuickOSM.tools.i18n import tr



class DecorateLayerAlgorithm(QgisAlgorithm):
    """Decorate the layer as a QuickOSM output."""

    LAYER = 'LAYER'
    OUTPUT_LAYER = 'OUTPUT_LAYER'

    def __init__(self):
        """Constructor"""
        super().__init__()
        self.feedback = None
        self.layer = None

    @staticmethod
    def name() -> str:
        """Return the name of the algorithm."""
        return 'decoratelayer'

    @staticmethod
    def displayName() -> str:
        """Return the display name of the algorithm."""
        return tr('Decorate a layer from OSM')

    @staticmethod
    def group() -> str:
        """Return the group of the algorithm."""
        return tr('Advanced')

    @staticmethod
    def groupId() -> str:
        """Return the id of the group."""
        return 'advanced'

    def shortHelpString(self) -> str:
        """Return a helper for the algorithm."""
        return tr('Decorate the layer as an QuickOSM output.')

    def flags(self):
        """Return the flags."""
        return super().flags() | QgsProcessingAlgorithm.Flag.FlagHideFromToolbox

    def add_parameters(self):
        """Set up the parameters."""
        param = QgsProcessingParameterVectorLayer(
            self.LAYER, tr('Layer')
        )
        help_string = tr('Path where the file will be download.')
        param.setHelp(help_string)
        self.addParameter(param)

    def add_outputs(self):
        """Set up the outputs of the algorithm."""
        output = QgsProcessingOutputVectorLayer(
            self.OUTPUT_LAYER, tr('Output layer')
        )
        self.addOutput(output)

    def fetch_based_parameters(self, parameters, context):
        """Get the parameters."""
        self.layer = self.parameterAsVectorLayer(parameters, self.LAYER, context)

    def initAlgorithm(self, config=None):
        """Set up of the algorithm."""
        _ = config
        self.add_parameters()
        self.add_outputs()

    def processAlgorithm(self, parameters, context, feedback):
        """Run the algorithm."""
        self.feedback = feedback
        self.fetch_based_parameters(parameters, context)

        fields = self.layer.fields().names()
        self.feedback.pushInfo('Set up the QuickOSM actions on the layer.')
        actions.add_actions(self.layer, fields)

        self.feedback.pushInfo('Write the metadata of the layer.')
        metadata = QgsLayerMetadata()
        metadata.setRights([tr("© OpenStreetMap contributors")])
        metadata.setLicenses(['https://openstreetmap.org/copyright'])
        self.layer.setMetadata(metadata)

        outputs = {
            self.OUTPUT_LAYER: self.layer,
        }
        return outputs


class SetColoringPostProcessor(QgsProcessingLayerPostProcessorInterface):
    """Color the layer with the value of the 'colour' field."""

    instance = None
    fields = []
    layer_type_dict = {
        'points': 1,
        'lines': 2,
        'multilinestrings': 5,
        'multipolygons': 6
    }

    def postProcessLayer(self, layer, context, feedback):
        """Run the coloring process"""
        _ = context

        layer_type = layer.wkbType()
        feedback.pushInfo('Creating the style from OSM data "colour".')
        index = self.fields.index('colour')
        if index != -1:
            colors = layer.uniqueValues(index)
            categories = []
            for value in colors:
                if str(value) == 'None':
                    value = ''
                if layer_type in [self.layer_type_dict['lines'], self.layer_type_dict['multilinestrings']]:
                    symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.GeometryType.LineGeometry)
                elif layer_type == self.layer_type_dict['points']:
                    symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.GeometryType.PointGeometry)
                elif layer_type == self.layer_type_dict['multipolygons']:
                    symbol = QgsSymbol.defaultSymbol(QgsWkbTypes.GeometryType.PolygonGeometry)
                else:
                    break
                symbol.setColor(QColor(value))
                category = QgsRendererCategory(str(value), symbol, str(value))
                categories.append(category)

            renderer = QgsCategorizedSymbolRenderer("colour", categories)
            layer.setRenderer(renderer)

            layer.triggerRepaint()

    # Hack to work around sip bug!
    @staticmethod
    def create(fields) -> 'SetColoringPostProcessor':
        """Launch the algorithm"""
        SetColoringPostProcessor.instance = SetColoringPostProcessor()
        SetColoringPostProcessor.fields = fields
        return SetColoringPostProcessor.instance
