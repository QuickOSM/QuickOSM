"""Tests for processing algorithms."""

import processing

from qgis.core import QgsApplication, QgsVectorLayer
from qgis.testing import unittest

from QuickOSM.quick_osm_processing.provider import Provider
from QuickOSM.test.definitions import TOWN_COORDS, TOWN_NAME


class TestProcessing(unittest.TestCase):
    """Tests for processing algorithms."""

    def setUp(self) -> None:
        """Set up the processing tests."""
        if not QgsApplication.processingRegistry().providers():
            self.provider = Provider()
            QgsApplication.processingRegistry().addProvider(self.provider)
        self.maxDiff = None

    def test_build_not_spatial_query(self):
        """Test for the build of a not spatial query algorithm."""
        result = processing.run(
            'quickosm:buildquerybyattributeonly',
            {
                'KEY': 'amenity',
                'SERVER': 'https://z.overpass-api.de/api/interpreter',
                'TIMEOUT': 25,
                'VALUE': 'bench'
            }
        )

        result_expected = {
            'OUTPUT_URL': 'https://z.overpass-api.de/api/interpreter?data=[out:xml]'
                          ' [timeout:25];%0A(%0A    node[%22amenity%22%3D%22bench%22];%0A'
                          '    way[%22amenity%22%3D%22bench%22];%0A    '
                          'relation[%22amenity%22%3D%22bench%22];%0A);%0A(._;%3E;);'
                          '%0Aout body;&info=QgisQuickOSMPlugin',
            'OUTPUT_OQL_QUERY':
                '[out:xml] [timeout:25];\n(\n    node["amenity"="bench"];\n'
                '    way["amenity"="bench"];\n    relation["amenity"="bench"];'
                '\n);\n(._;>;);\nout body;'
        }

        self.assertEqual(result_expected, result)

    def test_build_in_area_query(self):
        """Test for the build of a 'in area' query algorithm."""
        result = processing.run(
            'quickosm:buildqueryinsidearea',
            {
                'AREA': TOWN_NAME,
                'KEY': 'amenity',
                'SERVER': 'https://z.overpass-api.de/api/interpreter',
                'TIMEOUT': 25,
                'VALUE': 'bench'
            }
        )

        result_expected = {
            'OUTPUT_URL':
                'https://z.overpass-api.de/api/interpreter?data=[out:xml]'
                ' [timeout:25];%0A area(3600118810) -%3E .area_0;%0A(%0A    '
                'node[%22amenity%22%3D%22bench%22](area.area_0);%0A    '
                'way[%22amenity%22%3D%22bench%22](area.area_0);%0A    '
                'relation[%22amenity%22%3D%22bench%22](area.area_0);%0A);'
                '%0A(._;%3E;);%0Aout body;&info=QgisQuickOSMPlugin',
            'OUTPUT_OQL_QUERY':
                '[out:xml] [timeout:25];\n area(3600118810) -> .area_0;\n'
                '(\n    node["amenity"="bench"](area.area_0);\n    '
                'way["amenity"="bench"](area.area_0);\n    '
                'relation["amenity"="bench"](area.area_0);\n);'
                '\n(._;>;);\nout body;'
        }

        self.assertEqual(result_expected, result)

    def test_build_around_area_query(self):
        """Test for the build of an around area query algorithm."""
        result = processing.run(
            'quickosm:buildqueryaroundarea',
            {
                'AREA': TOWN_NAME,
                'DISTANCE': 1000,
                'KEY': 'amenity',
                'SERVER': 'https://lz4.overpass-api.de/api/interpreter',
                'TIMEOUT': 25,
                'VALUE': 'bench'
            }
        )

        result_expected = {
            'OUTPUT_URL':
                f'https://lz4.overpass-api.de/api/interpreter?data=[out:xml]'
                f' [timeout:25];%0A(%0A    node[%22amenity%22%3D%22bench%22]'
                f'(around:1000, {TOWN_COORDS});%0A    way[%22amenity%22%3D%22bench%22]'
                f'(around:1000, {TOWN_COORDS});%0A    relation[%22amenity%22%3D%22bench%22]'
                f'(around:1000, {TOWN_COORDS});%0A);%0A(._;%3E;);%0Aout'
                f' body;&info=QgisQuickOSMPlugin',
            'OUTPUT_OQL_QUERY':
                f'[out:xml] [timeout:25];\n(\n'
                f'    node["amenity"="bench"](around:1000, {TOWN_COORDS});\n'
                f'    way["amenity"="bench"](around:1000, {TOWN_COORDS});\n'
                f'    relation["amenity"="bench"](around:1000, {TOWN_COORDS});'
                f'\n);\n(._;>;);\nout body;'
        }

        self.assertEqual(result_expected, result)

    def test_build_in_extent_query(self):
        """Test for the build of a 'in extent' query algorithm."""
        result = processing.run(
            'quickosm:buildqueryextent',
            {
                'EXTENT': '3.809971100,3.963647400,43.557942300,43.654612100 [EPSG:4326]',
                'KEY': 'amenity',
                'SERVER': 'https://lz4.overpass-api.de/api/interpreter',
                'TIMEOUT': 25,
                'VALUE': 'bench'
            }
        )

        result_expected = {
            'OUTPUT_URL':
                'https://lz4.overpass-api.de/api/interpreter?data=[out:xml]'
                ' [timeout:25];%0A(%0A    node[%22amenity%22%3D%22bench%22]'
                '( 43.55794,3.80997,43.65461,3.96364);%0A    '
                'way[%22amenity%22%3D%22bench%22]( 43.55794,3.80997,43.65461,3.96364);%0A'
                '    relation[%22amenity%22%3D%22bench%22]'
                '( 43.55794,3.80997,43.65461,3.96364);%0A);'
                '%0A(._;%3E;);%0Aout body;&info=QgisQuickOSMPlugin',
            'OUTPUT_OQL_QUERY':
                '[out:xml] [timeout:25];\n(\n    node["amenity"="bench"]'
                '( 43.55794,3.80997,43.65461,3.96364);\n    '
                'way["amenity"="bench"]( 43.55794,3.80997,43.65461,3.96364);\n'
                '    relation["amenity"="bench"]( 43.55794,3.80997,43.65461,3.96364);'
                '\n);\n(._;>;);\nout body;'
        }

        self.assertEqual(result_expected, result)

    def test_build_in_extent_query_with_multitypes(self):
        """Test for the build of an in extent algorithm that uses the multitypes parameter."""
        result = processing.run(
            'quickosm:buildqueryextent',
            {
                'EXTENT': '8.71679,8.79689,51.70687,51.72602 [EPSG:4326]',
                'KEY': 'highway,footway',
                'SERVER': 'https://lz4.overpass-api.de/api/interpreter',
                'TIMEOUT': 25,
                'TYPE_MULTI_REQUEST': 'AND',
                'VALUE': 'footway,sidewalk'
            }
        )
        result_expected = {
            'OUTPUT_OQL_QUERY':
                '[out:xml] [timeout:25];\n(\n    node["highway"="footway"]["footway"="sidewalk"]'
                '( 51.70687,8.71679,51.72602,8.79689);\n    way["highway"="footway"]["footway"="sidewalk"]'
                '( 51.70687,8.71679,51.72602,8.79689);\n    relation["highway"="footway"]'
                '["footway"="sidewalk"]( 51.70687,8.71679,51.72602,8.79689);\n);\n(._;>;);\nout body;',
            'OUTPUT_URL':
                'https://lz4.overpass-api.de/api/interpreter?data=[out:xml] [timeout:25];%0A(%0A'
                '    node[%22highway%22%3D%22footway%22][%22footway%22%3D%22sidewalk%22]'
                '( 51.70687,8.71679,51.72602,8.79689);%0A    way[%22highway%22%3D%22footway%22]'
                '[%22footway%22%3D%22sidewalk%22]( 51.70687,8.71679,51.72602,8.79689);%0A    '
                'relation[%22highway%22%3D%22footway%22][%22footway%22%3D%22sidewalk%22]'
                '( 51.70687,8.71679,51.72602,8.79689);%0A);%0A(._;%3E;);%0Aout body;&info=QgisQuickOSMPlugin'
        }
        self.assertEqual(result_expected, result)

    def test_build_raw_query(self):
        """Test for the build of a raw query algorithm."""
        result = processing.run(
            'quickosm:buildrawquery',
            {
                'AREA': 'La Souterraine',
                'EXTENT': '3.809971100,3.963647400,43.557942300,43.654612100 [EPSG:4326]',
                'QUERY':
                    '[out:xml] [timeout:25];\n {{geocodeArea:La Souterraine}}'
                    ' -> .area_0;\n(\n    node[\"amenity\"=\"bench\"]'
                    '(area.area_0);\n    way[\"amenity\"=\"bench\"]'
                    '(area.area_0);\n    relation[\"amenity\"=\"bench\"]'
                    '(area.area_0);\n);\n(._;>;);\nout body;',
                'SERVER': 'server Overpass'
            }
        )

        result_expected = {
            'OUTPUT_URL':
                'server Overpass?data=[out:xml] [timeout:25];%0A '
                'area(3600118810) -%3E .area_0;%0A(%0A    '
                'node[%22amenity%22%3D%22bench%22](area.area_0);'
                '%0A    way[%22amenity%22%3D%22bench%22](area.area_0);'
                '%0A    relation[%22amenity%22%3D%22bench%22](area.area_0);'
                '%0A);%0A(._;%3E;);%0Aout body;&info=QgisQuickOSMPlugin',
            'OUTPUT_OQL_QUERY':
                '[out:xml] [timeout:25];\n area(3600118810) -> .area_0;\n'
                '(\n    node["amenity"="bench"](area.area_0);\n    '
                'way["amenity"="bench"](area.area_0);\n    '
                'relation["amenity"="bench"](area.area_0);\n);'
                '\n(._;>;);\nout body;'
        }

        self.assertEqual(result_expected, result)

    def test_open_osm_file(self):
        """Test for the opening of an osm file."""
        result = processing.run(
            'quickosm:openosmfile',
            {
                'FILE': '\\path\\to\\a\\file.osm',
                'OSM_CONF': ''
            }
        )

        self.assertIsInstance(result['OUTPUT_POINTS'], QgsVectorLayer)
        self.assertIn('|layername=points', result['OUTPUT_POINTS'].source())
        self.assertIsInstance(result['OUTPUT_LINES'], QgsVectorLayer)
        self.assertIn('|layername=lines', result['OUTPUT_LINES'].source())
        self.assertIsInstance(result['OUTPUT_MULTILINESTRINGS'], QgsVectorLayer)
        self.assertIn('|layername=multilinestrings', result['OUTPUT_MULTILINESTRINGS'].source())
        self.assertIsInstance(result['OUTPUT_MULTIPOLYGONS'], QgsVectorLayer)
        self.assertIn('|layername=multipolygons', result['OUTPUT_MULTIPOLYGONS'].source())
        self.assertIsInstance(result['OUTPUT_OTHER_RELATIONS'], QgsVectorLayer)
        self.assertIn('|layername=other_relations', result['OUTPUT_OTHER_RELATIONS'].source())


if __name__ == '__main__':
    unittest.main()
