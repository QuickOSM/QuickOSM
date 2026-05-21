"""Configuration panel."""

import logging

from json import load

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDialog

from QuickOSM.core.utilities.tools import (
    custom_config_file,
    get_setting,
    set_setting,
)
from QuickOSM.definitions.gui import Panels
from QuickOSM.definitions.nominatim import NOMINATIM_SERVERS
from QuickOSM.definitions.overpass import OVERPASS_SERVERS
from QuickOSM.ui.base_panel import BasePanel

LOGGER = logging.getLogger('QuickOSM')


class ConfigurationPanel(BasePanel):

    """Final implementation for the panel."""

    def __init__(self, dialog: QDialog):
        super().__init__(dialog)
        self.panel = Panels.Configuration

    def setup_panel(self):
        """Set UI related the configuration panel."""
        self.dialog.save_config_overpass.clicked.connect(self.set_server_overpass_api)
        self.dialog.save_config_nominatim.clicked.connect(self.set_server_nominatim_api)

        self.dialog.save_config_overpass.setIcon(QIcon(":images/themes/default/mActionFileSave.svg"))
        self.dialog.save_config_nominatim.setIcon(QIcon(":images/themes/default/mActionFileSave.svg"))

        for server in OVERPASS_SERVERS:
            self.dialog.combo_default_overpass.addItem(server)

        for server in NOMINATIM_SERVERS:
            self.dialog.combo_default_nominatim.addItem(server)

        # Read the config file
        custom_config = custom_config_file()
        if custom_config:
            with open(custom_config, encoding='utf8') as file:
                config_json = load(file)
                for server in config_json.get('overpass_servers', []):
                    if server not in OVERPASS_SERVERS:
                        LOGGER.info(
                            f'Custom overpass server list added: {server}')
                        self.dialog.combo_default_overpass.addItem(server)
                for server in config_json.get('nominatim_servers', []):
                    if server not in NOMINATIM_SERVERS:
                        LOGGER.info(
                            f'Custom nominatim server list added: {server}')
                        self.dialog.combo_default_nominatim.addItem(server)

        # Set settings about the overpass API
        # Set it after populating the combobox #235
        default_server = get_setting('defaultOAPI')
        if default_server:
            index = self.dialog.combo_default_overpass.findText(default_server)
            self.dialog.combo_default_overpass.setCurrentIndex(index)
        else:
            default_server = self.dialog.combo_default_overpass.currentText()
            set_setting('defaultOAPI', default_server)

        # Set settings about the nominatim APIs
        # Set it after populating the combobox #235
        default_server = get_setting('defaultNominatimAPI')
        if default_server:
            index = self.dialog.combo_default_nominatim.findText(default_server)
            self.dialog.combo_default_nominatim.setCurrentIndex(index)
        else:
            default_server = self.dialog.combo_default_nominatim.currentText()
            set_setting('defaultNominatimAPI', default_server)

    def set_server_overpass_api(self):
        """Save the new Overpass server."""
        default_server = self.dialog.combo_default_overpass.currentText()
        set_setting('defaultOAPI', default_server)

    def set_server_nominatim_api(self):
        """Save the new Nominatim server."""
        default_server = self.dialog.combo_default_nominatim.currentText()
        set_setting('defaultNominatimAPI', default_server)
