"""Definitions for output formats."""
import collections

from enum import Enum, unique

format_output = collections.namedtuple(
    'format_output',
    [
        'label',
        'driver_name',
        'extension',
    ]
)


@unique
class Format(Enum):
    """ Name of output formats."""
    GeoJSON = format_output('GeoJSON', 'GeoJSON', 'geojson')
    """GeoJSON"""

    GeoPackage = format_output('GeoPackage', 'GPKG', 'gpkg')
    """GeoPackage"""

    Shapefile = format_output('ESRI Shapefile', 'ESRI Shapefile', 'shp')
    """Shapefile"""

    Kml = format_output('Kml', 'KML', 'kml')
    """Kml"""
