"""Main dialog of QuickOSM."""

import logging
import traceback

from functools import partial
from os.path import split
from sys import exc_info

from qgis.core import Qgis, QgsFeedback, QgsMapLayer
from qgis.PyQt.QtCore import QEvent, QObject
from qgis.PyQt.QtGui import QIcon, QPixmap
from qgis.PyQt.QtWidgets import (
    QAction,
    QApplication,
    QDialog,
    QMessageBox,
    QPushButton,
)
from qgis.utils import iface as iface_import

from QuickOSM.core.actions import Actions
from QuickOSM.core.exceptions import QuickOsmException
from QuickOSM.core.utilities.utilities_qgis import open_log_panel
from QuickOSM.definitions.gui import Panels
from QuickOSM.definitions.osm import QueryLanguage
from QuickOSM.tools.i18n import tr
from QuickOSM.tools.resources import load_ui, resources_path
from QuickOSM.ui.configuration_panel import ConfigurationPanel
from QuickOSM.ui.map_preset_panel import MapPresetPanel
from QuickOSM.ui.osm_file_panel import OsmFilePanel
from QuickOSM.ui.query_panel import QueryPanel
from QuickOSM.ui.quick_query_panel import QuickQueryPanel


FORM_CLASS = load_ui('main_window.ui')
LOGGER = logging.getLogger('QuickOSM')


class Dialog(QDialog, FORM_CLASS):

    """Main class about the dialog of the plugin"""

    def __init__(self, iface=None, parent=None):
        """Constructor."""
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self._iface = iface

        self.query_menu_index = 2
        self.preset_menu_index = 0

        # Table mapping

        # Explaining quickly, these letters are referring to the panel
        # in the UI:
        # mp : Map preset
        # qq : Quick Query
        # q : Query
        # f : file
        self.external_panels = {
            Panels.MapPreset: MapPresetPanel(self),
            Panels.QuickQuery: QuickQueryPanel(self),
            Panels.Query: QueryPanel(self),
            Panels.File: OsmFilePanel(self),
            Panels.Configuration: ConfigurationPanel(self),
        }
        self.places_edits = {
            Panels.MapPreset: self.line_place_mp,
            Panels.QuickQuery: self.line_place_qq,
            Panels.Query: self.line_place_q,
        }
        self.query_type_buttons = {
            Panels.MapPreset: self.combo_query_type_mp,
            Panels.QuickQuery: self.combo_query_type_qq,
            Panels.Query: self.combo_query_type_q,
        }
        self.layers_buttons = {
            Panels.MapPreset: self.combo_extent_layer_mp,
            Panels.QuickQuery: self.combo_extent_layer_qq,
            Panels.Query: self.combo_extent_layer_q,
        }
        self.selection_features = {
            Panels.MapPreset: self.checkbox_selection_mp,
            Panels.QuickQuery: self.checkbox_selection_qq,
            Panels.Query: self.checkbox_selection_q,
        }
        self.run_buttons = {
            Panels.MapPreset: self.button_run_query_mp,
            Panels.QuickQuery: self.button_run_query_qq,
            Panels.Query: self.button_run_query_q,
            Panels.File: self.button_run_file,
        }
        self.cancel_buttons = {
            Panels.MapPreset: self.button_cancel_query_mp,
            Panels.QuickQuery: self.button_cancel_query_qq,
            Panels.Query: self.button_cancel_query_q,
            Panels.File: self.button_cancel_file,
        }
        self.execute_buttons = {
            Panels.MapPreset: self.stacked_execute_query_mp,
            Panels.QuickQuery: self.stacked_execute_query_qq,
            Panels.Query: self.stacked_execute_query_q,
            Panels.File: self.stacked_execute_file,
        }
        self.output_buttons = {
            Panels.MapPreset: [],
            Panels.QuickQuery: [
                self.checkbox_points_qq,
                self.checkbox_lines_qq,
                self.checkbox_multilinestrings_qq,
                self.checkbox_multipolygons_qq
            ],
            Panels.Query: [
                self.checkbox_points_q,
                self.checkbox_lines_q,
                self.checkbox_multilinestrings_q,
                self.checkbox_multipolygons_q,
            ],
            Panels.File: [
                self.checkbox_points_f,
                self.checkbox_lines_f,
                self.checkbox_multilinestrings_f,
                self.checkbox_multipolygons_f,
            ]
        }
        self.output_directories = {
            Panels.MapPreset: None,
            Panels.QuickQuery: self.output_directory_qq,
            Panels.Query: self.output_directory_q,
            Panels.File: self.output_directory_f
        }
        self.output_format = {
            Panels.MapPreset: None,
            Panels.QuickQuery: self.combo_format_qq,
            Panels.Query: self.combo_format_q,
            Panels.File: self.combo_format_f
        }
        self.prefix_edits = {
            Panels.MapPreset: None,
            Panels.QuickQuery: self.line_file_prefix_qq,
            Panels.Query: self.line_file_prefix_q,
            Panels.File: self.line_file_prefix_file,
        }
        self.advanced_panels = {
            Panels.MapPreset: None,
            Panels.QuickQuery: self.advanced_qq,
            Panels.Query: self.advanced_q,
        }
        self.query_language = {
            Panels.MapPreset: None,
            Panels.QuickQuery: QueryLanguage.OQL,
            Panels.Query: QueryLanguage.OQL,
        }
        self.action_oql_qq = QAction('OQL')
        self.action_oql_q = QAction('OQL')
        self.action_oql = {
            Panels.QuickQuery: self.action_oql_qq,
            Panels.Query: self.action_oql_q,
        }
        self.action_xml_qq = QAction('XML')
        self.action_xml_q = QAction('XML')
        self.action_xml = {
            Panels.QuickQuery: self.action_xml_qq,
            Panels.Query: self.action_xml_q,
        }

        icon = QIcon(resources_path('icons', 'QuickOSM.svg'))
        self.reload_action = QAction(icon, tr("Reload the query in a new file"), self.iface)
        actions = Actions(self)
        reloader = partial(actions.pre_run_reload)
        self.reload_action.triggered.connect(reloader)
        self.iface.addCustomActionForLayerType(
            self.reload_action, "", QgsMapLayer.LayerType.VectorLayer, False)

        self.feedback_process = QgsFeedback()

        item = self.menu_widget.item(0)
        item.setIcon(QIcon(resources_path('icons', 'map_tools.svg')))
        item = self.menu_widget.item(1)
        item.setIcon(QIcon(resources_path('icons', 'quick.png')))
        item = self.menu_widget.item(2)
        item.setIcon(QIcon(resources_path('icons', 'edit.png')))
        item = self.menu_widget.item(3)
        item.setIcon(QIcon(resources_path('icons', 'open.png')))
        item = self.menu_widget.item(4)
        item.setIcon(QIcon(resources_path('icons', 'general.svg')))
        item = self.menu_widget.item(5)
        item.setIcon(QIcon(resources_path('icons', 'info.png')))
        self.label_gnu.setPixmap(QPixmap(resources_path('icons', 'gnu.png')))

        # Set minimum width for the menu
        self.menu_widget.setMinimumWidth(
            self.menu_widget.sizeHintForColumn(0) + 10)

        self.progress_text.setText('')

        self.menu_widget.currentRowChanged['int'].connect(
            self.stacked_panels_widget.setCurrentIndex)

        for panel in self.external_panels.values():
            panel.setup_panel()
        self.menu_widget.setCurrentRow(0)

    @property
    def iface(self):
        """Get iface."""
        if self._iface:
            return self._iface
        return iface_import

    def eventFilter(self, obj: QObject, e: QEvent) -> bool:
        """Set up a custom event to avoid scroll"""
        return e.type() == QEvent.Type.Wheel

    def display_quickosm_exception(self, exception: QuickOsmException):
        """Display QuickOSM exceptions.

        These exceptions are been raised by QuickOSM itself.
        It should be an error from the user.

        :param exception: The exception to display.
        :rtype exception: QuickOsmException
        """
        self.set_progress_text('')
        if isinstance(exception, QuickOsmException):
            self.display_message_bar(
                exception.message,
                level=exception.level,
                duration=exception.duration,
                more_details=exception.more_details,
            )
        else:
            # Should not happen, just in case
            self.display_critical_exception(exception)

    def display_critical_exception(self, exception: BaseException):
        """Display others exceptions, these are critical.

        They are not managed by QuickOSM, so it's a bug from the plugin.

        :param exception: The exception to display.
        :rtype exception: BaseException
        """
        exc_type, _, exc_tb = exc_info()
        f_name = split(exc_tb.tb_frame.f_code.co_filename)[1]
        _, _, tb = exc_info()
        traceback.print_tb(tb)
        LOGGER.critical(
            tr('A critical error occurred, this is the traceback:'))
        LOGGER.critical(exc_type)
        LOGGER.critical(f_name)
        LOGGER.critical(exception)
        LOGGER.critical('\n'.join(traceback.format_tb(tb)))

        self.display_message_bar(
            tr(
                'Error in the QGIS log window, then the QuickOSM panel, copy/paste it and '
                'please report it, if you know how to copy/paste QGIS logs. '
                'Please check pinned tickets first.'
            ),
            level=Qgis.MessageLevel.Critical,
            open_logs=True,
            duration=10)

    def display_message_bar(
            self,
            title: str,
            message: str = None,
            level: Qgis.MessageLevel = Qgis.MessageLevel.Info,
            duration: int = 5,
            more_details: str = None,
            open_logs: bool = False):
        """Display a message.

        :param title: Title of the message.
        :type title: basestring

        :param message: The message.
        :type message: basestring

        :param level: A QGIS error level.

        :param duration: Duration in second.
        :type duration: int

        :param open_logs: If we need to add a button for the log panel.
        :type open_logs: bool

        :param more_details: The message to display in the "More button".
        :type more_details: basestring
        """
        widget = self.message_bar.createMessage(title, message)

        if more_details or open_logs:
            # Adding the button
            button = QPushButton(widget)
            widget.layout().addWidget(button)

            if open_logs:
                button.setText(tr('Open log panel'))
                # noinspection PyUnresolvedReferences
                button.pressed.connect(
                    lambda: open_log_panel())
            else:
                button.setText(tr('More details'))
                # noinspection PyUnresolvedReferences
                button.pressed.connect(
                    lambda: QMessageBox.information(None, title, more_details))

        self.message_bar.pushWidget(widget, level, duration)

    def reset_form(self):
        """Reset all the GUI to default state."""
        LOGGER.info('Dialog has been reset')

        # Map preset
        self.list_personal_preset_mp.clearSelection()
        self.list_default_mp.clearSelection()

        # Quickquery
        self.combo_preset_qq.setCurrentIndex(0)
        self.table_keys_values_qq.setRowCount(1)
        self.table_keys_values_qq.cellWidget(0, 1).setCurrentIndex(0)
        self.table_keys_values_qq.cellWidget(0, 2).lineEdit().setText('')
        self.checkbox_node.setChecked(True)
        self.checkbox_way.setChecked(True)
        self.checkbox_relation.setChecked(True)
        self.spin_place_qq.setValue(1000)
        self.spin_timeout.setValue(25)

        # Query
        self.text_query.setText('')
        self.edit_csv_points.setText('')
        self.edit_csv_lines.setText('')
        self.edit_csv_multilinestrings.setText('')
        self.edit_csv_multipolygons.setText('')

        # OSM File
        self.osm_file.lineEdit().setText('')
        self.osm_conf.lineEdit().setText('')
        self.combo_preset_f.setCurrentIndex(0)
        self.table_keys_values_f.setRowCount(1)
        self.table_keys_values_f.cellWidget(0, 1).setCurrentIndex(0)
        self.table_keys_values_f.cellWidget(0, 2).lineEdit().setText('')

        # Query type
        for q_type in self.query_type_buttons.values():
            q_type.setCurrentIndex(0)

        # Place nominatim
        for edit in self.places_edits.values():
            edit.setText('')

        # Option selected features
        for option in self.selection_features.values():
            option.setChecked(False)

        # Output layers
        for panel in self.output_buttons.values():
            for output in panel:
                output.setChecked(True)

        # Directories
        for edit in self.output_directories.values():
            if edit:
                edit.lineEdit().setText('')

        # Prefix
        for edit in self.prefix_edits.values():
            if edit:
                edit.setText('')

    def set_progress_percentage(self, percent: int):
        """Slot to update percentage during process."""
        self.progress_bar.setValue(percent)
        QApplication.processEvents()

    def set_progress_text(self, text: str):
        """Slot to update text during process."""
        self.progress_text.setText(text)
        QApplication.processEvents()
