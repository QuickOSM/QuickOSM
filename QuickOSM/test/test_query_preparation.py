"""Tests for the query preparation."""

import unittest

from qgis.core import QgsRectangle

from QuickOSM.core.api.nominatim import Nominatim
from QuickOSM.core.query_preparation import QueryPreparation


class FakeNominatim(Nominatim):
    """NOTE, because of the fake nominatim instance,
    latitude, longitude and relation ID are wrong and
    are replaced by the area name.
    """

    def get_first_polygon_from_query(self, fake_query):
        # It normally returns relation ID.
        return fake_query

    def get_first_point_from_query(self, fake_query):
        # It normally returns lat and lon
        return fake_query, fake_query


class TestQueryPreparation(unittest.TestCase):

    """Tests for the query preparation."""

    def setUp(self):
        self.maxDiff = None

    def test_is_oql(self):
        """Test if OQL or XML."""
        self.assertTrue(QueryPreparation('out skel qt;').is_oql_query())
        self.assertFalse(QueryPreparation('</osm-script>').is_oql_query())

    def test_invalid_query(self):
        """ Test an invalid query. """
        # out center is not compatible with OGR
        query = """
        );
        // print results
        out center meta;
        >;
        """
        query = QueryPreparation(query)
        self.assertFalse(query.is_compatible()[0])

    def test_replace_center(self):
        """Test we can replace {{center}} in a query."""
        extent = QgsRectangle(10.00, 0.5, 20.00, 1.5)

        def test(data, result, bbox=None):
            query = QueryPreparation(data, extent=bbox)
            query._replace_center()
            self.assertEqual(query._query_prepared, result)

        # No center.
        query = 'foobar{{bbox}}foobar'
        expected = 'foobar{{bbox}}foobar'
        test(query, expected)

        # One center in XML.
        query = 'foobar{{center}}foobar'
        expected = 'foobarlat="1" lon="15"foobar'
        test(query, expected, extent)

        # One center in OQL.
        query = 'foobar{{center}}foobar;'
        expected = 'foobar1,15foobar;'
        test(query, expected, extent)

        # Two centers in OQL.
        query = 'foobar{{center}}foobar{{center}}foobar;'
        expected = 'foobar1,15foobar1,15foobar;'
        test(query, expected, extent)

        # One center and one OQL in OQL.
        query = 'foobar{{center}}foobar{{bbox}}foobar;'
        expected = 'foobar1,15foobar{{bbox}}foobar;'
        test(query, expected, extent)

    def test_replace_big_bbox(self):
        """Test we can restrict a BBOX to +-90 and +-180."""
        extent = QgsRectangle(-181, -91, 181, 91)
        query = 'foobar{{bbox}}foobar'
        expected = 'foobare="180" n="90" s="-90" w="-180"foobar'
        query = QueryPreparation(query, extent=extent)
        query.replace_bbox()
        self.assertEqual(expected, query._query_prepared)

    def test_decimals(self):
        """ Test to have the correct number of decimals. """
        self.assertEqual(QueryPreparation._format_decimals_wgs84(0.123456), '0.12345')
        self.assertEqual(QueryPreparation._format_decimals_wgs84(0.12345), '0.12345')
        self.assertEqual(QueryPreparation._format_decimals_wgs84(0.1234), '0.1234')
        self.assertEqual(QueryPreparation._format_decimals_wgs84(0.1), '0.1')
        self.assertEqual(QueryPreparation._format_decimals_wgs84(0), '0')
        self.assertEqual(QueryPreparation._format_decimals_wgs84(20), '20')

    def test_replace_bbox(self):
        """Test we can replace {{bbox}} in a query."""
        extent = QgsRectangle(10.00, 0.5, 20.00, 1.5)

        def test(data, result, bbox=None):
            query = QueryPreparation(data, extent=bbox)
            query.replace_bbox()
            self.assertEqual(query._query_prepared, result)

        # One bbox.
        query = 'foobar{{bbox}}foobar'
        expected = 'foobare="20" n="1.5" s="0.5" w="10"foobar'
        test(query, expected, extent)

        # Two bbox.
        query = 'foo{{bbox}}foo{{bbox}}foo'
        expected = 'fooe="20" n="1.5" s="0.5" w="10"fooe="20" n="1.5" ' \
                   's="0.5" w="10"foo'
        test(query, expected, extent)

        # One bbox in OQL.
        query = 'foobar{{bbox}}foobar;'
        expected = 'foobar0.5,10,1.5,20foobar;'
        test(query, expected, extent)

        # One center and one OQL in OQL.
        query = 'foobar{{center}}foobar{{bbox}}foobar;'
        expected = 'foobar{{center}}foobar0.5,10,1.5,20foobar;'
        test(query, expected, extent)

    def test_replace_geocode_coords(self):
        """Test we can replace {{geocodeCoords:}} in a query."""

        def test(data, result, nominatim=None):
            query = QueryPreparation(data, area=nominatim)
            query._nominatim = FakeNominatim()
            query._replace_geocode_coords()
            self.assertEqual(query._query_prepared, result)

        # Test with another area instead of Paris in XML
        query = 'foobar{{geocodeCoords:Paris,France}}foobar'
        expected = 'foobarlat="not_paris" lon="not_paris"foobar'
        test(query, expected, 'not_paris')

        # Test with Paris in XML
        query = 'foobar{{geocodeCoords:Paris,France}}foobar'
        expected = 'foobarlat="Paris,France" lon="Paris,France"foobar'
        test(query, expected)

        # Test with WKT in XML
        query = 'foobar{{geocodeCoords:POINT(6 10)}}foobar'
        expected = 'foobarlat="10.0" lon="6.0"foobar'
        test(query, expected)

        # Test with WKT in OQL.
        query = 'foobar{{geocodeCoords:POINT(6 10)}}foobar;'
        expected = 'foobar10.0,6.0foobar;'
        test(query, expected)

        # Test with Paris in OQL.
        query = 'foobar{{geocodeCoords:Paris,France}}foobar;'
        expected = 'foobarParis,France,Paris,Francefoobar;'
        test(query, expected)

        # Test with Paris and Montpellier.
        query = (
            'foo{{geocodeCoords:Paris,France}}bar'
            'foo{{geocodeCoords:Montpellier}}bar'
        )
        expected = (
            'foolat="Paris,France" lon="Paris,France"bar'
            'foolat="Montpellier" lon="Montpellier"bar'
        )
        test(query, expected)

    def test_replace_geocode_area(self):
        """Test we can replace {{geocodeArea}} in a query."""

        # There is a HACK in the code to return 12345 and 54321 in the code.

        def test(data, result, nominatim=None):
            query = QueryPreparation(data, area=nominatim)
            query._nominatim = FakeNominatim()
            query._replace_geocode_area()
            self.assertEqual(query._query_prepared, result)

        # Test with another place.
        query = 'foobar{{geocodeArea:foo_BAR}}foobar'
        expected = 'foobarref="3600054321" type="area"foobar'
        test(query, expected, 'bar_FOO')

        # Test with Paris.
        query = 'foobar{{geocodeArea:foo_BAR}}foobar'
        expected = 'foobarref="3600012345" type="area"foobar'
        test(query, expected)

        # Test with Paris in XML.
        query = 'foobar{{geocodeArea:foo_BAR}}foobar'
        expected = 'foobarref="3600012345" type="area"foobar'
        test(query, expected)

        # Test with Paris in OQL.
        query = 'foobar{{geocodeArea:foo_BAR}}foobar;'
        expected = 'foobararea(3600012345)foobar;'
        test(query, expected)

        # Test with a fake OSM relation.
        query = 'foobar{{geocodeArea:123456}}foobar'
        expected = 'foobarref="3600123456" type="area"foobar'
        test(query, expected)

        # Test with foo_BAR
        # and bar_FOO.
        query = (
            'foo{{geocodeArea:foo_BAR}}bar'
            'foo{{geocodeArea:bar_FOO}}bar'
        )
        expected = (
            'fooref="3600012345" type="area"bar'
            'fooref="3600054321" type="area"bar'
        )
        test(query, expected)

    def test_clean_query(self):
        """Test we can clean a query."""

        def test(data, result):
            query = QueryPreparation(data)
            query.clean_query()
            self.assertEqual(query._query_prepared, result)

        test('  foo;;   ', 'foo;')
        test('	foo;	', 'foo;')
        test('   	foo	   ', 'foo')
        test('   	foo;\n	   ', 'foo;')

    def test_prepare_query(self):
        """Test we can prepare a query."""
        # Test geocodeArea simple.
        # There is a HACK in the code to return 12345
        query = (
            '<osm-script output="xml" timeout="25">    <id-query '
            '{{geocodeArea:foo_BAR}} into="area_0"/>    '
            '<union>        <query type="node">            '
            '<has-kv k="a" v="b"/>            '
            '<area-query from="area_0"/>        </query>        <query type='
            '"way">            <has-kv k="a" v="b"/>            <area-query '
            'from="area_0"/>        </query>        '
            '<query type="relation">            '
            '<has-kv k="a" v="b"/>            '
            '<area-query from="area_0"/>        </query>    </union>    '
            '<union>        <item/>        <recurse type="down"/>    '
            '</union>   <print mode="body"/></osm-script>'
        )
        expected = (
            '<osm-script output="xml" timeout="25">    <id-query '
            'ref="3600012345" type="area" into="area_0"/>    <union>        '
            '<query type="node">            <has-kv k="a" v="b"/>            '
            '<area-query from="area_0"/>        </query>        '
            '<query type="way">            <has-kv k="a" v="b"/>            '
            '<area-query from="area_0"/>        </query>        '
            '<query type="relation">            '
            '<has-kv k="a" v="b"/>            '
            '<area-query from="area_0"/>        </query>    </union>    '
            '<union>        <item/>        <recurse type="down"/>    '
            '</union>   <print mode="body"/></osm-script>'
        )
        query = QueryPreparation(query)
        query._nominatim = FakeNominatim()
        self.assertEqual(query.prepare_query(), expected)


if __name__ == '__main__':
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(TestQueryPreparation)
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
