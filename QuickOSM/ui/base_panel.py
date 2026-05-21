"""Panel core base class."""
from typing import List, Optional

from qgis.PyQt.QtWidgets import QDialog

from QuickOSM.definitions.gui import Panels


class BasePanel:

    """Base panel for QuickOSM dialog.

    This is a kind of virtual class.
    """

    def __init__(self, dialog: QDialog):
        self._panel: Optional[str] = None
        self._dialog = dialog

    @property
    def panel(self) -> Panels:
        """Return the panel."""
        if self._panel:
            return self._panel
        raise NotImplementedError

    @panel.setter
    def panel(self, panel: str):
        self._panel = panel

    @property
    def dialog(self) -> QDialog:
        """Return the dialog.

        :rtype: QDialog
        """
        return self._dialog

    def setup_panel(self):
        """Set up the UI for the panel."""
        raise NotImplementedError

    @staticmethod
    def filter_file_names(file_name: str, files_qml: List[str]) -> List[str]:
        """ Filter all QML files. """
        files = []
        for qml_file in files_qml:
            if qml_file.startswith(file_name):
                files.append(qml_file)
        return files
