"""Tests for Nominatim API requests."""

from qgis.testing import unittest

from QuickOSM.core.api.nominatim import Nominatim
from QuickOSM.core.exceptions import (
    NominatimAreaException,
    NominatimBadRequest,
)
from QuickOSM.definitions.nominatim import NOMINATIM_SERVERS


class TestNominatim(unittest.TestCase):
    """Tests for Nominatim API requests."""

    def test_wrong_request(self):
        """Test wrong request.

        This test is using internet.
        """
        nominatim = Nominatim(NOMINATIM_SERVERS[0])

        with self.assertRaises(NominatimBadRequest) as error:
            nominatim.query('')

        self.assertEqual(
            str(error.exception), 'Nominatim hasn\'t found any data for an area called "".'
        )

    def test_wrong_request_area(self):
        """Test wrong osm_id request.

        This test is using internet.
        """
        nominatim = Nominatim(NOMINATIM_SERVERS[0])

        with self.assertRaises(NominatimAreaException) as error:
            nominatim.get_first_polygon_from_query('CosWos')

        self.assertEqual(
            str(error.exception),
            '(\'No named area found for OSM relation called "CosWos".\', '
            '\'No OSM polygon (relation) has been found, you should try the '
            '"Around" query which will search for other OSM type.\')')

    def test_request_area(self):
        """Test valid osm_id request.

        This test is using internet.
        """
        nominatim = Nominatim(NOMINATIM_SERVERS[0])

        osm_id = nominatim.get_first_polygon_from_query('Montpellier', True)

        self.assertEqual(osm_id, 28722)

    def test_wrong_request_coord(self):
        """Test wrong coordinate request.

        This test is using internet.
        """
        nominatim = Nominatim(NOMINATIM_SERVERS[0])

        with self.assertRaises(NominatimBadRequest) as error:
            nominatim.get_first_point_from_query('fake_query')

        self.assertEqual(
            str(error.exception),
            'Nominatim hasn\'t found any data for an area called "fake_query".')

    def test_request_coord(self):
        """Test valid coordinate request.

        This test is using internet.
        """
        nominatim = Nominatim(NOMINATIM_SERVERS[0])

        coord = nominatim.get_first_point_from_query('Montpellier', True)

        self.assertTupleEqual(coord, ("3.8767337", "43.6112422"))


if __name__ == '__main__':
    unittest.main()
