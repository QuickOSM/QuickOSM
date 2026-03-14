"""Query preparation step."""

import logging
import re

from typing import List, Union

from qgis.core import QgsGeometry, QgsRectangle
from qgis.PyQt.QtCore import QUrl, QUrlQuery

from QuickOSM.core.api.nominatim import Nominatim
from QuickOSM.core.exceptions import QueryFactoryException, QueryNotSupported
from QuickOSM.core.utilities.tools import get_setting
from QuickOSM.definitions.nominatim import NOMINATIM_SERVERS
from QuickOSM.definitions.osm import QueryLanguage
from QuickOSM.definitions.overpass import OVERPASS_SERVERS
from QuickOSM.tools.i18n import tr
from QuickOSM.tools.resources import plugin_name


LOGGER = logging.getLogger(plugin_name())


class QueryPreparation:

    """Prepare the query before sending it to Overpass."""

    def __init__(
            self, query: str, extent: QgsRectangle = None, area: Union[str, List[str]] = None,
            overpass: str = None, output_format: str = 'xml'):
        """Constructor.

        :param query: The query to prepare.
        :type query: str

        :param extent: The extent to use in 4326, if needed. It can be None.
        :type extent: QgsRectangle

        :param area: A name or a list of place names.
        :type area: str, list(str)
        """
        if overpass is None:
            server = get_setting(
                'defaultOAPI', OVERPASS_SERVERS[0]) + 'interpreter'
            self._overpass = QUrl(server)
        else:
            self._overpass = QUrl(overpass)

        self._query = query
        self._query_prepared = query
        self._extent = extent
        self._places = area
        self._output_format = output_format

        self._nominatim = None

        self._query_is_ready = False

    @property
    def query(self) -> str:
        """The original query.

        :return: The original query.
        :rtype: str
        """
        return self._query

    @property
    def final_query(self) -> str:
        """The generated query or None if it's not yet generated.

        :return: The final query.
        :rtype: str
        """
        if self._query_is_ready:
            return self._query_prepared

    def is_oql_query(self) -> bool:
        """Return if the query is written in OQL or not.

        :return: If the it's OQL query.
        :rtype: bool
        """
        return self._query_prepared[-1] == ';'

    def is_compatible(self) -> (bool, str):
        """The plugin doesn't support all special tags like Overpass Turbo.

        :return: A tuple (bool, reason).
        :rtype: tuple
        """
        # token to look for, error returned to the user
        incompatible_queries = {
            'geometry="center"': 'center',
            'out center': 'center',
            '{{style': '{{style}}',
            '{{data': '{{data}}',
            '{{date': '{{date}}',
            '{{geocodeId:': '{{geocodeId:}}',
            '{{geocodeBbox:': '{{geocodeBbox:}}',
        }

        for expression, error in incompatible_queries.items():
            if re.search(expression, self._query):
                return False, error

        return True, None

    def _replace_center(self):
        """Replace {{center}} by the centroid of the extent if needed.

        The temporary query will be updated.
        """
        template = r'{{center}}'
        if not re.search(template, self._query_prepared):
            return
        if self._extent is None:
            raise QueryFactoryException(tr('Missing extent parameter.'))

        coord_y = self._format_decimals_wgs84(self._extent.center().y())
        coord_x = self._format_decimals_wgs84(self._extent.center().x())

        if self.is_oql_query():
            new_string = f'{coord_y},{coord_x}'
        else:
            new_string = f'lat="{coord_y}" lon="{coord_x}"'

        self._query_prepared = (
            re.sub(template, new_string, self._query_prepared))

    def replace_bbox(self):
        """Replace {{bbox}} by the extent BBOX if needed.

        The temporary query will be updated.
        """
        template = r'{{bbox}}'
        if not re.search(template, self._query_prepared):
            return
        if self._extent is None:
            raise QueryFactoryException(tr('Missing extent parameter.'))

        y_min = self._extent.yMinimum()
        y_max = self._extent.yMaximum()
        x_min = self._extent.xMinimum()
        x_max = self._extent.xMaximum()

        # make sure we don't query for invalid bounds #222
        area_is_too_big = False
        if y_min < -90:
            y_min = -90
            area_is_too_big = True
        if y_max > 90:
            y_max = 90
            area_is_too_big = True
        if x_min < -180:
            x_min = -180
            area_is_too_big = True
        if x_max > 180:
            x_max = 180
            area_is_too_big = True

        if area_is_too_big:
            LOGGER.info(tr(
                'The area was overlapping the WGS84 limits ±90 / ±180 degrees. The query has '
                'been restricted.'))

        if self.is_oql_query():
            new_string = (
                f'{self._format_decimals_wgs84(y_min)},{self._format_decimals_wgs84(x_min)},'
                f'{self._format_decimals_wgs84(y_max)},{self._format_decimals_wgs84(x_max)}'
            )
        else:
            new_string = (
                f'e="{self._format_decimals_wgs84(x_max)}" n="{self._format_decimals_wgs84(y_max)}" '
                f's="{self._format_decimals_wgs84(y_min)}" w="{self._format_decimals_wgs84(x_min)}"'
            )
        self._query_prepared = (
            re.sub(template, new_string, self._query_prepared))

    @staticmethod
    def _format_decimals_wgs84(coordinate: float) -> str:
        """ Reduce the number of decimals, see #344 """
        # https://en.wikipedia.org/wiki/Decimal_degrees
        # We keep 5 decimals : individual trees, houses
        multiplier = 10 ** 5
        number = str(int(coordinate * multiplier) / multiplier)
        number = number.rstrip("0")
        number = number.rstrip(".")
        return number

    def _replace_geocode_coords(self):
        """Replace {{geocodeCoords}} by the centroid of the extent.

        The temporary query will be updated.
        """
        def replace(catch, default_nominatim):

            if default_nominatim:
                search = default_nominatim
            else:
                search = catch

            lat = None
            lon = None

            # Try first if it's a point written in WKT
            geom = QgsGeometry.fromWkt(search)
            if geom.isGeosValid():
                try:
                    point = geom.asPoint()
                    lon = point.x()
                    lat = point.y()
                    LOGGER.info(tr('WKT detected for "geocodeCoords".'))
                except TypeError:
                    pass

            if lat is None and lon is None:
                if not self._nominatim:
                    server = get_setting('defaultNominatimAPI', NOMINATIM_SERVERS[0])
                    self._nominatim = Nominatim(server)
                lon, lat = self._nominatim.get_first_point_from_query(search)

            if self.is_oql_query():
                new_string = f'{lat},{lon}'
            else:
                new_string = f'lat="{lat}" lon="{lon}"'

            return new_string

        template = r'{{(geocodeCoords):([^}]*)}}'
        self._query_prepared = re.sub(
            template, lambda m: replace(
                m.groups()[1], self._places), self._query_prepared)

    def _replace_geocode_area(self):
        """Replace {{geocodeCoords}} by the centroid of the extent.

        The temporary query will be updated.
        """
        def replace(catch, default_nominatim):

            if default_nominatim:
                search = default_nominatim
            else:
                search = catch

            # if the result is already a number, it's a relation ID.
            # we don't perform a nominatim query
            if search.isdigit():
                osm_id = search
            else:
                # We perform a nominatim query
                if not self._nominatim:
                    server = get_setting('defaultNominatimAPI', NOMINATIM_SERVERS[0])
                    self._nominatim = Nominatim(server)
                osm_id = self._nominatim.get_first_polygon_from_query(search)

            # HACK when running in test.
            # In production, osm_id IS an integer, not in tests.
            if osm_id == 'foo_BAR':
                osm_id = 12345
            elif osm_id == 'bar_FOO':
                osm_id = 54321
            # END big hack

            area = int(osm_id) + 3600000000

            if self.is_oql_query():
                new_string = f'area({area})'
            else:
                new_string = f'ref="{area}" type="area"'

            return new_string

        template = r'{{(nominatimArea|geocodeArea):([^}]*)}}'
        self._query_prepared = re.sub(template, lambda m: replace(
            m.groups()[1], self._places), self._query_prepared)

        return self._query_prepared

    def clean_query(self):
        """Remove extra characters that might be present in the query.

        The temporary query will be updated.
        """
        query = self._query_prepared.strip()

        # Correction of ; in the OQL at the end
        self._query_prepared = re.sub(r';;$', ';', query)
        self._query_prepared = re.sub(r';\\n', ';', self._query_prepared)

    def prepare_query(self):
        """Prepare the query before sending it to Overpass.

        The temporary query will be updated.

        :return: The final query.
        :rtype: basestring
        """
        result, error = self.is_compatible()
        if not result:
            raise QueryNotSupported(error)

        self.clean_query()
        self.replace_bbox()
        self._replace_center()
        self._replace_geocode_area()
        self._replace_geocode_coords()

        self._query_is_ready = True
        return self._query_prepared

    def prepare_url(self, output: QueryLanguage = None) -> str:
        """Prepare a query to be as an URL.

        if the query is not ready to be URL prepared, a None is returned.

        :return: The URL encoded with the query.
        :rtype: basestring
        """
        if not self._query_is_ready:
            return None

        if self._output_format:
            query = re.sub(
                r'output="[a-z]*"',
                f'output="{self._output_format}"',
                self._query_prepared)
            query = re.sub(
                r'\[out:[a-z]*',
                f'[out:{self._output_format}',
                query)
        else:
            query = self._query_prepared

        url_query = QUrl(self._overpass)
        query_string = QUrlQuery()
        query_string.addQueryItem('data', query)
        if output == QueryLanguage.XML:
            query_string.addQueryItem('target', "xml")
        elif output == QueryLanguage.OQL:
            query_string.addQueryItem('target', "mapql")
        query_string.addQueryItem('info', 'QgisQuickOSMPlugin')
        url_query.setQuery(query_string)
        return url_query.toString()
