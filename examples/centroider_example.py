# Example: Centroiding only
import numpy as np

from daolite.compute import hardware
from daolite.pipeline.centroider import Centroider

start_times = np.array(
    [
        [500.0, 677.776],
        [677.776, 855.552],
        [855.552, 1033.328],
        [1033.328, 1211.104],
        [1211.104, 1388.88],
        [1388.88, 1566.656],
        [1566.656, 1744.432],
        [1744.432, 1922.208],
        [1922.208, 2099.984],
        [2099.984, 2277.76],
    ]
)

# Create centroid agenda - 100 subapertures per iteration
centroid_agenda = np.ones(10, dtype=int) * 100

result = Centroider(
    compute_resources=hardware.amd_epyc_7763(),
    start_times=start_times,
    centroid_agenda=centroid_agenda,
    n_pix_per_subap=16,
)
print("Centroiding timing:", result)
