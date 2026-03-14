"""Tests for processing algorithms using network."""

import processing

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsProcessingContext,
    QgsProject,
    QgsVectorLayer,
)
from qgis.testing import unittest

from QuickOSM.tools.resources import plugin_test_data_path
from QuickOSM.quick_osm_processing.provider import Provider
from QuickOSM.test.definitions import TOWN_COORDS, TOWN_NAME
from QuickOSM.test.mocked_web_server import (
    SequentialHandler,
    install_http_handler,
    launch,
)



class TestProcessing(unittest.TestCase):
    """Tests for processing algorithms using network."""

    @classmethod
    def setUpClass(cls):
        """ Set up the server. """
        cls.server, cls.port = launch()

    @classmethod
    def tearDownClass(cls):
        """ Stop the server. """
        cls.server.stop()

    def setUp(self) -> None:
        """Set up the processing tests."""
        if not QgsApplication.processingRegistry().providers():
            self.provider = Provider()
            QgsApplication.processingRegistry().addProvider(self.provider)
        self.maxDiff = None

    def test_process_raw_query(self):
        """Test for the process algorithm from a raw query."""
        handler = SequentialHandler()
        handler.add(
            'GET',
            "/interpreter?data=[out:xml]%20[timeout:25];%0A%20area(3600028722)%20-%3E%20.area_0;"
            "%0A(%0A%20%20%20%20node[%22amenity%22%3D%22bench%22](area.area_0);%0A%20%20%20%20way"
            "[%22amenity%22%3D%22bench%22](area.area_0);%0A%20%20%20%20relation[%22amenity%22%3D%22bench%22]"
            "(area.area_0);%0A);%0A(._;%3E;);%0Aout%20body;&info=QgisQuickOSMPlugin",
            200,
            {'Content-type': 'text/xml'},
            open(plugin_test_data_path('overpass', 'empty_osm_file.xml'), encoding='utf8').read(),
        )
        with install_http_handler(handler):
            result = processing.run(
                'quickosm:downloadosmdatarawquery',
                {
                    'QUERY':
                        '[out:xml] [timeout:25];\n area(3600028722) -> .area_0;\n'
                        '(\n    node[\"amenity\"=\"bench\"](area.area_0);\n    '
                        'way[\"amenity\"=\"bench\"](area.area_0);\n    '
                        'relation[\"amenity\"=\"bench\"](area.area_0);\n);\n'
                        '(._;>;);\nout body;',
                    'TIMEOUT': 25,
                    'SERVER': f'http://localhost:{self.port}/interpreter',
                    'EXTENT': '3.809971100,3.963647400,43.557942300,43.654612100 [EPSG:4326]',
                    'AREA': '',
                    'FILE': ''
                }
            )

        self.assertIsInstance(result['OUTPUT_POINTS'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_LINES'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_MULTILINESTRINGS'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_MULTIPOLYGONS'], QgsVectorLayer)

    def test_process_not_spatial_query(self):
        """Test for the process algorithm from a not spatial query."""
        handler = SequentialHandler()
        handler.add(
            'GET',
            '/interpreter?data=[out:xml]%20[timeout:25];%0A(%0A%20%20%20%20node[%22amenity%22%3D%22foo%22];'
            '%0A%20%20%20%20way[%22amenity%22%3D%22foo%22];%0A%20%20%20%20relation[%22amenity%22%3D%22foo%22]'
            ';%0A);%0A(._;%3E;);%0Aout%20body;&info=QgisQuickOSMPlugin',
            200,
            {'Content-type': 'text/xml'},
            open(plugin_test_data_path('overpass', 'empty_osm_file.xml'), encoding='utf8').read(),
        )
        with install_http_handler(handler):
            result = processing.run(
                'quickosm:downloadosmdatanotspatialquery',
                {
                    'KEY': 'amenity',
                    'SERVER': f'http://localhost:{self.port}/interpreter',
                    'TIMEOUT': 25,
                    'VALUE': 'foo'
                }
            )

        self.assertIsInstance(result['OUTPUT_POINTS'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_LINES'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_MULTILINESTRINGS'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_MULTIPOLYGONS'], QgsVectorLayer)

    def test_process_in_query(self):
        """Test for the process algorithm from an 'in' query."""
        handler = SequentialHandler()
        handler.add(
            'GET',
            '/interpreter?data=[out:xml]%20[timeout:25];%0A%20area(3600118810)%20-%3E%20.area_0;%0A'
            '(%0A%20%20%20%20node[%22amenity%22%3D%22bench%22](area.area_0);%0A%20%20%20%20way[%22amenity'
            '%22%3D%22bench%22](area.area_0);%0A%20%20%20%20relation[%22amenity%22%3D%22bench%22]'
            '(area.area_0);%0A);%0A(._;%3E;);%0Aout%20body;&info=QgisQuickOSMPlugin',
            200,
            {'Content-type': 'text/xml'},
            open(plugin_test_data_path('overpass', 'empty_osm_file.xml'), encoding='utf8').read(),
        )
        with install_http_handler(handler):
            result = processing.run(
                'quickosm:downloadosmdatainareaquery',
                {
                    'AREA': 'La Souterraine',
                    'KEY': 'amenity',
                    'SERVER': f'http://localhost:{self.port}/interpreter',
                    'TIMEOUT': 25,
                    'VALUE': 'bench'
                }
            )

        self.assertIsInstance(result['OUTPUT_POINTS'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_LINES'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_MULTILINESTRINGS'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_MULTIPOLYGONS'], QgsVectorLayer)

    def test_process_around_query(self):
        """Test for the process algorithm from an 'around' query."""
        handler = SequentialHandler()
        handler.add(
            'GET',
            f'/interpreter?data=[out:xml]%20[timeout:25];%0A(%0A%20%20%20%20node[%22amenity%22%3D%22bench%22]'
            f'(around:1500,%20{TOWN_COORDS});%0A%20%20%20%20way[%22amenity%22%3D%22bench%22]'
            f'(around:1500,%20{TOWN_COORDS});%0A%20%20%20%20relation[%22amenity%22%3D%22bench%22]'
            f'(around:1500,%20{TOWN_COORDS});%0A);%0A(._;%3E;);%0Aout%20body;&info=QgisQuickOSMPlugin',
            200,
            {'Content-type': 'text/xml'},
            open(plugin_test_data_path('overpass', 'empty_osm_file.xml'), encoding='utf8').read(),
        )
        with install_http_handler(handler):
            result = processing.run(
                'quickosm:downloadosmdataaroundareaquery',
                {
                    'AREA': TOWN_NAME,
                    'DISTANCE': 1500,
                    'KEY': 'amenity',
                    'SERVER': f'http://localhost:{self.port}/interpreter',
                    'TIMEOUT': 25,
                    'VALUE': 'bench'
                }
            )

        self.assertIsInstance(result['OUTPUT_POINTS'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_LINES'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_MULTILINESTRINGS'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_MULTIPOLYGONS'], QgsVectorLayer)

    def test_process_extent_query(self):
        """Test for the process algorithm from an 'extent' query."""
        handler = SequentialHandler()
        handler.add(
            'GET',
            '/interpreter?data=[out:xml]%20[timeout:25];%0A(%0A%20%20%20%20node[%22amenity%22%3D%22bench%22]'
            '(%2043.55794,3.80997,43.65461,3.96364);%0A%20%20%20%20way[%22amenity%22%3D%22bench%22]'
            '(%2043.55794,3.80997,43.65461,3.96364);%0A%20%20%20%20relation[%22amenity%22%3D%22bench%22]'
            '(%2043.55794,3.80997,43.65461,3.96364);%0A);%0A(._;%3E;);%0Aout%20body;&info=QgisQuickOSMPlugin',
            200,
            {'Content-type': 'text/xml'},
            open(plugin_test_data_path('overpass', 'empty_osm_file.xml'), encoding='utf8').read(),
        )
        with install_http_handler(handler):
            result = processing.run(
                'quickosm:downloadosmdataextentquery',
                {
                    'EXTENT': '3.809971100,3.963647400,43.557942300,43.654612100 [EPSG:4326]',
                    'KEY': 'amenity',
                    'SERVER': f'http://localhost:{self.port}/interpreter',
                    'TIMEOUT': 25,
                    'VALUE': 'bench'
                }
            )

        self.assertIsInstance(result['OUTPUT_POINTS'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_LINES'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_MULTILINESTRINGS'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_MULTIPOLYGONS'], QgsVectorLayer)

    def test_reprojection_extent_query(self):
        """Test for the reprojection from the project CRS."""
        # In processing.run, we can see some 2154 coordinates.
        # In the query, coordinates in 4326
        handler = SequentialHandler()
        handler.add(
            'GET',
            '/interpreter?data=[out:xml]%20[timeout:25];%0A(%0A%20%20%20%20node[%22landuse%22]'
            '(%2045.0843,-0.3832,45.09649,-0.36385);%0A%20%20%20%20way[%22landuse%22]'
            '(%2045.0843,-0.3832,45.09649,-0.36385);%0A%20%20%20%20relation[%22landuse%22]'
            '(%2045.0843,-0.3832,45.09649,-0.36385);%0A);%0A(._;%3E;);%0Aout%20body;&info=QgisQuickOSMPlugin',
            200,
            {'Content-type': 'text/xml'},
            open(plugin_test_data_path('overpass', 'empty_osm_file.xml'), encoding='utf8').read(),
        )
        project = QgsProject()
        project.setCrs(QgsCoordinateReferenceSystem(2154))
        context = QgsProcessingContext()
        context.setProject(project)

        with install_http_handler(handler):
            result = processing.run(
                'quickosm:downloadosmdataextentquery',
                {
                    'KEY': 'landuse',
                    'VALUE': '',
                    'EXTENT': '433888.4776000,435466.5863000,6448484.3786000,6449771.2615000 [EPSG:2154]',
                    'TIMEOUT': 25,
                    'SERVER': f'http://localhost:{self.port}/interpreter',
                },
                context=context
            )

        self.assertIsInstance(result['OUTPUT_POINTS'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_LINES'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_MULTILINESTRINGS'], QgsVectorLayer)
        self.assertIsInstance(result['OUTPUT_MULTIPOLYGONS'], QgsVectorLayer)


if __name__ == '__main__':
    unittest.main()
