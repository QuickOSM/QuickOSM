"""Generate a raw query."""


from typing import Dict

from qgis.core import QgsProcessingAlgorithm, QgsProcessingOutputString

from QuickOSM.core.query_preparation import QueryPreparation
from QuickOSM.tools.i18n import tr
from QuickOSM.quick_osm_processing.build_input import BuildRaw


class RawQueryAlgorithm(BuildRaw):
    """Processing algorithm to generate a raw query."""

    OUTPUT_URL = 'OUTPUT_URL'
    OUTPUT_OQL_QUERY = 'OUTPUT_OQL_QUERY'

    @staticmethod
    def group() -> str:
        """Return the group of the algorithm."""
        return tr('Advanced')

    @staticmethod
    def groupId() -> str:
        """Return the id of the group."""
        return 'advanced'

    @staticmethod
    def name() -> str:
        """Return the name of the algorithm."""
        return 'buildrawquery'

    @staticmethod
    def displayName() -> str:
        """Return the display name of the algorithm."""
        return tr('Build raw query')

    def shortHelpString(self) -> str:
        """Return a helper for the algorithm."""
        return 'A XML or OQL query to send to a Overpass API server.'

    def flags(self):
        """Return the flags."""
        return super().flags() | QgsProcessingAlgorithm.Flag.FlagHideFromToolbox

    def initAlgorithm(self, config=None):
        """Set up of the algorithm."""
        self.add_top_parameters()
        self.add_bottom_parameters()

        output = QgsProcessingOutputString(self.OUTPUT_URL, tr('Query as encoded URL'))
        self.addOutput(output)

        output = QgsProcessingOutputString(self.OUTPUT_OQL_QUERY, tr('Raw query as OQL'))
        self.addOutput(output)

    def processAlgorithm(self, parameters, context, feedback) -> Dict[str, str]:
        """Run the algorithm."""
        self.feedback = feedback
        self.fetch_based_parameters(parameters, context)

        self.feedback.pushInfo('Prepare the url.')

        query_preparation = QueryPreparation(
            self.query,
            extent=self.extent,  # It should be in 4326 already in this stage
            area=self.area,
            overpass=self.server
        )
        raw_query = query_preparation.prepare_query()
        url = query_preparation.prepare_url()

        outputs = {
            self.OUTPUT_URL: url,
            self.OUTPUT_OQL_QUERY: raw_query,
        }
        return outputs
