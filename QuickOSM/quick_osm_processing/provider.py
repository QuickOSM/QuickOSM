"""Processing QuickOSM provider."""

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon

from QuickOSM.tools.resources import resources_path
from QuickOSM.quick_osm_processing.advanced.build_query import (
    BuildQueryAroundAreaAlgorithm,
    BuildQueryExtentAlgorithm,
    BuildQueryInAreaAlgorithm,
    BuildQueryNotSpatialAlgorithm,
)

# from .advanced.download_overpass import (
#   DownloadOverpassUrl)
from QuickOSM.quick_osm_processing.advanced.decorate_output import (
    DecorateLayerAlgorithm,
)
from QuickOSM.quick_osm_processing.advanced.open_osm_file import OpenOsmFile
from QuickOSM.quick_osm_processing.advanced.raw_query import RawQueryAlgorithm
from QuickOSM.quick_osm_processing.quickosm_process import (
    DownloadOSMDataAroundAreaQuery,
    DownloadOSMDataExtentQuery,
    DownloadOSMDataInAreaQuery,
    DownloadOSMDataNotSpatialQuery,
    DownloadOSMDataRawQuery,
)



class Provider(QgsProcessingProvider):
    """Processing QuickOSM provider."""

    def id(self) -> str:  # NOQA
        """Return the id."""
        return 'quickosm'

    def name(self) -> str:
        """Return the name."""
        return 'QuickOSM'

    def icon(self):
        """Return the icon."""
        return QIcon(resources_path('icons', 'QuickOSM.svg'))

    def svgIconPath(self) -> str:
        """Return the icon path."""
        return resources_path('icons', 'QuickOSM.svg')

    def loadAlgorithms(self):
        """Load the algorithms"""
        self.addAlgorithm(BuildQueryInAreaAlgorithm())
        self.addAlgorithm(BuildQueryAroundAreaAlgorithm())
        self.addAlgorithm(BuildQueryExtentAlgorithm())
        self.addAlgorithm(BuildQueryNotSpatialAlgorithm())
        self.addAlgorithm(RawQueryAlgorithm())
        # self.addAlgorithm(DownloadOverpassUrl())
        self.addAlgorithm(OpenOsmFile())
        self.addAlgorithm(DownloadOSMDataRawQuery())
        self.addAlgorithm(DecorateLayerAlgorithm())
        self.addAlgorithm(DownloadOSMDataNotSpatialQuery())
        self.addAlgorithm(DownloadOSMDataInAreaQuery())
        self.addAlgorithm(DownloadOSMDataAroundAreaQuery())
        self.addAlgorithm(DownloadOSMDataExtentQuery())
