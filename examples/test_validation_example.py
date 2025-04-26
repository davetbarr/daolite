# Example: Validate/test pipeline component output
from daolite.simulation.camera import PCOCamLink
from daolite.compute import create_compute_resources_from_system
import numpy as np

comp = create_compute_resources_from_system()
output = PCOCamLink(n_pixels=128 * 128, group=4, compute_resources=comp)
assert np.all(output > 0), "Timing should be positive"
print("Test passed. Output:", output)
