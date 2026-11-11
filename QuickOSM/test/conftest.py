"""Pytest configuration: start a QGIS application before the tests are collected.

Previously, tests were launched inside QGIS by qgis_testrunner.sh, which provided
a real iface, the Processing plugin and the QuickOSM plugin loaded. With pytest,
we need to set up this environment ourselves.
"""

from unittest import mock

import qgis.utils

from qgis.core import QgsCoordinateReferenceSystem, QgsRectangle
from qgis.gui import QgsMapCanvas
from qgis.PyQt.QtCore import QObject
from qgis.testing import start_app

QGIS_APP = start_app()


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

Processing.initialize()
# QuickOSM checks that the Processing plugin is enabled.
qgis.utils.plugins.setdefault('processing', mock.MagicMock())

from qgis.core import QgsApplication  # noqa: E402

from QuickOSM.quick_osm_processing.provider import Provider  # noqa: E402

# Keep a reference, otherwise the Python object is garbage collected
# and the provider loses its id and its algorithms.
PROVIDER = Provider()
QgsApplication.processingRegistry().addProvider(PROVIDER)
