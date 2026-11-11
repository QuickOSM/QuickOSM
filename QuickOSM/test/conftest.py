"""Pytest configuration: set up QGIS before the tests are collected.

Tests can be launched:
* outside QGIS, with pytest: the QGIS application, a fake iface, Processing and
  the QuickOSM provider are set up here;
* inside QGIS Desktop, with `plugins['QuickOSM'].run_tests()`: the running
  application, iface and provider are reused.
"""

from unittest import mock

import qgis.utils

from qgis.core import (
    QgsApplication,
    QgsCoordinateReferenceSystem,
    QgsRectangle,
)
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QObject
from qgis.testing import start_app

if QgsApplication.instance() is None:
    QGIS_APP = start_app()
else:
    # Inside QGIS Desktop
    QGIS_APP = QgsApplication.instance()


class _FakeIface(QObject):
    """Stub of QgisInterface.

    It's a QObject, so it can be used as a parent for QActions, and any other
    attribute is a MagicMock, except the map canvas which must be a real one.
    """

    def __init__(self):
        super().__init__()
        self._canvas = QgsMapCanvas()
        self._canvas.setDestinationCrs(QgsCoordinateReferenceSystem('EPSG:4326'))
        self._canvas.setExtent(QgsRectangle(-180, -90, 180, 90))

    def mapCanvas(self):  # NOQA N802
        """Return the map canvas."""
        return self._canvas

    def __getattr__(self, name):
        value = mock.MagicMock(name=f'iface.{name}')
        setattr(self, name, value)
        return value


# Some modules import iface at import time,
# so it must be set before the test modules are collected.
if qgis.utils.iface is None:
    qgis.utils.iface = _FakeIface()

from processing.core.Processing import Processing  # noqa: E402

# It does nothing if Processing is already initialized.
Processing.initialize()
# QuickOSM checks that the Processing plugin is enabled.
qgis.utils.plugins.setdefault('processing', mock.MagicMock())

from QuickOSM.quick_osm_processing.provider import Provider  # noqa: E402

PROVIDER = None
if not QgsApplication.processingRegistry().providerById('quickosm'):
    # Keep a reference, otherwise the Python object is garbage collected
    # and the provider loses its id and its algorithms.
    PROVIDER = Provider()
    QgsApplication.processingRegistry().addProvider(PROVIDER)
