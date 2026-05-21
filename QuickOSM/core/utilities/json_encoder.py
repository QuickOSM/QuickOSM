"""Modify an json encoder/decoder to accept enum."""

import json

from qgis.core import QgsRectangle

from QuickOSM.definitions.format import Format
from QuickOSM.definitions.osm import LayerType, MultiType


class EnumEncoder(json.JSONEncoder):
    """Override the json encoder to serialize enum."""
    def default(self, obj):
        """Function of serialization."""
        if isinstance(obj, (LayerType, Format, MultiType)):
            return {"__enum__": str(obj)}
        if isinstance(obj, QgsRectangle):
            extent = [
                str(obj.xMinimum()), str(obj.yMinimum()),
                str(obj.xMaximum()), str(obj.yMaximum())
            ]
            return {"__extent__": ' '.join(extent)}
        return json.JSONEncoder.default(self, obj)


def as_enum(d):
    """Retrieval of enum from deserialization of a json file."""
    if "__enum__" in d:
        name, member = d["__enum__"].split(".")
        if name == 'LayerType':
            return getattr(LayerType, member)
        if name == 'Format':
            return getattr(Format, member)
        if name == 'MultiType':
            return getattr(MultiType, member)
    if "__extent__" in d:
        extent = d["__extent__"].split(' ')
        return QgsRectangle(
            float(extent[0]), float(extent[1]),
            float(extent[2]), float(extent[3])
        )

    return d
