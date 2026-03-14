"""Panel OSM Processing base class."""
from os.path import isdir

from qgis.core import QgsFeedback
from qgis.gui import QgsFileWidget
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QApplication, QDialog

from QuickOSM.core.exceptions import (
    DirectoryOutPutException,
    OutPutGeomTypesException,
    QuickOsmException,
)
from QuickOSM.definitions.format import Format
from QuickOSM.definitions.gui import Panels
from QuickOSM.definitions.osm import LayerType
from QuickOSM.tools.i18n import tr
from QuickOSM.ui.base_panel import BasePanel



class BaseProcessingPanel(BasePanel):

    """Base for processing panel.

    This panels will have a run button.

    This is a kind of virtual class.
    """

    def __init__(self, dialog: QDialog):
        super().__init__(dialog)

    def disable_enable_format_prefix(self):
        """Enable only if the directory is set."""
        boolean = not self.dialog.output_directories[self.panel].lineEdit().isNull()
        self.dialog.output_format[self.panel].setEnabled(boolean)
        self.dialog.prefix_edits[self.panel].setEnabled(boolean)

    def run(self):
        """Run the process"""
        self._start_process()
        try:
            self._run()
        except QuickOsmException as error:
            self.dialog.display_quickosm_exception(error)
        except Exception as error:
            self.dialog.display_critical_exception(error)
        finally:
            self._end_process()

    def run_saved_query(self, data: dict):
        """Run the process from a saved query."""
        self._start_process()
        try:
            self._run_saved_query(data)
        except QuickOsmException as error:
            self.dialog.display_quickosm_exception(error)
        except Exception as error:
            self.dialog.display_critical_exception(error)
        finally:
            self._end_process()

    def _run(self):
        raise NotImplementedError

    def _run_saved_query(self, data: dict):
        raise NotImplementedError

    def setup_panel(self):
        """Function to set custom UI for some panels."""
        if self.dialog.output_directories[self.panel]:
            self.dialog.output_directories[self.panel].lineEdit().setPlaceholderText(
                tr('Save to temporary file'))
            self.dialog.output_directories[self.panel].setStorageMode(
                QgsFileWidget.StorageMode.GetDirectory)
            self.dialog.output_directories[self.panel].setDialogTitle(tr('Select a directory'))

            self.dialog.output_format[self.panel].addItem(
                Format.GeoPackage.value.label, Format.GeoPackage)
            self.dialog.output_format[self.panel].addItem(
                Format.GeoJSON.value.label, Format.GeoJSON)
            self.dialog.output_format[self.panel].addItem(
                Format.Shapefile.value.label, Format.Shapefile)
            self.dialog.output_format[self.panel].addItem(
                Format.Kml.value.label, Format.Kml)

            self.dialog.output_directories[self.panel].lineEdit().textChanged.connect(
                self.disable_enable_format_prefix)
            self.disable_enable_format_prefix()

        self.dialog.execute_buttons[self.panel].setCurrentIndex(0)
        self.dialog.cancel_buttons[self.panel].clicked.connect(self.cancel_process)

        # def disable_prefix_file():
        #     # TODO
        #     def disable_prefix_file(directory, file_prefix):
        #         """If the directory is empty, we disable the file prefix."""
        #         if directory.filePath():
        #             file_prefix.setDisabled(False)
        #         else:
        #             file_prefix.setText('')
        #             file_prefix.setDisabled(True)
        #
        # self.output_directories[panel].fileChanged.connect(
        #    disable_prefix_file)

    def _start_process(self):
        """Make some stuff before launching the process."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        self.dialog.feedback_process = QgsFeedback()

        if self.panel == Panels.QuickQuery:
            self.dialog.button_show_query.setDisabled(True)

        if self.panel == Panels.Query:
            self.dialog.button_generate_query.setDisabled(True)

        self.dialog.execute_buttons[self.panel].setCurrentIndex(1)
        if self.dialog.output_directories[self.panel]:
            self.dialog.output_directories[self.panel].setDisabled(True)
        self.dialog.progress_bar.setMinimum(0)
        self.dialog.progress_bar.setMaximum(0)
        self.dialog.progress_bar.setValue(0)
        self.dialog.progress_text.setText('')
        QApplication.processEvents()

    def _end_process(self):
        """Make some stuff after the process."""
        QApplication.restoreOverrideCursor()

        if self.panel == Panels.QuickQuery:
            self.dialog.button_show_query.setDisabled(False)

        if self.panel == Panels.Query:
            self.dialog.button_generate_query.setDisabled(False)

        if self.dialog.output_directories[self.panel]:
            self.dialog.output_directories[self.panel].setDisabled(False)
            self.disable_enable_format_prefix()
        self.dialog.execute_buttons[self.panel].setCurrentIndex(0)
        self.dialog.progress_bar.setMinimum(0)
        self.dialog.progress_bar.setMaximum(100)
        self.dialog.progress_bar.setValue(100)
        QApplication.processEvents()

    def cancel_process(self):
        """Cancel the process"""
        self.dialog.feedback_process.cancel()

    def gather_values(self):
        """Retrieval of the values set by the user."""
        properties = dict()

        # For all queries
        properties['outputs'] = []
        if self.dialog.output_buttons[self.panel][0].isChecked():
            # noinspection PyTypeChecker
            properties['outputs'].append(LayerType.Points)
        if self.dialog.output_buttons[self.panel][1].isChecked():
            # noinspection PyTypeChecker
            properties['outputs'].append(LayerType.Lines)
        if self.dialog.output_buttons[self.panel][2].isChecked():
            # noinspection PyTypeChecker
            properties['outputs'].append(LayerType.Multilinestrings)
        if self.dialog.output_buttons[self.panel][3].isChecked():
            # noinspection PyTypeChecker
            properties['outputs'].append(LayerType.Multipolygons)

        if not properties['outputs']:
            raise OutPutGeomTypesException

        properties['output_directory'] = (
            self.dialog.output_directories[self.panel].filePath())
        properties['output_format'] = (
            self.dialog.output_format[self.panel].currentData())
        properties['prefix_file'] = self.dialog.prefix_edits[self.panel].text()

        if properties['output_directory'] and not (
                isdir(properties['output_directory'])):
            raise DirectoryOutPutException

        return properties
