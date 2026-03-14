"""Definitions for OSM concepts."""

from enum import Enum, unique

from QuickOSM.tools.i18n import tr



# Wait for python 3.6 minimum version
# class AutoEnum(Enum):
#     # noinspection PyMethodParameters
#     def _generate_next_value_(name, start, count, last_values):
#         return name


@unique
class QueryType(Enum):
    """Type of query that QuickOSM can generate."""
    NotSpatial = 'NotSpatial'
    """Not spatial"""

    BBox = 'BBox'
    """BBOX"""

    InArea = 'InArea'
    """In area"""

    AroundArea = 'AroundArea'
    """Around area"""


@unique
class QueryLanguage(Enum):
    """Language of query that QuickOSM can generate."""
    XML = "xml"
    """XML"""

    OQL = "oql"
    """OQL"""


@unique
class OsmType(Enum):
    """OSM objects."""
    Node = 'Node'
    """Node"""

    Way = 'Way'
    """Way"""

    Relation = 'Relation'
    "Relation"


@unique
class LayerType(Enum):
    """Layers that ogr2ogr can generate from an OSM file which are readable."""
    Points = 'Points'
    """Points"""

    Lines = 'Lines'
    """Lines"""

    Multilinestrings = 'Multilinestrings'
    """Multilinestrings"""

    Multipolygons = 'Multipolygons'
    """Multipolygons"""


# Layers available in the OGR, other_relations is useless.
OSM_LAYERS = [
    LayerType.Points, LayerType.Lines,
    LayerType.Multilinestrings, LayerType.Multipolygons
]

# Layers available in the OGR, other_relations is useless.
Osm_Layers = [
    OSM_LAYERS[k].value.lower() for k in range(len(OSM_LAYERS))
]

# White list for the attribute table
# if set to None all the keys will be keep
WHITE_LIST = {
    'multilinestrings': None,
    'points': None,
    'lines': None,
    'multipolygons': None
}


@unique
class MultiType(Enum):
    """Type of combination of two queries"""
    AND = tr('And')
    """And"""

    OR = tr('Or')
    """Or"""
