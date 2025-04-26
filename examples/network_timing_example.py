# Example: Model network/PCIe transfer timing
from daolite.compute import create_compute_resources
from daolite.utils.network import TimeOnNetwork, PCIE
import numpy as np

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

# Example: Ethernet/Network transfer timing
network_time = TimeOnNetwork(n_bits=1024*1024*8, compute_resources=compute)
print("Network transfer timing (1MB):", network_time)

# Example: PCIe transfer timing
start_times = np.zeros([1, 2])
pcie_time = PCIE(n_bits=1024*1024*8, compute_resources=compute, start_times=start_times)
print("PCIe transfer timing (1MB):", pcie_time)
