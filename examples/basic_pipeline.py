# Basic AO pipeline using the Pipeline API
from daolite.pipeline.pipeline import Pipeline, PipelineComponent, ComponentType
from daolite.compute.compute_resources import hardware
from daolite.simulation.camera import PCOCamLink
from daolite.pipeline.centroider import Centroider
from daolite.pipeline.reconstruction import Reconstruction
from daolite.pipeline.control import FullFrameControl
from daolite.pipeline.calibration import PixelCalibration
import numpy as np

pipeline = Pipeline()

n_pixels = 1024 * 1024
n_subaps = 80 * 80
n_pix_per_subap = 16 * 16
n_valid_subaps = int(n_subaps * 0.8)
n_acts = 5000
n_groups = 50

centroid_agenda = np.ones(n_groups) * (n_valid_subaps / n_groups)

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
        params={"n_pixels": n_pixels, "group": n_groups},
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
            "n_valid_subaps": n_valid_subaps,
            "n_pix_per_subap": n_pix_per_subap,
            "agenda": centroid_agenda,  # Pass agenda as numpy array
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
            "n_slopes": n_valid_subaps * 2,
            "n_acts": n_acts,
            "agenda": centroid_agenda,  # Pass agenda as numpy array
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
