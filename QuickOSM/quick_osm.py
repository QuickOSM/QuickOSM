"""QuickOSM main entry point for setting up the UI, Processing."""

import logging
import os
import shutil

from os.path import join

from qgis.core import QgsApplication, QgsZipUtils
from qgis.PyQt.QtCore import QCoreApplication, QTranslator, QUrl
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import (
    QAction,
    QDialog,
    QMenu,
    QMessageBox,
    QPushButton,
)

from QuickOSM.core.josm_remote import open_extent
from QuickOSM.core.utilities.tools import (
    check_processing_enable,
    get_setting,
    set_setting,
)
from QuickOSM.core.utilities.utilities_qgis import open_webpage
from QuickOSM.definitions.urls import DOC_PLUGIN_URL
from QuickOSM.tools.custom_logging import setup_logger
from QuickOSM.tools.i18n import setup_translation, tr
from QuickOSM.tools.resources import (
    plugin_name,
    plugin_path,
    resources_path,
)
from QuickOSM.tools.version import version
from QuickOSM.quick_osm_processing.provider import Provider


LOGGER = logging.getLogger('QuickOSM')


class QuickOSMPlugin:
    """Plugin QuickOSM."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        setup_logger(plugin_name())

        locale, file_path = setup_translation(
            folder=plugin_path("i18n"), file_pattern="quickosm_{}.qm")
        if file_path:
            # LOGGER.info('Translation to {}'.format(file_path))
            self.translator = QTranslator()
            self.translator.load(file_path)
            QCoreApplication.installTranslator(self.translator)
        else:
            # LOGGER.info('Translation not found: {}'.format(locale))
            pass

        self.extract_zip_file()

        self.provider = None

        self.toolbar = None
        self.help_action = None
        self.quickosm_menu = None
        self.vector_menu = None
        self.main_window_action = None
        self.josm_action = None

    @staticmethod
    def extract_zip_file():
        """ Extract or not the ZIP resources/i18n. """
        # resources/i18n is created with plugin installation

        preset_translation_path = join(resources_path(), 'i18n')
        version_file_translation_path = join(resources_path(), 'i18n', 'version.txt')
        version_file_presets = join(resources_path(), 'JOSM_preset', 'version.txt')
        if os.path.exists(preset_translation_path) and not os.path.exists(version_file_translation_path):
            # Legacy before 2.1.0
            shutil.rmtree(preset_translation_path)
            LOGGER.info('The version does not exist in the i18n folder, the folder needs to be unzipped.')

        if os.path.isdir(preset_translation_path) and os.path.isfile(version_file_translation_path):
            with open(version_file_translation_path, encoding='utf8') as check:
                old_version = check.read().strip()

            with open(version_file_presets, encoding='utf8') as expected:
                new_version = expected.read().strip()

            if old_version != new_version:
                # The folder needs to be unzipped again
                shutil.rmtree(preset_translation_path)
                LOGGER.info(
                    f'The version does not match in the i18n folder, the folder needs to be unzipped : '
                    f'old version {old_version} versus {new_version}'
                )

        if not os.path.isdir(preset_translation_path):
            if os.path.isfile(preset_translation_path + '.zip'):
                result = QgsZipUtils.unzip(preset_translation_path + '.zip', resources_path())
                if not result[0]:
                    os.mkdir(preset_translation_path)
                else:
                    LOGGER.info('Preset translations have been loaded and unzipped.')
                    files = os.listdir(preset_translation_path)
                    for file in files:
                        try:
                            file_path = join(preset_translation_path, file)
                            if '-r' in file:
                                new_file_path = join(preset_translation_path, file.replace('-r', '_'))
                                if not os.path.isfile(new_file_path):
                                    # Ticket #418
                                    os.rename(file_path, new_file_path)
                            elif '-' in file:
                                new_file_path = join(preset_translation_path, file.replace('-', '_'))
                                if not os.path.isfile(new_file_path):
                                    # Ticket #418
                                    os.rename(file_path, new_file_path)
                        except FileExistsError:
                            LOGGER.critical(
                                f'Error about existing file when extracting the ZIP file about {file}')
            else:
                os.mkdir(preset_translation_path)

    # noinspection PyPep8Naming
    def initProcessing(self):
        """Init Processing provider for QGIS >= 3.8."""
        self.provider = Provider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    # noinspection PyPep8Naming
    def initGui(self):
        """Init the user interface."""
        self.initProcessing()

        icon = QIcon(resources_path('icons', 'QuickOSM.svg'))

        self.help_action = QAction(icon, 'QuickOSM', self.iface.mainWindow())
        self.iface.pluginHelpMenu().addAction(self.help_action)
        self.help_action.triggered.connect(self.show_help)

        # Add the toolbar
        self.toolbar = self.iface.addToolBar('QuickOSM')
        self.toolbar.setObjectName('QuickOSM')

        # Setup menu
        self.quickosm_menu = QMenu('QuickOSM')
        self.quickosm_menu.setIcon(icon)
        self.vector_menu = self.iface.vectorMenu()
        self.vector_menu.addMenu(self.quickosm_menu)

        # Main window
        self.main_window_action = QAction(icon, 'QuickOSM…', self.iface.mainWindow())
        # noinspection PyUnresolvedReferences
        self.main_window_action.triggered.connect(self.open_dialog)
        self.toolbar.addAction(self.main_window_action)

        # Action JOSM
        self.josm_action = QAction(
            QIcon(resources_path('icons', 'josm_icon.svg')),
            tr('JOSM Remote'),
            self.iface.mainWindow())
        self.josm_action.triggered.connect(self.josm_remote)
        self.toolbar.addAction(self.josm_action)

        # Insert in the good order
        self.quickosm_menu.addAction(self.main_window_action)
        self.quickosm_menu.addAction(self.josm_action)

        LOGGER.info(f"Plugin loaded with version : {version()}")

    def unload(self):
        """Unload the user interface."""
        self.iface.removePluginVectorMenu('&QuickOSM', self.main_window_action)
        self.iface.removeToolBarIcon(self.main_window_action)
        QgsApplication.processingRegistry().removeProvider(self.provider)

        if self.help_action:
            self.iface.pluginHelpMenu().removeAction(self.help_action)
            del self.help_action

    @staticmethod
    def show_help():
        """Open the help web page"""
        QDesktopServices.openUrl(QUrl(DOC_PLUGIN_URL))

    def josm_remote(self):
        """Call the JOSM remote control using the current canvas extent."""
        map_settings = self.iface.mapCanvas().mapSettings()
        title = tr('JOSM Remote')
        if open_extent(map_settings.extent(), map_settings.destinationCrs()):
            self.iface.messageBar().pushSuccess(title, tr('Import done, check JOSM.'))
        else:
            self.iface.messageBar().pushCritical(title, tr('Is the remote enabled in the JOSM settings?'))

    def open_dialog(self):
        """Create and open the main dialog."""
        # Check if Processing is enabled
        # https://github.com/QuickOSM/QuickOSM/issues/352
        # https://github.com/QuickOSM/QuickOSM/issues/422
        flag, title, error = check_processing_enable()
        if not flag:
            error_dialog = QMessageBox(
                QMessageBox.Icon.Critical, title, error, QMessageBox.StandardButton.Ok, self.iface.mainWindow())
            error_dialog.exec()
            return

        from QuickOSM.ui.dialog import Dialog
        dialog = Dialog()
        self.open_copyright_message(dialog)
        dialog.exec()

    @staticmethod
    def open_copyright_message(dialog: QDialog):
        """Display a window to bring a reminder of the OSM copyrights."""

        def read_copyright():
            open_webpage('https://www.openstreetmap.org/copyright')
            set_setting("copyright_dialog", "OpenStreetMap")

        def know_copyright():
            set_setting("copyright_dialog", "OpenStreetMap")

        if not get_setting("copyright_dialog"):

            message = QMessageBox(dialog)
            text = tr(
                'OpenStreetMap® is open data, licensed under the'
                ' Open Data Commons Open Database License (ODbL) '
                'by the OpenStreetMap Foundation.'
            ) + '\n'
            text += tr(
                'The Foundation requires that you use the credit '
                '“© OpenStreetMap contributors” on any product using OSM data.'
            ) + '\n'
            text += tr(
                'You should read https://www.openstreetmap.org/copyright'
            )
            message.setText(text)
            message.setIcon(QMessageBox.Icon.Question)
            no_button = QPushButton(tr('I understand the copyrights, access to the plugin'), message)
            yes_button = QPushButton(tr('I want to read the copyrights'), message)
            message.addButton(no_button, QMessageBox.ButtonRole.NoRole)
            message.addButton(yes_button, QMessageBox.ButtonRole.YesRole)
            yes_button.clicked.connect(read_copyright)
            no_button.clicked.connect(know_copyright)
            message.exec()

    @staticmethod
    def run_tests():
        """Run the test inside QGIS."""
        try:
            from pathlib import Path

            from QuickOSM.qgis_plugin_tools.infrastructure.test_runner import (
                test_package,
            )
            test_package(f'{Path(__file__).parent.name}.__init__')
        except (AttributeError, ModuleNotFoundError):
            message = 'Could not load tests. Are you using a production package?'
            print(message)
            LOGGER.debug(message)
