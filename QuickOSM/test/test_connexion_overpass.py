"""Tests for Overpass API requests."""

from qgis.PyQt.QtCore import QUrl, QUrlQuery
from qgis.testing import unittest

from QuickOSM.core.api.connexion_oapi import ConnexionOAPI
from QuickOSM.core.exceptions import (
    OverpassBadRequestException,
    OverpassMemoryException,
    OverpassRuntimeError,
    OverpassTimeoutException,
)
from QuickOSM.definitions.overpass import OVERPASS_SERVERS
from QuickOSM.tools.resources import plugin_test_data_path



class TestOverpass(unittest.TestCase):
    """Tests for Overpass API requests."""

    def test_real_wrong_request(self):
        """Test wrong request.

        This test is using internet.
        """
        url = QUrl(OVERPASS_SERVERS[0])
        query_string = QUrlQuery()
        query_string.addQueryItem('data', 'fake_query')
        url.setQuery(query_string)
        overpass = ConnexionOAPI(url.toString())

        self.assertListEqual(overpass.errors, [])

        # We don't want the FileNotFoundError
        with self.assertRaises(OverpassBadRequestException):
            overpass.run()

        self.assertEqual(len(overpass.errors), 1)

    def test_parsing_http_string(self):
        """Test we can parse the HTTP return string from QGIS for timing out."""
        string = (
            'Network request http://www.overpass-api.de/api/interpreter?data='
            '%3Cosm-script output%3D%22xml%22 timeout%3D%2225%22%3E%0A %3Cid-'
            'query ref%3D%223600171496%22 type%3D%22area%22 into%3D%22area_0%'
            '22/%3E%0A %3Cunion%3E%0A %3Cquery type%3D%22node%22%3E%0A %3Chas'
            '-kv k%3D%22admin_level%22 v%3D%222%22/%3E%0A %3Carea-query from%'
            '3D%22area_0%22/%3E%0A %3C/query%3E%0A %3Cquery type%3D%22way%22%'
            '3E%0A %3Chas-kv k%3D%22admin_level%22 v%3D%222%22/%3E%0A %3Carea'
            '-query from%3D%22area_0%22/%3E%0A %3C/query%3E%0A %3Cquery type%'
            '3D%22relation%22%3E%0A %3Chas-kv k%3D%22admin_level%22 v%3D%222%'
            '22/%3E%0A %3Carea-query from%3D%22area_0%22/%3E%0A %3C/query%3E%'
            '0A %3C/union%3E%0A %3Cunion%3E%0A %3Citem/%3E%0A %3Crecurse type'
            '%3D%22down%22/%3E%0A %3C/union%3E%0A %3Cprint mode%3D%22body%22/'
            '%3E%0A%3C/osm-script%3E&info=QgisQuickOSMPlugin timed out'
        )
        with self.assertRaises(OverpassTimeoutException):
            ConnexionOAPI.is_query_timed_out(string)

    def test_read_xml_encoding(self):
        """ Test #240 related to encoding. """
        encoding_file = plugin_test_data_path('overpass', 'error_decode_utf8.xml')
        ConnexionOAPI.check_file(encoding_file)

    def test_xml_error(self):
        """Test we can parse Overpass error within a file."""

        timeout_file = plugin_test_data_path('overpass', 'query_timed_out.xml')
        with self.assertRaises(OverpassTimeoutException) as error:
            ConnexionOAPI.check_file(timeout_file)

        self.assertEqual(
            str(error.exception),
            'OverpassAPI timeout, try again later or a smaller query.')

        run_out_memory = plugin_test_data_path('overpass', 'run_out_memory.xml')
        with self.assertRaises(OverpassMemoryException) as error:
            ConnexionOAPI.check_file(run_out_memory)

        self.assertEqual(
            str(error.exception),
            "('OverpassAPI is out of memory, try another query or a smaller area.',"
            " 'The server would need more or less 513 MB of RAM.')")

        generic_error = plugin_test_data_path('overpass', 'generic_error.xml')
        with self.assertRaises(OverpassRuntimeError) as error:
            ConnexionOAPI.check_file(generic_error)

        self.assertEqual(str(error.exception), 'Overpass error: FAKE error that I do not know')

        bad_query = plugin_test_data_path('overpass', 'bad_query.xml')
        with self.assertRaises(OverpassBadRequestException) as error:

            ConnexionOAPI.check_file(bad_query)

        self.assertEqual(
            str(error.exception),
            'Bad request OverpassAPI.  line 10: parse error: Invalid parameter for print: &quot;centre&quot; '
        )
