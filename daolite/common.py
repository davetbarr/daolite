"""
Common definitions and base classes for daolite.
This module contains base classes and enums that are used throughout the daolite package.
Putting them here helps avoid circular imports.
"""

from enum import Enum, auto


class ComponentType(Enum):
    """Enum defining component types in an AO pipeline."""

    CAMERA = auto()
    CALIBRATION = auto()
    CENTROIDER = auto()
    RECONSTRUCTION = auto()
    CONTROL = auto()
    NETWORK = auto()
    DM = auto()  # Represents Deformable Mirror components (terminal pipeline points)
    OTHER = auto()


# Base type definitions to help avoid circular imports
ResourceId = str
ComponentId = str
