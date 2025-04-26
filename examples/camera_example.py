# Example: Camera simulation only
from daolite.compute import create_compute_resources
from daolite.simulation.camera import PCOCamLink

compute = create_compute_resources(
    cores=8,
    core_frequency=2.5e9,
    flops_per_cycle=16,
    memory_channels=2,
    memory_width=64,
    memory_frequency=2400e6,
    network_speed=25e9,
    time_in_driver=10,
)

result = PCOCamLink(compute, n_pixels=512 * 512, group=10)
print("Camera simulation timing:", result)
