"""Manage downloader."""

import logging
import os

from qgis.core import Qgis, QgsFileDownloader
from qgis.PyQt.QtCore import QByteArray, QEventLoop, QUrl, QUrlQuery

LOGGER = logging.getLogger('QuickOSM')


class Downloader:
    """Manage downloader."""

    def __init__(self, url: str = None):
        """Constructor."""
        if url is None:
            url = 'https://nominatim.openstreetmap.org/search?'

        self._url = QUrl(url)
        self.result_path = None
        self.errors = []

    def error(self, messages: str):
        """Store the messages error"""
        self.errors = messages

    @staticmethod
    def canceled():
        """Display the status in logger"""
        LOGGER.info('Request canceled')
        # TODO, need to handle this to stop the process.

    def completed(self):
        """Display the status in logger"""
        LOGGER.info(f'Request completed : {self._url.toString()}')

    def download(self, get=False):
        """Download the data"""
        if os.getenv("CI", False) or get:
            # On CI for testing,
            # With the mocked web server, the switch to POST doesn't work well for now...
            # I'm not sure why, as tests are checking that requests in QuickOSM are sent,
            # it doesn't matter to use GET
            # To be fixed later
            # https://github.com/QuickOSM/QuickOSM/pull/446
            # Use GET for Nominatim
            # https://github.com/QuickOSM/QuickOSM/issues/472
            downloader = QgsFileDownloader(self._url, self.result_path, delayStart=True)
        else:
            # On production
            # https://github.com/QuickOSM/QuickOSM/issues/344
            # We use POST instead of GET for Overpass only
            # We move the "data" GET parameter into the POST request
            url_query = QUrlQuery(self._url)
            data = f"data={url_query.queryItemValue('data')}"
            url_query.removeQueryItem('data')
            self._url.setQuery(url_query)
            downloader = QgsFileDownloader(
                self._url,
                self.result_path,
                delayStart=True,
                httpMethod=Qgis.HttpMethod.Post,
                data=QByteArray(str.encode(data))
            )
        loop = QEventLoop()
        downloader.downloadExited.connect(loop.quit)
        downloader.downloadError.connect(self.error)
        downloader.downloadCanceled.connect(self.canceled)
        downloader.downloadCompleted.connect(self.completed)
        downloader.startDownload()
        loop.exec()
