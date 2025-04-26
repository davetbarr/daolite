# Example: Create and use a custom compute resource
from daolite.compute import create_compute_resources
from daolite.pipeline.pipeline import Pipeline, PipelineComponent, ComponentType
from daolite.simulation.camera import PCOCamLink

custom_cpu = create_compute_resources(
    cores=16,
    core_frequency=2.5e9,
    flops_per_cycle=16,
    memory_channels=2,
    memory_width=64,
    memory_frequency=2400e6,
    network_speed=25e9,
    time_in_driver=10,
)

pipeline = Pipeline()
pipeline.add_component(
    PipelineComponent(
        component_type=ComponentType.CAMERA,
        name="Camera",
        compute=custom_cpu,
        function=PCOCamLink,
        params={"n_pixels": 512 * 512, "group": 10},
    )
)
results = pipeline.run(debug=True)
print("Custom resource timing:", results)
