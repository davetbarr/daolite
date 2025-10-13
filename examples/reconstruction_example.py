# Example: Reconstruction only
from daolite.pipeline.reconstruction import Reconstruction
from daolite.compute import hardware
import numpy as np

start_times = np.zeros([1, 2])

# Create centroid agenda - 200 slopes (100 subapertures * 2 for X and Y)
centroid_agenda = np.array([200], dtype=int)

result = Reconstruction(
    compute_resources=hardware.amd_epyc_7763(),
    start_times=start_times,
    centroid_agenda=centroid_agenda,
    n_acts=500
)
print("Reconstruction timing:", result)
