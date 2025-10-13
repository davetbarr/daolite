# Basic AO pipeline using the Pipeline API
import numpy as np

from daolite.compute.compute_resources import hardware
from daolite.pipeline.calibration import PixelCalibration
from daolite.pipeline.centroider import Centroider
from daolite.pipeline.control import FullFrameControl
from daolite.pipeline.pipeline import ComponentType, Pipeline, PipelineComponent
from daolite.pipeline.reconstruction import Reconstruction
from daolite.simulation.camera import PCOCamLink

pipeline = Pipeline()

n_pixels = 1024 * 1024
n_subaps = 80 * 80
n_pix_per_subap = 16 * 16
n_valid_subaps = int(n_subaps * 0.8)
n_acts = 5000
n_groups = 50

# Create agendas for the pipeline
pixel_agenda = np.ones(n_groups, dtype=int) * (n_pixels // n_groups)
centroid_agenda = np.ones(n_groups, dtype=int) * (n_valid_subaps // n_groups)

pipeline.add_component(
    PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=hardware.amd_epyc_7763(),
        function=PCOCamLink,
        params={"n_pixels": n_pixels, "group": n_groups},
    )
)

pipeline.add_component(
    PipelineComponent(
        component_type=ComponentType.CALIBRATION,
        name="Calibration",
        compute=hardware.amd_epyc_7763(),
        function=PixelCalibration,
        params={"pixel_agenda": pixel_agenda},
        dependencies=["Camera"],
    )
)

pipeline.add_component(
    PipelineComponent(
        component_type=ComponentType.CENTROIDER,
        name="Centroider",
        compute=hardware.nvidia_rtx_4090(),
        function=Centroider,
        params={
            "centroid_agenda": centroid_agenda,
            "n_pix_per_subap": n_pix_per_subap,
        },
        dependencies=["Calibration"],
    )
)
pipeline.add_component(
    PipelineComponent(
        component_type=ComponentType.RECONSTRUCTION,
        name="Reconstructor",
        compute=hardware.nvidia_rtx_4090(),
        function=Reconstruction,
        params={
            "centroid_agenda": centroid_agenda,
            "n_acts": n_acts,
        },
        dependencies=["Centroider"],
    )
)
pipeline.add_component(
    PipelineComponent(
        component_type=ComponentType.CONTROL,
        name="DM Controller",
        compute=hardware.amd_epyc_7763(),
        function=FullFrameControl,
        params={"n_acts": n_acts},
        dependencies=["Reconstructor"],
    )
)

results = pipeline.run(debug=True)
pipeline.visualize(
    title="Basic AO Pipeline Timing", save_path="basic_pipeline_timing.png"
)
