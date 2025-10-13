"""Pipeline components for AO system timing estimation."""

from daolite.pipeline.centroider import (
    Centroid,
    ReferenceSlopes,
    Error,
    Centroider,
)
from daolite.pipeline.extended_source_centroider import (
    CrossCorrelate,
    SquareDiff,
    ExtendedSourceCentroider,
)
from daolite.pipeline.descramble import Descramble
from daolite.pipeline.reconstruction import FullFrameReconstruction, Reconstruction
from daolite.pipeline.control import (
    Integrator,
    Offset,
    Saturation,
    DMPower,
    FullFrameControl,
)
from daolite.pipeline.pipeline import Pipeline, PipelineComponent

__all__ = [
    # Point source centroiding
    "Centroid",
    "ReferenceSlopes",
    "Error",
    "Centroider",
    # Extended source centroiding
    "CrossCorrelate",
    "SquareDiff",
    "ExtendedSourceCentroider",
    # Pixel descrambling
    "Descramble",
    # Reconstruction
    "FullFrameReconstruction",
    "Reconstruction",
    # Control
    "Integrator",
    "Offset",
    "Saturation",
    "DMPower",
    "FullFrameControl",
    # Pipeline
    "Pipeline",
    "PipelineComponent",
]
