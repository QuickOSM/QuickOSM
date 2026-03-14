"""Run the process of the plugin as an algorithm."""
from os.path import basename, dirname

import processing

from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingContext,
    QgsProcessingMultiStepFeedback,
    QgsProcessingOutputVectorLayer,
    QgsProcessingParameterFileDestination,
    QgsProcessingUtils,
    QgsReferencedRectangle,
)
from qgis.PyQt.QtGui import QIcon

from QuickOSM.core.api.connexion_oapi import ConnexionOAPI
from QuickOSM.core.parser.osm_parser import OsmParser
from QuickOSM.definitions.format import Format
from QuickOSM.tools.i18n import tr
from QuickOSM.tools.resources import resources_path
from QuickOSM.quick_osm_processing.advanced.build_query import (
    BuildQueryAroundAreaAlgorithm,
    BuildQueryExtentAlgorithm,
    BuildQueryInAreaAlgorithm,
    BuildQueryNotSpatialAlgorithm,
)
from QuickOSM.quick_osm_processing.advanced.decorate_output import (
    SetColoringPostProcessor,
)
from QuickOSM.quick_osm_processing.build_input import BuildRaw



class DownloadOSMData(QgisAlgorithm):
    """Set up the parameters needed for the download algorithms."""

    FILE = 'FILE'
    OUTPUT_POINTS = 'OUTPUT_POINTS'
    OUTPUT_LINES = 'OUTPUT_LINES'
    OUTPUT_MULTILINESTRINGS = 'OUTPUT_MULTILINESTRINGS'
    OUTPUT_MULTIPOLYGONS = 'OUTPUT_MULTIPOLYGONS'

    OUTPUT_CANCEL = {
        OUTPUT_POINTS: None,
        OUTPUT_LINES: None,
        OUTPUT_MULTILINESTRINGS: None,
        OUTPUT_MULTIPOLYGONS: None
    }

    def __init__(self):
        """Constructor"""
        super().__init__()
        self.file = None

    @staticmethod
    def group() -> str:
        """Return the group of the algorithm."""
        return ''

    @staticmethod
    def groupId() -> str:
        """Return the id of the group."""
        return ''

    def shortHelpString(self) -> str:
        """Return a helper for the algorithm."""
        return tr('Fetch the OSM data that match the request.')

    def icon(self):
        """Return the icon."""
        return QIcon(resources_path('icons', 'QuickOSM.svg'))

    def flags(self):
        """Return the flags."""
        return QgisAlgorithm.flags(self) | QgsProcessingAlgorithm.Flag.FlagHideFromModeler

    def fetch_based_parameters(self, parameters, context):
        """Get the parameters."""
        self.file = self.parameterAsFileOutput(parameters, self.FILE, context)

    def add_parameters(self):
        """Set up additional parameters."""
        param = QgsProcessingParameterFileDestination(
            self.FILE, tr('Output file'),
            optional=True)
        param.setFileFilter('*.gpkg')
        help_string = tr('Path where the file will be download.')
        param.setHelp(help_string)
        self.addParameter(param)

    def add_outputs(self):
        """Set up the outputs of the algorithm."""
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

    def initAlgorithm(self, config=None):
        """Set up of the algorithm."""
        _ = config
        self.add_top_parameters()
        self.add_bottom_parameters()
        self.add_parameters()
        self.add_outputs()

    def process_road(self, context, url):
        """Major step of the process"""

        if self.feedback.isCanceled():
            self.feedback.reportError('The algorithm has been canceled during the building of the url.')
            return self.OUTPUT_CANCEL

        self.feedback.setCurrentStep(1)
        self.feedback.pushInfo('Downloading data and OSM file.')

        connexion_overpass_api = ConnexionOAPI(url)
        osm_file = connexion_overpass_api.run()

        if self.feedback.isCanceled():
            self.feedback.reportError('The algorithm has been canceled during the download.')
            return self.OUTPUT_CANCEL

        self.feedback.setCurrentStep(2)
        self.feedback.pushInfo('Processing downloaded file.')

        out_dir = dirname(self.file) if self.file else None
        out_file = basename(self.file)[:-5] if self.file else None

        osm_parser = OsmParser(
            osm_file=osm_file,
            output_format=Format.GeoPackage,
            output_dir=out_dir,
            prefix_file=out_file,
            feedback_alg=True,
            feedback=self.feedback
        )

        layers = osm_parser.processing_parse()

        if self.feedback.isCanceled():
            self.feedback.reportError('The algorithm has been canceled during the parsing.')
            return self.OUTPUT_CANCEL

        self.feedback.setCurrentStep(7)
        self.feedback.pushInfo('Decorating the requested layers.')

        layer_output = []
        OUTPUT = {
            'points': self.OUTPUT_POINTS,
            'lines': self.OUTPUT_LINES,
            'multilinestrings': self.OUTPUT_MULTILINESTRINGS,
            'multipolygons': self.OUTPUT_MULTIPOLYGONS
        }

        for layer in layers:
            layers[layer]['layer_decorated'] = processing.run(
                "quickosm:decoratelayer",
                {
                    'LAYER': layers[layer]['vector_layer']
                },
                feedback=self.feedback
            )
            context.temporaryLayerStore().addMapLayer(layers[layer]['vector_layer'])
            layer_output.append(
                QgsProcessingUtils.mapLayerFromString(
                    layers[layer]['vector_layer'].id(), context, True
                )
            )
            if 'tags' in layers[layer]:
                layer_details = QgsProcessingContext.LayerDetails(
                    'OSMQuery_' + layer,
                    context.project(),
                    OUTPUT[layer]
                )
                if 'colour' in layers[layer]['tags']:
                    layer_details.setPostProcessor(
                        SetColoringPostProcessor.create(layers[layer]['tags'])
                    )
                context.addLayerToLoadOnCompletion(
                    layers[layer]['vector_layer'].id(),
                    layer_details
                )

        if self.feedback.isCanceled():
            self.feedback.reportError('The algorithm has been canceled during the post processing.')
            return self.OUTPUT_CANCEL

        outputs = {
            self.OUTPUT_POINTS: layer_output[0].id(),
            self.OUTPUT_LINES: layer_output[1].id(),
            self.OUTPUT_MULTILINESTRINGS: layer_output[2].id(),
            self.OUTPUT_MULTIPOLYGONS: layer_output[3].id(),
        }
        return outputs


class DownloadOSMDataRawQuery(DownloadOSMData, BuildRaw):
    """Run the process of the plugin as an algorithm with a raw query input."""

    @staticmethod
    def name() -> str:
        """Return the name of the algorithm."""
        return 'downloadosmdatarawquery'

    @staticmethod
    def displayName() -> str:
        """Return the display name of the algorithm."""
        return tr('Download OSM data from a raw query')

    def flags(self):
        """Return the flags."""
        return DownloadOSMData.flags(self)

    def fetch_based_parameters(self, parameters, context):
        """Get the parameters."""
        BuildRaw.fetch_based_parameters(self, parameters, context)
        DownloadOSMData.fetch_based_parameters(self, parameters, context)

    def processAlgorithm(self, parameters, context, feedback):
        """Run the algorithm."""
        self.feedback = QgsProcessingMultiStepFeedback(8, feedback)
        self.fetch_based_parameters(parameters, context)

        self.feedback.setCurrentStep(0)
        self.feedback.pushInfo('Building the query.')

        raw_query = processing.run(
            "quickosm:buildrawquery",
            {
                'AREA': self.area,
                'EXTENT': QgsReferencedRectangle(self.extent, self.extent_crs),
                'QUERY': self.query,
                'SERVER': self.server
            },
            feedback=self.feedback
        )
        url = raw_query['OUTPUT_URL']

        return self.process_road(context, url)


class DownloadOSMDataNotSpatialQuery(DownloadOSMData, BuildQueryNotSpatialAlgorithm):
    """Run the process of the plugin as an algorithm with a query input."""

    @staticmethod
    def name() -> str:
        """Return the name of the algorithm."""
        return 'downloadosmdatanotspatialquery'

    @staticmethod
    def displayName() -> str:
        """Return the display name of the algorithm."""
        return tr('Download OSM data from a not spatial query')

    def flags(self):
        """Return the flags."""
        return DownloadOSMData.flags(self)

    def fetch_based_parameters(self, parameters, context):
        """Get the parameters."""
        BuildQueryNotSpatialAlgorithm.fetch_based_parameters(self, parameters, context)
        DownloadOSMData.fetch_based_parameters(self, parameters, context)

    def processAlgorithm(self, parameters, context, feedback):
        """Run the algorithm."""
        self.feedback = QgsProcessingMultiStepFeedback(8, feedback)
        self.fetch_based_parameters(parameters, context)

        self.feedback.setCurrentStep(0)
        self.feedback.pushInfo('Building the query.')

        query = processing.run(
            "quickosm:buildquerybyattributeonly",
            {
                'KEY': self.key,
                'SERVER': self.server,
                'TIMEOUT': self.timeout,
                'TYPE_MULTI_REQUEST': self.type_multi_request,
                'VALUE': self.value
            },
            feedback=self.feedback
        )
        url = query['OUTPUT_URL']

        return self.process_road(context, url)


class DownloadOSMDataInAreaQuery(DownloadOSMData, BuildQueryInAreaAlgorithm):
    """Run the process of the plugin as an algorithm with a query input."""

    @staticmethod
    def name() -> str:
        """Return the name of the algorithm."""
        return 'downloadosmdatainareaquery'

    @staticmethod
    def displayName() -> str:
        """Return the display name of the algorithm."""
        return tr('Download OSM data from query in an area')

    def flags(self):
        """Return the flags."""
        return DownloadOSMData.flags(self)

    def fetch_based_parameters(self, parameters, context):
        """Get the parameters."""
        BuildQueryInAreaAlgorithm.fetch_based_parameters(self, parameters, context)
        DownloadOSMData.fetch_based_parameters(self, parameters, context)

    def processAlgorithm(self, parameters, context, feedback):
        """Run the algorithm."""
        self.feedback = QgsProcessingMultiStepFeedback(8, feedback)
        self.fetch_based_parameters(parameters, context)

        self.feedback.setCurrentStep(0)
        self.feedback.pushInfo('Building the query.')

        query = processing.run(
            "quickosm:buildqueryinsidearea",
            {
                'AREA': self.area,
                'KEY': self.key,
                'SERVER': self.server,
                'TIMEOUT': self.timeout,
                'TYPE_MULTI_REQUEST': self.type_multi_request,
                'VALUE': self.value
            },
            feedback=self.feedback
        )
        url = query['OUTPUT_URL']

        return self.process_road(context, url)


class DownloadOSMDataAroundAreaQuery(DownloadOSMData, BuildQueryAroundAreaAlgorithm):
    """Run the process of the plugin as an algorithm with a query input."""

    @staticmethod
    def name() -> str:
        """Return the name of the algorithm."""
        return 'downloadosmdataaroundareaquery'

    @staticmethod
    def displayName() -> str:
        """Return the display name of the algorithm."""
        return tr('Download OSM data from a query around an area')

    def flags(self):
        """Return the flags."""
        return DownloadOSMData.flags(self)

    def fetch_based_parameters(self, parameters, context):
        """Get the parameters."""
        BuildQueryAroundAreaAlgorithm.fetch_based_parameters(self, parameters, context)
        DownloadOSMData.fetch_based_parameters(self, parameters, context)

    def processAlgorithm(self, parameters, context, feedback):
        """Run the algorithm."""
        self.feedback = QgsProcessingMultiStepFeedback(8, feedback)
        self.fetch_based_parameters(parameters, context)

        self.feedback.setCurrentStep(0)
        self.feedback.pushInfo('Building the query.')

        query = processing.run(
            "quickosm:buildqueryaroundarea",
            {
                'AREA': self.area,
                'DISTANCE': self.distance,
                'KEY': self.key,
                'SERVER': self.server,
                'TIMEOUT': self.timeout,
                'TYPE_MULTI_REQUEST': self.type_multi_request,
                'VALUE': self.value
            },
            feedback=self.feedback
        )
        url = query['OUTPUT_URL']

        return self.process_road(context, url)


class DownloadOSMDataExtentQuery(DownloadOSMData, BuildQueryExtentAlgorithm):
    """Run the process of the plugin as an algorithm with a query input."""

    @staticmethod
    def name() -> str:
        """Return the name of the algorithm."""
        return 'downloadosmdataextentquery'

    @staticmethod
    def displayName() -> str:
        """Return the display name of the algorithm."""
        return tr('Download OSM data from a query in an extent')

    def flags(self):
        """Return the flags."""
        return DownloadOSMData.flags(self)

    def fetch_based_parameters(self, parameters, context):
        """Get the parameters."""
        BuildQueryExtentAlgorithm.fetch_based_parameters(self, parameters, context)
        DownloadOSMData.fetch_based_parameters(self, parameters, context)

    def processAlgorithm(self, parameters, context, feedback):
        """Run the algorithm."""
        self.feedback = QgsProcessingMultiStepFeedback(8, feedback)
        self.fetch_based_parameters(parameters, context)

        self.feedback.setCurrentStep(0)
        self.feedback.pushInfo('Building the query.')

        query = processing.run(
            "quickosm:buildqueryextent",
            {
                'EXTENT': QgsReferencedRectangle(self.extent, self.extent_crs),
                'KEY': self.key,
                'SERVER': self.server,
                'TIMEOUT': self.timeout,
                'TYPE_MULTI_REQUEST': self.type_multi_request,
                'VALUE': self.value
            },
            feedback=self.feedback
        )
        url = query['OUTPUT_URL']

        return self.process_road(context, url)
