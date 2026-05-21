"""A tool that enable to select or show an extent in the canvas."""
import logging

from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsPointXY,
    QgsProject,
    QgsRectangle,
    QgsWkbTypes,
)
from qgis.gui import QgsMapTool, QgsRubberBand
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtGui import QColor

LOGGER = logging.getLogger('QuickOSM')


class ShowExtent(QgsMapTool):
    """Show an extent in the canvas"""

    ShowEnded = pyqtSignal()

    def __init__(self, canvas):
        """Constructor"""
        QgsMapTool.__init__(self, canvas)

        self.canvas = canvas
        self.rubberBand = QgsRubberBand(self.canvas, QgsWkbTypes.GeometryType.PolygonGeometry)
        color = QColor(30, 230, 30, 65)
        self.rubberBand.setColor(color)
        self.rubberBand.setWidth(1)

        self.start_point = self.end_point = None

    def canvasPressEvent(self, event):
        """Change the outcome of the click event to end  the ongoing process."""
        _ = event
        self.rubberBand.hide()
        self.ShowEnded.emit()

    def show_extent(self, extent: QgsRectangle):
        """Display the extent on the canvas"""
        self.start_point = QgsPointXY(extent.xMinimum(), extent.yMinimum())
        self.end_point = QgsPointXY(extent.xMaximum(), extent.yMaximum())
        self.transform_coordinates()

        self.rubberBand.reset(QgsWkbTypes.GeometryType.PolygonGeometry)

        point1 = QgsPointXY(self.start_point.x(), self.start_point.y())
        point2 = QgsPointXY(self.start_point.x(), self.end_point.y())
        point3 = QgsPointXY(self.end_point.x(), self.end_point.y())
        point4 = QgsPointXY(self.end_point.x(), self.start_point.y())

        self.rubberBand.addPoint(point1, False)
        self.rubberBand.addPoint(point2, False)
        self.rubberBand.addPoint(point3, False)
        self.rubberBand.addPoint(point4, True)
        self.rubberBand.show()

        rect = QgsRectangle(self.start_point, self.end_point)
        self.canvas.setExtent(rect)

    def transform_coordinates(self):
        """Transform the coordinates in 4326."""
        if self.start_point is None or self.end_point is None:
            return None
        if self.start_point.x() == self.end_point.x() or self.start_point.y() == self.end_point.y():
            return None

        # Defining the crs from src and destiny
        epsg = self.canvas.mapSettings().destinationCrs().authid()
        crs_dest = QgsCoordinateReferenceSystem(epsg)
        crs_src = QgsCoordinateReferenceSystem('EPSG:4326')

        # Creating a transformer
        transformer = QgsCoordinateTransform(crs_src, crs_dest, QgsProject.instance())

        # Transforming the points
        self.start_point = transformer.transform(self.start_point)
        self.end_point = transformer.transform(self.end_point)
