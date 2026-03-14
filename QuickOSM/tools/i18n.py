"""I18n tools."""

from os.path import join

from qgis.PyQt.QtCore import QLocale, QFileInfo
from qgis.PyQt.QtWidgets import QApplication
from qgis.core import QgsSettings

from QuickOSM.tools.resources import resources_path


def setup_translation(file_pattern="{}.qm", folder=None):
    """Find the translation file according to locale.

    :param file_pattern: Custom file pattern to use to find QM files.
    :type file_pattern: basestring

    :param folder: Optional folder to look in if it's not the default.
    :type folder: basestring

    :return: The locale and the file path to the QM file, or None.
    :rtype: (basestring, basestring)
    """
    locale = QgsSettings().value("locale/userLocale", QLocale().name())

    if folder:
        ts_file = QFileInfo(join(folder, file_pattern.format(locale)))
    else:
        ts_file = QFileInfo(resources_path("i18n", file_pattern.format(locale)))
    if ts_file.exists():
        return locale, ts_file.absoluteFilePath()

    if folder:
        ts_file = QFileInfo(join(folder, file_pattern.format(locale[0:2])))
    else:
        ts_file = QFileInfo(resources_path("i18n", file_pattern.format(locale[0:2])))
    if ts_file.exists():
        return locale, ts_file.absoluteFilePath()

    return locale, None


def tr(text, context="@default"):
    return QApplication.translate(context, text)
