"""Processing algorithm to download an Overpass query."""

from processing.algs.qgis.QgisAlgorithm import QgisAlgorithm
from qgis.core import QgsProcessingOutputFile, QgsProcessingParameterString


class DownloadOverpassUrl(QgisAlgorithm):
    """Processing algorithm to download an Overpass query."""

    URL = 'URL'
    OUTPUT = 'OUTPUT'

    def __init__(self):
        super().__init__()
        self.feedback = None

    def group(self) -> str:
        """Return the group of the algorithm."""
        return self.tr('Advanced')

    @staticmethod
    def groupId() -> str:
        """Return the id of the group."""
        return 'advanced'

    @staticmethod
    def name() -> str:
        """Return the name of the algorithm."""
        return 'downloadoverpassquery'

    def displayName(self) -> str:
        """Return the display name of the algorithm."""
        return self.tr('Download from Overpass')

    def flags(self):
        """Return the flags."""
        return super().flags()  # | QgsProcessingAlgorithm.FlagHideFromToolbox

    def shortHelpString(self) -> str:
        """Return a helper for the algorithm."""
        return self.tr(
            'Like the native QGIS File Downloader algorithm, this algorithm '
            'will download an URL but it will also perform a OSM integrity '
            'check at the end of the download.')

    def initAlgorithm(self, config=None):
        """Set up of the algorithm."""
        self.addParameter(
            QgsProcessingParameterString(
                self.URL, self.tr('URL, with the query encoded')))

        self.addOutput(
            QgsProcessingOutputFile(
                self.OUTPUT, self.tr('Output')))

    def processAlgorithm(self, parameters, context, feedback) -> dict:
        """Run the algorithm."""
        self.feedback = feedback
        # url = self.parameterAsString(parameters, self.URL, context)
        output = self.parameterAsFileOutput(parameters, self.OUTPUT, context)

        # processing.run("native:filedownloader", {
        #     'URL': url,
        #     'OUTPUT': output,
        # }, context=context, feedback=feedback)

        # file_obj = codecs.open(self.result_path, 'r', 'utf-8')
        # file_obj.seek(0, 2)
        # fsize = file_obj.tell()
        # file_obj.seek(max(fsize - 1024, 0), 0)
        # lines = file_obj.readlines()
        # file_obj.close()
        #
        # lines = lines[-10:]  # Get last 10 lines
        # timeout = '<remark> runtime error: Query timed out in "[a-z]+" ' \
        #           'at line [\d]+ after ([\d]+) seconds. </remark>'
        # if re.search(timeout, ''.join(lines)):
        #     raise QgsProcessingException(tr('Overpass API timeout'))

        outputs = {
            self.OUTPUT: output,
        }
        return outputs
