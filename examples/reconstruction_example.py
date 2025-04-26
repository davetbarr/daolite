# Example: Reconstruction only
from daolite.pipeline.reconstruction import Reconstruction
from daolite.compute import hardware
import numpy as np

start_times = np.zeros([1, 2])

result = Reconstruction(
    n_slopes=200, n_acts=500, compute_resources=hardware.amd_epyc_7763(), start_times=start_times
)
print("Reconstruction timing:", result)
