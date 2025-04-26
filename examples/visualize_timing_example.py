# Example: Generate and save a pipeline timing plot
from daolite.pipeline.pipeline import Pipeline, PipelineComponent, ComponentType
from daolite.simulation.camera import PCOCamLink
from daolite.compute import hardware


pipeline = Pipeline()
pipeline.add_component(
    PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=hardware.amd_epyc_7763(),
        function=PCOCamLink,
        params={"n_pixels": 256 * 256, "group": 5},
    )
)
pipeline.run()
pipeline.visualize(title="Timing Plot Example", save_path="timing_plot_example.png")
print("Timing plot saved as timing_plot_example.png")
