"""Definitions for action visibilities."""

from enum import Enum, unique


@unique
class Visibility(Enum):
    """Visibility of actions."""
    Canvas = 'Canvas'
    """Canvas"""

    Feature = 'Feature'
    """Feature"""

    Field = 'Field'
    """Field"""

    Layer = 'Layer'
    """Field"""


@unique
class SaveType(Enum):
    """Type of save for saving a query."""
    New = 'Create new'
    """Create a new query"""

    Existing = 'Add existing'
    """Edit an existing one"""
