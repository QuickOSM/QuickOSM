"""Simple Processing algorithm to open an OSM file with sub layers."""

from os.path import exists
from typing import Dict

from osgeo import gdal
from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingException,
    QgsProcessingOutputVectorLayer,
    QgsProcessingParameterFile,
    QgsVectorLayer,
)

from QuickOSM.tools.i18n import tr



class OpenOsmFile(QgisAlgorithm):
    """Simple Processing algorithm to open an OSM file with sub layers."""

    FILE = 'FILE'
    OSM_CONF = 'OSM_CONF'
    OUTPUT_POINTS = 'OUTPUT_POINTS'
    OUTPUT_LINES = 'OUTPUT_LINES'
    OUTPUT_MULTILINESTRINGS = 'OUTPUT_MULTILINESTRINGS'
    OUTPUT_MULTIPOLYGONS = 'OUTPUT_MULTIPOLYGONS'
    OUTPUT_OTHER_RELATIONS = 'OUTPUT_OTHER_RELATIONS'

    def __init__(self):
        super().__init__()
        self.feedback = None

    @staticmethod
    def group() -> str:
        """Return the group of the algorithm."""
        return tr('Advanced')

    @staticmethod
    def groupId() -> str:
        """Return the id of the group."""
        return 'advanced'

    def flags(self):
        """Return the flags."""
        return super().flags() | QgsProcessingAlgorithm.Flag.FlagHideFromToolbox

    @staticmethod
    def name() -> str:
        """Return the name of the algorithm."""
        return 'openosmfile'

    def displayName(self) -> str:
        """Return the display name of the algorithm."""
        return self.tr('Open sublayers from an OSM file')

    def shortHelpString(self) -> str:
        """Return a helper for the algorithm."""
        return self.tr(
            'Open all sub-layers from an OSM file. A custom OSM configuration file can be specified '
            'following the OGR documentation. This algorithm will not make a copy of the input file, '
            'it will only open it using OGR and custom INI file if provided.')

    def initAlgorithm(self, config=None):
        """Set up of the algorithm."""
        param = QgsProcessingParameterFile(self.FILE, self.tr('OSM file'))
        help_string = tr('The extension can be a OSM or PBF file.')
        param.setHelp(help_string)
        self.addParameter(param)

        param = QgsProcessingParameterFile(
            self.OSM_CONF, tr('OSM configuration'), optional=True
        )
        help_string = tr(
            'The OGR OSM configuration file. This file is used to customize the import process '
            'about OSM tags. You should read the OGR documentation {url}').format(
            url='https://gdal.org/drivers/vector/osm.html'
        )
        param.setHelp(help_string)
        self.addParameter(param)

        output = QgsProcessingOutputVectorLayer(
            self.OUTPUT_POINTS, tr('Output points'), QgsProcessing.SourceType.TypeVectorPoint)
        self.addOutput(output)

        output = QgsProcessingOutputVectorLayer(
            self.OUTPUT_LINES, tr('Output lines'), QgsProcessing.SourceType.TypeVectorLine)
        self.addOutput(output)

        output = QgsProcessingOutputVectorLayer(
            self.OUTPUT_MULTILINESTRINGS, tr('Output multilinestrings'),
            QgsProcessing.SourceType.TypeVectorLine
        )
        self.addOutput(output)

        output = QgsProcessingOutputVectorLayer(
            self.OUTPUT_MULTIPOLYGONS, tr('Output multipolygons'),
            QgsProcessing.SourceType.TypeVectorPolygon
        )
        self.addOutput(output)

        output = QgsProcessingOutputVectorLayer(
            self.OUTPUT_OTHER_RELATIONS, tr('Output other relations'),
            QgsProcessing.SourceType.TypeVector
        )
        self.addOutput(output)

    def processAlgorithm(self, parameters, context, feedback) -> Dict[str, any]:
        """Run the algorithm."""
        self.feedback = feedback
        file = self.parameterAsString(parameters, self.FILE, context)
        osm_configuration = self.parameterAsString(
            parameters, self.OSM_CONF, context)

        if osm_configuration:
            if not exists(osm_configuration):
                raise QgsProcessingException(
                    self.tr('OSM Configuration file not found'))

            gdal.SetConfigOption('OSM_CONFIG_FILE', osm_configuration)

        gdal.SetConfigOption('OSM_USE_CUSTOM_INDEXING', 'NO')

        points = QgsVectorLayer(f'{file}|layername=points', 'points', 'ogr')
        context.temporaryLayerStore().addMapLayer(points)

        lines = QgsVectorLayer(f'{file}|layername=lines', 'lines', 'ogr')
        context.temporaryLayerStore().addMapLayer(lines)

        multilinestrings = QgsVectorLayer(f'{file}|layername=multilinestrings', 'multilinestrings', 'ogr')
        context.temporaryLayerStore().addMapLayer(multilinestrings)

        multipolygons = QgsVectorLayer(f'{file}|layername=multipolygons', 'multipolygons', 'ogr')
        context.temporaryLayerStore().addMapLayer(multipolygons)

        other_relations = QgsVectorLayer(f'{file}|layername=other_relations', 'other_relations', 'ogr')
        context.temporaryLayerStore().addMapLayer(other_relations)

        outputs = {
            self.OUTPUT_POINTS: points.id(),
            self.OUTPUT_LINES: lines.id(),
            self.OUTPUT_MULTILINESTRINGS: multilinestrings.id(),
            self.OUTPUT_MULTIPOLYGONS: multipolygons.id(),
            self.OUTPUT_OTHER_RELATIONS: other_relations.id()
        }

        gdal.SetConfigOption('OSM_CONFIG_FILE', None)
        gdal.SetConfigOption('OSM_USE_CUSTOM_INDEXING', None)

        return outputs
