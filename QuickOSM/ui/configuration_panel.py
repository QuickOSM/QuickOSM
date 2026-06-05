"""Configuration panel."""

import json
import logging

from os.path import join

from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QDialog, QMessageBox

from QuickOSM.core.utilities.tools import (
    custom_config_file,
    get_setting,
    quickosm_user_folder,
    set_setting,
)
from QuickOSM.definitions.gui import Panels
from QuickOSM.definitions.nominatim import NOMINATIM_SERVERS
from QuickOSM.definitions.overpass import OVERPASS_SERVERS
from QuickOSM.ui.base_panel import BasePanel


LOGGER = logging.getLogger('QuickOSM')


def _load_custom_config() -> dict:
    """Load the custom_config.json, returning an empty dict if absent."""
    config_path = custom_config_file()
    if config_path:
        try:
            with open(config_path, encoding='utf8') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            LOGGER.warning(f'Could not read custom_config.json: {e}')
    return {}


def _save_custom_config(config: dict) -> None:
    """Write *config* back to custom_config.json (creates the file if needed)."""
    config_path = join(quickosm_user_folder(), 'custom_config.json')
    try:
        with open(config_path, 'w', encoding='utf8') as f:
            json.dump(config, f, indent=4)
    except OSError as e:
        LOGGER.error(f'Could not write custom_config.json: {e}')


class ConfigurationPanel(BasePanel):

    """Final implementation for the panel."""

    def __init__(self, dialog: QDialog):
        super().__init__(dialog)
        self.panel = Panels.Configuration

    def setup_panel(self):
        """Set UI related the configuration panel."""
        # --- Save (default selection) buttons ---
        self.dialog.save_config_overpass.clicked.connect(self.set_server_overpass_api)
        self.dialog.save_config_nominatim.clicked.connect(self.set_server_nominatim_api)

        self.dialog.save_config_overpass.setIcon(
            QIcon(":images/themes/default/mActionFileSave.svg"))
        self.dialog.save_config_nominatim.setIcon(
            QIcon(":images/themes/default/mActionFileSave.svg"))

        # --- Add / Remove buttons for custom servers ---
        self.dialog.btn_add_overpass.clicked.connect(self._add_overpass_server)
        self.dialog.btn_remove_overpass.clicked.connect(self._remove_overpass_server)
        self.dialog.btn_add_nominatim.clicked.connect(self._add_nominatim_server)
        self.dialog.btn_remove_nominatim.clicked.connect(self._remove_nominatim_server)

        # --- Populate built-in servers into combo boxes ---
        for server in OVERPASS_SERVERS:
            self.dialog.combo_default_overpass.addItem(server)

        for server in NOMINATIM_SERVERS:
            self.dialog.combo_default_nominatim.addItem(server)

        # --- Load custom servers from custom_config.json ---
        config_json = _load_custom_config()

        for server in config_json.get('overpass_servers', []):
            if server not in OVERPASS_SERVERS:
                LOGGER.info(f'Custom overpass server list added: {server}')
                self.dialog.combo_default_overpass.addItem(server)
                self.dialog.list_custom_overpass.addItem(server)

        for server in config_json.get('nominatim_servers', []):
            if server not in NOMINATIM_SERVERS:
                LOGGER.info(f'Custom nominatim server list added: {server}')
                self.dialog.combo_default_nominatim.addItem(server)
                self.dialog.list_custom_nominatim.addItem(server)

        # --- Restore selected default server ---
        default_server = get_setting('defaultOAPI')
        if default_server:
            index = self.dialog.combo_default_overpass.findText(default_server)
            self.dialog.combo_default_overpass.setCurrentIndex(index)
        else:
            default_server = self.dialog.combo_default_overpass.currentText()
            set_setting('defaultOAPI', default_server)

        default_server = get_setting('defaultNominatimAPI')
        if default_server:
            index = self.dialog.combo_default_nominatim.findText(default_server)
            self.dialog.combo_default_nominatim.setCurrentIndex(index)
        else:
            default_server = self.dialog.combo_default_nominatim.currentText()
            set_setting('defaultNominatimAPI', default_server)

    # ------------------------------------------------------------------
    # Default-server helpers (existing behaviour)
    # ------------------------------------------------------------------

    def set_server_overpass_api(self):
        """Save the new Overpass server."""
        default_server = self.dialog.combo_default_overpass.currentText()
        set_setting('defaultOAPI', default_server)

    def set_server_nominatim_api(self):
        """Save the new Nominatim server."""
        default_server = self.dialog.combo_default_nominatim.currentText()
        set_setting('defaultNominatimAPI', default_server)

    # ------------------------------------------------------------------
    # Custom-server helpers (new)
    # ------------------------------------------------------------------

    def _add_overpass_server(self):
        """Add a custom Overpass server entered in the line-edit."""
        url = self.dialog.line_edit_overpass_url.text().strip()
        if not url:
            QMessageBox.warning(
                self.dialog, 'QuickOSM',
                'Please enter a URL.')
            return
        if not url.startswith('http'):
            QMessageBox.warning(
                self.dialog, 'QuickOSM',
                'The URL must begin with “http”.')
            return

        # Already present (built-in or custom)?
        all_items = [self.dialog.combo_default_overpass.itemText(i)
                     for i in range(self.dialog.combo_default_overpass.count())]
        if url in all_items:
            QMessageBox.information(
                self.dialog, 'QuickOSM',
                'This server is already in the list.')
            return

        # Add to combo and list widget
        self.dialog.combo_default_overpass.addItem(url)
        self.dialog.list_custom_overpass.addItem(url)
        self.dialog.line_edit_overpass_url.clear()

        # Persist to custom_config.json
        config = _load_custom_config()
        servers = config.get('overpass_servers', [])
        if url not in servers:
            servers.append(url)
        config['overpass_servers'] = servers
        _save_custom_config(config)

        LOGGER.info(f'Custom overpass server added via GUI: {url}')

    def _remove_overpass_server(self):
        """Remove the selected custom Overpass server."""
        selected = self.dialog.list_custom_overpass.currentItem()
        if not selected:
            QMessageBox.warning(
                self.dialog, 'QuickOSM',
                'Please select a server from the list.')
            return

        url = selected.text()

        # Remove from list widget
        row = self.dialog.list_custom_overpass.row(selected)
        self.dialog.list_custom_overpass.takeItem(row)

        # Remove from combo box
        index = self.dialog.combo_default_overpass.findText(url)
        if index >= 0:
            self.dialog.combo_default_overpass.removeItem(index)

        # Persist removal to custom_config.json
        config = _load_custom_config()
        servers = [s for s in config.get('overpass_servers', []) if s != url]
        config['overpass_servers'] = servers
        _save_custom_config(config)

        LOGGER.info(f'Custom overpass server removed via GUI: {url}')

    def _add_nominatim_server(self):
        """Add a custom Nominatim server entered in the line-edit."""
        url = self.dialog.line_edit_nominatim_url.text().strip()
        if not url:
            QMessageBox.warning(
                self.dialog, 'QuickOSM',
                'Please enter a URL.')
            return
        if not QUrl(url).isValid():
            QMessageBox.warning(
                self.dialog, 'QuickOSM',
                'The URL must begin with “http”.')
            return

        all_items = [self.dialog.combo_default_nominatim.itemText(i)
                     for i in range(self.dialog.combo_default_nominatim.count())]
        if url in all_items:
            QMessageBox.information(
                self.dialog, 'QuickOSM',
                'This server is already in the list.')
            return

        self.dialog.combo_default_nominatim.addItem(url)
        self.dialog.list_custom_nominatim.addItem(url)
        self.dialog.line_edit_nominatim_url.clear()

        config = _load_custom_config()
        servers = config.get('nominatim_servers', [])
        if url not in servers:
            servers.append(url)
        config['nominatim_servers'] = servers
        _save_custom_config(config)

        LOGGER.info(f'Custom nominatim server added via GUI: {url}')

    def _remove_nominatim_server(self):
        """Remove the selected custom Nominatim server."""
        selected = self.dialog.list_custom_nominatim.currentItem()
        if not selected:
            QMessageBox.warning(
                self.dialog, 'QuickOSM',
                'Please select a server from the list.')
            return

        url = selected.text()

        row = self.dialog.list_custom_nominatim.row(selected)
        self.dialog.list_custom_nominatim.takeItem(row)

        index = self.dialog.combo_default_nominatim.findText(url)
        if index >= 0:
            self.dialog.combo_default_nominatim.removeItem(index)

        config = _load_custom_config()
        servers = [s for s in config.get('nominatim_servers', []) if s != url]
        config['nominatim_servers'] = servers
        _save_custom_config(config)

        LOGGER.info(f'Custom nominatim server removed via GUI: {url}')

