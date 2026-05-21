from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsNetworkAccessManager,
    QgsProject,
    QgsRectangle,
)
from qgis.PyQt.QtCore import QUrl
from qgis.PyQt.QtNetwork import QNetworkReply, QNetworkRequest

URL = "http://localhost:8111"


def open_object(object_id: str) -> bool:
    """ Open the given OSM object in JOSM. """
    return _josm_request(f"load_object?objects={object_id}")


def open_extent(extent: QgsRectangle, crs_map: QgsCoordinateReferenceSystem) -> bool:
    """ Open the given extent in JOSM. """
    if crs_map.authid() != 'EPSG:4326':
        crs_4326 = QgsCoordinateReferenceSystem("EPSG:4326")
        transform = QgsCoordinateTransform(crs_map, crs_4326, QgsProject.instance())
        extent = transform.transform(extent)

    url = (
        f'load_and_zoom?'
        f'left={extent.xMinimum()}&right={extent.xMaximum()}&'
        f'top={extent.yMaximum()}&bottom={extent.yMinimum()}'
    )

    return _josm_request(url)


def _josm_request(request_url: str) -> bool:
    """ Do the request to JOSM. """
    request = QNetworkRequest()
    # noinspection PyArgumentList
    request.setUrl(QUrl(f"{URL}/{request_url}"))
    # noinspection PyArgumentList
    reply: QNetworkReply = QgsNetworkAccessManager.instance().get(request)
    return reply.error() == QNetworkReply.NetworkError.NoError
