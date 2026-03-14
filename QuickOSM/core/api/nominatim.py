"""Manage nominatim connexion."""

import json
import logging
import os

from qgis.PyQt.QtCore import QDir, QTemporaryFile, QUrlQuery

from QuickOSM.core.api.downloader import Downloader
from QuickOSM.core.exceptions import (
    NetWorkErrorException,
    NominatimAreaException,
    NominatimBadRequest,
)
from QuickOSM.definitions.osm import OsmType


from QuickOSM.tools.resources import plugin_test_data_path

LOGGER = logging.getLogger('QuickOSM')


class Nominatim(Downloader):

    """Manage connexion to Nominatim."""

    def __init__(self, url: str = None):
        """Constructor.

        :param url: URL of Nominatim server.
        :type url: basestring
        """
        super().__init__(url)

        temporary = QTemporaryFile(
            os.path.join(QDir.tempPath(), 'request-XXXXXX.json'))
        temporary.open()
        self.result_path = temporary.fileName()
        temporary.close()

    def error(self, messages: str):
        """Display the status in logger"""
        for message in messages:
            LOGGER.error(message)
        raise NetWorkErrorException('Nominatim API', ', '.join(messages))

    def query(self, query: str) -> dict:
        """Perform a nominatim query.

        :param query: Query to execute on the nominatim server.
        :type query: basestring

        :return: The result of the query as a dictionary.
        :rtype: dict

        :raise NetWorkErrorException:
        """

        query_string = QUrlQuery()
        query_string.addQueryItem('q', query)
        query_string.addQueryItem('format', 'json')
        query_string.addQueryItem('info', 'QgisQuickOSMPlugin')
        self._url.setQuery(query_string)

        # Use GET for Nominatim
        # https://github.com/QuickOSM/QuickOSM/issues/472
        self.download(get=True)

        with open(self.result_path, encoding='utf8') as json_file:
            data = json.load(json_file)
            if not data:
                raise NominatimBadRequest(query)
            return data

    def get_first_polygon_from_query(self, query: str, hack_test: bool = False) -> str:
        """Get first OSM_ID of a Nominatim area.

        :param query: Query to execute.
        :type query: basestring

        :param hack_test: set up test without internet
        :type hack_test: bool

        :return: First relation's with an "osm_id".
        :rtype: int

        :raise NominatimAreaException:
        """
        if hack_test:
            test_file = plugin_test_data_path('nominatim', 'search.json')
            with open(test_file, encoding='utf8') as json_file:
                data = json.load(json_file)
                if not data:
                    raise NominatimBadRequest(query)
        else:
            data = self.query(query)
        for result in data:
            if result.get('osm_type') == OsmType.Relation.name.lower():
                osm_id = result.get('osm_id')
                if osm_id:
                    return osm_id

        # If no result has been return
        raise NominatimAreaException(query)

    def get_first_point_from_query(self, query: str, hack_test: bool = False) -> (str, str):
        """Get first longitude, latitude of a Nominatim point.

        :param query: Query to execute.
        :type query: basestring

        :param hack_test: set up test without internet
        :type hack_test: bool

        :return: First node with its longitude and latitude.
        :rtype: tuple(float, float)

        :raise NominatimAreaException:
        """
        if hack_test:
            test_file = plugin_test_data_path('nominatim', 'search.json')
            with open(test_file, encoding='utf8') as json_file:
                data = json.load(json_file)
                if not data:
                    raise NominatimBadRequest(query)
        else:
            data = self.query(query)
        for result in data:
            lon = result.get('lon')
            lat = result.get('lat')
            if lon and lat:
                return lon, lat
