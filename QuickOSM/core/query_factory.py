"""Query factory, for building queries."""

import logging
import re

from typing import List
from xml.dom.minidom import parseString

from QuickOSM.core.exceptions import QueryFactoryException
from QuickOSM.definitions.osm import (
    MultiType,
    OsmType,
    QueryLanguage,
    QueryType,
)
from QuickOSM.tools.i18n import tr



SPACE_INDENT = '    '

# Simple keys/values
ALL_OBJECTS = tr(
    'All OSM objects in {extent} are going to be downloaded.')
ALL_VALUES = tr(
    'All OSM objects with the key {key} in {extent} are going to be downloaded.')
ALL_VALUES_WITH_DISTANCE = tr(
    'All OSM objects with the key {key} in {dist} meters of {extent} are going to be downloaded.')
NO_KEY = tr('All OSM objects in {extent} are going to be downloaded.')
NO_KEY_WITH_DISTANCE = tr(
    'All OSM objects in {dist} meters of {extent} are going to be downloaded.')
ATTRIBUTE_ONLY = tr(
    'All OSM objects with the key {key} are going to be downloaded.')

# Multiple keys/values
ATTRIBUTES_ONLY = tr(
    'All OSM objects with keys {key} are going to be downloaded.')
ALL_MULTI = tr(
    'All OSM objects with keys {key} in {extent} are going to be downloaded.')
ALL_MULTI_WITH_DISTANCE = tr(
    'All OSM objects with keys {key} in {dist} meters of {extent} are going to be downloaded.')

LOGGER = logging.getLogger('QuickOSM')


class QueryFactory:

    """Build a XML or OQL query."""

    def __init__(
            self,
            type_multi_request: list = None,
            query_type: QueryType = None,
            key: str = None,
            value: str = None,
            area: str = None,
            around_distance: int = None,
            osm_objects: List[OsmType] = None,
            output: str = 'xml',
            timeout: int = 25,
            print_mode: str = 'body',
    ):
        """
        Query Factory constructor according to Overpass API.

        :param type_multi_request: The type of query to build.
        :type type_multi_request: list(MultiType)

        :param query_type: The type of query to build.
        :type query_type: QueryType

        :param key: OSM key or None.
        :type key: str,None

        :param value: OSM value or None.
        :type value: str,None

        :param area: A place name if needed or None.
        :type area: str,None

        :param around_distance: Distance to use if it's an around query or None
        :type around_distance: int,None

        :param osm_objects: List of osm objects to query on (node/way/relation)
        :type osm_objects: list(OsmType)

        :param output:output of overpass : XML or JSON
        :type output: str

        :param timeout: Timeout of the query
        :type timeout: int

        :param print_mode: Print type of the overpass query (read overpass doc)
        :type print_mode: str
        """
        if isinstance(type_multi_request, list):
            self._type_multi_request = [x for x in type_multi_request if x]
        elif isinstance(type_multi_request, str):
            self._type_multi_request = self._convert_to_multitypes(type_multi_request)
        else:
            self._type_multi_request = []

        self._query_type = query_type

        if isinstance(key, str):
            key = key.split(',')
        elif key is None:
            key = []

        # The initial key might be an empty key, remove it.
        self._key = [x for x in key if x]

        if isinstance(value, str):
            if value == '':
                value = []
            else:
                value = value.split(',')
        elif value is None:
            value = []
        elif value == ['']:
            value = []
        self._value = value

        # Nominatim might be:
        # a list of places or
        # a single place or
        # not defined (None)
        self._area = None
        if area:
            self._area = [name.strip() for name in area.split(';')]

        self._distance_around = around_distance

        if osm_objects is None:
            # If None, we had all OSM Types from the enum
            # noinspection PyTypeChecker
            osm_objects = list(OsmType)

        self._osm_objects = osm_objects
        self._timeout = timeout
        self._output = output
        self._print_mode = print_mode

        self._checked = False

    @property
    def area(self) -> list:
        """Return the area defined for the query.

        Either None if no area or a list of areas.

        :rtype: list
        """
        return self._area

    @staticmethod
    def _convert_to_multitypes(type_multi_request: str) -> List[MultiType]:
        """Converts a string of comma separated 'AND'/'OR's to a list of MultiType equivalents.

        :param type_multi_request: A string of comma separated 'AND'/'OR's provided from input of processing
        algorithms
        :type type_multi_request: str

        :return: list of MultiType
        :rtype: list

        :raise QueryFactoryException:
        """
        types = []
        if type_multi_request:
            for type_ in type_multi_request.split(','):
                type_ = type_.strip()
                if type_ == 'AND':
                    types.append(MultiType.AND)
                elif type_ == 'OR':
                    types.append(MultiType.OR)
                else:
                    raise QueryFactoryException(
                        tr('Only values "AND"/"OR" are allowed as logical operators.'))
        return types

    def _check_parameters(self) -> bool:
        """Internal function to check that the query can be built.

        :return: True if everything went fine.

        :raise QueryFactoryException:
        """
        if not isinstance(self._query_type, QueryType):
            raise QueryFactoryException(tr('Wrong query type.'))

        for osmObject in self._osm_objects:
            if not isinstance(osmObject, OsmType):
                raise QueryFactoryException(tr('Wrong OSM object.'))

        if self._query_type == QueryType.AroundArea:
            if not self._distance_around:
                raise QueryFactoryException(
                    tr('No distance provided with the "around" query.'))

            try:
                int(self._distance_around)
            except ValueError:
                raise QueryFactoryException(
                    tr('Wrong distance parameter.'))

        if self._distance_around and self._query_type == QueryType.InArea:
            raise QueryFactoryException(
                tr('Distance parameter is incompatible with this query.'))

        if self._query_type == QueryType.InArea and not self._area:
            raise QueryFactoryException(
                tr('Named area is required when the query is "In".'))

        if self._query_type == QueryType.AroundArea and not self._area:
            raise QueryFactoryException(
                tr('Named area or a WKT is required when the query is "Around".'))

        if not self._key and self._value:
            raise QueryFactoryException(
                tr('Not possible to query a specific value without a key.'))

        if self._query_type == QueryType.NotSpatial:
            if not self._key:
                raise QueryFactoryException(
                    tr('A key is required.'))

        if len(self._key) > len(self._value):
            if len(self._key) != 1:
                raise QueryFactoryException(
                    tr('Missing some values for some keys.'))

        if len(self._key) < len(self._value):
            raise QueryFactoryException(
                tr('Missing some keys for some values.'))

        for key in self._key:
            if key != key.strip():
                raise QueryFactoryException(
                    tr(f'Key "{key}" contains leading or trailing whitespace.'))

        if len(self._key) != 0:
            if len(self._type_multi_request) > len(self._key) - 1:
                raise QueryFactoryException(
                    tr('Too many logical operators were provided.')
                )

            if len(self._type_multi_request) < len(self._key) - 1:
                raise QueryFactoryException(
                    tr('Not enough logical operators were provided.')
                )

        self._checked = True
        return True

    @staticmethod
    def get_pretty_xml(query):
        """Helper to get a good indentation of the query."""
        xml = parseString(query)
        return xml.toprettyxml()

    @staticmethod
    def replace_template(query):
        """Add some templates tags to the query {{ }}.

        This is a hack to get pretty XML working, because templates are not a
        valid XML !
        """
        query = re.sub(
            r' area_coords="(.*?)"', r' {{geocodeCoords:\1}}', query)
        query = re.sub(
            r' area="(.*?)"', r' {{geocodeArea:\1}}', query)
        query = query.replace(' bbox="custom"', ' {{bbox}}')
        return query

    def generate_xml(self) -> str:
        """Generate the XML.

        The query will not be valid because of Overpass templates !
        """
        query = f'<osm-script output="{self._output}" timeout="{self._timeout}">'

        if self._area:
            nominatim = self._area
        else:
            nominatim = None

        if nominatim and self._query_type != QueryType.AroundArea:

            for i, one_place in enumerate(nominatim):
                query += f'<id-query area="{one_place}" into="area_{i}"/>'

        query += '<union>'

        loop = 1 if not nominatim else len(nominatim)
        nb_query = self._type_multi_request.count(MultiType.OR) + 1

        for osm_object in self._osm_objects:
            for i in range(0, loop):
                type_request = self._type_multi_request.copy()
                keys = self._key.copy()
                values = self._value.copy()
                if self._key:
                    for _j in range(nb_query):
                        query += f'<query type="{osm_object.value.lower()}">'
                        query += f'<has-kv k="{keys.pop(0)}" '
                        if len(values) != 0 and values[0]:
                            query += f'v="{values.pop(0)}"'
                        elif len(values) != 0:
                            values.pop(0)

                        query += '/>'

                        while type_request and type_request.pop(0) == MultiType.AND:
                            query += f'<has-kv k="{keys.pop(0)}" '
                            if len(values) != 0 and values[0]:
                                query += f'v="{values.pop(0)}"'
                            elif len(values) != 0:
                                values.pop(0)

                            query += '/>'

                        if self._area and self._query_type == QueryType.InArea:
                            query += f'<area-query from="area_{i}" />'

                        elif self._area and self._query_type == QueryType.AroundArea:
                            query += f'<around area_coords="{nominatim[i]}" radius="{self._distance_around}" />'

                        elif self._query_type == QueryType.BBox:
                            query = f'{query}<bbox-query bbox="custom" />'

                        query += '</query>'
                else:
                    query += f'<query type="{osm_object.value.lower()}">'

                    if self._area and self._query_type == QueryType.InArea:
                        query += f'<area-query from="area_{i}" />'

                    elif self._area and self._query_type == QueryType.AroundArea:
                        query += f'<around area_coords="{nominatim[i]}" radius="{self._distance_around}" />'

                    elif self._query_type == QueryType.BBox:
                        query = f'{query}<bbox-query bbox="custom" />'

                    query += '</query>'

        query += '</union>'
        query += '<union>'
        query += '<item />'
        query += '<recurse type="down"/>'
        query += '</union>'
        query += f'<print mode="{self._print_mode}" />'
        query += '</osm-script>'

        return query

    def generate_oql(self) -> str:
        """Generate the OQL.

        The query will not be valid because of Overpass templates !
        """
        query = f'[out:{self._output}] [timeout:{self._timeout}];\n'

        if self._area:
            nominatim = self._area
        else:
            nominatim = None

        if nominatim and self._query_type == QueryType.InArea:

            for i, one_place in enumerate(nominatim):
                query += f' area="{one_place}" -> .area_{i};\n'

        query += '(\n'

        loop = 1 if not nominatim else len(nominatim)
        nb_query = self._type_multi_request.count(MultiType.OR) + 1

        for osm_object in self._osm_objects:
            for i in range(0, loop):
                type_request = self._type_multi_request.copy()
                keys = self._key.copy()
                values = self._value.copy()
                if self._key:
                    for _j in range(nb_query):
                        query += f'    {osm_object.value.lower()}'
                        query += f'["{keys.pop(0)}"'
                        if len(values) != 0 and values[0]:
                            query += f'="{values.pop(0)}"'
                        elif len(values) != 0:
                            values.pop(0)

                        query += ']'

                        while type_request and type_request.pop(0) == MultiType.AND:
                            query += f'["{keys.pop(0)}"'
                            if len(values) != 0 and values[0]:
                                query += f'="{values.pop(0)}"'
                            elif len(values) != 0:
                                values.pop(0)

                            query += ']'

                        if self._area and self._query_type == QueryType.InArea:
                            query += f'(area.area_{i})'

                        elif self._area and self._query_type == QueryType.AroundArea:
                            query += f'(around:{self._distance_around}, area_coords="{nominatim[i]}")'

                        elif self._query_type == QueryType.BBox:
                            query += '( bbox="custom")'

                        query += ';\n'

                else:
                    query += f'    {osm_object.value.lower()}'

                    if self._area and self._query_type != QueryType.AroundArea:
                        query += f'(area.area_{i})'

                    elif self._area and self._query_type == QueryType.AroundArea:
                        query += f'(around:{self._distance_around}, area_coords="{nominatim[i]}")'

                    elif self._query_type == QueryType.BBox:
                        query += '( bbox="custom")'

                    query += ';\n'

        query += ');\n'
        query += '(._;>;);\n'
        query += f'out {self._print_mode};'

        return query

    def make(self, output: QueryLanguage = QueryLanguage.OQL) -> str:
        """Make the query.

        :return: query
        :rtype: str
        """
        self._check_parameters()
        if output == QueryLanguage.OQL:
            query = self.generate_oql()

        elif output == QueryLanguage.XML:
            query = self.generate_xml()

            # get_pretty_xml works only with a valid XML, no template {{}}
            # So we replace fake XML after
            query = QueryFactory.get_pretty_xml(query)

            # get_pretty_xml add on XML header, let's remove the first line
            query = '\n'.join(query.split('\n')[1:])

        query = QueryFactory.replace_template(query)
        query = query.replace('	', SPACE_INDENT)

        return query

    def _make_for_test(self, output: QueryLanguage) -> str:
        """Helper for tests only!

        Without indentation and lines.
        """
        query = self.make(output)
        query = query.replace(SPACE_INDENT, '').replace('\n', '')
        return query

    def friendly_message(self) -> str:
        """Create a friendly/human message about what the query will do.

        return: The message
        rtype: str
        """
        self._check_parameters()

        place = self._area
        if self._area is not None:
            # human format a list
            and_str = tr('and')
            if len(self._area) == 1:
                place = self._area[0]  # simply unwrap the list
            elif len(self._area) == 2:
                place = f' {and_str} '.join(self._area)
            else:
                place = ', '.join(self._area[:-2]) + ', '
                place = place + f' {and_str} '.join(self._area[-2:])

        extent_lbl = ''
        dist_lbl = ''
        use_with_dist = False
        attrib_only = False

        # first translate the location information
        if self._query_type == QueryType.InArea:
            extent_lbl = place

        elif self._query_type == QueryType.AroundArea:
            extent_lbl = place
            dist_lbl = self._distance_around
            use_with_dist = True

        elif self._query_type == QueryType.BBox:
            extent_lbl = tr('the canvas or layer extent')

        elif self._query_type == QueryType.NotSpatial:
            attrib_only = True

        # Next get the key / values
        key = self._key
        val = self._value
        if len(val) == 0:
            val = ['']

        multi_keys = len(key) > 1

        if key:

            keys = []
            for k, v in zip(key, val):
                if v:
                    keys.append(f'\'{k}\'=\'{v}\'')
                else:
                    keys.append(f'\'{k}\'')

            if multi_keys:
                type_multi = self._type_multi_request
                key_lbl = ''
                index = 0
                for k, type_multi_k in enumerate(type_multi):
                    if index == k:
                        if type_multi_k == MultiType.AND:
                            i = 1
                            key_and = keys[k] + ' and ' + keys[k + i]

                            while (k + i) < len(type_multi) and type_multi[k + i] == MultiType.AND:
                                i += 1
                                key_and += ' and ' + keys[k + i]

                            key_lbl += f'({key_and})'
                            index = k + i
                        elif type_multi_k == MultiType.OR:
                            if k == 0:
                                key_lbl += keys[k]
                            key_lbl += ' or '
                            i = 1
                            while (k + i) < len(type_multi) and type_multi[k + i] == MultiType.OR:
                                key_lbl += keys[k + i] + ' or '
                                i += 1
                            index = k + i
                            if k + i == len(type_multi):
                                key_lbl += keys[k + i]
            else:
                key_lbl = keys[0]

            if attrib_only and multi_keys:
                return ATTRIBUTES_ONLY.format(key=key_lbl)
            if attrib_only:
                return ATTRIBUTE_ONLY.format(key=key_lbl)

            if use_with_dist and multi_keys:
                return ALL_MULTI_WITH_DISTANCE.format(key=key_lbl, dist=dist_lbl, extent=extent_lbl)
            if use_with_dist:
                return ALL_VALUES_WITH_DISTANCE.format(key=key_lbl, dist=dist_lbl, extent=extent_lbl)
            if multi_keys:
                return ALL_MULTI.format(key=key_lbl, extent=extent_lbl)
            return ALL_VALUES.format(key=key_lbl, extent=extent_lbl)

        if use_with_dist:
            return NO_KEY_WITH_DISTANCE.format(dist=dist_lbl, extent=extent_lbl)
        return NO_KEY.format(extent=extent_lbl)
