"""Configuration panel."""

import json
import logging

from functools import partial
from pathlib import Path

from qgis.core import QgsApplication
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
from QuickOSM.tools.i18n import tr
from QuickOSM.ui.base_panel import BasePanel

LOGGER = logging.getLogger('QuickOSM')


class Server:
    Nominatim = 'nominatim'
    Overpass = 'overpass'


class ConfigurationPanel(BasePanel):

    """Final implementation for the panel."""

    def __init__(self, dialog: QDialog):
        super().__init__(dialog)
        self.panel = Panels.Configuration

    def setup_panel(self):
        """Set UI related the configuration panel."""

        self.dialog.save_config_overpass.clicked.connect(self.set_server_overpass_api)
        self.dialog.save_config_nominatim.clicked.connect(self.set_server_nominatim_api)

        self.dialog.save_config_overpass.setIcon(
            QIcon(":images/themes/default/mActionFileSave.svg"))
        self.dialog.save_config_nominatim.setIcon(
            QIcon(":images/themes/default/mActionFileSave.svg"))

        self.dialog.line_edit_overpass_url.setPlaceholderText("https://my-overpass.org/api/")
        self.dialog.line_edit_nominatim_url.setPlaceholderText("https://my-nominatim.org/search?")

        add_new_server = tr('Add a new server in the list')
        remove_selected_server = tr('Remove the selected server from the list')

        self.dialog.btn_add_overpass.setText('')
        self.dialog.btn_add_overpass.setIcon(
            QIcon(QgsApplication.iconPath('symbologyAdd.svg')))
        self.dialog.btn_add_overpass.setToolTip(add_new_server)

        self.dialog.btn_remove_overpass.setText('')
        self.dialog.btn_remove_overpass.setIcon(
            QIcon(QgsApplication.iconPath('symbologyRemove.svg')))
        self.dialog.btn_remove_overpass.setToolTip(remove_selected_server)

        self.dialog.btn_add_nominatim.setText('')
        self.dialog.btn_add_nominatim.setIcon(
            QIcon(QgsApplication.iconPath('symbologyAdd.svg')))
        self.dialog.btn_add_nominatim.setToolTip(add_new_server)

        self.dialog.btn_remove_nominatim.setText('')
        self.dialog.btn_remove_nominatim.setIcon(
            QIcon(QgsApplication.iconPath('symbologyRemove.svg')))
        self.dialog.btn_remove_nominatim.setToolTip(remove_selected_server)

        self.dialog.btn_add_overpass.clicked.connect(partial(self._add_custom_server, Server.Overpass))
        self.dialog.btn_remove_overpass.clicked.connect(partial(self._remove_custom_server, Server.Overpass))
        self.dialog.btn_add_nominatim.clicked.connect(partial(self._add_custom_server,Server.Nominatim))
        self.dialog.btn_remove_nominatim.clicked.connect(partial(self._remove_custom_server, Server.Nominatim))

        # --- Populate built-in servers into combo boxes ---
        for server in OVERPASS_SERVERS:
            self.dialog.combo_default_overpass.addItem(server)

        for server in NOMINATIM_SERVERS:
            self.dialog.combo_default_nominatim.addItem(server)

        # --- Load custom servers from custom_config.json ---
        config_json = self._load_custom_config()

        for server in config_json.get(f'{Server.Overpass}_servers', []):
            if server not in OVERPASS_SERVERS:
                LOGGER.info(f'Custom {Server.Overpass} server list added: {server}')
                self.dialog.combo_default_overpass.addItem(server)
                self.dialog.list_custom_overpass.addItem(server)

        for server in config_json.get(f'{Server.Nominatim}_servers', []):
            if server not in NOMINATIM_SERVERS:
                LOGGER.info(f'Custom {Server.Nominatim} server list added: {server}')
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

    def set_server_overpass_api(self):
        """Save the new Overpass server."""
        default_server = self.dialog.combo_default_overpass.currentText()
        set_setting('defaultOAPI', default_server)

    def set_server_nominatim_api(self):
        """Save the new Nominatim server."""
        default_server = self.dialog.combo_default_nominatim.currentText()
        set_setting('defaultNominatimAPI', default_server)

    def _add_custom_server(self, server_type: str) -> bool:
        """Add a custom server entered in the line-edit."""
        if server_type == Server.Overpass:
            input_widget = self.dialog.line_edit_overpass_url
            combo_widget = self.dialog.combo_default_overpass
            list_widget = self.dialog.list_custom_overpass
        else:
            input_widget = self.dialog.line_edit_nominatim_url
            combo_widget = self.dialog.combo_default_nominatim
            list_widget = self.dialog.list_custom_nominatim

        url = input_widget.text().strip()
        all_items = [
            combo_widget.itemText(i) for i in range(combo_widget.count())
        ]

        if not url:
            QMessageBox.warning(
                self.dialog, 'QuickOSM',
                tr('Please enter a URL.'))
            return False

        if not url.startswith('http'):
            QMessageBox.warning(
                self.dialog, 'QuickOSM',
                tr('The URL must begin with “http”.'))
            return False

        if url in all_items:
            QMessageBox.information(
                self.dialog, 'QuickOSM',
                tr('This server is already in the list.'))
            return False

        # Add to combo and list widget
        combo_widget.addItem(url)
        list_widget.addItem(url)
        input_widget.clear()

        # Persist to custom_config.json
        config = self._load_custom_config()
        servers = config.get(f'{server_type}_servers', [])
        if url not in servers:
            servers.append(url)
        config[f'{server_type}_servers'] = servers
        self._save_custom_config(config)

        LOGGER.info(f'Custom {server_type} server added via GUI: {url}')
        return True

    def _remove_custom_server(self, server_type: str) -> bool:
        """Remove the selected custom server."""
        if server_type == Server.Overpass:
            list_widget = self.dialog.list_custom_overpass
            combo_widget = self.dialog.combo_default_overpass

        else:
            list_widget = self.dialog.list_custom_nominatim
            combo_widget = self.dialog.combo_default_nominatim

        selected = list_widget.currentItem()
        if not selected:
            QMessageBox.warning(
                self.dialog, 'QuickOSM',
                tr('Please select a server from the list.'))
            return False

        url = selected.text()

        # Remove from list widget
        list_widget.takeItem(list_widget.row(selected))

        # Remove from combo box
        index = combo_widget.findText(url)
        if index >= 0:
            combo_widget.removeItem(index)
            if server_type == Server.Overpass:
                self.set_server_overpass_api()
            else:
                self.set_server_nominatim_api()

        # Persist removal to custom_config.json
        config = self._load_custom_config()
        servers = [s for s in config.get(f'{server_type}_servers', []) if s != url]
        config[f'{server_type}_servers'] = servers
        self._save_custom_config(config)

        LOGGER.info(f'Custom {server_type} server removed via GUI: {url}')
        return True

    @staticmethod
    def _load_custom_config() -> dict:
        """Load the custom_config.json, returning an empty dict if absent."""
        config_path = custom_config_file()
        if config_path:
            try:
                with Path(config_path).open(encoding='utf8') as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                LOGGER.warning(f'Could not read custom_config.json: {e}')
        return {}

    @staticmethod
    def _save_custom_config(config: dict) -> bool:
        """Write config to custom_config.json (creates the file if needed)."""
        config_path = Path(quickosm_user_folder()) / 'custom_config.json'
        try:
            with config_path.open('w', encoding='utf8') as f:
                json.dump(config, f, indent=4)
                return True
        except OSError as e:
            LOGGER.error(f'Could not write custom_config.json: {e}')
            return False
