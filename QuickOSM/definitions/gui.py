"""Definitions for GUI concepts."""

from enum import Enum, unique


@unique
class Panels(Enum):
    """Name of panels in the GUI."""
    MapPreset = 'MapPreset'
    """Map preset"""

    QuickQuery = 'QuickQuery'
    """QuickQuery"""

    Query = 'Query'
    """Query"""

    File = 'File'
    """File"""

    Configuration = 'Configuration'
    """Configuration"""
