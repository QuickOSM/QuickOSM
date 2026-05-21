"""Test for the configuration panel."""

from qgis.testing import unittest

from QuickOSM.core.utilities.tools import get_setting, set_setting
from QuickOSM.definitions.nominatim import NOMINATIM_SERVERS
from QuickOSM.definitions.overpass import OVERPASS_SERVERS
from QuickOSM.ui.dialog import Dialog


class TestUiMainWindow(unittest.TestCase):
    """Test for the configuration panel."""

    def setUp(self) -> None:
        """Set up the test for the configuration panel."""
        set_setting('defaultOAPI', OVERPASS_SERVERS[0])
        set_setting('defaultNominatimAPI', NOMINATIM_SERVERS[0])

    def test_configuration_panel(self):
        """Test we can save the custom server."""
        count_overpass = len(OVERPASS_SERVERS)
        count_nominatim = len(NOMINATIM_SERVERS)

        dialog = Dialog()
        self.assertEqual(dialog.combo_default_overpass.count(), count_overpass)
        default_server = get_setting('defaultOAPI')
        self.assertEqual(default_server, OVERPASS_SERVERS[0])

        dialog.combo_default_overpass.setCurrentIndex(1)
        dialog.save_config_overpass.click()
        default_server = get_setting('defaultOAPI')
        self.assertEqual(default_server, OVERPASS_SERVERS[1])

        self.assertEqual(dialog.combo_default_nominatim.count(), count_nominatim)
        default_server = get_setting('defaultNominatimAPI')
        self.assertEqual(default_server, NOMINATIM_SERVERS[0])

        dialog.combo_default_nominatim.setCurrentIndex(1)
        dialog.save_config_nominatim.click()
        default_server = get_setting('defaultNominatimAPI')
        self.assertEqual(default_server, NOMINATIM_SERVERS[1])
